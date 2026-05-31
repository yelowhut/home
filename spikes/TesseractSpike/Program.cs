using OpenCvSharp;
using Tesseract;
using Page = Tesseract.Page;

const string imagePath = @"D:\git\home\img.png";
const string tessdataPath = @"D:\git\home\spikes\TesseractSpike\tessdata";
const string debugDir = @"D:\git\home\spikes\TesseractSpike\debug";

Directory.CreateDirectory(debugDir);

// ───────────────────────────────────────────────────────
// Step 1: Load image and report dimensions
// ───────────────────────────────────────────────────────
using var src = Cv2.ImRead(imagePath, ImreadModes.Color);
Console.WriteLine($"Source image: {src.Width}x{src.Height}");

// ───────────────────────────────────────────────────────
// Step 2: Crop the tooltip area (right portion of image)
// We crop the right ~25% which contains the item tooltip.
// Exclude the far-right character portrait (~5% width).
// ───────────────────────────────────────────────────────
int cropLeft = (int)(src.Width * 0.62);   // start of tooltip area
int cropRight = (int)(src.Width * 0.87);  // end before character portrait
int cropTop = (int)(src.Height * 0.03);
int cropBottom = (int)(src.Height * 0.85);

var tooltipRect = new OpenCvSharp.Rect(cropLeft, cropTop, cropRight - cropLeft, cropBottom - cropTop);
using var cropped = src[tooltipRect];
Cv2.ImWrite(Path.Combine(debugDir, "01_cropped.png"), cropped);
Console.WriteLine($"Cropped tooltip region: {cropped.Width}x{cropped.Height} (from x={cropLeft} to x={cropRight})");

// ───────────────────────────────────────────────────────
// Step 3: Preprocess
//   a) Upscale 2x BEFORE thresholding (more detail for Otsu)
//   b) Convert to grayscale
//   c) Apply Otsu's threshold
//   d) Invert (white text on dark -> black on white)
// ───────────────────────────────────────────────────────
using var upscaled = new Mat();
Cv2.Resize(cropped, upscaled, new OpenCvSharp.Size(cropped.Width * 2, cropped.Height * 2),
    interpolation: InterpolationFlags.Cubic);
Cv2.ImWrite(Path.Combine(debugDir, "02_upscaled.png"), upscaled);

using var gray = new Mat();
Cv2.CvtColor(upscaled, gray, ColorConversionCodes.BGR2GRAY);
Cv2.ImWrite(Path.Combine(debugDir, "03_gray.png"), gray);

using var thresh = new Mat();
Cv2.Threshold(gray, thresh, 0, 255, ThresholdTypes.Binary | ThresholdTypes.Otsu);
Cv2.ImWrite(Path.Combine(debugDir, "04_otsu.png"), thresh);

using var inverted = new Mat();
Cv2.BitwiseNot(thresh, inverted);
Cv2.ImWrite(Path.Combine(debugDir, "05_inverted.png"), inverted);

Console.WriteLine($"Preprocessed image: {inverted.Width}x{inverted.Height}");
Console.WriteLine();

// ───────────────────────────────────────────────────────
// Step 4: Run Tesseract with different PSM modes
// ───────────────────────────────────────────────────────
var psmModes = new[]
{
    (PageSegMode.SingleBlock, "PSM 6 - Uniform block of text"),
    (PageSegMode.SingleColumn, "PSM 4 - Single column of text"),
    (PageSegMode.SparseText, "PSM 11 - Sparse text"),
};

// Convert Mat to Pix for Tesseract
byte[] imageBytes = inverted.ToBytes(".png");

// Track per-mode stats
var modeStats = new Dictionary<string, (int total, int good, float meanConf)>();

foreach (var (psm, label) in psmModes)
{
    Console.WriteLine(new string('=', 70));
    Console.WriteLine($"  {label}");
    Console.WriteLine(new string('=', 70));

    using var engine = new TesseractEngine(tessdataPath, "eng", EngineMode.Default);
    using var pix = Pix.LoadFromMemory(imageBytes);
    using Page page = engine.Process(pix, psm);

    float meanConf = page.GetMeanConfidence();
    Console.WriteLine($"Mean confidence: {meanConf:P1}");
    Console.WriteLine();

    // Per-line iteration
    Console.WriteLine($"{"Line",-5} {"Conf",6}  Text");
    Console.WriteLine(new string('-', 70));

    int lineNum = 0;
    int totalLines = 0;
    int goodLines = 0;
    using var iter = page.GetIterator();
    iter.Begin();
    do
    {
        string? text = iter.GetText(PageIteratorLevel.TextLine);
        float conf = iter.GetConfidence(PageIteratorLevel.TextLine);

        if (string.IsNullOrWhiteSpace(text))
            continue;

        lineNum++;
        string trimmed = text.TrimEnd('\n', '\r', ' ');
        string quality = conf > 80 ? "OK" : conf > 50 ? "~~" : "XX";

        Console.WriteLine($"{lineNum,-5} {conf,5:F1}%  [{quality}] {trimmed}");

        totalLines++;
        if (conf > 70)
            goodLines++;
    } while (iter.Next(PageIteratorLevel.TextLine));

    modeStats[label] = (totalLines, goodLines, meanConf);

    Console.WriteLine();
    Console.WriteLine($"Total lines: {lineNum}, Mean confidence: {meanConf:P1}");
    double pct = totalLines > 0 ? (double)goodLines / totalLines * 100 : 0;
    Console.WriteLine($"Lines above 70% confidence: {goodLines}/{totalLines} ({pct:F0}%)");
    Console.WriteLine();
}

// ───────────────────────────────────────────────────────
// Step 5: Summary verdict (based on best PSM mode)
// ───────────────────────────────────────────────────────
Console.WriteLine(new string('=', 70));
Console.WriteLine("  SUMMARY - Comparison across PSM modes");
Console.WriteLine(new string('=', 70));

string bestLabel = "";
double bestPct = 0;
foreach (var (label, (total, good, meanConf)) in modeStats)
{
    double pct = total > 0 ? (double)good / total * 100 : 0;
    Console.WriteLine($"  {label}:");
    Console.WriteLine($"    Mean confidence: {meanConf:P1}");
    Console.WriteLine($"    Lines >70% conf: {good}/{total} ({pct:F0}%)");
    if (pct > bestPct || (pct == bestPct && meanConf > (modeStats.ContainsKey(bestLabel) ? modeStats[bestLabel].meanConf : 0)))
    {
        bestPct = pct;
        bestLabel = label;
    }
}

Console.WriteLine();
Console.WriteLine($"Best mode: {bestLabel} ({bestPct:F0}% of lines above 70% confidence)");
Console.WriteLine();

string verdict;
if (bestPct >= 70)
    verdict = "VIABLE for affix extraction. Numeric stats and affix names read correctly with " +
              $"{bestLabel}. Item-name headers using stylized glyphs (e.g. LORD -> L(R)RD) " +
              "will need fuzzy matching. Tighter tooltip cropping would further improve results.";
else if (bestPct >= 50)
    verdict = "NEEDS WORK - Partially readable; may need custom training, better preprocessing, or tighter cropping.";
else
    verdict = "NOT VIABLE - Too much garbled text; consider alternatives (Windows.Media.Ocr, cloud OCR, custom model).";

Console.WriteLine($"OCR accuracy is roughly {bestPct:F0}% -- {verdict}");
Console.WriteLine();
Console.WriteLine("Debug images saved to: " + debugDir);
