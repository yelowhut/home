using System.Drawing;
using OpenCvSharp;
using Tesseract;

namespace D4LootFilter.Ocr;

public class TesseractOcrEngine : IDisposable
{
    private readonly TesseractEngine _engine;
    private float _minConfidence;
    public float MinConfidence { get => _minConfidence; set => _minConfidence = value; }

    public TesseractOcrEngine(string tessdataPath, float minConfidence = 60)
    {
        _engine = new TesseractEngine(tessdataPath, "eng", EngineMode.Default);
        _engine.DefaultPageSegMode = PageSegMode.SingleColumn; // PSM 4
        _minConfidence = minConfidence;
    }

    public List<OcrLine> ExtractLines(Mat preprocessedImage)
    {
        // Convert Mat to bytes then load as Pix (spike-validated approach, no extra NuGet required)
        byte[] imageBytes = preprocessedImage.ToBytes(".png");
        using var pix = Pix.LoadFromMemory(imageBytes);
        using var page = _engine.Process(pix);

        var lines = new List<OcrLine>();
        using var iter = page.GetIterator();

        iter.Begin();
        do
        {
            if (iter.TryGetBoundingBox(PageIteratorLevel.TextLine, out var bounds))
            {
                var text = iter.GetText(PageIteratorLevel.TextLine)?.Trim();
                var confidence = iter.GetConfidence(PageIteratorLevel.TextLine);

                if (!string.IsNullOrWhiteSpace(text) && confidence >= _minConfidence)
                {
                    lines.Add(new OcrLine(
                        text,
                        new Rectangle(bounds.X1, bounds.Y1, bounds.Width, bounds.Height),
                        confidence
                    ));
                }
            }
        } while (iter.Next(PageIteratorLevel.TextLine));

        return lines;
    }

    public void Dispose()
    {
        _engine.Dispose();
    }
}
