namespace D4LootFilter.Scraper.Tests;

public class BuildProfileParserTests
{
    private readonly string _testJson;

    public BuildProfileParserTests()
    {
        _testJson = File.ReadAllText(
            Path.Combine(AppContext.BaseDirectory, "TestData", "whirlwind-barb-response.json"));
    }

    [Fact]
    public void Parse_ValidResponse_ReturnsBuildProfile()
    {
        var profile = BuildProfileParser.Parse(_testJson, "https://mobalytics.gg/diablo-4/builds/barbarian-whirl-wind-barb");

        Assert.NotNull(profile);
        Assert.Equal("barbarian-whirl-wind-barb", profile.Id);
        Assert.Equal("Whirlwind", profile.Name);
        Assert.Equal("https://mobalytics.gg/diablo-4/builds/barbarian-whirl-wind-barb", profile.SourceUrl);
        Assert.Equal("Barbarian", profile.Class);
    }

    [Fact]
    public void Parse_ExtractsVariantNames()
    {
        var profile = BuildProfileParser.Parse(_testJson, "https://mobalytics.gg/diablo-4/builds/barbarian-whirl-wind-barb");

        Assert.Equal(2, profile.Variants.Count);
        Assert.Equal("Selig Overpower", profile.Variants[0].Name);
        Assert.Equal("Pit Push", profile.Variants[1].Name);
        Assert.Equal(0, profile.Variants[0].Id);
        Assert.Equal(1, profile.Variants[1].Id);
    }

    [Fact]
    public void Parse_GroupsItemsByCategory()
    {
        var profile = BuildProfileParser.Parse(_testJson, "https://mobalytics.gg/diablo-4/builds/barbarian-whirl-wind-barb");

        var variant = profile.Variants[0];
        var categories = variant.Equipment.Categories;

        var legendary = categories.FirstOrDefault(c => c.Name == "Legendary");
        var uniques = categories.FirstOrDefault(c => c.Name == "Uniques");

        Assert.NotNull(legendary);
        Assert.NotNull(uniques);
        // Variant 0: chest-armor (aspect) + dual-wield-weapon-1 (aspect) = 2 legendary
        Assert.Equal(2, legendary.Items.Count);
        // Variant 0: gloves (unique) + ring-1 (unique) = 2 uniques
        Assert.Equal(2, uniques.Items.Count);
    }

    [Fact]
    public void Parse_MapsSlotSlugsCorrectly()
    {
        var profile = BuildProfileParser.Parse(_testJson, "https://mobalytics.gg/diablo-4/builds/barbarian-whirl-wind-barb");

        var variant = profile.Variants[0];
        var allItems = variant.Equipment.Categories.SelectMany(c => c.Items).ToList();

        Assert.Contains(allItems, i => i.Slot == "Chest Armor");
        Assert.Contains(allItems, i => i.Slot == "Gloves");
        Assert.Contains(allItems, i => i.Slot == "Weapon");
        Assert.Contains(allItems, i => i.Slot == "Ring");
    }

    [Fact]
    public void Parse_ConvertsAffixSlugsToTitleCase()
    {
        var profile = BuildProfileParser.Parse(_testJson, "https://mobalytics.gg/diablo-4/builds/barbarian-whirl-wind-barb");

        var variant = profile.Variants[0];
        var chestAffixes = variant.GetAffixesForSlot("Chest Armor");

        Assert.Contains(chestAffixes, a => a.Name == "Strength");
        Assert.Contains(chestAffixes, a => a.Name == "Maximum Resource");
        Assert.Contains(chestAffixes, a => a.Name == "Ranks To Rallying Cry");
        Assert.Contains(chestAffixes, a => a.Name == "Fury Per Second");
    }

    [Fact]
    public void Parse_ExtractsGaMarkers()
    {
        var profile = BuildProfileParser.Parse(_testJson, "https://mobalytics.gg/diablo-4/builds/barbarian-whirl-wind-barb");

        var variant = profile.Variants[0];
        var chestAffixes = variant.GetAffixesForSlot("Chest Armor");

        var maxResource = chestAffixes.First(a => a.Name == "Maximum Resource");
        Assert.True(maxResource.IsGa);

        var strength = chestAffixes.First(a => a.Name == "Strength");
        Assert.False(strength.IsGa);
    }

    [Fact]
    public void Parse_ExcludesTemperingStats()
    {
        var profile = BuildProfileParser.Parse(_testJson, "https://mobalytics.gg/diablo-4/builds/barbarian-whirl-wind-barb");

        var variant = profile.Variants[0];
        var chestAffixes = variant.GetAffixesForSlot("Chest Armor");

        // Tempering stat "worldly-endurance-armor" should NOT appear
        Assert.DoesNotContain(chestAffixes, a => a.Name.Contains("Worldly"));
        Assert.Equal(4, chestAffixes.Count);
    }

    [Fact]
    public void Parse_SecondVariantParsesCorrectly()
    {
        var profile = BuildProfileParser.Parse(_testJson, "https://mobalytics.gg/diablo-4/builds/barbarian-whirl-wind-barb");

        var variant = profile.Variants[1];
        Assert.Equal("Pit Push", variant.Name);

        var helmAffixes = variant.GetAffixesForSlot("Helm");
        Assert.Equal(2, helmAffixes.Count);
        Assert.Contains(helmAffixes, a => a.Name == "Cooldown Reduction" && a.IsGa);
        Assert.Contains(helmAffixes, a => a.Name == "Maximum Life" && !a.IsGa);
    }

    [Fact]
    public void Parse_SetsActiveVariantToFirst()
    {
        var profile = BuildProfileParser.Parse(_testJson, "https://mobalytics.gg/diablo-4/builds/barbarian-whirl-wind-barb");

        Assert.Equal(0, profile.ActiveVariantId);
    }

    [Fact]
    public void Parse_UsesItemTitleAsName()
    {
        var profile = BuildProfileParser.Parse(_testJson, "https://mobalytics.gg/diablo-4/builds/barbarian-whirl-wind-barb");

        var variant = profile.Variants[0];
        var uniques = variant.Equipment.Categories.First(c => c.Name == "Uniques");
        Assert.Contains(uniques.Items, i => i.Name == "Gohr's Devastating Grips");
        Assert.Contains(uniques.Items, i => i.Name == "Ring of Starless Skies");
    }

    [Fact]
    public void Parse_InvalidJson_ThrowsException()
    {
        Assert.ThrowsAny<Exception>(() =>
            BuildProfileParser.Parse("not json", "https://mobalytics.gg/diablo-4/builds/test"));
    }

    [Fact]
    public void Parse_ErrorInResponse_ThrowsException()
    {
        var errorJson = """
        {
          "data": {
            "game": {
              "documents": {
                "userGeneratedDocumentBySlug": {
                  "error": "Build not found",
                  "data": null
                }
              }
            }
          }
        }
        """;
        var ex = Assert.Throws<InvalidOperationException>(() =>
            BuildProfileParser.Parse(errorJson, "https://mobalytics.gg/diablo-4/builds/test"));
        Assert.Contains("Build not found", ex.Message);
    }
}
