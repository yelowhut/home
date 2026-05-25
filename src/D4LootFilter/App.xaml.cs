using System.IO;
using System.Runtime.InteropServices;
using System.Threading;
using System.Windows;
using System.Windows.Interop;
using D4LootFilter.Overlay;
using D4LootFilter.Services;

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

        Console.CancelKeyPress += (_, args) =>
        {
            args.Cancel = true;
            Dispatcher.Invoke(() => Shutdown());
        };

        AppDomain.CurrentDomain.ProcessExit += (_, _) =>
        {
            _pipeline?.Dispose();
        };

        var logDir = Path.Combine(AppContext.BaseDirectory, "logs");
        _logger = new FileLogger(logDir);

        var vm = new OverlayViewModel();
        var profileService = new ProfileService();
        profileService.LoadTestProfile();
        _logger.Log($"Profile loaded: {profileService.ActiveProfile?.Name}");

        var tessdataPath = Path.Combine(AppContext.BaseDirectory, "tessdata");

        _overlay = new OverlayWindow { DataContext = vm };
        _overlay.Show();

        // Register F12 as global exit hotkey
        var hwnd = new WindowInteropHelper(_overlay).Handle;
        RegisterHotKey(hwnd, HOTKEY_EXIT, 0, 0x7B); // VK_F12
        var source = HwndSource.FromHwnd(hwnd);
        source?.AddHook(WndProc);
        _logger.Log("F12 = exit app");

        _pipeline = new PipelineService(vm, profileService, tessdataPath, _logger);
        _pipeline.UseFullScreen();
        _pipeline.Start();
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
        if (_overlay != null)
        {
            var hwnd = new WindowInteropHelper(_overlay).Handle;
            UnregisterHotKey(hwnd, HOTKEY_EXIT);
        }
        _logger?.Log("App exiting");
        _logger?.Dispose();
        if (_ownsMutex)
            _mutex?.ReleaseMutex();
        _mutex?.Dispose();
        base.OnExit(e);
    }
}
