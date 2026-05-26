using System.Windows;
using System.Windows.Controls;
using System.Windows.Documents;
using System.Windows.Media;
using D4LootFilter.Matching.Models;

namespace D4LootFilter.Views;

public partial class BuildViewerWindow : Window
{
    private static readonly string[] LeftSlots = ["Helm", "Chest Armor", "Gloves", "Pants", "Boots", "Weapon"];
    private static readonly string[] RightSlots = ["Amulet", "Ring", "Off-Hand"];

    private static readonly Dictionary<string, string> SlotIcons = new()
    {
        ["Helm"] = "🪖",
        ["Chest Armor"] = "🧥",
        ["Gloves"] = "🧤",
        ["Pants"] = "👖",
        ["Boots"] = "👢",
        ["Weapon"] = "⚔️",
        ["Amulet"] = "📿",
        ["Ring"] = "💍",
        ["Off-Hand"] = "🛡️",
    };

    public BuildViewerWindow()
    {
        InitializeComponent();
    }

    public void LoadBuild(BuildProfile profile, BuildVariant variant)
    {
        BuildNameText.Text = $"{profile.Name} — {variant.Name}";
        BuildInfoText.Text = $"{profile.Class} • {variant.Equipment.Categories.SelectMany(c => c.Items).Count()} items";

        var allItems = variant.Equipment.Categories
            .SelectMany(c => c.Items)
            .ToList();

        LeftColumn.Children.Clear();
        RightColumn.Children.Clear();

        foreach (var slotName in LeftSlots)
        {
            var items = allItems.Where(i => i.Slot == slotName).ToList();
            foreach (var item in items)
                LeftColumn.Children.Add(CreateItemCard(item, isRightAligned: false));
        }

        foreach (var slotName in RightSlots)
        {
            var items = allItems.Where(i => i.Slot == slotName).ToList();
            foreach (var item in items)
                RightColumn.Children.Add(CreateItemCard(item, isRightAligned: true));
        }

        // Any items with slots not in left/right go to left
        var coveredSlots = LeftSlots.Concat(RightSlots).ToHashSet();
        foreach (var item in allItems.Where(i => !coveredSlots.Contains(i.Slot)))
            LeftColumn.Children.Add(CreateItemCard(item, isRightAligned: false));
    }

    private static UIElement CreateItemCard(EquipmentItem item, bool isRightAligned)
    {
        var card = new Border
        {
            Background = new SolidColorBrush((Color)ColorConverter.ConvertFromString("#16213e")),
            BorderBrush = new SolidColorBrush((Color)ColorConverter.ConvertFromString("#2a2a4a")),
            BorderThickness = new Thickness(1),
            CornerRadius = new CornerRadius(4),
            Padding = new Thickness(10, 8, 10, 8),
            Margin = new Thickness(0, 0, 0, 8),
        };

        var outerStack = new DockPanel();
        var icon = SlotIcons.GetValueOrDefault(item.Slot, "📦");

        var iconBlock = new TextBlock
        {
            Text = icon,
            FontSize = 28,
            VerticalAlignment = VerticalAlignment.Top,
            Margin = isRightAligned ? new Thickness(10, 0, 0, 0) : new Thickness(0, 0, 10, 0),
        };

        var textStack = new StackPanel();

        // Item name + category tag
        var headerPanel = new WrapPanel();
        headerPanel.Children.Add(new TextBlock
        {
            Text = $"{item.Slot}",
            FontSize = 11,
            Foreground = new SolidColorBrush((Color)ColorConverter.ConvertFromString("#888888")),
            Margin = new Thickness(0, 0, 6, 0),
            VerticalAlignment = VerticalAlignment.Center,
        });
        headerPanel.Children.Add(new TextBlock
        {
            Text = item.Name,
            FontSize = 13,
            FontWeight = FontWeights.SemiBold,
            Foreground = new SolidColorBrush(Colors.White),
            VerticalAlignment = VerticalAlignment.Center,
        });

        if (!string.IsNullOrEmpty(item.Category) && item.Category != "Other")
        {
            var tagColor = item.Category == "Uniques"
                ? (Color)ColorConverter.ConvertFromString("#d1a781")
                : (Color)ColorConverter.ConvertFromString("#d98c3c");

            var tag = new Border
            {
                Background = new SolidColorBrush(Color.FromArgb(30, tagColor.R, tagColor.G, tagColor.B)),
                BorderBrush = new SolidColorBrush(tagColor),
                BorderThickness = new Thickness(1),
                CornerRadius = new CornerRadius(3),
                Padding = new Thickness(6, 1, 6, 1),
                Margin = new Thickness(6, 0, 0, 0),
                VerticalAlignment = VerticalAlignment.Center,
            };
            tag.Child = new TextBlock
            {
                Text = item.Category == "Uniques" ? "UNIQUE" : "LEGENDARY",
                FontSize = 9,
                Foreground = new SolidColorBrush(tagColor),
                FontWeight = FontWeights.Bold,
            };
            headerPanel.Children.Add(tag);
        }

        textStack.Children.Add(headerPanel);

        // Affixes
        foreach (var affix in item.Affixes)
        {
            var affixText = new TextBlock { FontSize = 12, Margin = new Thickness(0, 2, 0, 0) };
            if (affix.IsGa)
            {
                affixText.Inlines.Add(new Run("⭐ ") { Foreground = new SolidColorBrush((Color)ColorConverter.ConvertFromString("#ffd700")) });
                affixText.Inlines.Add(new Run(affix.Name) { Foreground = new SolidColorBrush((Color)ColorConverter.ConvertFromString("#ffd700")) });
            }
            else
            {
                affixText.Inlines.Add(new Run("• ") { Foreground = new SolidColorBrush((Color)ColorConverter.ConvertFromString("#888888")) });
                affixText.Inlines.Add(new Run(affix.Name) { Foreground = new SolidColorBrush((Color)ColorConverter.ConvertFromString("#e0e0e0")) });
            }
            textStack.Children.Add(affixText);
        }

        // Tempering affixes
        foreach (var temper in item.TemperingAffixes)
        {
            var temperText = new TextBlock { FontSize = 12, Margin = new Thickness(0, 2, 0, 0) };
            var temperColor = temper.IsGa
                ? (Color)ColorConverter.ConvertFromString("#ffd700")
                : (Color)ColorConverter.ConvertFromString("#7ba4d4");
            temperText.Inlines.Add(new Run("⚒ ") { Foreground = new SolidColorBrush(temperColor) });
            temperText.Inlines.Add(new Run(temper.Name) { Foreground = new SolidColorBrush(temperColor) });
            if (temper.IsGa)
                temperText.Inlines.Add(new Run(" ⭐") { Foreground = new SolidColorBrush((Color)ColorConverter.ConvertFromString("#ffd700")) });
            textStack.Children.Add(temperText);
        }

        if (isRightAligned)
        {
            // Text on left, icon on right
            DockPanel.SetDock(iconBlock, Dock.Right);
            outerStack.Children.Add(iconBlock);
            outerStack.Children.Add(textStack);
        }
        else
        {
            // Icon on left, text on right
            DockPanel.SetDock(iconBlock, Dock.Left);
            outerStack.Children.Add(iconBlock);
            outerStack.Children.Add(textStack);
        }

        card.Child = outerStack;
        return card;
    }
}
