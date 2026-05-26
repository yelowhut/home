using System.Windows;
using System.Windows.Controls;
using D4LootFilter.Matching.Models;
using D4LootFilter.Scraper;

namespace D4LootFilter.Views;

public partial class CaptureRegionView : UserControl
{
    private SettingsService? _settingsService;
    private Action<CaptureRegion?>? _onRegionChanged;

    public CaptureRegionView()
    {
        InitializeComponent();
    }

    public void Init(SettingsService settingsService, Action<CaptureRegion?> onRegionChanged)
    {
        _settingsService = settingsService;
        _onRegionChanged = onRegionChanged;
        RefreshDisplay();
    }

    public void RefreshDisplay()
    {
        if (_settingsService == null) return;
        var settings = _settingsService.Load();
        var screenW = (int)SystemParameters.PrimaryScreenWidth;
        var screenH = (int)SystemParameters.PrimaryScreenHeight;
        var key = $"{screenW}x{screenH}";

        if (settings.CaptureRegions.TryGetValue(key, out var region))
            RegionInfo.Text = $"Region: ({region.X}, {region.Y}) {region.Width}×{region.Height}";
        else
            RegionInfo.Text = "No region set — using full screen";

        ResolutionInfo.Text = $"Screen: {key}";
    }

    private void OnRecalibrate(object sender, RoutedEventArgs e)
    {
        var overlay = new CalibrationOverlay();
        Window.GetWindow(this)?.Hide();
        overlay.ShowDialog();
        Window.GetWindow(this)?.Show();

        if (overlay.SelectedRegion is { } rect)
        {
            var settings = _settingsService!.Load();
            var screenW = (int)SystemParameters.PrimaryScreenWidth;
            var screenH = (int)SystemParameters.PrimaryScreenHeight;
            var key = $"{screenW}x{screenH}";

            var newRegions = new Dictionary<string, CaptureRegion>(settings.CaptureRegions)
            {
                [key] = new CaptureRegion(rect.X, rect.Y, rect.Width, rect.Height)
            };
            var updated = settings with { CaptureRegions = newRegions };
            _settingsService!.Save(updated);
            _onRegionChanged?.Invoke(new CaptureRegion(rect.X, rect.Y, rect.Width, rect.Height));
            RefreshDisplay();
        }
    }

    private void OnUseFullScreen(object sender, RoutedEventArgs e)
    {
        _onRegionChanged?.Invoke(null);
        var settings = _settingsService!.Load();
        var screenW = (int)SystemParameters.PrimaryScreenWidth;
        var screenH = (int)SystemParameters.PrimaryScreenHeight;
        var key = $"{screenW}x{screenH}";
        var newRegions = new Dictionary<string, CaptureRegion>(settings.CaptureRegions);
        newRegions.Remove(key);
        _settingsService!.Save(settings with { CaptureRegions = newRegions });
        RefreshDisplay();
    }
}
