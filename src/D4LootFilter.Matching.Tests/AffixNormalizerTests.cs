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
