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
