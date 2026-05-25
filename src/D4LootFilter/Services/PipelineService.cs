using System.Drawing;
using D4LootFilter.Capture;
using D4LootFilter.Matching;
using D4LootFilter.Matching.Models;
using D4LootFilter.Ocr;
using D4LootFilter.Overlay;
using OpenCvSharp;

namespace D4LootFilter.Services;

public class PipelineService : IDisposable
{
    private readonly DxgiCapture _capture;
    private readonly TesseractOcrEngine _ocr;
    private readonly AffixMatcher _matcher;
    private readonly SlotDetector _slotDetector;
    private readonly FrameChangeDetector _changeDetector;
    private readonly TooltipDetector _tooltipDetector;
    private readonly AffixNormalizer _normalizer;
    private readonly OverlayViewModel _overlayVm;
    private readonly ProfileService _profileService;
    private readonly FileLogger _log;

    private CancellationTokenSource? _cts;
    private Task? _captureTask;
    private OpenCvSharp.Rect _captureRegion;
    private int _pollingDelayMs = 33;
    private string? _debugDir;
    private int _debugSaveCount;

    public PipelineService(
        OverlayViewModel overlayVm,
        ProfileService profileService,
        string tessdataPath,
        FileLogger logger)
    {
        _capture = new DxgiCapture();
        _ocr = new TesseractOcrEngine(tessdataPath);
        _matcher = new AffixMatcher(maxDistance: 2);
        _slotDetector = new SlotDetector();
        _changeDetector = new FrameChangeDetector();
        _tooltipDetector = new TooltipDetector();
        _normalizer = new AffixNormalizer();
        _overlayVm = overlayVm;
        _profileService = profileService;
        _log = logger;
        _debugDir = System.IO.Path.Combine(AppContext.BaseDirectory, "debug");
        System.IO.Directory.CreateDirectory(_debugDir);
    }

    public void SetCaptureRegion(int x, int y, int width, int height)
    {
        _captureRegion = new OpenCvSharp.Rect(x, y, width, height);
    }

    public void UseFullScreen()
    {
        _captureRegion = new OpenCvSharp.Rect(0, 0, _capture.ScreenWidth, _capture.ScreenHeight);
    }

    public void Start()
    {
        _cts = new CancellationTokenSource();
        _captureTask = Task.Factory.StartNew(
            () => CaptureLoop(_cts.Token),
            _cts.Token,
            TaskCreationOptions.LongRunning,
            TaskScheduler.Default
        );
    }

    public void Stop()
    {
        _cts?.Cancel();
        _captureTask?.Wait(TimeSpan.FromSeconds(2));
    }

    private void CaptureLoop(CancellationToken ct)
    {
        int noTooltipFrames = 0;
        int frameCount = 0;
        int changeCount = 0;

        _log.Log($"Pipeline started. Screen: {_capture.ScreenWidth}x{_capture.ScreenHeight}");
        _log.Log($"Capture region: ({_captureRegion.X},{_captureRegion.Y}) {_captureRegion.Width}x{_captureRegion.Height}");

        while (!ct.IsCancellationRequested)
        {
            try
            {
                using var fullFrame = _capture.CaptureFrame(timeoutMs: 100);
                if (fullFrame == null)
                {
                    Thread.Sleep(_pollingDelayMs);
                    continue;
                }

                frameCount++;
                var isFullScreen = _captureRegion.Width >= _capture.ScreenWidth && _captureRegion.Height >= _capture.ScreenHeight;
                using var regionFrame = isFullScreen ? fullFrame : ImagePreprocessor.CropRegion(fullFrame, _captureRegion);

                changeCount++;
                if (changeCount % 300 == 1)
                    _log.Log($"Scanning frame {frameCount} (check #{changeCount})");

                var tooltipBounds = _tooltipDetector.DetectTooltipBounds(regionFrame);
                if (tooltipBounds == null)
                {
                    noTooltipFrames++;
                    if (noTooltipFrames > 3)
                    {
                        System.Windows.Application.Current?.Dispatcher.Invoke(() => _overlayVm.Hide());
                        noTooltipFrames = 0;
                    }
                    Thread.Sleep(_pollingDelayMs);
                    continue;
                }

                var tb = tooltipBounds.Value;

                noTooltipFrames = 0;

                using var tooltip = ImagePreprocessor.CropRegion(regionFrame, tb);
                using var preprocessed = ImagePreprocessor.Preprocess(tooltip);

                if (_debugSaveCount < 10 && _debugDir != null)
                {
                    var prefix = System.IO.Path.Combine(_debugDir, $"frame{_debugSaveCount:D2}");
                    Cv2.ImWrite($"{prefix}_tooltip.png", tooltip);
                    Cv2.ImWrite($"{prefix}_preprocessed.png", preprocessed);
                    _debugSaveCount++;
                    _log.Log($"Saved debug images: {prefix}_*.png");
                }

                var ocrLines = _ocr.ExtractLines(preprocessed);

                if (ocrLines.Count == 0)
                {
                    Thread.Sleep(_pollingDelayMs);
                    continue;
                }

                var allText = string.Join(" ", ocrLines.Select(l => l.Text));
                var isItemTooltip = allText.Contains("Item Power", StringComparison.OrdinalIgnoreCase)
                    || allText.Contains("Requires Level", StringComparison.OrdinalIgnoreCase)
                    || allText.Contains("Sell Value", StringComparison.OrdinalIgnoreCase);

                if (!isItemTooltip)
                {
                    Thread.Sleep(_pollingDelayMs);
                    continue;
                }

                _log.Log($"ITEM TOOLTIP detected at ({tb.X},{tb.Y}) {tb.Width}x{tb.Height}");
                _log.Log($"OCR: {ocrLines.Count} lines");
                foreach (var line in ocrLines)
                    _log.Log($"  [{line.Confidence:F0}%] {line.Text}");

                var profile = _profileService.ActiveProfile;
                var variant = profile?.GetActiveVariant();
                if (variant == null)
                {
                    Thread.Sleep(_pollingDelayMs);
                    continue;
                }

                var textLines = ocrLines.Select(l => l.Text).ToArray();
                var slot = _slotDetector.DetectSlot(textLines);
                var buildAffixes = slot != null
                    ? variant.GetAffixesForSlot(slot)
                    : variant.GetAllAffixes();

                _log.Log($"Slot: {slot ?? "unknown"}, build affixes for slot: {buildAffixes.Count}");

                if (buildAffixes.Count == 0)
                {
                    Thread.Sleep(_pollingDelayMs);
                    continue;
                }

                var affixLines = textLines.Where(l => _normalizer.IsLikelyAffix(l)).ToArray();
                var results = _matcher.Match(affixLines, buildAffixes);
                var summary = AffixMatcher.Summarize(results, buildAffixes);

                _log.Log($"Match: {summary.MatchedCount}/{summary.TotalBuildAffixes}, GA: {summary.GaMatchedCount}");
                foreach (var r in results.Where(r => r.IsMatched))
                    _log.Log($"  ✓ {r.AffixName}{(r.IsGa ? " [GA]" : "")}");
                if (summary.MissingAffixes.Count > 0)
                    _log.Log($"  Missing: {string.Join(", ", summary.MissingAffixes)}");

                var captureRect = new Rectangle(
                    _captureRegion.X + tb.X,
                    _captureRegion.Y + tb.Y,
                    tb.Width,
                    tb.Height
                );
                var boundingBoxes = ocrLines
                    .Where(l => _normalizer.IsLikelyAffix(l.Text))
                    .Select(l => l.BoundingBox)
                    .ToList();

                System.Windows.Application.Current?.Dispatcher.Invoke(() =>
                {
                    _overlayVm.Update(results, summary, profile!.Name, slot ?? "Unknown", captureRect, boundingBoxes);
                });
            }
            catch (Exception ex)
            {
                _log.Log($"ERROR: {ex.GetType().Name}: {ex.Message}");
            }

            Thread.Sleep(_pollingDelayMs);
        }

        _log.Log("Pipeline stopped");
    }

    public void Dispose()
    {
        Stop();
        _capture.Dispose();
        _ocr.Dispose();
    }
}
