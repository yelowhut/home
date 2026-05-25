// src/D4LootFilter.Capture/TooltipDetector.cs
using OpenCvSharp;

namespace D4LootFilter.Capture;

public class TooltipDetector
{
    private const int DarkThreshold = 35;
    private const double MinDarkRatio = 0.3;
    private const int MinTooltipWidth = 100;
    private const int MinTooltipHeight = 80;

    public Rect? DetectTooltipBounds(Mat regionImage)
    {
        using var gray = new Mat();
        if (regionImage.Channels() > 1)
            Cv2.CvtColor(regionImage, gray, ColorConversionCodes.BGR2GRAY);
        else
            regionImage.CopyTo(gray);

        using var darkMask = new Mat();
        Cv2.Threshold(gray, darkMask, DarkThreshold, 255, ThresholdTypes.BinaryInv);

        var darkRatio = (double)Cv2.CountNonZero(darkMask) / (darkMask.Rows * darkMask.Cols);
        if (darkRatio < MinDarkRatio)
            return null;

        using var kernel = Cv2.GetStructuringElement(MorphShapes.Rect, new Size(5, 5));
        using var closed = new Mat();
        Cv2.MorphologyEx(darkMask, closed, MorphTypes.Close, kernel, iterations: 3);

        Cv2.FindContours(closed, out var contours, out _, RetrievalModes.External, ContourApproximationModes.ApproxSimple);

        Rect? bestRect = null;
        double bestArea = 0;
        foreach (var contour in contours)
        {
            var rect = Cv2.BoundingRect(contour);
            if (rect.Width >= MinTooltipWidth && rect.Height >= MinTooltipHeight)
            {
                var area = (double)rect.Width * rect.Height;
                if (area > bestArea)
                {
                    bestArea = area;
                    bestRect = rect;
                }
            }
        }

        return bestRect;
    }
}
