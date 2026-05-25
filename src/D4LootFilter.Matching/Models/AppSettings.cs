namespace D4LootFilter.Matching.Models;

public record AppSettings
{
    public Dictionary<string, CaptureRegion> CaptureRegions { get; init; } = new();
    public string ActiveProfileId { get; init; } = "";
    public int PollingFps { get; init; } = 30;
    public int OcrConfidenceThreshold { get; init; } = 60;
    public int FuzzyMatchMaxDistance { get; init; } = 2;
    public double OverlayOpacity { get; init; } = 0.85;
    public bool StartMinimized { get; init; } = true;
    public bool AutoStartCapture { get; init; }
}
