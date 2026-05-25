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

    private CancellationTokenSource? _cts;
    private Task? _captureTask;
    private OpenCvSharp.Rect _captureRegion;
    private int _pollingDelayMs = 33; // ~30fps

    public PipelineService(
        OverlayViewModel overlayVm,
        ProfileService profileService,
        string tessdataPath)
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
    }

    public void SetCaptureRegion(int x, int y, int width, int height)
    {
        _captureRegion = new OpenCvSharp.Rect(x, y, width, height);
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

                using var regionFrame = ImagePreprocessor.CropRegion(fullFrame, _captureRegion);
                if (!_changeDetector.HasChanged(regionFrame))
                {
                    Thread.Sleep(_pollingDelayMs);
                    continue;
                }

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

                noTooltipFrames = 0;

                using var tooltip = ImagePreprocessor.CropRegion(regionFrame, tooltipBounds.Value);
                using var preprocessed = ImagePreprocessor.Preprocess(tooltip);
                var ocrLines = _ocr.ExtractLines(preprocessed);

                if (ocrLines.Count == 0)
                {
                    Thread.Sleep(_pollingDelayMs);
                    continue;
                }

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

                if (buildAffixes.Count == 0)
                {
                    Thread.Sleep(_pollingDelayMs);
                    continue;
                }

                var affixLines = textLines.Where(l => _normalizer.IsLikelyAffix(l)).ToArray();
                var results = _matcher.Match(affixLines, buildAffixes);
                var summary = AffixMatcher.Summarize(results, buildAffixes);

                var captureRect = new Rectangle(
                    _captureRegion.X + tooltipBounds.Value.X,
                    _captureRegion.Y + tooltipBounds.Value.Y,
                    tooltipBounds.Value.Width,
                    tooltipBounds.Value.Height
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
            catch (Exception)
            {
                // Swallow capture errors, continue loop
            }

            Thread.Sleep(_pollingDelayMs);
        }
    }

    public void Dispose()
    {
        Stop();
        _capture.Dispose();
        _ocr.Dispose();
    }
}
