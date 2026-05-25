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
