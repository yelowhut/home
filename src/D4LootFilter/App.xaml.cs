using System.IO;
using System.Runtime.InteropServices;
using System.Threading;
using System.Windows;
using System.Windows.Interop;
using D4LootFilter.Matching.Models;
using D4LootFilter.Overlay;
using D4LootFilter.Scraper;
using D4LootFilter.Services;
using D4LootFilter.TrayIcon;
using D4LootFilter.ViewModels;
using D4LootFilter.Views;

namespace D4LootFilter;

public partial class App : Application
{
    private const int WM_HOTKEY = 0x0312;
    private const int HOTKEY_EXIT = 1;

    [DllImport("user32.dll")]
    private static extern bool RegisterHotKey(IntPtr hWnd, int id, uint fsModifiers, uint vk);

    [DllImport("user32.dll")]
    private static extern bool UnregisterHotKey(IntPtr hWnd, int id);

    private static Mutex? _mutex;
    private bool _ownsMutex;
    private PipelineService? _pipeline;
    private OverlayWindow? _overlay;
    private FileLogger? _logger;
    private TrayIconManager? _trayIcon;
    private SettingsWindow? _settingsWindow;
    private SettingsService? _settingsService;
    private ProfileService? _profileService;
    private bool _isPaused;

    protected override void OnStartup(StartupEventArgs e)
    {
        _mutex = new Mutex(true, "D4LootFilter_SingleInstance", out bool createdNew);
        _ownsMutex = createdNew;
        if (!createdNew)
        {
            MessageBox.Show("D4 Loot Filter is already running.", "D4 Loot Filter", MessageBoxButton.OK);
            Shutdown();
            return;
        }

        base.OnStartup(e);

        var appDataDir = Path.Combine(
            Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData),
            "D4LootFilter");

        var logDir = Path.Combine(appDataDir, "logs");
        _logger = new FileLogger(logDir);

        _settingsService = new SettingsService(Path.Combine(appDataDir, "settings.json"));
        var settings = _settingsService.Load();

        _profileService = new ProfileService(Path.Combine(appDataDir, "profiles"));

        if (!string.IsNullOrEmpty(settings.ActiveProfileId))
            _profileService.SetActive(settings.ActiveProfileId);

        _logger.Log($"Profile: {_profileService.ActiveProfile?.Name ?? "none"}");

        var overlayVm = new OverlayViewModel();
        var tessdataPath = Path.Combine(AppContext.BaseDirectory, "tessdata");

        _overlay = new OverlayWindow { DataContext = overlayVm };
        _overlay.Show();

        var hwnd = new WindowInteropHelper(_overlay).Handle;
        RegisterHotKey(hwnd, HOTKEY_EXIT, 0, 0x7B);
        HwndSource.FromHwnd(hwnd)?.AddHook(WndProc);
        _logger.Log("F12 = exit app");

        _pipeline = new PipelineService(overlayVm, _profileService, tessdataPath, _logger);
        ApplyCaptureRegion(settings);
        _pipeline.UpdateSettings(settings.PollingFps, settings.OcrConfidenceThreshold, settings.FuzzyMatchMaxDistance);

        _settingsWindow = new SettingsWindow();
        SetupSettingsWindow();

        _trayIcon = new TrayIconManager(
            _profileService,
            _settingsService,
            OnPauseResume,
            () => Dispatcher.Invoke(Shutdown),
            () => _settingsWindow!);

        if (settings.AutoStartCapture && _profileService.ActiveProfile != null)
        {
            _pipeline.Start();
            _logger.Log("Pipeline auto-started");
        }

        _trayIcon.UpdateStatus(_isPaused || !_pipeline.IsRunning);

        if (!settings.StartMinimized || _profileService.ListProfiles().Count == 0)
            _settingsWindow.ShowOnTab(0);
    }

    private void SetupSettingsWindow()
    {
        var profilesVm = new ProfilesViewModel(_profileService!, _settingsService!, OnProfileChanged);
        if (_settingsWindow!.FindName("ProfilesContent") is ProfilesView profilesView)
            profilesView.DataContext = profilesVm;

        if (_settingsWindow.FindName("CaptureRegionContent") is CaptureRegionView captureView)
            captureView.Init(_settingsService!, OnRegionChanged);

        var settingsVm = new SettingsViewModel(_settingsService!, OnSettingsApplied);
        if (_settingsWindow.FindName("SettingsContent") is SettingsView settingsView)
            settingsView.DataContext = settingsVm;
    }

    private void ApplyCaptureRegion(AppSettings settings)
    {
        var screenW = (int)SystemParameters.PrimaryScreenWidth;
        var screenH = (int)SystemParameters.PrimaryScreenHeight;
        var key = $"{screenW}x{screenH}";

        if (settings.CaptureRegions.TryGetValue(key, out var region))
        {
            _pipeline!.SetCaptureRegion(region.X, region.Y, region.Width, region.Height);
            _logger?.Log($"Capture region: ({region.X},{region.Y}) {region.Width}x{region.Height}");
        }
        else
        {
            _pipeline!.UseFullScreen();
            _logger?.Log("Capture: full screen");
        }
    }

    private void OnProfileChanged()
    {
        var wasRunning = _pipeline?.IsRunning ?? false;
        if (wasRunning) _pipeline?.Stop();
        if (_profileService?.ActiveProfile != null && wasRunning) _pipeline?.Start();
        _trayIcon?.UpdateStatus(_isPaused || !(_pipeline?.IsRunning ?? false));
    }

    private void OnRegionChanged(CaptureRegion? region)
    {
        var wasRunning = _pipeline?.IsRunning ?? false;
        if (wasRunning) _pipeline?.Stop();
        if (region != null)
            _pipeline?.SetCaptureRegion(region.X, region.Y, region.Width, region.Height);
        else
            _pipeline?.UseFullScreen();
        if (wasRunning) _pipeline?.Start();
    }

    private void OnSettingsApplied(AppSettings settings)
    {
        _pipeline?.UpdateSettings(settings.PollingFps, settings.OcrConfidenceThreshold, settings.FuzzyMatchMaxDistance);
    }

    private void OnPauseResume()
    {
        if (_pipeline == null) return;
        if (_pipeline.IsRunning)
        {
            _pipeline.Pause();
            _isPaused = true;
        }
        else
        {
            _pipeline.Resume();
            _isPaused = false;
        }
        _trayIcon?.UpdateStatus(_isPaused);
    }

    private IntPtr WndProc(IntPtr hwnd, int msg, IntPtr wParam, IntPtr lParam, ref bool handled)
    {
        if (msg == WM_HOTKEY && wParam.ToInt32() == HOTKEY_EXIT)
        {
            _logger?.Log("F12 pressed — shutting down");
            Shutdown();
            handled = true;
        }
        return IntPtr.Zero;
    }

    protected override void OnExit(ExitEventArgs e)
    {
        _pipeline?.Dispose();
        _trayIcon?.Dispose();
        if (_overlay != null)
        {
            var hwnd = new WindowInteropHelper(_overlay).Handle;
            UnregisterHotKey(hwnd, HOTKEY_EXIT);
        }
        _logger?.Log("App exiting");
        _logger?.Dispose();
        if (_ownsMutex) _mutex?.ReleaseMutex();
        _mutex?.Dispose();
        base.OnExit(e);
    }
}
