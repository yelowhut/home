namespace D4LootFilter.Scraper.Tests;

public class EndToEndTests : IDisposable
{
    private readonly string _tempDir;

    public EndToEndTests()
    {
        _tempDir = Path.Combine(Path.GetTempPath(), $"d4lf-e2e-{Guid.NewGuid():N}");
        Directory.CreateDirectory(_tempDir);
    }

    [Fact]
    public void FullPipeline_ParseUrl_ParseFixture_SaveAndLoad()
    {
        var url = "https://mobalytics.gg/diablo-4/builds/barbarian-whirl-wind-barb";
        var slug = UrlParser.ParseSlug(url);
        Assert.Equal("barbarian-whirl-wind-barb", slug);

        var json = File.ReadAllText(
            Path.Combine(AppContext.BaseDirectory, "TestData", "whirlwind-barb-response.json"));
        var profile = BuildProfileParser.Parse(json, url);

        Assert.Equal("Whirlwind", profile.Name);
        Assert.Equal("Barbarian", profile.Class);
        Assert.Equal(2, profile.Variants.Count);

        var service = new ProfileService(_tempDir);
        service.SaveProfile(profile);

        var loaded = service.LoadProfile(profile.Id);
        Assert.NotNull(loaded);
        Assert.Equal(profile.Name, loaded.Name);
        Assert.Equal(profile.Variants.Count, loaded.Variants.Count);

        var variant = loaded.Variants[0];
        var chestAffixes = variant.GetAffixesForSlot("Chest Armor");
        Assert.Equal(4, chestAffixes.Count);
        Assert.Contains(chestAffixes, a => a.Name == "Maximum Resource" && a.IsGa);

        var listed = service.ListProfiles();
        Assert.Single(listed);

        service.DeleteProfile(profile.Id);
        Assert.Empty(service.ListProfiles());
    }

    [Trait("Category", "Integration")]
    [Fact]
    public async Task FullPipeline_LiveApi_ImportAndSave()
    {
        var service = new ProfileService(_tempDir);

        var profile = await service.ImportFromUrlAsync(
            "https://mobalytics.gg/diablo-4/builds/barbarian-whirl-wind-barb");

        Assert.NotNull(profile);
        Assert.NotEmpty(profile.Name);
        Assert.True(profile.Variants.Count > 0);
        Assert.True(profile.Variants[0].Equipment.Categories.Count > 0);

        var loaded = service.LoadProfile(profile.Id);
        Assert.NotNull(loaded);
        Assert.Equal(profile.Name, loaded.Name);
    }

    public void Dispose()
    {
        if (Directory.Exists(_tempDir))
            Directory.Delete(_tempDir, recursive: true);
    }
}
