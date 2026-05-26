using System.Collections.ObjectModel;
using System.ComponentModel;
using System.Runtime.CompilerServices;
using System.Windows;
using D4LootFilter.Matching.Models;
using D4LootFilter.Scraper;

namespace D4LootFilter.ViewModels;

public class ProfilesViewModel : INotifyPropertyChanged
{
    private readonly ProfileService _profileService;
    private readonly SettingsService _settingsService;
    private readonly Action _onProfileChanged;

    private string _importUrl = "";
    private string _errorMessage = "";
    private bool _isImporting;
    private BuildProfile? _selectedProfile;
    private int _selectedVariantIndex;
    private ObservableCollection<BuildProfile> _profiles = [];

    public ProfilesViewModel(ProfileService profileService, SettingsService settingsService, Action onProfileChanged)
    {
        _profileService = profileService;
        _settingsService = settingsService;
        _onProfileChanged = onProfileChanged;
        RefreshProfiles();
    }

    public string ImportUrl { get => _importUrl; set => SetField(ref _importUrl, value); }
    public string ErrorMessage { get => _errorMessage; set => SetField(ref _errorMessage, value); }
    public bool IsImporting { get => _isImporting; set => SetField(ref _isImporting, value); }

    public BuildProfile? SelectedProfile
    {
        get => _selectedProfile;
        set
        {
            SetField(ref _selectedProfile, value);
            OnPropertyChanged(nameof(HasSelection));
            OnPropertyChanged(nameof(Variants));
            SelectedVariantIndex = 0;
        }
    }

    public bool HasSelection => _selectedProfile != null;
    public List<BuildVariant> Variants => _selectedProfile?.Variants ?? [];

    public int SelectedVariantIndex { get => _selectedVariantIndex; set => SetField(ref _selectedVariantIndex, value); }
    public ObservableCollection<BuildProfile> Profiles { get => _profiles; set => SetField(ref _profiles, value); }

    public async Task ImportAsync()
    {
        if (string.IsNullOrWhiteSpace(ImportUrl) || IsImporting) return;
        IsImporting = true;
        ErrorMessage = "";
        try
        {
            var profile = await _profileService.ImportFromUrlAsync(ImportUrl);
            ImportUrl = "";
            RefreshProfiles();
            SelectedProfile = Profiles.FirstOrDefault(p => p.Id == profile.Id);
            var settings = _settingsService.Load() with { ActiveProfileId = profile.Id, ActiveVariantId = 0 };
            _settingsService.Save(settings);
            _profileService.SetActive(profile.Id);
            _onProfileChanged();
        }
        catch (Exception ex)
        {
            ErrorMessage = ex.Message;
            _ = ClearErrorAfterDelay();
        }
        finally
        {
            IsImporting = false;
        }
    }

    public void Activate()
    {
        if (SelectedProfile == null) return;
        var variantId = SelectedVariantIndex >= 0 && SelectedVariantIndex < Variants.Count
            ? Variants[SelectedVariantIndex].Id : 0;
        var settings = _settingsService.Load() with { ActiveProfileId = SelectedProfile.Id, ActiveVariantId = variantId };
        _settingsService.Save(settings);
        _profileService.SetActive(SelectedProfile.Id);
        _onProfileChanged();
        RefreshProfiles();
    }

    public void Delete()
    {
        if (SelectedProfile == null) return;
        var result = MessageBox.Show($"Delete profile \"{SelectedProfile.Name}\"?", "Confirm Delete", MessageBoxButton.YesNo, MessageBoxImage.Warning);
        if (result != MessageBoxResult.Yes) return;
        _profileService.DeleteProfile(SelectedProfile.Id);
        SelectedProfile = null;
        RefreshProfiles();
        _onProfileChanged();
    }

    private void RefreshProfiles()
    {
        Profiles = new ObservableCollection<BuildProfile>(_profileService.ListProfiles());
    }

    private async Task ClearErrorAfterDelay()
    {
        await Task.Delay(5000);
        ErrorMessage = "";
    }

    public event PropertyChangedEventHandler? PropertyChanged;
    private void OnPropertyChanged([CallerMemberName] string? name = null) =>
        PropertyChanged?.Invoke(this, new PropertyChangedEventArgs(name));
    private void SetField<T>(ref T field, T value, [CallerMemberName] string? name = null)
    {
        if (!EqualityComparer<T>.Default.Equals(field, value))
        { field = value; OnPropertyChanged(name); }
    }
}
