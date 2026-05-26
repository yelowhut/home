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
                    var temperingAffixes = ParseTemperingStats(entity);

                    items.Add((category, new EquipmentItem
                    {
                        Slot = slotName,
                        Name = itemTitle,
                        Category = category,
                        Affixes = affixes,
                        TemperingAffixes = temperingAffixes,
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
            modifiers.ValueKind != JsonValueKind.Object ||
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

    private static List<Affix> ParseTemperingStats(JsonElement entity)
    {
        var affixes = new List<Affix>();
        if (!entity.TryGetProperty("modifiers", out var modifiers) ||
            modifiers.ValueKind != JsonValueKind.Object ||
            !modifiers.TryGetProperty("temperingStats", out var temperingStats) ||
            temperingStats.ValueKind != JsonValueKind.Array)
            return affixes;

        foreach (var stat in temperingStats.EnumerateArray())
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
