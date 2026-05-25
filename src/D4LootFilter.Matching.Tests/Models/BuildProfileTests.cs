using System.Text.Json;
using D4LootFilter.Matching.Models;

namespace D4LootFilter.Matching.Tests.Models;

public class BuildProfileTests
{
    [Fact]
    public void Deserialize_ProfileJson_ParsesAllFields()
    {
        var json = """
        {
          "id": "test-build",
          "name": "Test Build",
          "source_url": "https://mobalytics.gg/diablo-4/builds/test",
          "class": "Sorcerer",
          "imported_at": "2026-05-25T12:00:00Z",
          "variants": [
            {
              "id": 0,
              "name": "Default",
              "equipment": {
                "categories": [
                  {
                    "name": "Legendary",
                    "items": [
                      {
                        "slot": "Helm",
                        "name": "Godslayer Crown",
                        "affixes": [
                          { "name": "Cooldown Reduction", "is_ga": true },
                          { "name": "Maximum Life", "is_ga": false }
                        ]
                      }
                    ]
                  }
                ]
              }
            }
          ],
          "active_variant_id": 0
        }
        """;

        var options = new JsonSerializerOptions { PropertyNamingPolicy = JsonNamingPolicy.SnakeCaseLower };
        var profile = JsonSerializer.Deserialize<BuildProfile>(json, options);

        Assert.NotNull(profile);
        Assert.Equal("test-build", profile.Id);
        Assert.Equal("Sorcerer", profile.Class);
        Assert.Single(profile.Variants);
        Assert.Equal("Default", profile.Variants[0].Name);
        Assert.Single(profile.Variants[0].Equipment.Categories);
        Assert.Equal("Helm", profile.Variants[0].Equipment.Categories[0].Items[0].Slot);
        Assert.Equal(2, profile.Variants[0].Equipment.Categories[0].Items[0].Affixes.Count);
        Assert.True(profile.Variants[0].Equipment.Categories[0].Items[0].Affixes[0].IsGa);
    }

    [Fact]
    public void GetAffixesForSlot_ReturnsCorrectAffixes()
    {
        var variant = new BuildVariant
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
                                Name = "Crown",
                                Affixes = [new Affix { Name = "Maximum Life", IsGa = false }]
                            },
                            new EquipmentItem
                            {
                                Slot = "Chest Armor",
                                Name = "Plate",
                                Affixes = [new Affix { Name = "Armor", IsGa = true }]
                            }
                        ]
                    }
                ]
            }
        };

        var helmAffixes = variant.GetAffixesForSlot("Helm");
        Assert.Single(helmAffixes);
        Assert.Equal("Maximum Life", helmAffixes[0].Name);

        var chestAffixes = variant.GetAffixesForSlot("Chest Armor");
        Assert.Single(chestAffixes);
        Assert.True(chestAffixes[0].IsGa);
    }

    [Fact]
    public void GetAllAffixes_ReturnsAffixesFromAllCategories()
    {
        var variant = new BuildVariant
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
                        Items = [new EquipmentItem { Slot = "Helm", Name = "A", Affixes = [new Affix { Name = "Life", IsGa = false }] }]
                    },
                    new EquipmentCategory
                    {
                        Name = "Uniques",
                        Items = [new EquipmentItem { Slot = "Helm", Name = "B", Affixes = [new Affix { Name = "Armor", IsGa = true }] }]
                    }
                ]
            }
        };

        var all = variant.GetAffixesForSlot("Helm");
        Assert.Equal(2, all.Count);
    }
}
