using OpenCvSharp;

namespace D4LootFilter.Ocr;

public static class ImagePreprocessor
{
    public static Mat Preprocess(Mat source)
    {
        // Convert to grayscale first if needed
        var gray = new Mat();
        if (source.Channels() > 1)
            Cv2.CvtColor(source, gray, ColorConversionCodes.BGR2GRAY);
        else
            source.CopyTo(gray);

        // Upscale 2x before thresholding for more detail (spike confirmed this order gives best results)
        var upscaled = new Mat();
        Cv2.Resize(gray, upscaled, new Size(gray.Width * 2, gray.Height * 2), interpolation: InterpolationFlags.Cubic);
        gray.Dispose();

        // Otsu's threshold
        var thresh = new Mat();
        Cv2.Threshold(upscaled, thresh, 0, 255, ThresholdTypes.Binary | ThresholdTypes.Otsu);
        upscaled.Dispose();

        // Invert: white text on dark background → black text on white background
        var inverted = new Mat();
        Cv2.BitwiseNot(thresh, inverted);
        thresh.Dispose();

        return inverted;
    }

    public static Mat CropRegion(Mat source, Rect region)
    {
        var clamped = new Rect(
            Math.Max(0, region.X),
            Math.Max(0, region.Y),
            Math.Min(region.Width, source.Width - Math.Max(0, region.X)),
            Math.Min(region.Height, source.Height - Math.Max(0, region.Y))
        );
        return new Mat(source, clamped);
    }
}
