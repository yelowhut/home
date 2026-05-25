// src/D4LootFilter.Capture/FrameChangeDetector.cs
using OpenCvSharp;

namespace D4LootFilter.Capture;

public class FrameChangeDetector
{
    private ulong _previousHash;
    private const int HashSize = 8;

    public bool HasChanged(Mat frame)
    {
        var hash = ComputeHash(frame);
        var distance = HammingDistance(_previousHash, hash);
        _previousHash = hash;
        return distance > 5;
    }

    private static ulong ComputeHash(Mat frame)
    {
        using var gray = new Mat();
        if (frame.Channels() > 1)
            Cv2.CvtColor(frame, gray, ColorConversionCodes.BGR2GRAY);
        else
            frame.CopyTo(gray);

        using var resized = new Mat();
        Cv2.Resize(gray, resized, new Size(HashSize, HashSize), interpolation: InterpolationFlags.Area);

        var mean = Cv2.Mean(resized);
        ulong hash = 0;

        for (int y = 0; y < HashSize; y++)
        {
            for (int x = 0; x < HashSize; x++)
            {
                if (resized.At<byte>(y, x) > mean.Val0)
                    hash |= 1UL << (y * HashSize + x);
            }
        }

        return hash;
    }

    private static int HammingDistance(ulong a, ulong b)
    {
        var xor = a ^ b;
        int count = 0;
        while (xor != 0)
        {
            count += (int)(xor & 1);
            xor >>= 1;
        }
        return count;
    }
}
