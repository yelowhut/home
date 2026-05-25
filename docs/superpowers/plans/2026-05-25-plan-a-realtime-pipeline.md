# D4 Loot Filter — Plan A: Real-Time Pipeline

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a working capture → OCR → match → overlay pipeline that highlights D4 item affixes in real time using a hardcoded test profile.

**Architecture:** Single WPF app with dedicated capture thread (DXGI Desktop Duplication), OCR thread pool (Tesseract 5, PSM 4), fuzzy affix matcher, and transparent click-through overlay window. A hardcoded JSON profile provides the build data until Plan B (scraper) is implemented.

**Tech Stack:** .NET 8, WPF, Vortice.Windows (DXGI), Tesseract.NET, OpenCvSharp4, FuzzySharp, System.Text.Json

**Spike findings baked into this plan:**
- Use Tesseract PSM 4 (single column), not PSM 6
- Strip leading icon glyphs with regex `^[^+a-zA-Z0-9]*`
- Fuzzy match distance ≤ 2 covers OCR errors (e.g. `®` for `O`)
- WPF click-through overlay confirmed working via `WS_EX_TRANSPARENT`

---

### Task 1: Solution scaffold and project structure

**Files:**
- Create: `src/D4LootFilter.sln`
- Create: `src/D4LootFilter/D4LootFilter.csproj` (WPF app)
- Create: `src/D4LootFilter.Capture/D4LootFilter.Capture.csproj` (classlib)
- Create: `src/D4LootFilter.Ocr/D4LootFilter.Ocr.csproj` (classlib)
- Create: `src/D4LootFilter.Matching/D4LootFilter.Matching.csproj` (classlib)
- Create: `src/D4LootFilter.Matching.Tests/D4LootFilter.Matching.Tests.csproj` (xunit)
- Create: `src/D4LootFilter.Ocr.Tests/D4LootFilter.Ocr.Tests.csproj` (xunit)

- [ ] **Step 1: Create solution and projects**

```powershell
cd D:\git\home\src
dotnet new sln -n D4LootFilter
dotnet new wpf -n D4LootFilter -o D4LootFilter --framework net8.0
dotnet new classlib -n D4LootFilter.Capture -o D4LootFilter.Capture --framework net8.0
dotnet new classlib -n D4LootFilter.Ocr -o D4LootFilter.Ocr --framework net8.0
dotnet new classlib -n D4LootFilter.Matching -o D4LootFilter.Matching --framework net8.0
dotnet new xunit -n D4LootFilter.Matching.Tests -o D4LootFilter.Matching.Tests --framework net8.0
dotnet new xunit -n D4LootFilter.Ocr.Tests -o D4LootFilter.Ocr.Tests --framework net8.0

dotnet sln add D4LootFilter/D4LootFilter.csproj
dotnet sln add D4LootFilter.Capture/D4LootFilter.Capture.csproj
dotnet sln add D4LootFilter.Ocr/D4LootFilter.Ocr.csproj
dotnet sln add D4LootFilter.Matching/D4LootFilter.Matching.csproj
dotnet sln add D4LootFilter.Matching.Tests/D4LootFilter.Matching.Tests.csproj
dotnet sln add D4LootFilter.Ocr.Tests/D4LootFilter.Ocr.Tests.csproj
```

- [ ] **Step 2: Add project references**

```powershell
cd D:\git\home\src
dotnet add D4LootFilter/D4LootFilter.csproj reference D4LootFilter.Capture/D4LootFilter.Capture.csproj
dotnet add D4LootFilter/D4LootFilter.csproj reference D4LootFilter.Ocr/D4LootFilter.Ocr.csproj
dotnet add D4LootFilter/D4LootFilter.csproj reference D4LootFilter.Matching/D4LootFilter.Matching.csproj
dotnet add D4LootFilter.Matching.Tests/D4LootFilter.Matching.Tests.csproj reference D4LootFilter.Matching/D4LootFilter.Matching.csproj
dotnet add D4LootFilter.Ocr.Tests/D4LootFilter.Ocr.Tests.csproj reference D4LootFilter.Ocr/D4LootFilter.Ocr.csproj
```

- [ ] **Step 3: Add NuGet packages**

```powershell
cd D:\git\home\src
dotnet add D4LootFilter.Capture/D4LootFilter.Capture.csproj package Vortice.Direct3D11
dotnet add D4LootFilter.Capture/D4LootFilter.Capture.csproj package Vortice.DXGI
dotnet add D4LootFilter.Ocr/D4LootFilter.Ocr.csproj package Tesseract
dotnet add D4LootFilter.Ocr/D4LootFilter.Ocr.csproj package OpenCvSharp4
dotnet add D4LootFilter.Ocr/D4LootFilter.Ocr.csproj package OpenCvSharp4.runtime.win
dotnet add D4LootFilter.Matching/D4LootFilter.Matching.csproj package FuzzySharp
```

- [ ] **Step 4: Download Tesseract trained data**

```powershell
New-Item -ItemType Directory -Force "D:\git\home\src\D4LootFilter\tessdata"
Invoke-WebRequest -Uri "https://github.com/tesseract-ocr/tessdata/raw/main/eng.traineddata" -OutFile "D:\git\home\src\D4LootFilter\tessdata\eng.traineddata"
```

Add to `D4LootFilter.csproj` so `eng.traineddata` is copied to output:

```xml
<ItemGroup>
  <None Include="tessdata\eng.traineddata">
    <CopyToOutputDirectory>PreserveNewest</CopyToOutputDirectory>
    <Link>tessdata\eng.traineddata</Link>
  </None>
</ItemGroup>
```

- [ ] **Step 5: Verify build**

Run: `dotnet build D:\git\home\src\D4LootFilter.sln`
Expected: Build succeeded, 0 errors.

- [ ] **Step 6: Commit**

```bash
git add src/
git commit -m "feat: scaffold solution with Capture, Ocr, Matching projects"
```

---

### Task 2: Data model — profile, affix, settings records

**Files:**
- Create: `src/D4LootFilter.Matching/Models/BuildProfile.cs`
- Create: `src/D4LootFilter.Matching/Models/AppSettings.cs`
- Create: `src/D4LootFilter.Matching/Models/CaptureRegion.cs`
- Test: `src/D4LootFilter.Matching.Tests/Models/BuildProfileTests.cs`

- [ ] **Step 1: Write failing tests for profile serialization**

```csharp
// src/D4LootFilter.Matching.Tests/Models/BuildProfileTests.cs
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `dotnet test src/D4LootFilter.Matching.Tests/ --verbosity normal`
Expected: FAIL — types do not exist yet.

- [ ] **Step 3: Implement data models**

```csharp
// src/D4LootFilter.Matching/Models/BuildProfile.cs
using System.Text.Json.Serialization;

namespace D4LootFilter.Matching.Models;

public record BuildProfile
{
    public string Id { get; init; } = "";
    public string Name { get; init; } = "";
    public string SourceUrl { get; init; } = "";
    public string Class { get; init; } = "";
    public DateTime ImportedAt { get; init; }
    public List<BuildVariant> Variants { get; init; } = [];
    public int ActiveVariantId { get; init; }

    public BuildVariant? GetActiveVariant() =>
        Variants.FirstOrDefault(v => v.Id == ActiveVariantId);
}

public record BuildVariant
{
    public int Id { get; init; }
    public string Name { get; init; } = "";
    public Equipment Equipment { get; init; } = new();

    public List<Affix> GetAffixesForSlot(string slot) =>
        Equipment.Categories
            .SelectMany(c => c.Items)
            .Where(i => i.Slot.Equals(slot, StringComparison.OrdinalIgnoreCase))
            .SelectMany(i => i.Affixes)
            .ToList();

    public List<Affix> GetAllAffixes() =>
        Equipment.Categories
            .SelectMany(c => c.Items)
            .SelectMany(i => i.Affixes)
            .ToList();
}

public record Equipment
{
    public List<EquipmentCategory> Categories { get; init; } = [];
}

public record EquipmentCategory
{
    public string Name { get; init; } = "";
    public List<EquipmentItem> Items { get; init; } = [];
}

public record EquipmentItem
{
    public string Slot { get; init; } = "";
    public string Name { get; init; } = "";
    public List<Affix> Affixes { get; init; } = [];
}

public record Affix
{
    public string Name { get; init; } = "";
    public bool IsGa { get; init; }
}
```

```csharp
// src/D4LootFilter.Matching/Models/CaptureRegion.cs
namespace D4LootFilter.Matching.Models;

public record CaptureRegion(int X, int Y, int Width, int Height);
```

```csharp
// src/D4LootFilter.Matching/Models/AppSettings.cs
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `dotnet test src/D4LootFilter.Matching.Tests/ --verbosity normal`
Expected: All 3 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add src/D4LootFilter.Matching/ src/D4LootFilter.Matching.Tests/
git commit -m "feat: add data models for build profiles, affixes, and settings"
```

---

### Task 3: Slot detection from OCR text

**Files:**
- Create: `src/D4LootFilter.Matching/SlotDetector.cs`
- Test: `src/D4LootFilter.Matching.Tests/SlotDetectorTests.cs`

- [ ] **Step 1: Write failing tests**

```csharp
// src/D4LootFilter.Matching.Tests/SlotDetectorTests.cs
using D4LootFilter.Matching;

namespace D4LootFilter.Matching.Tests;

public class SlotDetectorTests
{
    private readonly SlotDetector _detector = new();

    [Theory]
    [InlineData("Ancestral Legendary Helm", "Helm")]
    [InlineData("Unique Chest Armor", "Chest Armor")]
    [InlineData("Ancestral Rare Gloves", "Gloves")]
    [InlineData("Sacred Legendary Pants", "Pants")]
    [InlineData("Ancestral Legendary Boots", "Boots")]
    [InlineData("Unique Amulet", "Amulet")]
    [InlineData("Ancestral Legendary Ring", "Ring")]
    [InlineData("Ancestral Legendary Two-Handed Sword", "Weapon")]
    [InlineData("Unique Two-Handed Mace", "Weapon")]
    [InlineData("Ancestral Legendary Dagger", "Weapon")]
    [InlineData("Ancestral Legendary Focus", "Off-Hand")]
    [InlineData("Sacred Shield", "Off-Hand")]
    public void DetectSlot_FromItemTypeLine_ReturnsCorrectSlot(string line, string expectedSlot)
    {
        var result = _detector.DetectSlot(new[] { line });
        Assert.Equal(expectedSlot, result);
    }

    [Fact]
    public void DetectSlot_FromMultipleLines_FindsSlotInFirstFewLines()
    {
        var lines = new[]
        {
            "Godslayer Crown",
            "Ancestral Legendary Helm",
            "820 Item Power",
            "+12.5% Cooldown Reduction"
        };
        Assert.Equal("Helm", _detector.DetectSlot(lines));
    }

    [Fact]
    public void DetectSlot_NoSlotFound_ReturnsNull()
    {
        var lines = new[] { "Some random text", "+500 Intelligence" };
        Assert.Null(_detector.DetectSlot(lines));
    }

    [Theory]
    [InlineData("Ancestral Legendary Crossbow", "Weapon")]
    [InlineData("Unique Wand", "Weapon")]
    [InlineData("Ancestral Legendary Totem", "Off-Hand")]
    [InlineData("Ancestral Legendary Polearm", "Weapon")]
    [InlineData("Ancestral Legendary Scythe", "Weapon")]
    public void DetectSlot_WeaponTypes_AllMapToWeapon(string line, string expected)
    {
        Assert.Equal(expected, _detector.DetectSlot(new[] { line }));
    }
}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `dotnet test src/D4LootFilter.Matching.Tests/ --filter SlotDetector --verbosity normal`
Expected: FAIL — `SlotDetector` does not exist.

- [ ] **Step 3: Implement SlotDetector**

```csharp
// src/D4LootFilter.Matching/SlotDetector.cs
using System.Text.RegularExpressions;

namespace D4LootFilter.Matching;

public class SlotDetector
{
    private static readonly (string Pattern, string Slot)[] SlotPatterns =
    [
        ("Chest Armor", "Chest Armor"),
        ("Helm", "Helm"),
        ("Gloves", "Gloves"),
        ("Pants", "Pants"),
        ("Boots", "Boots"),
        ("Amulet", "Amulet"),
        ("Ring", "Ring"),
        ("Shield", "Off-Hand"),
        ("Focus", "Off-Hand"),
        ("Totem", "Off-Hand"),
        ("Sword", "Weapon"),
        ("Mace", "Weapon"),
        ("Axe", "Weapon"),
        ("Polearm", "Weapon"),
        ("Staff", "Weapon"),
        ("Bow", "Weapon"),
        ("Crossbow", "Weapon"),
        ("Dagger", "Weapon"),
        ("Scythe", "Weapon"),
        ("Wand", "Weapon"),
    ];

    public string? DetectSlot(IReadOnlyList<string> lines)
    {
        var searchLines = lines.Take(5);
        foreach (var line in searchLines)
        {
            foreach (var (pattern, slot) in SlotPatterns)
            {
                if (Regex.IsMatch(line, $@"\b{Regex.Escape(pattern)}\b", RegexOptions.IgnoreCase))
                    return slot;
            }
        }
        return null;
    }
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `dotnet test src/D4LootFilter.Matching.Tests/ --filter SlotDetector --verbosity normal`
Expected: All tests PASS.

- [ ] **Step 5: Commit**

```bash
git add src/D4LootFilter.Matching/SlotDetector.cs src/D4LootFilter.Matching.Tests/SlotDetectorTests.cs
git commit -m "feat: add slot detection from tooltip text lines"
```

---

### Task 4: Affix normalization and fuzzy matching

**Files:**
- Create: `src/D4LootFilter.Matching/AffixNormalizer.cs`
- Create: `src/D4LootFilter.Matching/AffixMatcher.cs`
- Create: `src/D4LootFilter.Matching/MatchResult.cs`
- Test: `src/D4LootFilter.Matching.Tests/AffixNormalizerTests.cs`
- Test: `src/D4LootFilter.Matching.Tests/AffixMatcherTests.cs`

- [ ] **Step 1: Write failing tests for normalizer**

```csharp
// src/D4LootFilter.Matching.Tests/AffixNormalizerTests.cs
using D4LootFilter.Matching;

namespace D4LootFilter.Matching.Tests;

public class AffixNormalizerTests
{
    private readonly AffixNormalizer _normalizer = new();

    [Theory]
    [InlineData("+12.5% Cooldown Reduction", "cooldown reduction")]
    [InlineData("+1,042 Maximum Life", "maximum life")]
    [InlineData("+18.7% Total Armor", "total armor")]
    [InlineData("+8.2% Attack Speed", "attack speed")]
    [InlineData("-15% Damage Reduction", "damage reduction")]
    [InlineData("+560 Total Armor", "total armor")]
    [InlineData("@ +12.5% Cooldown Reduction", "cooldown reduction")]
    [InlineData("* +1,042 Maximum Life", "maximum life")]
    [InlineData("(R) +560 Total Armor", "total armor")]
    [InlineData("+210 Intelligence +[100 - 121]", "intelligence")]
    public void Normalize_StripsNumbersAndGlyphs(string input, string expected)
    {
        Assert.Equal(expected, _normalizer.Normalize(input));
    }

    [Theory]
    [InlineData("Ancestral Legendary Helm")]
    [InlineData("820 Item Power")]
    [InlineData("Godslayer Crown")]
    [InlineData("Requires Level 70")]
    [InlineData("Sell Value: 69,577")]
    public void IsLikelyAffix_NonAffixLines_ReturnsFalse(string input)
    {
        Assert.False(_normalizer.IsLikelyAffix(input));
    }

    [Theory]
    [InlineData("+12.5% Cooldown Reduction")]
    [InlineData("+1,042 Maximum Life")]
    [InlineData("@ +560 Total Armor")]
    public void IsLikelyAffix_AffixLines_ReturnsTrue(string input)
    {
        Assert.True(_normalizer.IsLikelyAffix(input));
    }
}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `dotnet test src/D4LootFilter.Matching.Tests/ --filter AffixNormalizer --verbosity normal`
Expected: FAIL.

- [ ] **Step 3: Implement AffixNormalizer**

```csharp
// src/D4LootFilter.Matching/AffixNormalizer.cs
using System.Text.RegularExpressions;

namespace D4LootFilter.Matching;

public partial class AffixNormalizer
{
    [GeneratedRegex(@"^[^+\-a-zA-Z0-9]*")]
    private static partial Regex LeadingGlyphsRegex();

    [GeneratedRegex(@"^[+\-]?[\d,.]+%?\s*")]
    private static partial Regex LeadingNumbersRegex();

    [GeneratedRegex(@"\s*[+\-]?\[[\d\s,.\-]+\].*$")]
    private static partial Regex TrailingRangeRegex();

    [GeneratedRegex(@"^[^+\-a-zA-Z0-9]*[+\-][\d]")]
    private static partial Regex AffixPatternRegex();

    public string Normalize(string ocrLine)
    {
        var text = LeadingGlyphsRegex().Replace(ocrLine, "");
        text = LeadingNumbersRegex().Replace(text, "");
        text = TrailingRangeRegex().Replace(text, "");
        return text.Trim().ToLowerInvariant();
    }

    public bool IsLikelyAffix(string ocrLine)
    {
        return AffixPatternRegex().IsMatch(ocrLine);
    }
}
```

- [ ] **Step 4: Run normalizer tests**

Run: `dotnet test src/D4LootFilter.Matching.Tests/ --filter AffixNormalizer --verbosity normal`
Expected: All PASS.

- [ ] **Step 5: Write failing tests for matcher**

```csharp
// src/D4LootFilter.Matching.Tests/AffixMatcherTests.cs
using D4LootFilter.Matching;
using D4LootFilter.Matching.Models;

namespace D4LootFilter.Matching.Tests;

public class AffixMatcherTests
{
    private readonly AffixMatcher _matcher = new(maxDistance: 2);

    private static List<Affix> TestAffixes =>
    [
        new Affix { Name = "Cooldown Reduction", IsGa = true },
        new Affix { Name = "Maximum Life", IsGa = false },
        new Affix { Name = "Total Armor", IsGa = false },
        new Affix { Name = "Intelligence", IsGa = false }
    ];

    [Fact]
    public void Match_ExactMatch_ReturnsMatchWithHighConfidence()
    {
        var results = _matcher.Match(
            ["+12.5% Cooldown Reduction"],
            TestAffixes
        );

        Assert.Single(results);
        Assert.True(results[0].IsMatched);
        Assert.Equal("Cooldown Reduction", results[0].AffixName);
        Assert.True(results[0].IsGa);
    }

    [Fact]
    public void Match_MultipleLines_ReturnsAllMatches()
    {
        var ocrLines = new[]
        {
            "+12.5% Cooldown Reduction",
            "+1,042 Maximum Life",
            "+560 Total Armor",
            "+8.2% Attack Speed"
        };

        var results = _matcher.Match(ocrLines, TestAffixes);

        Assert.Equal(4, results.Count);
        Assert.Equal(3, results.Count(r => r.IsMatched));
        Assert.Single(results.Where(r => !r.IsMatched));
    }

    [Fact]
    public void Match_FuzzyMatch_HandlesOcrErrors()
    {
        // OCR might read "Cooldown Reduction" as "Cooldown Reductlon" (1 char diff)
        var results = _matcher.Match(
            ["+12.5% Cooldown Reductlon"],
            TestAffixes
        );

        Assert.Single(results);
        Assert.True(results[0].IsMatched);
        Assert.Equal("Cooldown Reduction", results[0].AffixName);
    }

    [Fact]
    public void Match_NoMatch_ReturnsUnmatchedResult()
    {
        var results = _matcher.Match(
            ["+8.2% Attack Speed"],
            TestAffixes
        );

        Assert.Single(results);
        Assert.False(results[0].IsMatched);
    }

    [Fact]
    public void Match_ContainsMatch_WorksAsFallback()
    {
        // OCR reads extra text but contains the affix name
        var results = _matcher.Match(
            ["+560 Total Armor (Enchanted)"],
            TestAffixes
        );

        Assert.Single(results);
        Assert.True(results[0].IsMatched);
    }

    [Fact]
    public void MatchSummary_ReturnsCorrectCounts()
    {
        var ocrLines = new[]
        {
            "+12.5% Cooldown Reduction",
            "+1,042 Maximum Life",
            "+8.2% Attack Speed"
        };

        var results = _matcher.Match(ocrLines, TestAffixes);
        var summary = AffixMatcher.Summarize(results, TestAffixes);

        Assert.Equal(2, summary.MatchedCount);
        Assert.Equal(4, summary.TotalBuildAffixes);
        Assert.Equal(1, summary.GaMatchedCount);
        Assert.Equal(2, summary.MissingAffixes.Count);
        Assert.Contains("Total Armor", summary.MissingAffixes);
        Assert.Contains("Intelligence", summary.MissingAffixes);
    }
}
```

- [ ] **Step 6: Run matcher tests to verify they fail**

Run: `dotnet test src/D4LootFilter.Matching.Tests/ --filter AffixMatcher --verbosity normal`
Expected: FAIL.

- [ ] **Step 7: Implement MatchResult and AffixMatcher**

```csharp
// src/D4LootFilter.Matching/MatchResult.cs
namespace D4LootFilter.Matching;

public record AffixMatchResult(
    string OcrText,
    string AffixName,
    bool IsGa,
    bool IsMatched,
    int LineIndex
);

public record MatchSummary(
    int MatchedCount,
    int TotalBuildAffixes,
    int GaMatchedCount,
    List<string> MissingAffixes
);
```

```csharp
// src/D4LootFilter.Matching/AffixMatcher.cs
using D4LootFilter.Matching.Models;
using FuzzySharp;

namespace D4LootFilter.Matching;

public class AffixMatcher
{
    private readonly AffixNormalizer _normalizer = new();
    private readonly int _maxDistance;

    public AffixMatcher(int maxDistance = 2)
    {
        _maxDistance = maxDistance;
    }

    public List<AffixMatchResult> Match(IReadOnlyList<string> ocrLines, List<Affix> buildAffixes)
    {
        var results = new List<AffixMatchResult>();
        var normalizedBuildAffixes = buildAffixes
            .Select(a => (Affix: a, Normalized: a.Name.ToLowerInvariant()))
            .ToList();

        for (int i = 0; i < ocrLines.Count; i++)
        {
            var line = ocrLines[i];
            if (!_normalizer.IsLikelyAffix(line))
                continue;

            var normalized = _normalizer.Normalize(line);
            if (string.IsNullOrWhiteSpace(normalized))
                continue;

            var bestMatch = FindBestMatch(normalized, normalizedBuildAffixes);
            if (bestMatch != null)
            {
                results.Add(new AffixMatchResult(line, bestMatch.Value.Affix.Name, bestMatch.Value.Affix.IsGa, true, i));
            }
            else
            {
                results.Add(new AffixMatchResult(line, normalized, false, false, i));
            }
        }

        return results;
    }

    private (Affix Affix, string Normalized)? FindBestMatch(
        string normalized,
        List<(Affix Affix, string Normalized)> buildAffixes)
    {
        // Exact match
        var exact = buildAffixes.FirstOrDefault(b => b.Normalized == normalized);
        if (exact.Affix != null)
            return exact;

        // Fuzzy match (Levenshtein)
        foreach (var candidate in buildAffixes)
        {
            var distance = Fuzz.Ratio(normalized, candidate.Normalized);
            // FuzzySharp Ratio returns 0-100 (100 = identical). Convert threshold.
            if (distance >= 85)
                return candidate;
        }

        // Contains match
        foreach (var candidate in buildAffixes)
        {
            if (normalized.Contains(candidate.Normalized) || candidate.Normalized.Contains(normalized))
                return candidate;
        }

        return null;
    }

    public static MatchSummary Summarize(List<AffixMatchResult> results, List<Affix> buildAffixes)
    {
        var matchedNames = results.Where(r => r.IsMatched).Select(r => r.AffixName).ToHashSet();
        var missing = buildAffixes
            .Where(a => !matchedNames.Contains(a.Name))
            .Select(a => a.Name)
            .ToList();

        return new MatchSummary(
            MatchedCount: results.Count(r => r.IsMatched),
            TotalBuildAffixes: buildAffixes.Count,
            GaMatchedCount: results.Count(r => r.IsMatched && r.IsGa),
            MissingAffixes: missing
        );
    }
}
```

- [ ] **Step 8: Run all matching tests**

Run: `dotnet test src/D4LootFilter.Matching.Tests/ --verbosity normal`
Expected: All tests PASS.

- [ ] **Step 9: Commit**

```bash
git add src/D4LootFilter.Matching/ src/D4LootFilter.Matching.Tests/
git commit -m "feat: add affix normalizer, fuzzy matcher, and slot detector"
```

---

### Task 5: OCR pipeline — Tesseract wrapper and image preprocessing

**Files:**
- Create: `src/D4LootFilter.Ocr/OcrLine.cs`
- Create: `src/D4LootFilter.Ocr/ImagePreprocessor.cs`
- Create: `src/D4LootFilter.Ocr/TesseractOcrEngine.cs`
- Test: `src/D4LootFilter.Ocr.Tests/ImagePreprocessorTests.cs`
- Test: `src/D4LootFilter.Ocr.Tests/TesseractOcrEngineTests.cs`
- Copy: `D:\git\home\img.png` → `src/D4LootFilter.Ocr.Tests/TestData/tooltip-sample.png`

- [ ] **Step 1: Copy test image and add NuGet packages to test project**

```powershell
New-Item -ItemType Directory -Force "D:\git\home\src\D4LootFilter.Ocr.Tests\TestData"
Copy-Item "D:\git\home\img.png" "D:\git\home\src\D4LootFilter.Ocr.Tests\TestData\tooltip-sample.png"
New-Item -ItemType Directory -Force "D:\git\home\src\D4LootFilter.Ocr.Tests\tessdata"
Copy-Item "D:\git\home\spikes\TesseractSpike\tessdata\eng.traineddata" "D:\git\home\src\D4LootFilter.Ocr.Tests\tessdata\eng.traineddata"
```

Add to `D4LootFilter.Ocr.Tests.csproj`:

```xml
<ItemGroup>
  <None Include="TestData\**" CopyToOutputDirectory="PreserveNewest" />
  <None Include="tessdata\**" CopyToOutputDirectory="PreserveNewest" />
</ItemGroup>
```

Also add NuGet packages to test project:

```powershell
cd D:\git\home\src
dotnet add D4LootFilter.Ocr.Tests/D4LootFilter.Ocr.Tests.csproj package Tesseract
dotnet add D4LootFilter.Ocr.Tests/D4LootFilter.Ocr.Tests.csproj package OpenCvSharp4
dotnet add D4LootFilter.Ocr.Tests/D4LootFilter.Ocr.Tests.csproj package OpenCvSharp4.runtime.win
```

- [ ] **Step 2: Create OcrLine record**

```csharp
// src/D4LootFilter.Ocr/OcrLine.cs
using System.Drawing;

namespace D4LootFilter.Ocr;

public record OcrLine(string Text, Rectangle BoundingBox, float Confidence);
```

- [ ] **Step 3: Write failing tests for ImagePreprocessor**

```csharp
// src/D4LootFilter.Ocr.Tests/ImagePreprocessorTests.cs
using D4LootFilter.Ocr;
using OpenCvSharp;

namespace D4LootFilter.Ocr.Tests;

public class ImagePreprocessorTests
{
    [Fact]
    public void Preprocess_ReturnsInvertedGrayscaleImage()
    {
        using var src = new Mat(100, 200, MatType.CV_8UC3, new Scalar(20, 20, 30));
        // Draw white text simulation
        Cv2.PutText(src, "+500 Life", new Point(10, 50), HersheyFonts.HersheySimplex, 0.6, new Scalar(220, 220, 220), 1);

        using var result = ImagePreprocessor.Preprocess(src);

        Assert.Equal(MatType.CV_8UC1, result.Type());
        Assert.True(result.Rows > 0);
        Assert.True(result.Cols > 0);
    }

    [Fact]
    public void CropRegion_ReturnsCorrectSize()
    {
        using var src = new Mat(1080, 1920, MatType.CV_8UC3, Scalar.Black);
        var region = new Rect(400, 200, 500, 600);

        using var cropped = ImagePreprocessor.CropRegion(src, region);

        Assert.Equal(600, cropped.Rows);
        Assert.Equal(500, cropped.Cols);
    }
}
```

- [ ] **Step 4: Implement ImagePreprocessor**

```csharp
// src/D4LootFilter.Ocr/ImagePreprocessor.cs
using OpenCvSharp;

namespace D4LootFilter.Ocr;

public static class ImagePreprocessor
{
    public static Mat Preprocess(Mat source)
    {
        var gray = new Mat();
        if (source.Channels() > 1)
            Cv2.CvtColor(source, gray, ColorConversionCodes.BGR2GRAY);
        else
            source.CopyTo(gray);

        var upscaled = new Mat();
        Cv2.Resize(gray, upscaled, new Size(gray.Width * 2, gray.Height * 2), interpolation: InterpolationFlags.Cubic);
        gray.Dispose();

        var thresh = new Mat();
        Cv2.Threshold(upscaled, thresh, 0, 255, ThresholdTypes.Binary | ThresholdTypes.Otsu);
        upscaled.Dispose();

        var inverted = new Mat();
        Cv2.BitwiseNot(thresh, inverted);
        thresh.Dispose();

        return inverted;
    }

    public static Mat CropRegion(Mat source, Rect region)
    {
        var clamped = new Rect(
            Math.Max(0, region.X),
            Math.Max(0, region.Y),
            Math.Min(region.Width, source.Width - Math.Max(0, region.X)),
            Math.Min(region.Height, source.Height - Math.Max(0, region.Y))
        );
        return new Mat(source, clamped);
    }
}
```

- [ ] **Step 5: Run preprocessor tests**

Run: `dotnet test src/D4LootFilter.Ocr.Tests/ --filter ImagePreprocessor --verbosity normal`
Expected: All PASS.

- [ ] **Step 6: Write integration test for TesseractOcrEngine**

```csharp
// src/D4LootFilter.Ocr.Tests/TesseractOcrEngineTests.cs
using D4LootFilter.Ocr;
using OpenCvSharp;

namespace D4LootFilter.Ocr.Tests;

public class TesseractOcrEngineTests : IDisposable
{
    private readonly TesseractOcrEngine _engine;

    public TesseractOcrEngineTests()
    {
        _engine = new TesseractOcrEngine(
            Path.Combine(AppContext.BaseDirectory, "tessdata"),
            minConfidence: 50
        );
    }

    [Fact]
    public void ExtractLines_FromTooltipSample_ReturnsText()
    {
        using var image = Cv2.ImRead(
            Path.Combine(AppContext.BaseDirectory, "TestData", "tooltip-sample.png")
        );
        Assert.False(image.Empty(), "Test image not found");

        // Crop right portion (tooltip area) — approximately right 35%
        var tooltipRegion = new Rect(
            (int)(image.Width * 0.55), 0,
            (int)(image.Width * 0.35), image.Height
        );
        using var cropped = ImagePreprocessor.CropRegion(image, tooltipRegion);
        using var preprocessed = ImagePreprocessor.Preprocess(cropped);

        var lines = _engine.ExtractLines(preprocessed);

        Assert.NotEmpty(lines);
        // Should find at least some affix-like text
        Assert.Contains(lines, l => l.Text.Contains("Life", StringComparison.OrdinalIgnoreCase)
                                  || l.Text.Contains("Armor", StringComparison.OrdinalIgnoreCase)
                                  || l.Text.Contains("Intelligence", StringComparison.OrdinalIgnoreCase));
    }

    public void Dispose()
    {
        _engine.Dispose();
    }
}
```

- [ ] **Step 7: Implement TesseractOcrEngine**

```csharp
// src/D4LootFilter.Ocr/TesseractOcrEngine.cs
using System.Drawing;
using OpenCvSharp;
using OpenCvSharp.Extensions;
using Tesseract;

namespace D4LootFilter.Ocr;

public class TesseractOcrEngine : IDisposable
{
    private readonly TesseractEngine _engine;
    private readonly float _minConfidence;

    public TesseractOcrEngine(string tessdataPath, float minConfidence = 60)
    {
        _engine = new TesseractEngine(tessdataPath, "eng", EngineMode.Default);
        _engine.DefaultPageSegMode = PageSegMode.SingleColumn; // PSM 4
        _minConfidence = minConfidence;
    }

    public List<OcrLine> ExtractLines(Mat preprocessedImage)
    {
        using var bitmap = BitmapConverter.ToBitmap(preprocessedImage);
        using var pix = PixConverter.ToPix(bitmap);
        using var page = _engine.Process(pix);

        var lines = new List<OcrLine>();
        using var iter = page.GetIterator();

        iter.Begin();
        do
        {
            if (iter.TryGetBoundingBox(PageIteratorLevel.TextLine, out var bounds))
            {
                var text = iter.GetText(PageIteratorLevel.TextLine)?.Trim();
                var confidence = iter.GetConfidence(PageIteratorLevel.TextLine);

                if (!string.IsNullOrWhiteSpace(text) && confidence >= _minConfidence)
                {
                    lines.Add(new OcrLine(
                        text,
                        new Rectangle(bounds.X1, bounds.Y1, bounds.Width, bounds.Height),
                        confidence
                    ));
                }
            }
        } while (iter.Next(PageIteratorLevel.TextLine));

        return lines;
    }

    public void Dispose()
    {
        _engine.Dispose();
    }
}
```

- [ ] **Step 8: Run all OCR tests**

Run: `dotnet test src/D4LootFilter.Ocr.Tests/ --verbosity normal`
Expected: All PASS.

- [ ] **Step 9: Commit**

```bash
git add src/D4LootFilter.Ocr/ src/D4LootFilter.Ocr.Tests/
git commit -m "feat: add OCR pipeline with Tesseract and image preprocessing"
```

---

### Task 6: Screen capture — DXGI Desktop Duplication

**Files:**
- Create: `src/D4LootFilter.Capture/DxgiCapture.cs`
- Create: `src/D4LootFilter.Capture/FrameChangeDetector.cs`
- Create: `src/D4LootFilter.Capture/CapturedFrame.cs`

No unit tests for this task — DXGI requires a real display adapter. Verified by running the app in Task 8.

- [ ] **Step 1: Enable unsafe blocks and create CapturedFrame record**

Add `<AllowUnsafeBlocks>true</AllowUnsafeBlocks>` to `D4LootFilter.Capture.csproj` `<PropertyGroup>`.


```csharp
// src/D4LootFilter.Capture/CapturedFrame.cs
using OpenCvSharp;

namespace D4LootFilter.Capture;

public record CapturedFrame(Mat Image, bool HasChanged);
```

Add OpenCvSharp to Capture project:

```powershell
cd D:\git\home\src
dotnet add D4LootFilter.Capture/D4LootFilter.Capture.csproj package OpenCvSharp4
dotnet add D4LootFilter.Capture/D4LootFilter.Capture.csproj package OpenCvSharp4.runtime.win
```

- [ ] **Step 2: Implement FrameChangeDetector**

```csharp
// src/D4LootFilter.Capture/FrameChangeDetector.cs
using OpenCvSharp;

namespace D4LootFilter.Capture;

public class FrameChangeDetector
{
    private ulong _previousHash;
    private const int HashSize = 8;

    public bool HasChanged(Mat frame)
    {
        var hash = ComputeHash(frame);
        var distance = HammingDistance(_previousHash, hash);
        _previousHash = hash;
        return distance > 5;
    }

    private static ulong ComputeHash(Mat frame)
    {
        using var gray = new Mat();
        if (frame.Channels() > 1)
            Cv2.CvtColor(frame, gray, ColorConversionCodes.BGR2GRAY);
        else
            frame.CopyTo(gray);

        using var resized = new Mat();
        Cv2.Resize(gray, resized, new Size(HashSize, HashSize), interpolation: InterpolationFlags.Area);

        var mean = Cv2.Mean(resized);
        ulong hash = 0;

        for (int y = 0; y < HashSize; y++)
        {
            for (int x = 0; x < HashSize; x++)
            {
                if (resized.At<byte>(y, x) > mean.Val0)
                    hash |= 1UL << (y * HashSize + x);
            }
        }

        return hash;
    }

    private static int HammingDistance(ulong a, ulong b)
    {
        var xor = a ^ b;
        int count = 0;
        while (xor != 0)
        {
            count += (int)(xor & 1);
            xor >>= 1;
        }
        return count;
    }
}
```

- [ ] **Step 3: Implement DxgiCapture**

```csharp
// src/D4LootFilter.Capture/DxgiCapture.cs
using System.Runtime.InteropServices;
using OpenCvSharp;
using Vortice.Direct3D;
using Vortice.Direct3D11;
using Vortice.DXGI;

namespace D4LootFilter.Capture;

public class DxgiCapture : IDisposable
{
    private readonly ID3D11Device _device;
    private readonly ID3D11DeviceContext _context;
    private readonly IDXGIOutputDuplication _duplication;
    private readonly ID3D11Texture2D _stagingTexture;
    private readonly int _width;
    private readonly int _height;

    public DxgiCapture(int adapterIndex = 0, int outputIndex = 0)
    {
        using var factory = DXGI.CreateDXGIFactory1<IDXGIFactory1>();
        using var adapter = factory.GetAdapter1(adapterIndex);
        using var output = adapter.GetOutput(outputIndex);
        using var output1 = output.QueryInterface<IDXGIOutput1>();

        D3D11.D3D11CreateDevice(
            adapter,
            DriverType.Unknown,
            DeviceCreationFlags.None,
            new[] { FeatureLevel.Level_11_0 },
            out _device,
            out _context
        );

        _duplication = output1.DuplicateOutput(_device);

        var desc = output.Description;
        _width = desc.DesktopCoordinates.Right - desc.DesktopCoordinates.Left;
        _height = desc.DesktopCoordinates.Bottom - desc.DesktopCoordinates.Top;

        var stagingDesc = new Texture2DDescription
        {
            Width = _width,
            Height = _height,
            MipLevels = 1,
            ArraySize = 1,
            Format = Vortice.DXGI.Format.B8G8R8A8_UNorm,
            SampleDescription = new SampleDescription(1, 0),
            Usage = ResourceUsage.Staging,
            CPUAccessFlags = CpuAccessFlags.Read,
        };
        _stagingTexture = _device.CreateTexture2D(stagingDesc);
    }

    public Mat? CaptureFrame(int timeoutMs = 100)
    {
        var result = _duplication.AcquireNextFrame(timeoutMs, out _, out var resource);
        if (result.Failure)
            return null;

        try
        {
            using var texture = resource.QueryInterface<ID3D11Texture2D>();
            _context.CopyResource(_stagingTexture, texture);

            var mapped = _context.Map(_stagingTexture, 0, MapMode.Read);
            try
            {
                var mat = new Mat(_height, _width, MatType.CV_8UC4);
                var srcPtr = mapped.DataPointer;
                var dstPtr = mat.Data;
                for (int y = 0; y < _height; y++)
                {
                    var src = srcPtr + y * mapped.RowPitch;
                    var dst = dstPtr + y * _width * 4;
                    Buffer.MemoryCopy((void*)src, (void*)dst, _width * 4, _width * 4);
                }
                return mat;
            }
            finally
            {
                _context.Unmap(_stagingTexture, 0);
            }
        }
        finally
        {
            resource.Dispose();
            _duplication.ReleaseFrame();
        }
    }

    public void Dispose()
    {
        _stagingTexture.Dispose();
        _duplication.Dispose();
        _context.Dispose();
        _device.Dispose();
    }
}
```

- [ ] **Step 4: Build to verify compilation**

Run: `dotnet build src/D4LootFilter.Capture/D4LootFilter.Capture.csproj`
Expected: Build succeeded.

- [ ] **Step 5: Commit**

```bash
git add src/D4LootFilter.Capture/
git commit -m "feat: add DXGI screen capture and frame change detection"
```

---

### Task 7: Tooltip detector

**Files:**
- Create: `src/D4LootFilter.Capture/TooltipDetector.cs`

- [ ] **Step 1: Implement TooltipDetector**

```csharp
// src/D4LootFilter.Capture/TooltipDetector.cs
using OpenCvSharp;

namespace D4LootFilter.Capture;

public class TooltipDetector
{
    private const int DarkThreshold = 35;
    private const double MinDarkRatio = 0.3;
    private const int MinTooltipWidth = 100;
    private const int MinTooltipHeight = 80;

    public Rect? DetectTooltipBounds(Mat regionImage)
    {
        using var gray = new Mat();
        if (regionImage.Channels() > 1)
            Cv2.CvtColor(regionImage, gray, ColorConversionCodes.BGR2GRAY);
        else
            regionImage.CopyTo(gray);

        using var darkMask = new Mat();
        Cv2.Threshold(gray, darkMask, DarkThreshold, 255, ThresholdTypes.BinaryInv);

        var darkRatio = (double)Cv2.CountNonZero(darkMask) / (darkMask.Rows * darkMask.Cols);
        if (darkRatio < MinDarkRatio)
            return null;

        using var kernel = Cv2.GetStructuringElement(MorphShapes.Rect, new Size(5, 5));
        using var closed = new Mat();
        Cv2.MorphologyEx(darkMask, closed, MorphTypes.Close, kernel, iterations: 3);

        Cv2.FindContours(closed, out var contours, out _, RetrievalModes.External, ContourApproximationModes.ApproxSimple);

        Rect? bestRect = null;
        double bestArea = 0;
        foreach (var contour in contours)
        {
            var rect = Cv2.BoundingRect(contour);
            if (rect.Width >= MinTooltipWidth && rect.Height >= MinTooltipHeight)
            {
                var area = (double)rect.Width * rect.Height;
                if (area > bestArea)
                {
                    bestArea = area;
                    bestRect = rect;
                }
            }
        }

        return bestRect;
    }
}
```

- [ ] **Step 2: Build to verify compilation**

Run: `dotnet build src/D4LootFilter.Capture/D4LootFilter.Capture.csproj`
Expected: Build succeeded.

- [ ] **Step 3: Commit**

```bash
git add src/D4LootFilter.Capture/TooltipDetector.cs
git commit -m "feat: add tooltip boundary detector using dark region contours"
```

---

### Task 8: Overlay window — transparent click-through WPF

**Files:**
- Create: `src/D4LootFilter/Overlay/OverlayWindow.xaml`
- Create: `src/D4LootFilter/Overlay/OverlayWindow.xaml.cs`
- Create: `src/D4LootFilter/Overlay/OverlayViewModel.cs`

- [ ] **Step 1: Create OverlayViewModel**

```csharp
// src/D4LootFilter/Overlay/OverlayViewModel.cs
using System.Collections.ObjectModel;
using System.ComponentModel;
using System.Runtime.CompilerServices;
using D4LootFilter.Matching;

namespace D4LootFilter.Overlay;

public class OverlayViewModel : INotifyPropertyChanged
{
    private bool _isVisible;
    private string _buildName = "";
    private string _slotName = "";
    private int _matchedCount;
    private int _totalCount;
    private int _gaMatchedCount;
    private ObservableCollection<AffixHighlight> _highlights = [];
    private ObservableCollection<string> _missingAffixes = [];

    public bool IsVisible
    {
        get => _isVisible;
        set => SetField(ref _isVisible, value);
    }

    public string BuildName
    {
        get => _buildName;
        set => SetField(ref _buildName, value);
    }

    public string SlotName
    {
        get => _slotName;
        set => SetField(ref _slotName, value);
    }

    public int MatchedCount
    {
        get => _matchedCount;
        set => SetField(ref _matchedCount, value);
    }

    public int TotalCount
    {
        get => _totalCount;
        set => SetField(ref _totalCount, value);
    }

    public int GaMatchedCount
    {
        get => _gaMatchedCount;
        set => SetField(ref _gaMatchedCount, value);
    }

    public ObservableCollection<AffixHighlight> Highlights
    {
        get => _highlights;
        set => SetField(ref _highlights, value);
    }

    public ObservableCollection<string> MissingAffixes
    {
        get => _missingAffixes;
        set => SetField(ref _missingAffixes, value);
    }

    public void Update(List<AffixMatchResult> results, MatchSummary summary, string buildName, string slotName,
        System.Drawing.Rectangle captureRegion, List<System.Drawing.Rectangle> boundingBoxes)
    {
        BuildName = buildName;
        SlotName = slotName;
        MatchedCount = summary.MatchedCount;
        TotalCount = summary.TotalBuildAffixes;
        GaMatchedCount = summary.GaMatchedCount;
        MissingAffixes = new ObservableCollection<string>(summary.MissingAffixes);

        var newHighlights = new ObservableCollection<AffixHighlight>();
        for (int i = 0; i < results.Count; i++)
        {
            var r = results[i];
            if (!r.IsMatched) continue;

            var bbox = i < boundingBoxes.Count ? boundingBoxes[i] : new System.Drawing.Rectangle();
            newHighlights.Add(new AffixHighlight
            {
                Text = r.AffixName,
                IsGa = r.IsGa,
                Left = captureRegion.X + bbox.X / 2.0,   // /2 because OCR image is upscaled 2x
                Top = captureRegion.Y + bbox.Y / 2.0,
                Width = bbox.Width / 2.0,
                Height = bbox.Height / 2.0,
            });
        }
        Highlights = newHighlights;
        IsVisible = results.Any(r => r.IsMatched);
    }

    public void Hide()
    {
        IsVisible = false;
        Highlights.Clear();
    }

    public event PropertyChangedEventHandler? PropertyChanged;

    private void SetField<T>(ref T field, T value, [CallerMemberName] string? name = null)
    {
        if (!EqualityComparer<T>.Default.Equals(field, value))
        {
            field = value;
            PropertyChanged?.Invoke(this, new PropertyChangedEventArgs(name));
        }
    }
}

public class AffixHighlight : INotifyPropertyChanged
{
    public string Text { get; set; } = "";
    public bool IsGa { get; set; }
    public double Left { get; set; }
    public double Top { get; set; }
    public double Width { get; set; }
    public double Height { get; set; }

    public event PropertyChangedEventHandler? PropertyChanged;
}
```

- [ ] **Step 2: Create OverlayWindow XAML**

```xml
<!-- src/D4LootFilter/Overlay/OverlayWindow.xaml -->
<Window x:Class="D4LootFilter.Overlay.OverlayWindow"
        xmlns="http://schemas.microsoft.com/winfx/2006/xaml/presentation"
        xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml"
        xmlns:local="clr-namespace:D4LootFilter.Overlay"
        WindowStyle="None"
        AllowsTransparency="True"
        Background="Transparent"
        Topmost="True"
        ShowInTaskbar="False"
        WindowState="Maximized">

    <Grid x:Name="RootGrid" Visibility="{Binding IsVisible, Converter={StaticResource BoolToVisibility}}">
        <!-- Affix highlights drawn on Canvas -->
        <ItemsControl ItemsSource="{Binding Highlights}">
            <ItemsControl.ItemsPanel>
                <ItemsPanelTemplate>
                    <Canvas/>
                </ItemsPanelTemplate>
            </ItemsControl.ItemsPanel>
            <ItemsControl.ItemContainerStyle>
                <Style TargetType="ContentPresenter">
                    <Setter Property="Canvas.Left" Value="{Binding Left}"/>
                    <Setter Property="Canvas.Top" Value="{Binding Top}"/>
                </Style>
            </ItemsControl.ItemContainerStyle>
            <ItemsControl.ItemTemplate>
                <DataTemplate>
                    <Border Width="{Binding Width}" Height="{Binding Height}"
                            CornerRadius="2">
                        <Border.Style>
                            <Style TargetType="Border">
                                <Setter Property="Background" Value="#264CAF50"/>
                                <Setter Property="BorderBrush" Value="#4CAF50"/>
                                <Setter Property="BorderThickness" Value="3,0,0,0"/>
                                <Style.Triggers>
                                    <DataTrigger Binding="{Binding IsGa}" Value="True">
                                        <Setter Property="Background" Value="#26FFD700"/>
                                        <Setter Property="BorderBrush" Value="#FFD700"/>
                                    </DataTrigger>
                                </Style.Triggers>
                            </Style>
                        </Border.Style>
                    </Border>
                </DataTemplate>
            </ItemsControl.ItemTemplate>
        </ItemsControl>

        <!-- Mini panel -->
        <Border HorizontalAlignment="Right" VerticalAlignment="Top"
                Margin="0,180,20,0" Width="200"
                Background="#D9000000" BorderBrush="#444" BorderThickness="1"
                CornerRadius="6" Padding="12"
                Visibility="{Binding IsVisible, Converter={StaticResource BoolToVisibility}}">
            <StackPanel>
                <TextBlock Text="{Binding BuildName}" Foreground="White" FontSize="13" FontWeight="Bold" Margin="0,0,0,4"/>
                <TextBlock Foreground="#AAA" FontSize="11" Margin="0,0,0,4">
                    <Run Text="Slot: "/><Run Text="{Binding SlotName}"/>
                </TextBlock>
                <Grid Margin="0,0,0,4">
                    <Grid.ColumnDefinitions>
                        <ColumnDefinition Width="*"/>
                        <ColumnDefinition Width="Auto"/>
                    </Grid.ColumnDefinitions>
                    <Border Background="#333" CornerRadius="3" Height="6" Margin="0,0,8,0"/>
                    <TextBlock Grid.Column="1" Foreground="#4CAF50" FontSize="12" FontWeight="Bold">
                        <Run Text="{Binding MatchedCount}"/><Run Text="/"/><Run Text="{Binding TotalCount}"/>
                    </TextBlock>
                </Grid>
                <TextBlock Foreground="#FFD700" FontSize="11" Margin="0,0,0,4">
                    <Run Text="⭐ "/><Run Text="{Binding GaMatchedCount}"/><Run Text=" GA matched"/>
                </TextBlock>
                <Border BorderBrush="#333" BorderThickness="0,1,0,0" Padding="0,4,0,0">
                    <StackPanel>
                        <TextBlock Text="Missing:" Foreground="#888" FontSize="11" Margin="0,0,0,2"/>
                        <ItemsControl ItemsSource="{Binding MissingAffixes}">
                            <ItemsControl.ItemTemplate>
                                <DataTemplate>
                                    <TextBlock Foreground="#E57373" FontSize="11">
                                        <Run Text="• "/><Run Text="{Binding}"/>
                                    </TextBlock>
                                </DataTemplate>
                            </ItemsControl.ItemTemplate>
                        </ItemsControl>
                    </StackPanel>
                </Border>
            </StackPanel>
        </Border>
    </Grid>

    <Window.Resources>
        <BooleanToVisibilityConverter x:Key="BoolToVisibility"/>
    </Window.Resources>
</Window>
```

- [ ] **Step 3: Create OverlayWindow code-behind (click-through)**

```csharp
// src/D4LootFilter/Overlay/OverlayWindow.xaml.cs
using System.Runtime.InteropServices;
using System.Windows;
using System.Windows.Interop;

namespace D4LootFilter.Overlay;

public partial class OverlayWindow : Window
{
    private const int WS_EX_TRANSPARENT = 0x00000020;
    private const int GWL_EXSTYLE = -20;

    [DllImport("user32.dll")]
    private static extern int GetWindowLong(IntPtr hwnd, int index);

    [DllImport("user32.dll")]
    private static extern int SetWindowLong(IntPtr hwnd, int index, int newStyle);

    public OverlayWindow()
    {
        InitializeComponent();
        Loaded += OnLoaded;
    }

    private void OnLoaded(object sender, RoutedEventArgs e)
    {
        var hwnd = new WindowInteropHelper(this).Handle;
        int exStyle = GetWindowLong(hwnd, GWL_EXSTYLE);
        SetWindowLong(hwnd, GWL_EXSTYLE, exStyle | WS_EX_TRANSPARENT);
    }
}
```

- [ ] **Step 4: Build to verify compilation**

Run: `dotnet build src/D4LootFilter/D4LootFilter.csproj`
Expected: Build succeeded.

- [ ] **Step 5: Commit**

```bash
git add src/D4LootFilter/Overlay/
git commit -m "feat: add transparent click-through overlay window with affix highlights"
```

---

### Task 9: Hardcoded test profile

**Files:**
- Create: `src/D4LootFilter/TestData/test-profile.json`
- Create: `src/D4LootFilter/Services/ProfileService.cs`

- [ ] **Step 1: Create test profile JSON**

```json
// src/D4LootFilter/TestData/test-profile.json
{
  "id": "test-sorcerer",
  "name": "Sorcerer Ball Lightning",
  "source_url": "https://mobalytics.gg/diablo-4/builds/sorcerer-ball-lightning",
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
                  { "name": "Maximum Life", "is_ga": false },
                  { "name": "Total Armor", "is_ga": false },
                  { "name": "Intelligence", "is_ga": false }
                ]
              },
              {
                "slot": "Chest Armor",
                "name": "Archon Faulds",
                "affixes": [
                  { "name": "Maximum Life", "is_ga": true },
                  { "name": "Armor", "is_ga": false },
                  { "name": "Resistance to All Elements", "is_ga": false },
                  { "name": "Intelligence", "is_ga": false }
                ]
              },
              {
                "slot": "Gloves",
                "name": "Archon Gauntlets",
                "affixes": [
                  { "name": "Attack Speed", "is_ga": true },
                  { "name": "Critical Strike Chance", "is_ga": false },
                  { "name": "Lucky Hit Chance", "is_ga": false },
                  { "name": "Intelligence", "is_ga": false }
                ]
              },
              {
                "slot": "Pants",
                "name": "Archon Faulds",
                "affixes": [
                  { "name": "Maximum Life", "is_ga": false },
                  { "name": "Armor", "is_ga": false },
                  { "name": "Damage Reduction", "is_ga": true },
                  { "name": "Intelligence", "is_ga": false }
                ]
              },
              {
                "slot": "Boots",
                "name": "Archon Greaves",
                "affixes": [
                  { "name": "Movement Speed", "is_ga": false },
                  { "name": "Mana Cost Reduction", "is_ga": true },
                  { "name": "Intelligence", "is_ga": false },
                  { "name": "Ranks to Ball Lightning", "is_ga": false }
                ]
              },
              {
                "slot": "Amulet",
                "name": "Amulet",
                "affixes": [
                  { "name": "Cooldown Reduction", "is_ga": true },
                  { "name": "Mana Cost Reduction", "is_ga": false },
                  { "name": "Movement Speed", "is_ga": false },
                  { "name": "Ranks to Defensive Skills", "is_ga": false }
                ]
              },
              {
                "slot": "Ring",
                "name": "Ring",
                "affixes": [
                  { "name": "Critical Strike Chance", "is_ga": true },
                  { "name": "Lucky Hit Chance", "is_ga": false },
                  { "name": "Maximum Life", "is_ga": false },
                  { "name": "Resource Generation", "is_ga": false }
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
```

Add to `.csproj`:

```xml
<ItemGroup>
  <EmbeddedResource Include="TestData\test-profile.json" />
</ItemGroup>
```

- [ ] **Step 2: Create ProfileService**

```csharp
// src/D4LootFilter/Services/ProfileService.cs
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
```

- [ ] **Step 3: Build**

Run: `dotnet build src/D4LootFilter/D4LootFilter.csproj`
Expected: Build succeeded.

- [ ] **Step 4: Commit**

```bash
git add src/D4LootFilter/TestData/ src/D4LootFilter/Services/
git commit -m "feat: add test profile and profile service for loading build data"
```

---

### Task 10: Pipeline integration — wire capture → OCR → match → overlay

**Files:**
- Create: `src/D4LootFilter/Services/PipelineService.cs`
- Modify: `src/D4LootFilter/App.xaml.cs`
- Modify: `src/D4LootFilter/MainWindow.xaml`

- [ ] **Step 1: Create PipelineService**

```csharp
// src/D4LootFilter/Services/PipelineService.cs
using System.Drawing;
using D4LootFilter.Capture;
using D4LootFilter.Matching;
using D4LootFilter.Matching.Models;
using D4LootFilter.Ocr;
using D4LootFilter.Overlay;
using OpenCvSharp;

namespace D4LootFilter.Services;

public class PipelineService : IDisposable
{
    private readonly DxgiCapture _capture;
    private readonly TesseractOcrEngine _ocr;
    private readonly AffixMatcher _matcher;
    private readonly SlotDetector _slotDetector;
    private readonly FrameChangeDetector _changeDetector;
    private readonly TooltipDetector _tooltipDetector;
    private readonly AffixNormalizer _normalizer;
    private readonly OverlayViewModel _overlayVm;
    private readonly ProfileService _profileService;

    private CancellationTokenSource? _cts;
    private Task? _captureTask;
    private OpenCvSharp.Rect _captureRegion;
    private int _pollingDelayMs = 33; // ~30fps

    public PipelineService(
        OverlayViewModel overlayVm,
        ProfileService profileService,
        string tessdataPath)
    {
        _capture = new DxgiCapture();
        _ocr = new TesseractOcrEngine(tessdataPath);
        _matcher = new AffixMatcher(maxDistance: 2);
        _slotDetector = new SlotDetector();
        _changeDetector = new FrameChangeDetector();
        _tooltipDetector = new TooltipDetector();
        _normalizer = new AffixNormalizer();
        _overlayVm = overlayVm;
        _profileService = profileService;
    }

    public void SetCaptureRegion(int x, int y, int width, int height)
    {
        _captureRegion = new OpenCvSharp.Rect(x, y, width, height);
    }

    public void Start()
    {
        _cts = new CancellationTokenSource();
        _captureTask = Task.Factory.StartNew(
            () => CaptureLoop(_cts.Token),
            _cts.Token,
            TaskCreationOptions.LongRunning,
            TaskScheduler.Default
        );
    }

    public void Stop()
    {
        _cts?.Cancel();
        _captureTask?.Wait(TimeSpan.FromSeconds(2));
    }

    private void CaptureLoop(CancellationToken ct)
    {
        int noTooltipFrames = 0;

        while (!ct.IsCancellationRequested)
        {
            try
            {
                using var fullFrame = _capture.CaptureFrame(timeoutMs: 100);
                if (fullFrame == null)
                {
                    Thread.Sleep(_pollingDelayMs);
                    continue;
                }

                using var regionFrame = ImagePreprocessor.CropRegion(fullFrame, _captureRegion);
                if (!_changeDetector.HasChanged(regionFrame))
                {
                    Thread.Sleep(_pollingDelayMs);
                    continue;
                }

                var tooltipBounds = _tooltipDetector.DetectTooltipBounds(regionFrame);
                if (tooltipBounds == null)
                {
                    noTooltipFrames++;
                    if (noTooltipFrames > 3)
                    {
                        System.Windows.Application.Current?.Dispatcher.Invoke(() => _overlayVm.Hide());
                        noTooltipFrames = 0;
                    }
                    Thread.Sleep(_pollingDelayMs);
                    continue;
                }

                noTooltipFrames = 0;

                using var tooltip = ImagePreprocessor.CropRegion(regionFrame, tooltipBounds.Value);
                using var preprocessed = ImagePreprocessor.Preprocess(tooltip);
                var ocrLines = _ocr.ExtractLines(preprocessed);

                if (ocrLines.Count == 0)
                {
                    Thread.Sleep(_pollingDelayMs);
                    continue;
                }

                var profile = _profileService.ActiveProfile;
                var variant = profile?.GetActiveVariant();
                if (variant == null)
                {
                    Thread.Sleep(_pollingDelayMs);
                    continue;
                }

                var textLines = ocrLines.Select(l => l.Text).ToArray();
                var slot = _slotDetector.DetectSlot(textLines);
                var buildAffixes = slot != null
                    ? variant.GetAffixesForSlot(slot)
                    : variant.GetAllAffixes();

                if (buildAffixes.Count == 0)
                {
                    Thread.Sleep(_pollingDelayMs);
                    continue;
                }

                var affixLines = textLines.Where(l => _normalizer.IsLikelyAffix(l)).ToArray();
                var results = _matcher.Match(affixLines, buildAffixes);
                var summary = AffixMatcher.Summarize(results, buildAffixes);

                var captureRect = new Rectangle(
                    _captureRegion.X + tooltipBounds.Value.X,
                    _captureRegion.Y + tooltipBounds.Value.Y,
                    tooltipBounds.Value.Width,
                    tooltipBounds.Value.Height
                );
                var boundingBoxes = ocrLines
                    .Where(l => new AffixNormalizer().IsLikelyAffix(l.Text))
                    .Select(l => l.BoundingBox)
                    .ToList();

                System.Windows.Application.Current?.Dispatcher.Invoke(() =>
                {
                    _overlayVm.Update(results, summary, profile!.Name, slot ?? "Unknown", captureRect, boundingBoxes);
                });
            }
            catch (Exception)
            {
                // Swallow capture errors, continue loop
            }

            Thread.Sleep(_pollingDelayMs);
        }
    }

    public void Dispose()
    {
        Stop();
        _capture.Dispose();
        _ocr.Dispose();
    }
}
```

- [ ] **Step 2: Update App.xaml.cs for startup wiring**

```csharp
// src/D4LootFilter/App.xaml.cs
using System.IO;
using System.Threading;
using System.Windows;
using D4LootFilter.Overlay;
using D4LootFilter.Services;

namespace D4LootFilter;

public partial class App : Application
{
    private static Mutex? _mutex;
    private PipelineService? _pipeline;
    private OverlayWindow? _overlay;

    protected override void OnStartup(StartupEventArgs e)
    {
        _mutex = new Mutex(true, "D4LootFilter_SingleInstance", out bool createdNew);
        if (!createdNew)
        {
            MessageBox.Show("D4 Loot Filter is already running.", "D4 Loot Filter", MessageBoxButton.OK);
            Shutdown();
            return;
        }

        base.OnStartup(e);

        var vm = new OverlayViewModel();
        var profileService = new ProfileService();
        profileService.LoadTestProfile();

        var tessdataPath = Path.Combine(AppContext.BaseDirectory, "tessdata");

        _overlay = new OverlayWindow { DataContext = vm };
        _overlay.Show();

        _pipeline = new PipelineService(vm, profileService, tessdataPath);
        // Default capture region — user can recalibrate later
        // For testing: right 40% of a 1920x1080 screen
        _pipeline.SetCaptureRegion(1150, 100, 700, 800);
        _pipeline.Start();
    }

    protected override void OnExit(ExitEventArgs e)
    {
        _pipeline?.Dispose();
        _mutex?.ReleaseMutex();
        _mutex?.Dispose();
        base.OnExit(e);
    }
}
```

- [ ] **Step 3: Update MainWindow.xaml to be hidden (app runs as overlay only)**

```xml
<!-- src/D4LootFilter/MainWindow.xaml -->
<Window x:Class="D4LootFilter.MainWindow"
        xmlns="http://schemas.microsoft.com/winfx/2006/xaml/presentation"
        xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml"
        Title="D4 Loot Filter" Height="1" Width="1"
        WindowStyle="None" ShowInTaskbar="False"
        Visibility="Hidden">
</Window>
```

Remove the `StartupUri="MainWindow.xaml"` from `App.xaml` so the app starts via `OnStartup` only.

- [ ] **Step 4: Build the full solution**

Run: `dotnet build src/D4LootFilter.sln`
Expected: Build succeeded.

- [ ] **Step 5: Run all tests**

Run: `dotnet test src/D4LootFilter.sln --verbosity normal`
Expected: All tests PASS.

- [ ] **Step 6: Commit**

```bash
git add src/
git commit -m "feat: wire capture → OCR → match → overlay pipeline end-to-end"
```

---

### Task 11: Manual integration test — run over D4 or test image

- [ ] **Step 1: Run the application**

```powershell
dotnet run --project src/D4LootFilter/D4LootFilter.csproj
```

- [ ] **Step 2: Verify with D4 running (or any window with tooltip-like content)**

Test checklist:
1. App starts without errors
2. Overlay window is transparent and click-through
3. When a D4 tooltip appears in the capture region, OCR runs and highlights appear
4. Gold highlights for GA affixes, green for regular matches
5. Mini-panel shows build name, slot, match count, missing affixes
6. Highlights disappear when tooltip is no longer visible
7. ESC (or close from Task Manager) stops the app

- [ ] **Step 3: Document any issues found and fix**

If OCR accuracy is low:
- Adjust `DarkThreshold` in `TooltipDetector.cs`
- Adjust `_minConfidence` in `TesseractOcrEngine` constructor
- Tweak the capture region coordinates in `App.xaml.cs`

- [ ] **Step 4: Final commit with any fixes**

```bash
git add -A
git commit -m "fix: tune pipeline parameters after integration testing"
```

---

## Summary

| Task | Component | Estimated Time |
|---|---|---|
| 1 | Solution scaffold | 10 min |
| 2 | Data models | 15 min |
| 3 | Slot detector | 10 min |
| 4 | Affix normalizer + matcher | 20 min |
| 5 | OCR pipeline | 20 min |
| 6 | DXGI screen capture | 15 min |
| 7 | Tooltip detector | 10 min |
| 8 | Overlay window | 15 min |
| 9 | Test profile + service | 10 min |
| 10 | Pipeline integration | 20 min |
| 11 | Manual integration test | 15 min |
| **Total** | | **~2.5 hours** |

**Result:** A working .exe that captures screen, detects D4 tooltips, runs OCR, matches affixes against a hardcoded Sorcerer build, and highlights matches with a transparent overlay.

**Next plans:**
- **Plan B** — Mobalytics GraphQL scraper (import builds from URL)
- **Plan C** — Full UI (system tray, settings window, profile management, region calibration)
