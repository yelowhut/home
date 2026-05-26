using System.Drawing;
using System.Windows;
using System.Windows.Controls;
using D4LootFilter.Matching.Models;
using D4LootFilter.Scraper;
using D4LootFilter.Views;
using Hardcodet.Wpf.TaskbarNotification;

namespace D4LootFilter.TrayIcon;

public class TrayIconManager : IDisposable
{
    private readonly TaskbarIcon _trayIcon;
    private readonly ProfileService _profileService;
    private readonly SettingsService _settingsService;
    private readonly Action _onPauseResume;
    private readonly Action _onExit;
    private readonly Func<SettingsWindow> _getSettingsWindow;
    private bool _isPaused;

    public TrayIconManager(
        ProfileService profileService,
        SettingsService settingsService,
        Action onPauseResume,
        Action onExit,
        Func<SettingsWindow> getSettingsWindow)
    {
        _profileService = profileService;
        _settingsService = settingsService;
        _onPauseResume = onPauseResume;
        _onExit = onExit;
        _getSettingsWindow = getSettingsWindow;

        _trayIcon = new TaskbarIcon
        {
            Icon = CreateIcon(),
            ToolTipText = "D4 Loot Filter",
        };
        _trayIcon.TrayMouseDoubleClick += (_, _) => _getSettingsWindow().ShowOnTab(0);
        RebuildMenu();
    }

    public void UpdateStatus(bool isPaused)
    {
        _isPaused = isPaused;
        var profile = _profileService.ActiveProfile;
        var status = profile == null ? "No Profile" : isPaused ? "Paused" : "Running";
        _trayIcon.ToolTipText = $"D4 Loot Filter — {status}";
        RebuildMenu();
    }

    private void RebuildMenu()
    {
        var menu = new ContextMenu();

        var profile = _profileService.ActiveProfile;
        var statusText = profile != null
            ? $"{profile.Name} — {profile.GetActiveVariant()?.Name ?? "?"}"
            : "No profile loaded";
        var statusItem = new MenuItem { Header = statusText, IsEnabled = false };
        menu.Items.Add(statusItem);
        menu.Items.Add(new Separator());

        var switchMenu = new MenuItem { Header = "Switch Profile" };
        var profiles = _profileService.ListProfiles();
        var settings = _settingsService.Load();
        foreach (var p in profiles)
        {
            var profileMenu = new MenuItem { Header = $"{p.Name} ({p.Class})" };
            foreach (var v in p.Variants)
            {
                var isActive = p.Id == settings.ActiveProfileId && v.Id == settings.ActiveVariantId;
                var variantItem = new MenuItem
                {
                    Header = v.Name,
                    IsCheckable = true,
                    IsChecked = isActive,
                };
                var capturedProfile = p;
                var capturedVariant = v;
                variantItem.Click += (_, _) =>
                {
                    var s = _settingsService.Load() with
                    {
                        ActiveProfileId = capturedProfile.Id,
                        ActiveVariantId = capturedVariant.Id,
                    };
                    _settingsService.Save(s);
                    _profileService.SetActive(capturedProfile.Id);
                    UpdateStatus(_isPaused);
                };
                profileMenu.Items.Add(variantItem);
            }
            switchMenu.Items.Add(profileMenu);
        }
        menu.Items.Add(switchMenu);
        menu.Items.Add(new Separator());

        var pauseItem = new MenuItem { Header = _isPaused ? "Resume" : "Pause" };
        pauseItem.Click += (_, _) => _onPauseResume();
        menu.Items.Add(pauseItem);

        var settingsItem = new MenuItem { Header = "Settings..." };
        settingsItem.Click += (_, _) => _getSettingsWindow().ShowOnTab(0);
        menu.Items.Add(settingsItem);

        menu.Items.Add(new Separator());

        var exitItem = new MenuItem { Header = "Exit" };
        exitItem.Click += (_, _) => _onExit();
        menu.Items.Add(exitItem);

        _trayIcon.ContextMenu = menu;
    }

    private static Icon CreateIcon()
    {
        using var bmp = new Bitmap(16, 16);
        using var g = Graphics.FromImage(bmp);
        g.Clear(Color.FromArgb(26, 26, 46));
        using var pen = new Pen(Color.FromArgb(255, 215, 0), 2);
        g.DrawEllipse(pen, 2, 2, 11, 11);
        g.DrawLine(pen, 11, 11, 14, 14);
        return System.Drawing.Icon.FromHandle(bmp.GetHicon());
    }

    public void Dispose()
    {
        _trayIcon.Dispose();
    }
}
