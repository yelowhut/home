using OpenCvSharp;

namespace D4LootFilter.Capture;

public class TooltipDetector
{
    private Mat? _previousFrame;
    private const int MinTooltipWidth = 400;
    private const int MinTooltipHeight = 500;
    private const int MaxTooltipWidth = 900;
    private const int MaxTooltipHeight = 1300;
    private const int DiffThreshold = 30;
    private const double MinChangeFraction = 0.005;

    public Rect? DetectTooltipBounds(Mat currentFrame)
    {
        using var gray = new Mat();
        if (currentFrame.Channels() > 1)
            Cv2.CvtColor(currentFrame, gray, ColorConversionCodes.BGR2GRAY);
        else
            currentFrame.CopyTo(gray);

        if (_previousFrame == null || _previousFrame.Size() != gray.Size())
        {
            _previousFrame?.Dispose();
            _previousFrame = gray.Clone();
            return null;
        }

        using var diff = new Mat();
        Cv2.Absdiff(gray, _previousFrame, diff);

        _previousFrame.Dispose();
        _previousFrame = gray.Clone();

        using var threshed = new Mat();
        Cv2.Threshold(diff, threshed, DiffThreshold, 255, ThresholdTypes.Binary);

        var changedPixels = Cv2.CountNonZero(threshed);
        var totalPixels = threshed.Rows * threshed.Cols;
        var changeFraction = (double)changedPixels / totalPixels;

        if (changeFraction < MinChangeFraction || changeFraction > 0.5)
            return null;

        using var kernel = Cv2.GetStructuringElement(MorphShapes.Rect, new Size(15, 15));
        using var dilated = new Mat();
        Cv2.Dilate(threshed, dilated, kernel, iterations: 3);

        Cv2.FindContours(dilated, out var contours, out _, RetrievalModes.External, ContourApproximationModes.ApproxSimple);

        Rect? bestRect = null;
        double bestArea = 0;

        foreach (var contour in contours)
        {
            var rect = Cv2.BoundingRect(contour);

            if (rect.Width < MinTooltipWidth || rect.Height < MinTooltipHeight)
                continue;
            if (rect.Width > MaxTooltipWidth || rect.Height > MaxTooltipHeight)
                continue;

            var area = (double)rect.Width * rect.Height;
            if (area > bestArea)
            {
                bestArea = area;
                bestRect = rect;
            }
        }

        return bestRect;
    }

    public void Reset()
    {
        _previousFrame?.Dispose();
        _previousFrame = null;
    }
}
