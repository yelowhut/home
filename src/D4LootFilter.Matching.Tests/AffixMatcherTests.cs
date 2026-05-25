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
