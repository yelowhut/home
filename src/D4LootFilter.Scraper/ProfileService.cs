using System.Text.Json;
using D4LootFilter.Matching.Models;

namespace D4LootFilter.Scraper;

public class ProfileService
{
    private static readonly JsonSerializerOptions JsonOptions = new()
    {
        PropertyNamingPolicy = JsonNamingPolicy.SnakeCaseLower,
        WriteIndented = true,
    };

    private readonly string _profilesDir;
    private BuildProfile? _activeProfile;

    public BuildProfile? ActiveProfile => _activeProfile;

    public ProfileService(string profilesDir)
    {
        _profilesDir = profilesDir;
        Directory.CreateDirectory(_profilesDir);
    }

    public async Task<BuildProfile> ImportFromUrlAsync(string url, CancellationToken ct = default)
    {
        var slug = UrlParser.ParseSlug(url);
        var client = new MobalyticsClient(new HttpClient());
        var json = await client.FetchBuildAsync(slug, ct);
        var profile = BuildProfileParser.Parse(json, url);
        SaveProfile(profile);
        _activeProfile = profile;
        return profile;
    }

    public void SaveProfile(BuildProfile profile)
    {
        var path = GetProfilePath(profile.Id);
        var json = JsonSerializer.Serialize(profile, JsonOptions);
        File.WriteAllText(path, json);
    }

    public BuildProfile? LoadProfile(string id)
    {
        var path = GetProfilePath(id);
        if (!File.Exists(path)) return null;
        var json = File.ReadAllText(path);
        var profile = JsonSerializer.Deserialize<BuildProfile>(json, JsonOptions);
        return profile;
    }

    public void SetActive(string id)
    {
        _activeProfile = LoadProfile(id);
    }

    public List<BuildProfile> ListProfiles()
    {
        if (!Directory.Exists(_profilesDir))
            return [];

        var profiles = new List<BuildProfile>();
        foreach (var file in Directory.GetFiles(_profilesDir, "*.json"))
        {
            var json = File.ReadAllText(file);
            var profile = JsonSerializer.Deserialize<BuildProfile>(json, JsonOptions);
            if (profile != null)
                profiles.Add(profile);
        }
        return profiles;
    }

    public bool DeleteProfile(string id)
    {
        var path = GetProfilePath(id);
        if (!File.Exists(path)) return false;
        File.Delete(path);
        if (_activeProfile?.Id == id)
            _activeProfile = null;
        return true;
    }

    private string GetProfilePath(string id) => Path.Combine(_profilesDir, $"{id}.json");
}
