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
        var searchLines = lines.Take(8).ToList();

        // Try each line individually
        foreach (var line in searchLines)
        {
            var result = MatchLine(line);
            if (result != null) return result;
        }

        // Try concatenating consecutive lines (OCR may split "Chest\nArmor")
        for (int i = 0; i < searchLines.Count - 1; i++)
        {
            var combined = searchLines[i] + " " + searchLines[i + 1];
            var result = MatchLine(combined);
            if (result != null) return result;
        }

        return null;
    }

    private static string? MatchLine(string line)
    {
        foreach (var (pattern, slot) in SlotPatterns)
        {
            if (Regex.IsMatch(line, $@"\b{Regex.Escape(pattern)}\b", RegexOptions.IgnoreCase))
                return slot;
        }
        return null;
    }
}
