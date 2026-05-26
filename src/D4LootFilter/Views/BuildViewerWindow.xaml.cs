using System.Windows;
using System.Windows.Controls;
using System.Windows.Documents;
using System.Windows.Media;
using D4LootFilter.Matching.Models;

namespace D4LootFilter.Views;

public partial class BuildViewerWindow : Window
{
    private static readonly HashSet<string> LeftSlots = ["Helm", "Chest Armor", "Gloves", "Pants", "Boots", "Weapon"];
    private static readonly HashSet<string> RightSlots = ["Amulet", "Ring", "Off-Hand", "Off-Weapon"];

    private static readonly string[] LeftSlotOrder = ["Helm", "Chest Armor", "Gloves", "Pants", "Boots", "Weapon"];
    private static readonly string[] RightSlotOrder = ["Amulet", "Ring", "Off-Hand", "Off-Weapon"];

    private static readonly Dictionary<string, string> SlotIcons = new()
    {
        ["Helm"] = "\U0001FA96",
        ["Chest Armor"] = "\U0001F9E5",
        ["Gloves"] = "\U0001F9E4",
        ["Pants"] = "\U0001F456",
        ["Boots"] = "\U0001F462",
        ["Weapon"] = "⚔️",
        ["Off-Weapon"] = "\U0001F5E1️",
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
            .Where(i => LeftSlots.Contains(i.Slot) || RightSlots.Contains(i.Slot))
            .ToList();

        LeftColumn.Children.Clear();
        RightColumn.Children.Clear();

        foreach (var slotName in LeftSlotOrder)
        {
            foreach (var item in allItems.Where(i => i.Slot == slotName))
                LeftColumn.Children.Add(CreateItemCard(item, isRightAligned: false));
        }

        foreach (var slotName in RightSlotOrder)
        {
            foreach (var item in allItems.Where(i => i.Slot == slotName))
                RightColumn.Children.Add(CreateItemCard(item, isRightAligned: true));
        }
    }

    private static UIElement CreateItemCard(EquipmentItem item, bool isRightAligned)
    {
        var rarityColor = RarityColors.GetValueOrDefault(item.Rarity, RarityColors["Legendary"]);

        var card = new Border
        {
            Background = new SolidColorBrush((Color)ColorConverter.ConvertFromString("#16213e")),
            BorderBrush = new SolidColorBrush(Color.FromArgb(80, rarityColor.R, rarityColor.G, rarityColor.B)),
            BorderThickness = new Thickness(1),
            CornerRadius = new CornerRadius(4),
            Padding = new Thickness(10, 8, 10, 8),
            Margin = new Thickness(0, 0, 0, 8),
        };

        var outerStack = new DockPanel();
        var icon = SlotIcons.GetValueOrDefault(item.Slot, "\U0001F4E6");

        var iconBlock = new TextBlock
        {
            Text = icon,
            FontSize = 28,
            VerticalAlignment = VerticalAlignment.Top,
            Margin = isRightAligned ? new Thickness(10, 0, 0, 0) : new Thickness(0, 0, 10, 0),
        };

        var textStack = new StackPanel();

        // Slot label
        var slotLabel = item.Slot == "Off-Weapon" ? "Off-Hand Weapon" : item.Slot;
        textStack.Children.Add(new TextBlock
        {
            Text = slotLabel,
            FontSize = 10,
            Foreground = new SolidColorBrush((Color)ColorConverter.ConvertFromString("#666666")),
            Margin = new Thickness(0, 0, 0, 2),
        });

        // Item name with rarity color
        var nameText = CreateSelectableText(item.Name, 13, rarityColor, FontWeights.SemiBold);
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
                FontSize = 9,
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
                textStack.Children.Add(CreateSelectableText($"⭐ {affix.Name}", 12,
                    (Color)ColorConverter.ConvertFromString("#ffd700")));
            }
            else
            {
                textStack.Children.Add(CreateSelectableText($"• {affix.Name}", 12,
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
            textStack.Children.Add(CreateSelectableText($"⚒ {temper.Name}{suffix}", 12, temperColor));
        }

        if (isRightAligned)
        {
            DockPanel.SetDock(iconBlock, Dock.Right);
            outerStack.Children.Add(iconBlock);
            outerStack.Children.Add(textStack);
        }
        else
        {
            DockPanel.SetDock(iconBlock, Dock.Left);
            outerStack.Children.Add(iconBlock);
            outerStack.Children.Add(textStack);
        }

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
