using D4LootFilter.Ocr;
using OpenCvSharp;

namespace D4LootFilter.Ocr.Tests;

public class ImagePreprocessorTests
{
    [Fact]
    public void Preprocess_ReturnsInvertedGrayscaleImage()
    {
        using var src = new Mat(100, 200, MatType.CV_8UC3, new Scalar(20, 20, 30));
        Cv2.PutText(src, "+500 Life", new Point(10, 50), HersheyFonts.HersheySimplex, 0.6, new Scalar(220, 220, 220), 1);

        using var result = ImagePreprocessor.Preprocess(src);

        Assert.Equal(MatType.CV_8UC1, result.Type());
        Assert.True(result.Rows > 0);
        Assert.True(result.Cols > 0);
    }

    [Fact]
    public void CropRegion_ReturnsCorrectSize()
    {
        using var src = new Mat(1080, 1920, MatType.CV_8UC3, Scalar.Black);
        var region = new Rect(400, 200, 500, 600);

        using var cropped = ImagePreprocessor.CropRegion(src, region);

        Assert.Equal(600, cropped.Rows);
        Assert.Equal(500, cropped.Cols);
    }
}
