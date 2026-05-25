// src/D4LootFilter.Capture/CapturedFrame.cs
using OpenCvSharp;

namespace D4LootFilter.Capture;

public record CapturedFrame(Mat Image, bool HasChanged);
