using System.ComponentModel;
using System.Runtime.CompilerServices;
using D4LootFilter.Matching.Models;
using D4LootFilter.Scraper;

namespace D4LootFilter.ViewModels;

public class SettingsViewModel : INotifyPropertyChanged
{
    private readonly SettingsService _settingsService;
    private readonly Action<AppSettings> _onSettingsApplied;

    private int _pollingFps;
    private int _ocrConfidence;
    private int _fuzzyMatchDistance;
    private double _overlayOpacity;
    private bool _startMinimized;
    private bool _autoStartCapture;

    public SettingsViewModel(SettingsService settingsService, Action<AppSettings> onSettingsApplied)
    {
        _settingsService = settingsService;
        _onSettingsApplied = onSettingsApplied;
        LoadFromDisk();
    }

    public int PollingFps { get => _pollingFps; set => SetField(ref _pollingFps, value); }
    public int OcrConfidence { get => _ocrConfidence; set => SetField(ref _ocrConfidence, value); }
    public int FuzzyMatchDistance { get => _fuzzyMatchDistance; set => SetField(ref _fuzzyMatchDistance, value); }
    public double OverlayOpacity { get => _overlayOpacity; set => SetField(ref _overlayOpacity, value); }
    public bool StartMinimized { get => _startMinimized; set => SetField(ref _startMinimized, value); }
    public bool AutoStartCapture { get => _autoStartCapture; set => SetField(ref _autoStartCapture, value); }

    public void Save()
    {
        var current = _settingsService.Load();
        var updated = current with
        {
            PollingFps = PollingFps,
            OcrConfidenceThreshold = OcrConfidence,
            FuzzyMatchMaxDistance = FuzzyMatchDistance,
            OverlayOpacity = OverlayOpacity,
            StartMinimized = StartMinimized,
            AutoStartCapture = AutoStartCapture,
        };
        _settingsService.Save(updated);
        _onSettingsApplied(updated);
    }

    public void ResetToDefaults()
    {
        var defaults = new AppSettings();
        PollingFps = defaults.PollingFps;
        OcrConfidence = defaults.OcrConfidenceThreshold;
        FuzzyMatchDistance = defaults.FuzzyMatchMaxDistance;
        OverlayOpacity = defaults.OverlayOpacity;
        StartMinimized = defaults.StartMinimized;
        AutoStartCapture = defaults.AutoStartCapture;
    }

    private void LoadFromDisk()
    {
        var s = _settingsService.Load();
        _pollingFps = s.PollingFps;
        _ocrConfidence = s.OcrConfidenceThreshold;
        _fuzzyMatchDistance = s.FuzzyMatchMaxDistance;
        _overlayOpacity = s.OverlayOpacity;
        _startMinimized = s.StartMinimized;
        _autoStartCapture = s.AutoStartCapture;
    }

    public event PropertyChangedEventHandler? PropertyChanged;

    private void SetField<T>(ref T field, T value, [CallerMemberName] string? name = null)
    {
        if (!EqualityComparer<T>.Default.Equals(field, value))
        {
            field = value;
            PropertyChanged?.Invoke(this, new PropertyChangedEventArgs(name));
        }
    }
}
