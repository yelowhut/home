using System.Windows;
using System.Windows.Controls;
using System.Windows.Media;
using D4LootFilter.Matching.Models;

namespace D4LootFilter.Views;

public partial class BuildViewerWindow : Window
{
    private static readonly HashSet<string> ArmorSlots = ["Helm", "Chest Armor", "Gloves", "Pants", "Boots"];
    private static readonly HashSet<string> WeaponSlots = ["Weapon", "Slashing Weapon", "Bludgeoning Weapon", "Off-Weapon"];
    private static readonly HashSet<string> JewelrySlots = ["Amulet", "Ring", "Off-Hand"];

    private static readonly string[] ArmorSlotOrder = ["Helm", "Chest Armor", "Gloves", "Pants", "Boots"];
    private static readonly string[] WeaponSlotOrder = ["Weapon", "Slashing Weapon", "Bludgeoning Weapon", "Off-Weapon"];
    private static readonly string[] JewelrySlotOrder = ["Amulet", "Ring", "Off-Hand"];

    private static readonly Dictionary<string, string> SlotIcons = new()
    {
        ["Helm"] = "\U0001FA96",
        ["Chest Armor"] = "\U0001F9E5",
        ["Gloves"] = "\U0001F9E4",
        ["Pants"] = "\U0001F456",
        ["Boots"] = "\U0001F462",
        ["Weapon"] = "\u2694\ufe0f",
        ["Slashing Weapon"] = "\u2694\ufe0f",
        ["Bludgeoning Weapon"] = "\U0001F528",
        ["Off-Weapon"] = "\U0001F5E1\ufe0f",
        ["Amulet"] = "\U0001F4BF",
        ["Ring"] = "\U0001F48D",
        ["Off-Hand"] = "\U0001F6E1️",
    };

    private static readonly Dictionary<string, Color> RarityColors = new()
    {
        ["Mythic"] = (Color)ColorConverter.ConvertFromString("#bf4aff"),
        ["Unique"] = (Color)ColorConverter.ConvertFromString("#d1a781"),
        ["Chaos"] = (Color)ColorConverter.ConvertFromString("#ff4a4a"),
        ["Legendary"] = (Color)ColorConverter.ConvertFromString("#d98c3c"),
    };

    public BuildViewerWindow()
    {
        InitializeComponent();
    }

    public void LoadBuild(BuildProfile profile, BuildVariant variant)
    {
        BuildNameText.Text = $"{profile.Name} — {variant.Name}";
        BuildInfoText.Text = $"{profile.Class}";

        var allItems = variant.Equipment.Categories
            .SelectMany(c => c.Items)
            .Where(i => ArmorSlots.Contains(i.Slot) || WeaponSlots.Contains(i.Slot) || JewelrySlots.Contains(i.Slot))
            .ToList();

        ArmorColumn.Children.Clear();
        WeaponsColumn.Children.Clear();
        JewelryColumn.Children.Clear();

        AddItems(ArmorColumn, allItems, ArmorSlotOrder);
        AddItems(WeaponsColumn, allItems, WeaponSlotOrder);
        AddItems(JewelryColumn, allItems, JewelrySlotOrder);
    }

    private static void AddItems(Panel column, List<EquipmentItem> allItems, string[] slotOrder)
    {
        foreach (var slotName in slotOrder)
        {
            foreach (var item in allItems.Where(i => i.Slot == slotName))
                column.Children.Add(CreateItemCard(item));
        }
    }

    private static UIElement CreateItemCard(EquipmentItem item)
    {
        var rarityColor = RarityColors.GetValueOrDefault(item.Rarity, RarityColors["Legendary"]);

        var card = new Border
        {
            Background = new SolidColorBrush((Color)ColorConverter.ConvertFromString("#16213e")),
            BorderBrush = new SolidColorBrush(Color.FromArgb(80, rarityColor.R, rarityColor.G, rarityColor.B)),
            BorderThickness = new Thickness(1),
            CornerRadius = new CornerRadius(4),
            Padding = new Thickness(8, 7, 8, 7),
            Margin = new Thickness(0, 0, 0, 8),
        };

        var outerStack = new DockPanel();
        var icon = SlotIcons.GetValueOrDefault(item.Slot, "\U0001F4E6");

        var iconBlock = new TextBlock
        {
            Text = icon,
            FontSize = 24,
            VerticalAlignment = VerticalAlignment.Top,
            Margin = new Thickness(0, 0, 8, 0),
        };

        var textStack = new StackPanel();

        // Slot label
        var slotLabel = string.IsNullOrWhiteSpace(item.DisplaySlot)
            ? item.Slot == "Off-Weapon" ? "Off-Hand Weapon" : item.Slot
            : item.DisplaySlot;
        textStack.Children.Add(new TextBlock
        {
            Text = slotLabel,
            FontSize = 9,
            Foreground = new SolidColorBrush((Color)ColorConverter.ConvertFromString("#666666")),
            Margin = new Thickness(0, 0, 0, 2),
        });

        // Item name with rarity color
        var nameText = CreateSelectableText(item.Name, 12, rarityColor, FontWeights.SemiBold);
        textStack.Children.Add(nameText);

        // Rarity tag
        if (!string.IsNullOrEmpty(item.Rarity))
        {
            var tag = new Border
            {
                Background = new SolidColorBrush(Color.FromArgb(25, rarityColor.R, rarityColor.G, rarityColor.B)),
                BorderBrush = new SolidColorBrush(Color.FromArgb(100, rarityColor.R, rarityColor.G, rarityColor.B)),
                BorderThickness = new Thickness(1),
                CornerRadius = new CornerRadius(3),
                Padding = new Thickness(6, 1, 6, 1),
                Margin = new Thickness(0, 3, 0, 4),
                HorizontalAlignment = HorizontalAlignment.Left,
            };
            tag.Child = new TextBlock
            {
                Text = item.Rarity.ToUpperInvariant(),
                FontSize = 8,
                Foreground = new SolidColorBrush(rarityColor),
                FontWeight = FontWeights.Bold,
            };
            textStack.Children.Add(tag);
        }

        // Affixes
        foreach (var affix in item.Affixes)
        {
            if (affix.IsGa)
            {
                textStack.Children.Add(CreateSelectableText($"⭐ {affix.Name}", 11,
                    (Color)ColorConverter.ConvertFromString("#ffd700")));
            }
            else
            {
                textStack.Children.Add(CreateSelectableText($"• {affix.Name}", 11,
                    (Color)ColorConverter.ConvertFromString("#e0e0e0")));
            }
        }

        // Tempering affixes
        foreach (var temper in item.TemperingAffixes)
        {
            var temperColor = temper.IsGa
                ? (Color)ColorConverter.ConvertFromString("#ffd700")
                : (Color)ColorConverter.ConvertFromString("#7ba4d4");
            var suffix = temper.IsGa ? " ⭐" : "";
            textStack.Children.Add(CreateSelectableText($"⚒ {temper.Name}{suffix}", 11, temperColor));
        }

        DockPanel.SetDock(iconBlock, Dock.Left);
        outerStack.Children.Add(iconBlock);
        outerStack.Children.Add(textStack);

        card.Child = outerStack;
        return card;
    }

    private static TextBox CreateSelectableText(string text, double fontSize, Color color,
        FontWeight? fontWeight = null)
    {
        return new TextBox
        {
            Text = text,
            FontSize = fontSize,
            Foreground = new SolidColorBrush(color),
            FontWeight = fontWeight ?? FontWeights.Normal,
            Background = Brushes.Transparent,
            BorderThickness = new Thickness(0),
            IsReadOnly = true,
            IsTabStop = false,
            Padding = new Thickness(0),
            Margin = new Thickness(0, 1, 0, 1),
            TextWrapping = TextWrapping.Wrap,
            Cursor = System.Windows.Input.Cursors.Arrow,
        };
    }
}
