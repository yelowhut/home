using System.Text.Json;
using D4LootFilter.Matching.Models;

namespace D4LootFilter.Scraper.Tests;

public class ProfileServiceTests : IDisposable
{
    private readonly string _tempDir;
    private readonly ProfileService _service;

    public ProfileServiceTests()
    {
        _tempDir = Path.Combine(Path.GetTempPath(), $"d4lf-test-{Guid.NewGuid():N}");
        Directory.CreateDirectory(_tempDir);
        _service = new ProfileService(_tempDir);
    }

    [Fact]
    public void SaveProfile_CreatesJsonFile()
    {
        var profile = MakeProfile("test-build", "Test Build");

        _service.SaveProfile(profile);

        var filePath = Path.Combine(_tempDir, "test-build.json");
        Assert.True(File.Exists(filePath));

        var json = File.ReadAllText(filePath);
        Assert.Contains("test-build", json);
        Assert.Contains("Test Build", json);
    }

    [Fact]
    public void LoadProfile_ReadsExistingSave()
    {
        var original = MakeProfile("my-build", "My Build");
        _service.SaveProfile(original);

        var loaded = _service.LoadProfile("my-build");

        Assert.NotNull(loaded);
        Assert.Equal("my-build", loaded.Id);
        Assert.Equal("My Build", loaded.Name);
        Assert.Single(loaded.Variants);
    }

    [Fact]
    public void LoadProfile_NonExistent_ReturnsNull()
    {
        var result = _service.LoadProfile("does-not-exist");
        Assert.Null(result);
    }

    [Fact]
    public void ListProfiles_ReturnsAllSavedProfiles()
    {
        _service.SaveProfile(MakeProfile("build-a", "Build A"));
        _service.SaveProfile(MakeProfile("build-b", "Build B"));

        var list = _service.ListProfiles();

        Assert.Equal(2, list.Count);
        Assert.Contains(list, p => p.Id == "build-a");
        Assert.Contains(list, p => p.Id == "build-b");
    }

    [Fact]
    public void ListProfiles_EmptyDirectory_ReturnsEmptyList()
    {
        var list = _service.ListProfiles();
        Assert.Empty(list);
    }

    [Fact]
    public void DeleteProfile_RemovesFile()
    {
        _service.SaveProfile(MakeProfile("doomed", "Doomed Build"));
        Assert.True(File.Exists(Path.Combine(_tempDir, "doomed.json")));

        var deleted = _service.DeleteProfile("doomed");

        Assert.True(deleted);
        Assert.False(File.Exists(Path.Combine(_tempDir, "doomed.json")));
    }

    [Fact]
    public void DeleteProfile_NonExistent_ReturnsFalse()
    {
        var deleted = _service.DeleteProfile("ghost");
        Assert.False(deleted);
    }

    private static BuildProfile MakeProfile(string id, string name) => new()
    {
        Id = id,
        Name = name,
        SourceUrl = $"https://mobalytics.gg/diablo-4/builds/{id}",
        Class = "Barbarian",
        ImportedAt = DateTime.UtcNow,
        Variants =
        [
            new BuildVariant
            {
                Id = 0,
                Name = "Default",
                Equipment = new Equipment
                {
                    Categories =
                    [
                        new EquipmentCategory
                        {
                            Name = "Legendary",
                            Items =
                            [
                                new EquipmentItem
                                {
                                    Slot = "Helm",
                                    Name = "Test Helm",
                                    Affixes = [new Affix { Name = "Strength", IsGa = false }],
                                }
                            ]
                        }
                    ]
                }
            }
        ],
        ActiveVariantId = 0,
    };

    public void Dispose()
    {
        if (Directory.Exists(_tempDir))
            Directory.Delete(_tempDir, recursive: true);
    }
}
