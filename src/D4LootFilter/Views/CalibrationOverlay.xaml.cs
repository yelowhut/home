using System.Windows;
using System.Windows.Controls;
using System.Windows.Input;

namespace D4LootFilter.Views;

public partial class CalibrationOverlay : Window
{
    private Point _startPoint;
    private bool _isDragging;

    public System.Drawing.Rectangle? SelectedRegion { get; private set; }

    public CalibrationOverlay()
    {
        InitializeComponent();
        Loaded += (_, _) =>
        {
            Canvas.SetLeft(Instructions, (ActualWidth - Instructions.ActualWidth) / 2);
            Canvas.SetTop(Instructions, ActualHeight / 2 - 20);
        };
        KeyDown += (_, e) =>
        {
            if (e.Key == Key.Escape) { SelectedRegion = null; Close(); }
        };
        MouseLeftButtonDown += OnMouseDown;
        MouseMove += OnMouseMove;
        MouseLeftButtonUp += OnMouseUp;
    }

    private void OnMouseDown(object sender, MouseButtonEventArgs e)
    {
        _startPoint = e.GetPosition(DrawCanvas);
        _isDragging = true;
        SelectionRect.Visibility = Visibility.Visible;
        Instructions.Visibility = Visibility.Collapsed;
        Canvas.SetLeft(SelectionRect, _startPoint.X);
        Canvas.SetTop(SelectionRect, _startPoint.Y);
        SelectionRect.Width = 0;
        SelectionRect.Height = 0;
        CaptureMouse();
    }

    private void OnMouseMove(object sender, MouseEventArgs e)
    {
        if (!_isDragging) return;
        var pos = e.GetPosition(DrawCanvas);
        var x = Math.Min(pos.X, _startPoint.X);
        var y = Math.Min(pos.Y, _startPoint.Y);
        var w = Math.Abs(pos.X - _startPoint.X);
        var h = Math.Abs(pos.Y - _startPoint.Y);
        Canvas.SetLeft(SelectionRect, x);
        Canvas.SetTop(SelectionRect, y);
        SelectionRect.Width = w;
        SelectionRect.Height = h;
    }

    private void OnMouseUp(object sender, MouseButtonEventArgs e)
    {
        if (!_isDragging) return;
        _isDragging = false;
        ReleaseMouseCapture();

        var pos = e.GetPosition(DrawCanvas);
        var x = (int)Math.Min(pos.X, _startPoint.X);
        var y = (int)Math.Min(pos.Y, _startPoint.Y);
        var w = (int)Math.Abs(pos.X - _startPoint.X);
        var h = (int)Math.Abs(pos.Y - _startPoint.Y);

        if (w > 20 && h > 20)
        {
            SelectedRegion = new System.Drawing.Rectangle(x, y, w, h);
            Close();
        }
    }
}
