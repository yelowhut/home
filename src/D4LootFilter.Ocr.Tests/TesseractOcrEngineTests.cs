using D4LootFilter.Ocr;
using OpenCvSharp;

namespace D4LootFilter.Ocr.Tests;

public class TesseractOcrEngineTests : IDisposable
{
    private readonly TesseractOcrEngine _engine;

    public TesseractOcrEngineTests()
    {
        _engine = new TesseractOcrEngine(
            Path.Combine(AppContext.BaseDirectory, "tessdata"),
            minConfidence: 50
        );
    }

    [Fact]
    public void ExtractLines_FromTooltipSample_ReturnsText()
    {
        using var image = Cv2.ImRead(
            Path.Combine(AppContext.BaseDirectory, "TestData", "tooltip-sample.png")
        );
        Assert.False(image.Empty(), "Test image not found");

        var tooltipRegion = new Rect(
            (int)(image.Width * 0.55), 0,
            (int)(image.Width * 0.35), image.Height
        );
        using var cropped = ImagePreprocessor.CropRegion(image, tooltipRegion);
        using var preprocessed = ImagePreprocessor.Preprocess(cropped);

        var lines = _engine.ExtractLines(preprocessed);

        Assert.NotEmpty(lines);
        Assert.Contains(lines, l => l.Text.Contains("Life", StringComparison.OrdinalIgnoreCase)
                                  || l.Text.Contains("Armor", StringComparison.OrdinalIgnoreCase)
                                  || l.Text.Contains("Intelligence", StringComparison.OrdinalIgnoreCase));
    }

    public void Dispose()
    {
        _engine.Dispose();
    }
}
