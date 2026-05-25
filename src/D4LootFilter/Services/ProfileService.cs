using System.IO;
using System.Reflection;
using System.Text.Json;
using D4LootFilter.Matching.Models;

namespace D4LootFilter.Services;

public class ProfileService
{
    private static readonly JsonSerializerOptions JsonOptions = new()
    {
        PropertyNamingPolicy = JsonNamingPolicy.SnakeCaseLower,
        WriteIndented = true,
    };

    private BuildProfile? _activeProfile;

    public BuildProfile? ActiveProfile => _activeProfile;

    public BuildProfile LoadTestProfile()
    {
        var assembly = Assembly.GetExecutingAssembly();
        using var stream = assembly.GetManifestResourceStream("D4LootFilter.TestData.test-profile.json")
            ?? throw new FileNotFoundException("Test profile not found in embedded resources");
        _activeProfile = JsonSerializer.Deserialize<BuildProfile>(stream, JsonOptions)
            ?? throw new InvalidOperationException("Failed to deserialize test profile");
        return _activeProfile;
    }

    public BuildProfile LoadFromFile(string path)
    {
        var json = File.ReadAllText(path);
        _activeProfile = JsonSerializer.Deserialize<BuildProfile>(json, JsonOptions)
            ?? throw new InvalidOperationException($"Failed to deserialize profile from {path}");
        return _activeProfile;
    }
}
