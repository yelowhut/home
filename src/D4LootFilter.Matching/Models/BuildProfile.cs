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
