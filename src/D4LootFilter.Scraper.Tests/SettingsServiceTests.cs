using D4LootFilter.Matching.Models;

namespace D4LootFilter.Scraper.Tests;

public class SettingsServiceTests : IDisposable
{
    private readonly string _tempDir;
    private readonly string _settingsPath;

    public SettingsServiceTests()
    {
        _tempDir = Path.Combine(Path.GetTempPath(), $"d4lf-settings-{Guid.NewGuid():N}");
        Directory.CreateDirectory(_tempDir);
        _settingsPath = Path.Combine(_tempDir, "settings.json");
    }

    [Fact]
    public void Load_NoFile_ReturnsDefaults()
    {
        var service = new SettingsService(_settingsPath);
        var settings = service.Load();
        Assert.Equal(30, settings.PollingFps);
        Assert.Equal(60, settings.OcrConfidenceThreshold);
        Assert.Equal(2, settings.FuzzyMatchMaxDistance);
        Assert.Equal(0.85, settings.OverlayOpacity);
        Assert.True(settings.StartMinimized);
        Assert.False(settings.AutoStartCapture);
        Assert.Equal("", settings.ActiveProfileId);
    }

    [Fact]
    public void Save_ThenLoad_RoundTrips()
    {
        var service = new SettingsService(_settingsPath);
        var settings = new AppSettings
        {
            ActiveProfileId = "test-build",
            ActiveVariantId = 1,
            PollingFps = 45,
            OcrConfidenceThreshold = 70,
            FuzzyMatchMaxDistance = 3,
            OverlayOpacity = 0.9,
            StartMinimized = false,
            AutoStartCapture = true,
            CaptureRegions = new Dictionary<string, CaptureRegion>
            {
                ["1920x1080"] = new(400, 200, 500, 600)
            }
        };
        service.Save(settings);
        var loaded = service.Load();
        Assert.Equal("test-build", loaded.ActiveProfileId);
        Assert.Equal(1, loaded.ActiveVariantId);
        Assert.Equal(45, loaded.PollingFps);
        Assert.Equal(70, loaded.OcrConfidenceThreshold);
        Assert.True(loaded.AutoStartCapture);
        Assert.Single(loaded.CaptureRegions);
        Assert.Equal(400, loaded.CaptureRegions["1920x1080"].X);
    }

    [Fact]
    public void Save_CreatesDirectoryIfMissing()
    {
        var deepPath = Path.Combine(_tempDir, "sub", "dir", "settings.json");
        var service = new SettingsService(deepPath);
        service.Save(new AppSettings());
        Assert.True(File.Exists(deepPath));
    }

    [Fact]
    public void Load_CorruptFile_ReturnsDefaults()
    {
        File.WriteAllText(_settingsPath, "not json{{{");
        var service = new SettingsService(_settingsPath);
        var settings = service.Load();
        Assert.Equal(30, settings.PollingFps);
    }

    public void Dispose()
    {
        if (Directory.Exists(_tempDir))
            Directory.Delete(_tempDir, recursive: true);
    }
}
