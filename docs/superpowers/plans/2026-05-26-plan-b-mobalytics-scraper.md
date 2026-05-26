# Plan B: Mobalytics GraphQL Scraper — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Import D4 build profiles from Mobalytics URLs via their GraphQL API, converting the response into the existing `BuildProfile` data model.

**Architecture:** New `D4LootFilter.Scraper` class library with three components — `UrlParser` (URL→slug), `MobalyticsClient` (slug→GraphQL JSON), `BuildProfileParser` (JSON→BuildProfile). The existing `ProfileService` gets extended with import/save/list/delete methods. All three scraper components are pure/testable; the HTTP client is the only I/O boundary.

**Tech Stack:** .NET 8, System.Text.Json, System.Net.Http, xUnit

**Spike reference:** `spikes/MobalyticsSpike/` contains working GraphQL query, saved responses, and extraction logic.

---

### Task 1: Scaffold Scraper projects and add to solution

**Files:**
- Create: `src/D4LootFilter.Scraper/D4LootFilter.Scraper.csproj`
- Create: `src/D4LootFilter.Scraper.Tests/D4LootFilter.Scraper.Tests.csproj`
- Modify: `src/D4LootFilter.sln`
- Modify: `src/D4LootFilter/D4LootFilter.csproj`

- [ ] **Step 1: Create the Scraper class library**

```powershell
cd D:\git\home\src
dotnet new classlib -n D4LootFilter.Scraper -o D4LootFilter.Scraper --framework net8.0
```

Delete the generated `Class1.cs`:

```powershell
Remove-Item D:\git\home\src\D4LootFilter.Scraper\Class1.cs
```

- [ ] **Step 2: Create the Scraper test project**

```powershell
cd D:\git\home\src
dotnet new xunit -n D4LootFilter.Scraper.Tests -o D4LootFilter.Scraper.Tests --framework net8.0
```

Delete the generated `UnitTest1.cs`:

```powershell
Remove-Item D:\git\home\src\D4LootFilter.Scraper.Tests\UnitTest1.cs
```

- [ ] **Step 3: Add projects to solution and wire references**

```powershell
cd D:\git\home\src
dotnet sln add D4LootFilter.Scraper/D4LootFilter.Scraper.csproj
dotnet sln add D4LootFilter.Scraper.Tests/D4LootFilter.Scraper.Tests.csproj
dotnet add D4LootFilter.Scraper/D4LootFilter.Scraper.csproj reference D4LootFilter.Matching/D4LootFilter.Matching.csproj
dotnet add D4LootFilter.Scraper.Tests/D4LootFilter.Scraper.Tests.csproj reference D4LootFilter.Scraper/D4LootFilter.Scraper.csproj
dotnet add D4LootFilter/D4LootFilter.csproj reference D4LootFilter.Scraper/D4LootFilter.Scraper.csproj
```

- [ ] **Step 4: Create test fixture from spike data**

Create a trimmed test fixture with one variant containing 3 items (one aspect, one unique, one with GA markers). This avoids bundling the full 1.8MB response.

Create directory:

```powershell
New-Item -ItemType Directory -Force "D:\git\home\src\D4LootFilter.Scraper.Tests\TestData"
```

Create file `src/D4LootFilter.Scraper.Tests/TestData/whirlwind-barb-response.json`:

```json
{
  "data": {
    "game": {
      "documents": {
        "userGeneratedDocumentBySlug": {
          "error": null,
          "data": {
            "id": "1010fee2-b3d1-4489-9193-021b622cd925",
            "slugifiedName": "barbarian-whirl-wind-barb",
            "type": "builds",
            "data": {
              "name": "Whirlwind",
              "buildVariants": {
                "values": [
                  {
                    "id": "5",
                    "genericBuilder": {
                      "slots": [
                        {
                          "gameSlotSlug": "chest-armor",
                          "gameEntity": {
                            "slug": "blood-boiling-aspect",
                            "title": "Blood Boiling Aspect",
                            "type": "aspects",
                            "modifiers": {
                              "gearStats": [
                                { "id": "strength", "isGreater": false, "isMasterwork": false },
                                { "id": "maximum-resource", "isGreater": true, "isMasterwork": true },
                                { "id": "ranks-to-rallying-cry", "isGreater": false, "isMasterwork": false },
                                { "id": "fury-per-second", "isGreater": false, "isMasterwork": false }
                              ],
                              "temperingStats": [
                                { "id": "worldly-endurance-armor", "isGreater": false, "isMasterwork": false }
                              ]
                            },
                            "entity": {
                              "__typename": "D4Aspect",
                              "title": "Blood Boiling Aspect"
                            }
                          }
                        },
                        {
                          "gameSlotSlug": "gloves",
                          "gameEntity": {
                            "slug": "gohrs-devastating-grips",
                            "title": "Gohr's Devastating Grips",
                            "type": "uniqueItems",
                            "modifiers": {
                              "gearStats": [
                                { "id": "strength", "isGreater": false, "isMasterwork": false },
                                { "id": "critical-strike-damage-multiplier", "isGreater": false, "isMasterwork": false },
                                { "id": "vulnerable-damage-multiplier", "isGreater": true, "isMasterwork": true },
                                { "id": "physical-damage-multiplier", "isGreater": false, "isMasterwork": false }
                              ],
                              "temperingStats": [
                                { "id": "sharpened-finesse-damage-per-overpower-stack", "isGreater": true, "isMasterwork": false }
                              ]
                            },
                            "entity": {
                              "__typename": "D4UniqueItem",
                              "title": "Gohr's Devastating Grips",
                              "chaos": false,
                              "mythic": false
                            }
                          }
                        },
                        {
                          "gameSlotSlug": "dual-wield-weapon-1",
                          "gameEntity": {
                            "slug": "crushing-aspect",
                            "title": "Crushing Aspect",
                            "type": "aspects",
                            "modifiers": {
                              "gearStats": [
                                { "id": "strength", "isGreater": false, "isMasterwork": false },
                                { "id": "critical-strike-damage-multiplier", "isGreater": true, "isMasterwork": true },
                                { "id": "physical-damage-multiplier", "isGreater": false, "isMasterwork": false }
                              ],
                              "temperingStats": []
                            },
                            "entity": {
                              "__typename": "D4Aspect",
                              "title": "Crushing Aspect"
                            }
                          }
                        },
                        {
                          "gameSlotSlug": "ring-1",
                          "gameEntity": {
                            "slug": "ring-of-starless-skies",
                            "title": "Ring of Starless Skies",
                            "type": "uniqueItems",
                            "modifiers": {
                              "gearStats": [
                                { "id": "maximum-life", "isGreater": false, "isMasterwork": false },
                                { "id": "resource-cost-reduction", "isGreater": true, "isMasterwork": false }
                              ],
                              "temperingStats": []
                            },
                            "entity": {
                              "__typename": "D4UniqueItem",
                              "title": "Ring of Starless Skies",
                              "chaos": false,
                              "mythic": false
                            }
                          }
                        }
                      ]
                    }
                  },
                  {
                    "id": "6",
                    "genericBuilder": {
                      "slots": [
                        {
                          "gameSlotSlug": "helm",
                          "gameEntity": {
                            "slug": "harlequin-crest",
                            "title": "Harlequin Crest",
                            "type": "uniqueItems",
                            "modifiers": {
                              "gearStats": [
                                { "id": "cooldown-reduction", "isGreater": true, "isMasterwork": false },
                                { "id": "maximum-life", "isGreater": false, "isMasterwork": false }
                              ],
                              "temperingStats": []
                            },
                            "entity": {
                              "__typename": "D4UniqueItem",
                              "title": "Harlequin Crest",
                              "chaos": false,
                              "mythic": false
                            }
                          }
                        }
                      ]
                    }
                  }
                ]
              }
            },
            "content": [
              {
                "__typename": "NgfDocumentCmWidgetContentVariantsV1",
                "data": {
                  "childrenVariants": [
                    { "id": "5", "title": "Selig Overpower" },
                    { "id": "6", "title": "Pit Push" }
                  ]
                }
              }
            ]
          }
        }
      }
    }
  }
}
```

Add to `D4LootFilter.Scraper.Tests.csproj` so test data is copied to output:

```xml
<ItemGroup>
  <None Include="TestData\**" CopyToOutputDirectory="PreserveNewest" />
</ItemGroup>
```

- [ ] **Step 5: Verify build**

Run: `dotnet build D:\git\home\src\D4LootFilter.sln`
Expected: Build succeeded, 0 errors.

- [ ] **Step 6: Commit**

```bash
git add src/D4LootFilter.Scraper/ src/D4LootFilter.Scraper.Tests/ src/D4LootFilter.sln src/D4LootFilter/D4LootFilter.csproj
git commit -m "feat: scaffold Scraper project with test fixture"
```

---

### Task 2: UrlParser — extract slug from Mobalytics URL

**Files:**
- Create: `src/D4LootFilter.Scraper/UrlParser.cs`
- Test: `src/D4LootFilter.Scraper.Tests/UrlParserTests.cs`

- [ ] **Step 1: Write failing tests**

```csharp
// src/D4LootFilter.Scraper.Tests/UrlParserTests.cs
namespace D4LootFilter.Scraper.Tests;

public class UrlParserTests
{
    [Theory]
    [InlineData("https://mobalytics.gg/diablo-4/builds/barbarian-whirl-wind-barb", "barbarian-whirl-wind-barb")]
    [InlineData("https://mobalytics.gg/diablo-4/builds/sorcerer-ball-lightning", "sorcerer-ball-lightning")]
    [InlineData("https://mobalytics.gg/diablo-4/builds/barbarian-whirl-wind-barb?ws-ngf5-1=activeVariantId,5", "barbarian-whirl-wind-barb")]
    [InlineData("http://mobalytics.gg/diablo-4/builds/some-build", "some-build")]
    [InlineData("mobalytics.gg/diablo-4/builds/some-build", "some-build")]
    [InlineData("https://mobalytics.gg/diablo-4/builds/some-build/", "some-build")]
    public void ParseSlug_ValidUrls_ReturnsSlug(string url, string expectedSlug)
    {
        var result = UrlParser.ParseSlug(url);
        Assert.Equal(expectedSlug, result);
    }

    [Theory]
    [InlineData("https://google.com/something")]
    [InlineData("https://mobalytics.gg/diablo-4/tier-list")]
    [InlineData("https://mobalytics.gg/diablo-4/builds/")]
    [InlineData("https://mobalytics.gg/diablo-4/builds")]
    [InlineData("")]
    [InlineData("not-a-url")]
    public void ParseSlug_InvalidUrls_ThrowsArgumentException(string url)
    {
        Assert.Throws<ArgumentException>(() => UrlParser.ParseSlug(url));
    }
}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `dotnet test D:\git\home\src\D4LootFilter.Scraper.Tests/ --filter UrlParser --verbosity normal`
Expected: FAIL — `UrlParser` does not exist.

- [ ] **Step 3: Implement UrlParser**

```csharp
// src/D4LootFilter.Scraper/UrlParser.cs
using System.Text.RegularExpressions;

namespace D4LootFilter.Scraper;

public static partial class UrlParser
{
    [GeneratedRegex(@"(?:https?://)?mobalytics\.gg/diablo-4/builds/([a-z0-9][a-z0-9\-]+[a-z0-9])/?(?:\?.*)?$", RegexOptions.IgnoreCase)]
    private static partial Regex BuildUrlRegex();

    public static string ParseSlug(string url)
    {
        var match = BuildUrlRegex().Match(url);
        if (!match.Success)
            throw new ArgumentException($"Invalid Mobalytics build URL: {url}");
        return match.Groups[1].Value;
    }
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `dotnet test D:\git\home\src\D4LootFilter.Scraper.Tests/ --filter UrlParser --verbosity normal`
Expected: All tests PASS.

- [ ] **Step 5: Commit**

```bash
git add src/D4LootFilter.Scraper/UrlParser.cs src/D4LootFilter.Scraper.Tests/UrlParserTests.cs
git commit -m "feat: add UrlParser to extract build slug from Mobalytics URLs"
```

---

### Task 3: BuildProfileParser — transform GraphQL JSON to BuildProfile

**Files:**
- Create: `src/D4LootFilter.Scraper/BuildProfileParser.cs`
- Test: `src/D4LootFilter.Scraper.Tests/BuildProfileParserTests.cs`

- [ ] **Step 1: Write failing tests**

```csharp
// src/D4LootFilter.Scraper.Tests/BuildProfileParserTests.cs
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `dotnet test D:\git\home\src\D4LootFilter.Scraper.Tests/ --filter BuildProfileParser --verbosity normal`
Expected: FAIL — `BuildProfileParser` does not exist.

- [ ] **Step 3: Implement BuildProfileParser**

```csharp
// src/D4LootFilter.Scraper/BuildProfileParser.cs
using System.Globalization;
using System.Text.Json;
using D4LootFilter.Matching.Models;

namespace D4LootFilter.Scraper;

public static class BuildProfileParser
{
    private static readonly Dictionary<string, string> SlotMapping = new(StringComparer.OrdinalIgnoreCase)
    {
        ["helm"] = "Helm",
        ["chest-armor"] = "Chest Armor",
        ["gloves"] = "Gloves",
        ["pants"] = "Pants",
        ["boots"] = "Boots",
        ["amulet"] = "Amulet",
        ["ring-1"] = "Ring",
        ["ring-2"] = "Ring",
        ["two-handed-weapon"] = "Weapon",
        ["dual-wield-weapon-1"] = "Weapon",
        ["dual-wield-weapon-2"] = "Weapon",
        ["main-hand"] = "Weapon",
        ["off-hand-weapon"] = "Weapon",
        ["off-hand"] = "Off-Hand",
    };

    private static readonly Dictionary<string, string> CategoryMapping = new(StringComparer.OrdinalIgnoreCase)
    {
        ["aspects"] = "Legendary",
        ["uniqueItems"] = "Uniques",
    };

    public static BuildProfile Parse(string json, string sourceUrl)
    {
        using var doc = JsonDocument.Parse(json);
        var root = doc.RootElement;

        var docData = root
            .GetProperty("data")
            .GetProperty("game")
            .GetProperty("documents")
            .GetProperty("userGeneratedDocumentBySlug");

        if (docData.TryGetProperty("error", out var errorEl) &&
            errorEl.ValueKind == JsonValueKind.String)
        {
            throw new InvalidOperationException($"Mobalytics API error: {errorEl.GetString()}");
        }

        var data = docData.GetProperty("data");
        var slug = data.GetProperty("slugifiedName").GetString() ?? "";
        var buildName = data.GetProperty("data").GetProperty("name").GetString() ?? "";

        var variantNames = ExtractVariantNames(data);
        var variants = ParseVariants(data.GetProperty("data").GetProperty("buildVariants").GetProperty("values"), variantNames);

        var className = ExtractClassName(slug);

        return new BuildProfile
        {
            Id = slug,
            Name = buildName,
            SourceUrl = sourceUrl,
            Class = className,
            ImportedAt = DateTime.UtcNow,
            Variants = variants,
            ActiveVariantId = 0,
        };
    }

    private static Dictionary<string, string> ExtractVariantNames(JsonElement data)
    {
        var names = new Dictionary<string, string>();
        if (!data.TryGetProperty("content", out var content) || content.ValueKind != JsonValueKind.Array)
            return names;

        foreach (var widget in content.EnumerateArray())
        {
            if (widget.TryGetProperty("__typename", out var tn) &&
                tn.GetString() == "NgfDocumentCmWidgetContentVariantsV1" &&
                widget.TryGetProperty("data", out var wData) &&
                wData.TryGetProperty("childrenVariants", out var children))
            {
                foreach (var child in children.EnumerateArray())
                {
                    var id = child.GetProperty("id").GetString() ?? "";
                    var title = child.GetProperty("title").GetString() ?? "";
                    names[id] = title;
                }
            }
        }
        return names;
    }

    private static List<BuildVariant> ParseVariants(JsonElement variantsArray, Dictionary<string, string> variantNames)
    {
        var variants = new List<BuildVariant>();
        int index = 0;

        foreach (var variant in variantsArray.EnumerateArray())
        {
            var variantId = variant.GetProperty("id").GetString() ?? "";
            var name = variantNames.GetValueOrDefault(variantId, $"Variant {index + 1}");

            var items = new List<(string Category, EquipmentItem Item)>();

            if (variant.TryGetProperty("genericBuilder", out var builder) &&
                builder.TryGetProperty("slots", out var slots))
            {
                foreach (var slot in slots.EnumerateArray())
                {
                    var slotSlug = slot.GetProperty("gameSlotSlug").GetString() ?? "";
                    var entity = slot.GetProperty("gameEntity");

                    var itemTitle = entity.GetProperty("title").GetString() ?? "";
                    var entityType = entity.GetProperty("type").GetString() ?? "";
                    var category = CategoryMapping.GetValueOrDefault(entityType, "Other");
                    var slotName = SlotMapping.GetValueOrDefault(slotSlug, SlugToTitleCase(slotSlug));

                    var affixes = ParseGearStats(entity);

                    items.Add((category, new EquipmentItem
                    {
                        Slot = slotName,
                        Name = itemTitle,
                        Affixes = affixes,
                    }));
                }
            }

            var categories = items
                .GroupBy(i => i.Category)
                .Select(g => new EquipmentCategory
                {
                    Name = g.Key,
                    Items = g.Select(i => i.Item).ToList(),
                })
                .ToList();

            variants.Add(new BuildVariant
            {
                Id = index,
                Name = name,
                Equipment = new Equipment { Categories = categories },
            });
            index++;
        }

        return variants;
    }

    private static List<Affix> ParseGearStats(JsonElement entity)
    {
        var affixes = new List<Affix>();
        if (!entity.TryGetProperty("modifiers", out var modifiers) ||
            !modifiers.TryGetProperty("gearStats", out var gearStats) ||
            gearStats.ValueKind != JsonValueKind.Array)
            return affixes;

        foreach (var stat in gearStats.EnumerateArray())
        {
            if (stat.ValueKind != JsonValueKind.Object) continue;
            var id = stat.GetProperty("id").GetString() ?? "";
            var isGreater = stat.TryGetProperty("isGreater", out var g) && g.ValueKind == JsonValueKind.True;

            affixes.Add(new Affix
            {
                Name = SlugToTitleCase(id),
                IsGa = isGreater,
            });
        }

        return affixes;
    }

    internal static string SlugToTitleCase(string slug)
    {
        if (string.IsNullOrEmpty(slug)) return slug;
        var words = slug.Split('-');
        return string.Join(" ", words.Select(w =>
            string.IsNullOrEmpty(w) ? w : char.ToUpper(w[0], CultureInfo.InvariantCulture) + w[1..]));
    }

    private static string ExtractClassName(string slug)
    {
        string[] classes = ["barbarian", "sorcerer", "sorceress", "rogue", "druid", "necromancer", "spiritborn"];
        var first = slug.Split('-').FirstOrDefault() ?? "";
        var match = classes.FirstOrDefault(c => c.Equals(first, StringComparison.OrdinalIgnoreCase));
        if (match == null) return "";
        if (match.Equals("sorceress", StringComparison.OrdinalIgnoreCase)) return "Sorcerer";
        return CultureInfo.InvariantCulture.TextInfo.ToTitleCase(match);
    }
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `dotnet test D:\git\home\src\D4LootFilter.Scraper.Tests/ --filter BuildProfileParser --verbosity normal`
Expected: All tests PASS.

- [ ] **Step 5: Commit**

```bash
git add src/D4LootFilter.Scraper/BuildProfileParser.cs src/D4LootFilter.Scraper.Tests/BuildProfileParserTests.cs
git commit -m "feat: add BuildProfileParser to convert GraphQL response to BuildProfile"
```

---

### Task 4: MobalyticsClient — HTTP client for GraphQL API

**Files:**
- Create: `src/D4LootFilter.Scraper/MobalyticsClient.cs`
- Test: `src/D4LootFilter.Scraper.Tests/MobalyticsClientTests.cs`

- [ ] **Step 1: Write failing tests**

The unit test uses a fake `HttpMessageHandler` to avoid real network calls. The integration test hits the live API but is skipped by default.

```csharp
// src/D4LootFilter.Scraper.Tests/MobalyticsClientTests.cs
using System.Net;
using System.Text;

namespace D4LootFilter.Scraper.Tests;

public class MobalyticsClientTests
{
    [Fact]
    public async Task FetchBuildAsync_SuccessfulResponse_ReturnsJson()
    {
        var expectedJson = """{"data":{"game":{"documents":{"userGeneratedDocumentBySlug":{"error":null,"data":{"id":"test"}}}}}}""";
        var handler = new FakeHandler(HttpStatusCode.OK, expectedJson);
        var client = new MobalyticsClient(new HttpClient(handler));

        var result = await client.FetchBuildAsync("test-build");

        Assert.Contains("\"id\":\"test\"", result);
    }

    [Fact]
    public async Task FetchBuildAsync_HttpError_ThrowsHttpRequestException()
    {
        var handler = new FakeHandler(HttpStatusCode.Forbidden, "Blocked");
        var client = new MobalyticsClient(new HttpClient(handler));

        await Assert.ThrowsAsync<HttpRequestException>(() => client.FetchBuildAsync("test-build"));
    }

    [Fact]
    public async Task FetchBuildAsync_SendsCorrectRequest()
    {
        var handler = new FakeHandler(HttpStatusCode.OK, """{"data":{}}""");
        var client = new MobalyticsClient(new HttpClient(handler));

        await client.FetchBuildAsync("my-build-slug");

        Assert.NotNull(handler.LastRequest);
        Assert.Equal(HttpMethod.Post, handler.LastRequest.Method);
        Assert.Equal("https://mobalytics.gg/api/diablo4/v4/graphql/query", handler.LastRequest.RequestUri?.ToString());

        var body = handler.LastRequestBody ?? "";
        Assert.Contains("my-build-slug", body);
        Assert.Contains("Diablo4UgFeaturedDocumentQuery", body);
    }

    [Trait("Category", "Integration")]
    [Fact]
    public async Task FetchBuildAsync_LiveApi_ReturnsValidResponse()
    {
        var client = new MobalyticsClient(new HttpClient());

        var json = await client.FetchBuildAsync("barbarian-whirl-wind-barb");

        Assert.Contains("buildVariants", json);
        Assert.Contains("genericBuilder", json);
    }

    private class FakeHandler : HttpMessageHandler
    {
        private readonly HttpStatusCode _statusCode;
        private readonly string _responseBody;
        public HttpRequestMessage? LastRequest { get; private set; }
        public string? LastRequestBody { get; private set; }

        public FakeHandler(HttpStatusCode statusCode, string responseBody)
        {
            _statusCode = statusCode;
            _responseBody = responseBody;
        }

        protected override async Task<HttpResponseMessage> SendAsync(HttpRequestMessage request, CancellationToken cancellationToken)
        {
            LastRequest = request;
            if (request.Content != null)
                LastRequestBody = await request.Content.ReadAsStringAsync(cancellationToken);

            return new HttpResponseMessage(_statusCode)
            {
                Content = new StringContent(_responseBody, Encoding.UTF8, "application/json")
            };
        }
    }
}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `dotnet test D:\git\home\src\D4LootFilter.Scraper.Tests/ --filter "MobalyticsClientTests&Category!=Integration" --verbosity normal`
Expected: FAIL — `MobalyticsClient` does not exist.

- [ ] **Step 3: Implement MobalyticsClient**

```csharp
// src/D4LootFilter.Scraper/MobalyticsClient.cs
using System.Text;
using System.Text.Json;

namespace D4LootFilter.Scraper;

public class MobalyticsClient
{
    private const string Endpoint = "https://mobalytics.gg/api/diablo4/v4/graphql/query";

    private const string Query = """
        query Diablo4UgFeaturedDocumentQuery($input: Diablo4UserGeneratedDocumentInputBySlug!) {
          game: diablo4 {
            documents {
              userGeneratedDocumentBySlug(input: $input) {
                error
                data {
                  id
                  slugifiedName
                  type
                  data {
                    name
                    buildVariants {
                      values {
                        id
                        genericBuilder {
                          slots {
                            gameSlotSlug
                            gameEntity {
                              slug
                              title
                              type
                              modifiers {
                                gearStats { id isGreater isMasterwork }
                                temperingStats { id isGreater isMasterwork }
                              }
                              entity {
                                ... on D4Aspect { __typename title: name }
                                ... on D4UniqueItem { __typename title: name chaos mythic }
                              }
                            }
                          }
                        }
                      }
                    }
                  }
                  content
                }
              }
            }
          }
        }
        """;

    private readonly HttpClient _httpClient;

    public MobalyticsClient(HttpClient httpClient)
    {
        _httpClient = httpClient;
    }

    public async Task<string> FetchBuildAsync(string slug, CancellationToken ct = default)
    {
        var payload = new
        {
            query = Query,
            variables = new
            {
                input = new
                {
                    slug,
                    type = "builds",
                    widgetsOverride = Array.Empty<object>(),
                }
            },
            operationName = "Diablo4UgFeaturedDocumentQuery",
        };

        var json = JsonSerializer.Serialize(payload);
        using var request = new HttpRequestMessage(HttpMethod.Post, Endpoint)
        {
            Content = new StringContent(json, Encoding.UTF8, "application/json"),
        };
        request.Headers.Add("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36");
        request.Headers.Add("Accept", "application/json");
        request.Headers.Add("Origin", "https://mobalytics.gg");
        request.Headers.Add("Referer", $"https://mobalytics.gg/diablo-4/builds/{slug}");

        using var response = await _httpClient.SendAsync(request, ct);
        response.EnsureSuccessStatusCode();
        return await response.Content.ReadAsStringAsync(ct);
    }
}
```

- [ ] **Step 4: Run unit tests to verify they pass**

Run: `dotnet test D:\git\home\src\D4LootFilter.Scraper.Tests/ --filter "MobalyticsClientTests&Category!=Integration" --verbosity normal`
Expected: All 3 unit tests PASS.

- [ ] **Step 5: Run integration test to verify live API still works**

Run: `dotnet test D:\git\home\src\D4LootFilter.Scraper.Tests/ --filter "MobalyticsClientTests&Category=Integration" --verbosity normal`
Expected: PASS (if internet is available).

- [ ] **Step 6: Commit**

```bash
git add src/D4LootFilter.Scraper/MobalyticsClient.cs src/D4LootFilter.Scraper.Tests/MobalyticsClientTests.cs
git commit -m "feat: add MobalyticsClient for GraphQL API calls"
```

---

### Task 5: Update ProfileService — import, save, list, delete

**Files:**
- Modify: `src/D4LootFilter/Services/ProfileService.cs`
- Test: `src/D4LootFilter.Scraper.Tests/ProfileServiceTests.cs`

- [ ] **Step 1: Write failing tests**

```csharp
// src/D4LootFilter.Scraper.Tests/ProfileServiceTests.cs
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `dotnet test D:\git\home\src\D4LootFilter.Scraper.Tests/ --filter ProfileServiceTests --verbosity normal`
Expected: FAIL — `ProfileService` constructor does not accept a directory path, and `SaveProfile`/`LoadProfile`/`ListProfiles`/`DeleteProfile` methods don't exist.

Note: The test project needs a reference to the main app project. Since `ProfileService` lives in the WPF app (`D4LootFilter`) which targets `net8.0-windows`, and the test project targets `net8.0`, we need to move `ProfileService` to the `D4LootFilter.Scraper` project instead. This is a better home for it anyway — it's the persistence layer for imported profiles.

- [ ] **Step 3: Move and rewrite ProfileService**

Move `ProfileService` from `src/D4LootFilter/Services/ProfileService.cs` to `src/D4LootFilter.Scraper/ProfileService.cs`. Update the namespace.

Delete the old file:

```powershell
Remove-Item "D:\git\home\src\D4LootFilter\Services\ProfileService.cs"
```

Write new file:

```csharp
// src/D4LootFilter.Scraper/ProfileService.cs
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
```

- [ ] **Step 4: Update App.xaml.cs to use new ProfileService**

Update `src/D4LootFilter/App.xaml.cs` — change the `ProfileService` import and constructor call. Replace:

```csharp
using D4LootFilter.Services;
```

with:

```csharp
using D4LootFilter.Scraper;
```

And replace:

```csharp
var profileService = new ProfileService();
profileService.LoadTestProfile();
```

with:

```csharp
var profilesDir = Path.Combine(
    Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData),
    "D4LootFilter", "profiles");
var profileService = new ProfileService(profilesDir);

// Load test profile from embedded resource for now
var assembly = System.Reflection.Assembly.GetExecutingAssembly();
using var stream = assembly.GetManifestResourceStream("D4LootFilter.TestData.test-profile.json");
if (stream != null)
{
    var testProfile = JsonSerializer.Deserialize<BuildProfile>(stream,
        new JsonSerializerOptions { PropertyNamingPolicy = JsonNamingPolicy.SnakeCaseLower });
    if (testProfile != null)
    {
        profileService.SaveProfile(testProfile);
        profileService.SetActive(testProfile.Id);
    }
}
```

Add the required usings at the top of `App.xaml.cs`:

```csharp
using System.Text.Json;
using D4LootFilter.Matching.Models;
```

- [ ] **Step 5: Update PipelineService.cs to use new ProfileService namespace**

Add to the top of `src/D4LootFilter/Services/PipelineService.cs`:

```csharp
using D4LootFilter.Scraper;
```

Remove the old `using D4LootFilter.Services;` self-reference if `ProfileService` was in that namespace (it was — `PipelineService` just uses the type directly via constructor injection, but the `ProfileService` type now lives in `D4LootFilter.Scraper`).

- [ ] **Step 6: Run tests to verify they pass**

Run: `dotnet test D:\git\home\src\D4LootFilter.Scraper.Tests/ --filter ProfileServiceTests --verbosity normal`
Expected: All 7 tests PASS.

- [ ] **Step 7: Build the full solution**

Run: `dotnet build D:\git\home\src\D4LootFilter.sln`
Expected: Build succeeded, 0 errors.

- [ ] **Step 8: Commit**

```bash
git add src/D4LootFilter.Scraper/ProfileService.cs src/D4LootFilter.Scraper.Tests/ProfileServiceTests.cs src/D4LootFilter/App.xaml.cs src/D4LootFilter/Services/
git commit -m "feat: move ProfileService to Scraper, add save/load/list/delete/import"
```

---

### Task 6: End-to-end integration test

**Files:**
- Create: `src/D4LootFilter.Scraper.Tests/EndToEndTests.cs`

- [ ] **Step 1: Write integration test that exercises the full import pipeline**

```csharp
// src/D4LootFilter.Scraper.Tests/EndToEndTests.cs
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
```

- [ ] **Step 2: Run offline test**

Run: `dotnet test D:\git\home\src\D4LootFilter.Scraper.Tests/ --filter "EndToEndTests&Category!=Integration" --verbosity normal`
Expected: PASS.

- [ ] **Step 3: Run live integration test**

Run: `dotnet test D:\git\home\src\D4LootFilter.Scraper.Tests/ --filter "EndToEndTests&Category=Integration" --verbosity normal`
Expected: PASS (if internet available).

- [ ] **Step 4: Run all tests in the solution**

Run: `dotnet test D:\git\home\src\D4LootFilter.sln --filter "Category!=Integration" --verbosity normal`
Expected: All tests PASS.

- [ ] **Step 5: Commit**

```bash
git add src/D4LootFilter.Scraper.Tests/EndToEndTests.cs
git commit -m "feat: add end-to-end integration test for Mobalytics import pipeline"
```

---

## Summary

| Task | Component | What it does |
|---|---|---|
| 1 | Scaffold | Create Scraper project/tests, add to solution, create test fixture |
| 2 | UrlParser | Extract build slug from Mobalytics URL |
| 3 | BuildProfileParser | Transform GraphQL JSON → BuildProfile model |
| 4 | MobalyticsClient | HTTP client for GraphQL API with fake handler tests |
| 5 | ProfileService | Move to Scraper, add save/load/list/delete/import |
| 6 | E2E test | Full pipeline: URL → parse → save → load → verify |

**Result:** A working import pipeline that takes a Mobalytics build URL, fetches the build data via GraphQL, and saves it as a `BuildProfile` JSON file ready for use by the overlay pipeline from Plan A.
