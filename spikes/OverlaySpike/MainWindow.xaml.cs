using System.Runtime.InteropServices;
using System.Windows;
using System.Windows.Interop;
using System.Windows.Threading;

namespace OverlaySpike;

public partial class MainWindow : Window
{
    private const int WS_EX_TRANSPARENT = 0x00000020;
    private const int GWL_EXSTYLE = -20;
    private const int WM_HOTKEY = 0x0312;
    private const int HOTKEY_ESC = 1;
    private const int HOTKEY_SPACE = 2;

    [DllImport("user32.dll")]
    private static extern int GetWindowLong(IntPtr hwnd, int index);

    [DllImport("user32.dll")]
    private static extern int SetWindowLong(IntPtr hwnd, int index, int newStyle);

    [DllImport("user32.dll")]
    private static extern bool RegisterHotKey(IntPtr hWnd, int id, uint fsModifiers, uint vk);

    [DllImport("user32.dll")]
    private static extern bool UnregisterHotKey(IntPtr hWnd, int id);

    private bool _overlayVisible = true;

    public MainWindow()
    {
        InitializeComponent();
        Loaded += OnLoaded;
        Closed += OnClosed;
    }

    private void OnLoaded(object sender, RoutedEventArgs e)
    {
        var hwnd = new WindowInteropHelper(this).Handle;

        int exStyle = GetWindowLong(hwnd, GWL_EXSTYLE);
        SetWindowLong(hwnd, GWL_EXSTYLE, exStyle | WS_EX_TRANSPARENT);

        RegisterHotKey(hwnd, HOTKEY_ESC, 0, 0x1B);    // ESC
        RegisterHotKey(hwnd, HOTKEY_SPACE, 0, 0x20);   // Space

        var source = HwndSource.FromHwnd(hwnd);
        source?.AddHook(WndProc);
    }

    private void OnClosed(object? sender, EventArgs e)
    {
        var hwnd = new WindowInteropHelper(this).Handle;
        UnregisterHotKey(hwnd, HOTKEY_ESC);
        UnregisterHotKey(hwnd, HOTKEY_SPACE);
    }

    private IntPtr WndProc(IntPtr hwnd, int msg, IntPtr wParam, IntPtr lParam, ref bool handled)
    {
        if (msg == WM_HOTKEY)
        {
            int id = wParam.ToInt32();
            if (id == HOTKEY_ESC)
            {
                Close();
                handled = true;
            }
            else if (id == HOTKEY_SPACE)
            {
                _overlayVisible = !_overlayVisible;
                OverlayCanvas.Visibility = _overlayVisible ? Visibility.Visible : Visibility.Hidden;
                handled = true;
            }
        }
        return IntPtr.Zero;
    }
}
