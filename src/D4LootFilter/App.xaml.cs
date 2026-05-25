using System.IO;
using System.Threading;
using System.Windows;
using D4LootFilter.Overlay;
using D4LootFilter.Services;

namespace D4LootFilter;

public partial class App : Application
{
    private static Mutex? _mutex;
    private bool _ownsMutex;
    private PipelineService? _pipeline;
    private OverlayWindow? _overlay;

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

        var vm = new OverlayViewModel();
        var profileService = new ProfileService();
        profileService.LoadTestProfile();

        var tessdataPath = Path.Combine(AppContext.BaseDirectory, "tessdata");

        _overlay = new OverlayWindow { DataContext = vm };
        _overlay.Show();

        _pipeline = new PipelineService(vm, profileService, tessdataPath);
        _pipeline.UseFullScreen();
        _pipeline.Start();
    }

    protected override void OnExit(ExitEventArgs e)
    {
        _pipeline?.Dispose();
        if (_ownsMutex)
            _mutex?.ReleaseMutex();
        _mutex?.Dispose();
        base.OnExit(e);
    }
}
