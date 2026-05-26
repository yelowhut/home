# Plan C: Full UI — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add system tray, dark-themed settings window (Profiles/Capture Region/Settings tabs), and region calibration overlay to make the D4 Loot Filter fully user-controllable.

**Architecture:** WPF MVVM pattern. `SettingsService` handles persistence to `%AppData%/D4LootFilter/settings.json`. ViewModels orchestrate UI logic and call existing services (`ProfileService`, `PipelineService`). System tray via `Hardcodet.NotifyIcon.Wpf`. Dark theme via WPF ResourceDictionary. App.xaml.cs rewritten to wire everything together.

**Tech Stack:** .NET 8 WPF, Hardcodet.NotifyIcon.Wpf, existing D4LootFilter.Matching/Scraper/Capture/Ocr

**Existing code referenced:**
- `AppSettings` model: `src/D4LootFilter.Matching/Models/AppSettings.cs`
- `CaptureRegion` model: `src/D4LootFilter.Matching/Models/CaptureRegion.cs`
- `ProfileService`: `src/D4LootFilter.Scraper/ProfileService.cs`
- `PipelineService`: `src/D4LootFilter/Services/PipelineService.cs`
- `OverlayViewModel` INPC pattern: `src/D4LootFilter/Overlay/OverlayViewModel.cs`

---

### Task 1: Update AppSettings model and add SettingsService

**Files:**
- Modify: `src/D4LootFilter.Matching/Models/AppSettings.cs`
- Create: `src/D4LootFilter.Scraper/SettingsService.cs`
- Test: `src/D4LootFilter.Scraper.Tests/SettingsServiceTests.cs`

- [ ] **Step 1: Update AppSettings model to include ActiveVariantId**

The existing `AppSettings` is missing `ActiveVariantId`. Add it:

```csharp
// src/D4LootFilter.Matching/Models/AppSettings.cs
namespace D4LootFilter.Matching.Models;

public record AppSettings
{
    public Dictionary<string, CaptureRegion> CaptureRegions { get; init; } = new();
    public string ActiveProfileId { get; init; } = "";
    public int ActiveVariantId { get; init; }
    public int PollingFps { get; init; } = 30;
    public int OcrConfidenceThreshold { get; init; } = 60;
    public int FuzzyMatchMaxDistance { get; init; } = 2;
    public double OverlayOpacity { get; init; } = 0.85;
    public bool StartMinimized { get; init; } = true;
    public bool AutoStartCapture { get; init; }
}
```

- [ ] **Step 2: Write failing tests for SettingsService**

```csharp
// src/D4LootFilter.Scraper.Tests/SettingsServiceTests.cs
using D4LootFilter.Matching.Models;

namespace D4LootFilter.Scraper.Tests;

public class SettingsServiceTests : IDisposable
{
    private readonly string _tempDir;
    private readonly string _settingsPath;

    public SettingsServiceTests()
    {
        _tempDir = Path.Combine(Path.GetTempPath(), $"d4lf-settings-{Guid.NewGuid():N}");
        Directory.CreateDirectory(_tempDir);
        _settingsPath = Path.Combine(_tempDir, "settings.json");
    }

    [Fact]
    public void Load_NoFile_ReturnsDefaults()
    {
        var service = new SettingsService(_settingsPath);
        var settings = service.Load();

        Assert.Equal(30, settings.PollingFps);
        Assert.Equal(60, settings.OcrConfidenceThreshold);
        Assert.Equal(2, settings.FuzzyMatchMaxDistance);
        Assert.Equal(0.85, settings.OverlayOpacity);
        Assert.True(settings.StartMinimized);
        Assert.False(settings.AutoStartCapture);
        Assert.Equal("", settings.ActiveProfileId);
    }

    [Fact]
    public void Save_ThenLoad_RoundTrips()
    {
        var service = new SettingsService(_settingsPath);
        var settings = new AppSettings
        {
            ActiveProfileId = "test-build",
            ActiveVariantId = 1,
            PollingFps = 45,
            OcrConfidenceThreshold = 70,
            FuzzyMatchMaxDistance = 3,
            OverlayOpacity = 0.9,
            StartMinimized = false,
            AutoStartCapture = true,
            CaptureRegions = new Dictionary<string, CaptureRegion>
            {
                ["1920x1080"] = new(400, 200, 500, 600)
            }
        };

        service.Save(settings);
        var loaded = service.Load();

        Assert.Equal("test-build", loaded.ActiveProfileId);
        Assert.Equal(1, loaded.ActiveVariantId);
        Assert.Equal(45, loaded.PollingFps);
        Assert.Equal(70, loaded.OcrConfidenceThreshold);
        Assert.True(loaded.AutoStartCapture);
        Assert.Single(loaded.CaptureRegions);
        Assert.Equal(400, loaded.CaptureRegions["1920x1080"].X);
    }

    [Fact]
    public void Save_CreatesDirectoryIfMissing()
    {
        var deepPath = Path.Combine(_tempDir, "sub", "dir", "settings.json");
        var service = new SettingsService(deepPath);

        service.Save(new AppSettings());

        Assert.True(File.Exists(deepPath));
    }

    [Fact]
    public void Load_CorruptFile_ReturnsDefaults()
    {
        File.WriteAllText(_settingsPath, "not json{{{");
        var service = new SettingsService(_settingsPath);

        var settings = service.Load();

        Assert.Equal(30, settings.PollingFps);
    }

    public void Dispose()
    {
        if (Directory.Exists(_tempDir))
            Directory.Delete(_tempDir, recursive: true);
    }
}
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `dotnet test D:\git\home\src\D4LootFilter.Scraper.Tests/ --filter SettingsService --verbosity normal`
Expected: FAIL — `SettingsService` does not exist.

- [ ] **Step 4: Implement SettingsService**

```csharp
// src/D4LootFilter.Scraper/SettingsService.cs
using System.Text.Json;
using D4LootFilter.Matching.Models;

namespace D4LootFilter.Scraper;

public class SettingsService
{
    private static readonly JsonSerializerOptions JsonOptions = new()
    {
        PropertyNamingPolicy = JsonNamingPolicy.SnakeCaseLower,
        WriteIndented = true,
    };

    private readonly string _path;

    public SettingsService(string path)
    {
        _path = path;
    }

    public AppSettings Load()
    {
        if (!File.Exists(_path))
            return new AppSettings();

        try
        {
            var json = File.ReadAllText(_path);
            return JsonSerializer.Deserialize<AppSettings>(json, JsonOptions) ?? new AppSettings();
        }
        catch
        {
            return new AppSettings();
        }
    }

    public void Save(AppSettings settings)
    {
        var dir = Path.GetDirectoryName(_path);
        if (!string.IsNullOrEmpty(dir))
            Directory.CreateDirectory(dir);

        var json = JsonSerializer.Serialize(settings, JsonOptions);
        File.WriteAllText(_path, json);
    }
}
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `dotnet test D:\git\home\src\D4LootFilter.Scraper.Tests/ --filter SettingsService --verbosity normal`
Expected: All 4 tests PASS.

- [ ] **Step 6: Commit**

```bash
git add src/D4LootFilter.Matching/Models/AppSettings.cs src/D4LootFilter.Scraper/SettingsService.cs src/D4LootFilter.Scraper.Tests/SettingsServiceTests.cs
git commit -m "feat: add SettingsService for app settings persistence"
```

---

### Task 2: Add PipelineService Pause/Resume/UpdateSettings

**Files:**
- Modify: `src/D4LootFilter/Services/PipelineService.cs`

- [ ] **Step 1: Add IsRunning, Pause, Resume, and UpdateSettings to PipelineService**

Add these members to the existing `PipelineService` class. Insert after the existing `Stop()` method (around line 76):

```csharp
    public bool IsRunning => _captureTask != null && !_captureTask.IsCompleted;

    public void Pause()
    {
        _log.Log("Pipeline paused");
        Stop();
    }

    public void Resume()
    {
        _log.Log("Pipeline resumed");
        Start();
    }

    public void UpdateSettings(int fps, int ocrThreshold, int matchDistance)
    {
        _pollingDelayMs = Math.Max(16, 1000 / Math.Clamp(fps, 15, 60));
        _ocr.MinConfidence = ocrThreshold;
        _matcher.MaxDistance = matchDistance;
        _log.Log($"Settings updated: FPS={fps}, OCR={ocrThreshold}, Match={matchDistance}");
    }
```

- [ ] **Step 2: Expose MinConfidence on TesseractOcrEngine**

Add a public setter to `src/D4LootFilter.Ocr/TesseractOcrEngine.cs`. Change the field:

```csharp
    private float _minConfidence;
    public float MinConfidence { get => _minConfidence; set => _minConfidence = value; }
```

Update the constructor to use `_minConfidence` instead of the readonly field.

- [ ] **Step 3: Expose MaxDistance on AffixMatcher**

In `src/D4LootFilter.Matching/AffixMatcher.cs`, change the field:

```csharp
    private int _maxDistance;
    public int MaxDistance { get => _maxDistance; set => _maxDistance = value; }
```

Update the constructor to use `_maxDistance`.

- [ ] **Step 4: Build the full solution**

Run: `dotnet build D:\git\home\src\D4LootFilter.sln`
Expected: Build succeeded.

- [ ] **Step 5: Run all existing tests**

Run: `dotnet test D:\git\home\src\D4LootFilter.sln --filter "Category!=Integration" --verbosity normal`
Expected: All tests PASS.

- [ ] **Step 6: Commit**

```bash
git add src/D4LootFilter/Services/PipelineService.cs src/D4LootFilter.Ocr/TesseractOcrEngine.cs src/D4LootFilter.Matching/AffixMatcher.cs
git commit -m "feat: add Pause/Resume/UpdateSettings to PipelineService"
```

---

### Task 3: Dark theme resource dictionary

**Files:**
- Create: `src/D4LootFilter/Themes/DarkTheme.xaml`
- Modify: `src/D4LootFilter/App.xaml`

- [ ] **Step 1: Create DarkTheme.xaml**

```xml
<!-- src/D4LootFilter/Themes/DarkTheme.xaml -->
<ResourceDictionary xmlns="http://schemas.microsoft.com/winfx/2006/xaml/presentation"
                    xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml">

    <!-- Colors -->
    <Color x:Key="BgColor">#1a1a2e</Color>
    <Color x:Key="PanelColor">#16213e</Color>
    <Color x:Key="AccentColor">#ffd700</Color>
    <Color x:Key="TextColor">#e0e0e0</Color>
    <Color x:Key="TextSecondaryColor">#888888</Color>
    <Color x:Key="BorderColor">#2a2a4a</Color>

    <SolidColorBrush x:Key="BgBrush" Color="{StaticResource BgColor}"/>
    <SolidColorBrush x:Key="PanelBrush" Color="{StaticResource PanelColor}"/>
    <SolidColorBrush x:Key="AccentBrush" Color="{StaticResource AccentColor}"/>
    <SolidColorBrush x:Key="TextBrush" Color="{StaticResource TextColor}"/>
    <SolidColorBrush x:Key="TextSecondaryBrush" Color="{StaticResource TextSecondaryColor}"/>
    <SolidColorBrush x:Key="BorderBrush" Color="{StaticResource BorderColor}"/>

    <!-- Default TextBlock -->
    <Style TargetType="TextBlock">
        <Setter Property="Foreground" Value="{StaticResource TextBrush}"/>
        <Setter Property="FontFamily" Value="Segoe UI"/>
    </Style>

    <!-- TextBox -->
    <Style x:Key="DarkTextBox" TargetType="TextBox">
        <Setter Property="Background" Value="{StaticResource PanelBrush}"/>
        <Setter Property="Foreground" Value="{StaticResource TextBrush}"/>
        <Setter Property="BorderBrush" Value="{StaticResource BorderBrush}"/>
        <Setter Property="CaretBrush" Value="{StaticResource TextBrush}"/>
        <Setter Property="Padding" Value="8,6"/>
        <Setter Property="FontSize" Value="13"/>
    </Style>

    <!-- Button -->
    <Style x:Key="AccentButton" TargetType="Button">
        <Setter Property="Background" Value="{StaticResource AccentBrush}"/>
        <Setter Property="Foreground" Value="#1a1a2e"/>
        <Setter Property="BorderThickness" Value="0"/>
        <Setter Property="Padding" Value="16,8"/>
        <Setter Property="FontWeight" Value="SemiBold"/>
        <Setter Property="FontSize" Value="13"/>
        <Setter Property="Cursor" Value="Hand"/>
        <Setter Property="Template">
            <Setter.Value>
                <ControlTemplate TargetType="Button">
                    <Border Background="{TemplateBinding Background}"
                            CornerRadius="4" Padding="{TemplateBinding Padding}">
                        <ContentPresenter HorizontalAlignment="Center" VerticalAlignment="Center"/>
                    </Border>
                    <ControlTemplate.Triggers>
                        <Trigger Property="IsMouseOver" Value="True">
                            <Setter Property="Background" Value="#ffe033"/>
                        </Trigger>
                        <Trigger Property="IsEnabled" Value="False">
                            <Setter Property="Background" Value="#555"/>
                            <Setter Property="Foreground" Value="#888"/>
                        </Trigger>
                    </ControlTemplate.Triggers>
                </ControlTemplate>
            </Setter.Value>
        </Setter>
    </Style>

    <!-- Secondary Button -->
    <Style x:Key="SecondaryButton" TargetType="Button">
        <Setter Property="Background" Value="{StaticResource PanelBrush}"/>
        <Setter Property="Foreground" Value="{StaticResource TextBrush}"/>
        <Setter Property="BorderBrush" Value="{StaticResource BorderBrush}"/>
        <Setter Property="BorderThickness" Value="1"/>
        <Setter Property="Padding" Value="16,8"/>
        <Setter Property="FontSize" Value="13"/>
        <Setter Property="Cursor" Value="Hand"/>
        <Setter Property="Template">
            <Setter.Value>
                <ControlTemplate TargetType="Button">
                    <Border Background="{TemplateBinding Background}"
                            BorderBrush="{TemplateBinding BorderBrush}"
                            BorderThickness="{TemplateBinding BorderThickness}"
                            CornerRadius="4" Padding="{TemplateBinding Padding}">
                        <ContentPresenter HorizontalAlignment="Center" VerticalAlignment="Center"/>
                    </Border>
                    <ControlTemplate.Triggers>
                        <Trigger Property="IsMouseOver" Value="True">
                            <Setter Property="Background" Value="#1e2a4a"/>
                        </Trigger>
                    </ControlTemplate.Triggers>
                </ControlTemplate>
            </Setter.Value>
        </Setter>
    </Style>

    <!-- Danger Button (delete) -->
    <Style x:Key="DangerButton" TargetType="Button" BasedOn="{StaticResource SecondaryButton}">
        <Setter Property="Foreground" Value="#E57373"/>
        <Setter Property="BorderBrush" Value="#E57373"/>
        <Style.Triggers>
            <Trigger Property="IsMouseOver" Value="True">
                <Setter Property="Background" Value="#2a1515"/>
            </Trigger>
        </Style.Triggers>
    </Style>

    <!-- ListView -->
    <Style x:Key="DarkListView" TargetType="ListView">
        <Setter Property="Background" Value="{StaticResource PanelBrush}"/>
        <Setter Property="Foreground" Value="{StaticResource TextBrush}"/>
        <Setter Property="BorderBrush" Value="{StaticResource BorderBrush}"/>
        <Setter Property="BorderThickness" Value="1"/>
    </Style>

    <!-- ComboBox -->
    <Style x:Key="DarkComboBox" TargetType="ComboBox">
        <Setter Property="Background" Value="{StaticResource PanelBrush}"/>
        <Setter Property="Foreground" Value="{StaticResource TextBrush}"/>
        <Setter Property="BorderBrush" Value="{StaticResource BorderBrush}"/>
        <Setter Property="Padding" Value="8,6"/>
        <Setter Property="FontSize" Value="13"/>
    </Style>

    <!-- Slider -->
    <Style x:Key="DarkSlider" TargetType="Slider">
        <Setter Property="Foreground" Value="{StaticResource AccentBrush}"/>
        <Setter Property="Minimum" Value="0"/>
        <Setter Property="Maximum" Value="100"/>
    </Style>

    <!-- CheckBox -->
    <Style x:Key="DarkCheckBox" TargetType="CheckBox">
        <Setter Property="Foreground" Value="{StaticResource TextBrush}"/>
        <Setter Property="FontSize" Value="13"/>
    </Style>

</ResourceDictionary>
```

- [ ] **Step 2: Register theme in App.xaml**

```xml
<!-- src/D4LootFilter/App.xaml -->
<Application x:Class="D4LootFilter.App"
             xmlns="http://schemas.microsoft.com/winfx/2006/xaml/presentation"
             xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml"
             xmlns:local="clr-namespace:D4LootFilter">
    <Application.Resources>
        <ResourceDictionary>
            <ResourceDictionary.MergedDictionaries>
                <ResourceDictionary Source="Themes/DarkTheme.xaml"/>
            </ResourceDictionary.MergedDictionaries>
            <BooleanToVisibilityConverter x:Key="BoolToVisibility"/>
        </ResourceDictionary>
    </Application.Resources>
</Application>
```

- [ ] **Step 3: Build to verify**

Run: `dotnet build D:\git\home\src\D4LootFilter\D4LootFilter.csproj`
Expected: Build succeeded.

- [ ] **Step 4: Commit**

```bash
git add src/D4LootFilter/Themes/DarkTheme.xaml src/D4LootFilter/App.xaml
git commit -m "feat: add dark theme resource dictionary"
```

---

### Task 4: SettingsWindow shell with three tabs

**Files:**
- Create: `src/D4LootFilter/Views/SettingsWindow.xaml`
- Create: `src/D4LootFilter/Views/SettingsWindow.xaml.cs`

- [ ] **Step 1: Create SettingsWindow XAML**

```xml
<!-- src/D4LootFilter/Views/SettingsWindow.xaml -->
<Window x:Class="D4LootFilter.Views.SettingsWindow"
        xmlns="http://schemas.microsoft.com/winfx/2006/xaml/presentation"
        xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml"
        Title="D4 Loot Filter — Settings"
        Width="550" Height="450"
        ResizeMode="NoResize"
        WindowStartupLocation="CenterScreen"
        Background="{StaticResource BgBrush}">

    <TabControl Background="Transparent" BorderThickness="0" Padding="0" Margin="12">
        <TabControl.Resources>
            <Style TargetType="TabItem">
                <Setter Property="Foreground" Value="{StaticResource TextSecondaryBrush}"/>
                <Setter Property="FontSize" Value="14"/>
                <Setter Property="Padding" Value="16,8"/>
                <Setter Property="Template">
                    <Setter.Value>
                        <ControlTemplate TargetType="TabItem">
                            <Border x:Name="Bd" Padding="{TemplateBinding Padding}" Background="Transparent"
                                    BorderThickness="0,0,0,2" BorderBrush="Transparent" Cursor="Hand">
                                <ContentPresenter ContentSource="Header"/>
                            </Border>
                            <ControlTemplate.Triggers>
                                <Trigger Property="IsSelected" Value="True">
                                    <Setter TargetName="Bd" Property="BorderBrush" Value="{StaticResource AccentBrush}"/>
                                    <Setter Property="Foreground" Value="{StaticResource AccentBrush}"/>
                                </Trigger>
                                <Trigger Property="IsMouseOver" Value="True">
                                    <Setter Property="Foreground" Value="{StaticResource TextBrush}"/>
                                </Trigger>
                            </ControlTemplate.Triggers>
                        </ControlTemplate>
                    </Setter.Value>
                </Setter>
            </Style>
        </TabControl.Resources>

        <TabItem Header="Profiles" x:Name="ProfilesTab">
            <TextBlock Text="Profiles tab placeholder" Margin="12"/>
        </TabItem>
        <TabItem Header="Capture Region">
            <TextBlock Text="Capture Region tab placeholder" Margin="12"/>
        </TabItem>
        <TabItem Header="Settings">
            <TextBlock Text="Settings tab placeholder" Margin="12"/>
        </TabItem>
    </TabControl>
</Window>
```

- [ ] **Step 2: Create code-behind (hide on close)**

```csharp
// src/D4LootFilter/Views/SettingsWindow.xaml.cs
using System.ComponentModel;
using System.Windows;

namespace D4LootFilter.Views;

public partial class SettingsWindow : Window
{
    public SettingsWindow()
    {
        InitializeComponent();
    }

    protected override void OnClosing(CancelEventArgs e)
    {
        e.Cancel = true;
        Hide();
    }

    public void ShowOnTab(int tabIndex)
    {
        Show();
        Activate();
        var tabControl = (System.Windows.Controls.TabControl)Content;
        if (tabIndex >= 0 && tabIndex < tabControl.Items.Count)
            tabControl.SelectedIndex = tabIndex;
    }
}
```

- [ ] **Step 3: Build to verify**

Run: `dotnet build D:\git\home\src\D4LootFilter\D4LootFilter.csproj`
Expected: Build succeeded.

- [ ] **Step 4: Commit**

```bash
git add src/D4LootFilter/Views/
git commit -m "feat: add SettingsWindow shell with dark-themed tabs"
```

---

### Task 5: System tray icon and menu

**Files:**
- Modify: `src/D4LootFilter/D4LootFilter.csproj` (add NuGet + icon)
- Create: `src/D4LootFilter/TrayIcon/TrayIconManager.cs`

- [ ] **Step 1: Add Hardcodet.NotifyIcon.Wpf package**

```powershell
cd D:\git\home\src
dotnet add D4LootFilter/D4LootFilter.csproj package Hardcodet.NotifyIcon.Wpf
```

- [ ] **Step 2: Create a simple .ico file**

Create a minimal 16x16 icon programmatically. We'll generate it at startup instead of bundling a file — simpler for now:

```csharp
// src/D4LootFilter/TrayIcon/TrayIconManager.cs
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
        menu.Style = null;

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
```

- [ ] **Step 3: Build to verify**

Run: `dotnet build D:\git\home\src\D4LootFilter\D4LootFilter.csproj`
Expected: Build succeeded.

- [ ] **Step 4: Commit**

```bash
git add src/D4LootFilter/TrayIcon/ src/D4LootFilter/D4LootFilter.csproj
git commit -m "feat: add system tray icon with context menu"
```

---

### Task 6: Profiles tab (import, list, activate, delete)

**Files:**
- Create: `src/D4LootFilter/Views/ProfilesView.xaml`
- Create: `src/D4LootFilter/Views/ProfilesView.xaml.cs`
- Create: `src/D4LootFilter/ViewModels/ProfilesViewModel.cs`

- [ ] **Step 1: Create ProfilesViewModel**

```csharp
// src/D4LootFilter/ViewModels/ProfilesViewModel.cs
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

    public string ImportUrl
    {
        get => _importUrl;
        set => SetField(ref _importUrl, value);
    }

    public string ErrorMessage
    {
        get => _errorMessage;
        set => SetField(ref _errorMessage, value);
    }

    public bool IsImporting
    {
        get => _isImporting;
        set => SetField(ref _isImporting, value);
    }

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

    public int SelectedVariantIndex
    {
        get => _selectedVariantIndex;
        set => SetField(ref _selectedVariantIndex, value);
    }

    public ObservableCollection<BuildProfile> Profiles
    {
        get => _profiles;
        set => SetField(ref _profiles, value);
    }

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

            var settings = _settingsService.Load() with
            {
                ActiveProfileId = profile.Id,
                ActiveVariantId = 0,
            };
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
            ? Variants[SelectedVariantIndex].Id
            : 0;

        var settings = _settingsService.Load() with
        {
            ActiveProfileId = SelectedProfile.Id,
            ActiveVariantId = variantId,
        };
        _settingsService.Save(settings);
        _profileService.SetActive(SelectedProfile.Id);
        _onProfileChanged();
        RefreshProfiles();
    }

    public void Delete()
    {
        if (SelectedProfile == null) return;
        var result = MessageBox.Show(
            $"Delete profile \"{SelectedProfile.Name}\"?",
            "Confirm Delete",
            MessageBoxButton.YesNo,
            MessageBoxImage.Warning);
        if (result != MessageBoxResult.Yes) return;

        _profileService.DeleteProfile(SelectedProfile.Id);
        SelectedProfile = null;
        RefreshProfiles();
        _onProfileChanged();
    }

    private void RefreshProfiles()
    {
        var settings = _settingsService.Load();
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
        {
            field = value;
            OnPropertyChanged(name);
        }
    }
}
```

- [ ] **Step 2: Create ProfilesView XAML**

```xml
<!-- src/D4LootFilter/Views/ProfilesView.xaml -->
<UserControl x:Class="D4LootFilter.Views.ProfilesView"
             xmlns="http://schemas.microsoft.com/winfx/2006/xaml/presentation"
             xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml">

    <StackPanel Margin="4,8">
        <!-- Import -->
        <TextBlock Text="Import Build" FontSize="14" FontWeight="SemiBold" Margin="0,0,0,8"/>
        <DockPanel Margin="0,0,0,4">
            <Button DockPanel.Dock="Right" Content="Import" Margin="8,0,0,0"
                    Style="{StaticResource AccentButton}"
                    Click="OnImportClick"
                    IsEnabled="{Binding IsImporting, Converter={StaticResource InverseBool}}"/>
            <TextBox Text="{Binding ImportUrl, UpdateSourceTrigger=PropertyChanged}"
                     Style="{StaticResource DarkTextBox}"
                     Tag="Paste Mobalytics build URL..."/>
        </DockPanel>
        <TextBlock Text="{Binding ErrorMessage}" Foreground="#E57373" FontSize="11"
                   Visibility="{Binding ErrorMessage, Converter={StaticResource StringToVisibility}}"
                   Margin="0,0,0,4"/>
        <ProgressBar IsIndeterminate="True" Height="2" Margin="0,0,0,8"
                     Visibility="{Binding IsImporting, Converter={StaticResource BoolToVisibility}}"/>

        <!-- Profile List -->
        <TextBlock Text="Imported Profiles" FontSize="14" FontWeight="SemiBold" Margin="0,4,0,8"/>
        <ListView ItemsSource="{Binding Profiles}" SelectedItem="{Binding SelectedProfile}"
                  Style="{StaticResource DarkListView}" Height="140">
            <ListView.View>
                <GridView>
                    <GridViewColumn Header="Name" Width="180" DisplayMemberBinding="{Binding Name}"/>
                    <GridViewColumn Header="Class" Width="100" DisplayMemberBinding="{Binding Class}"/>
                    <GridViewColumn Header="Imported" Width="140" DisplayMemberBinding="{Binding ImportedAt, StringFormat='{}{0:yyyy-MM-dd HH:mm}'}"/>
                </GridView>
            </ListView.View>
        </ListView>

        <!-- Details -->
        <Border Margin="0,8,0,0" Padding="12" Background="{StaticResource PanelBrush}"
                BorderBrush="{StaticResource BorderBrush}" BorderThickness="1" CornerRadius="4"
                Visibility="{Binding HasSelection, Converter={StaticResource BoolToVisibility}}">
            <StackPanel>
                <TextBlock FontSize="14" FontWeight="SemiBold">
                    <Run Text="{Binding SelectedProfile.Name, Mode=OneWay}"/>
                    <Run Text=" — " Foreground="{StaticResource TextSecondaryBrush}"/>
                    <Run Text="{Binding SelectedProfile.Class, Mode=OneWay}" Foreground="{StaticResource TextSecondaryBrush}"/>
                </TextBlock>
                <DockPanel Margin="0,8,0,0">
                    <TextBlock Text="Variant:" VerticalAlignment="Center" Margin="0,0,8,0"/>
                    <Button DockPanel.Dock="Right" Content="Delete" Margin="8,0,0,0"
                            Style="{StaticResource DangerButton}" Click="OnDeleteClick"/>
                    <Button DockPanel.Dock="Right" Content="Activate" Margin="8,0,0,0"
                            Style="{StaticResource AccentButton}" Click="OnActivateClick"/>
                    <ComboBox ItemsSource="{Binding Variants}" SelectedIndex="{Binding SelectedVariantIndex}"
                              DisplayMemberPath="Name" Style="{StaticResource DarkComboBox}"/>
                </DockPanel>
            </StackPanel>
        </Border>
    </StackPanel>
</UserControl>
```

- [ ] **Step 3: Create ProfilesView code-behind**

```csharp
// src/D4LootFilter/Views/ProfilesView.xaml.cs
using System.Windows;
using System.Windows.Controls;
using D4LootFilter.ViewModels;

namespace D4LootFilter.Views;

public partial class ProfilesView : UserControl
{
    public ProfilesView()
    {
        InitializeComponent();
    }

    private async void OnImportClick(object sender, RoutedEventArgs e)
    {
        if (DataContext is ProfilesViewModel vm)
            await vm.ImportAsync();
    }

    private void OnActivateClick(object sender, RoutedEventArgs e)
    {
        if (DataContext is ProfilesViewModel vm)
            vm.Activate();
    }

    private void OnDeleteClick(object sender, RoutedEventArgs e)
    {
        if (DataContext is ProfilesViewModel vm)
            vm.Delete();
    }
}
```

- [ ] **Step 4: Add value converters to App.xaml**

Add these converters to `App.xaml` inside the `<ResourceDictionary>`:

```xml
        <local:InverseBoolConverter x:Key="InverseBool"/>
        <local:StringToVisibilityConverter x:Key="StringToVisibility"/>
```

Create `src/D4LootFilter/Converters.cs`:

```csharp
// src/D4LootFilter/Converters.cs
using System.Globalization;
using System.Windows;
using System.Windows.Data;

namespace D4LootFilter;

public class InverseBoolConverter : IValueConverter
{
    public object Convert(object value, Type targetType, object parameter, CultureInfo culture)
        => value is bool b ? !b : value;
    public object ConvertBack(object value, Type targetType, object parameter, CultureInfo culture)
        => value is bool b ? !b : value;
}

public class StringToVisibilityConverter : IValueConverter
{
    public object Convert(object value, Type targetType, object parameter, CultureInfo culture)
        => string.IsNullOrEmpty(value as string) ? Visibility.Collapsed : Visibility.Visible;
    public object ConvertBack(object value, Type targetType, object parameter, CultureInfo culture)
        => throw new NotImplementedException();
}
```

- [ ] **Step 5: Wire ProfilesView into SettingsWindow**

Replace the Profiles tab placeholder in `SettingsWindow.xaml`:

```xml
        <TabItem Header="Profiles" x:Name="ProfilesTab">
            <local:ProfilesView x:Name="ProfilesContent"/>
        </TabItem>
```

Add namespace: `xmlns:local="clr-namespace:D4LootFilter.Views"` to the Window tag.

- [ ] **Step 6: Build to verify**

Run: `dotnet build D:\git\home\src\D4LootFilter\D4LootFilter.csproj`
Expected: Build succeeded.

- [ ] **Step 7: Commit**

```bash
git add src/D4LootFilter/Views/ src/D4LootFilter/ViewModels/ src/D4LootFilter/Converters.cs src/D4LootFilter/App.xaml
git commit -m "feat: add Profiles tab with import, list, activate, delete"
```

---

### Task 7: Capture Region tab and Calibration Overlay

**Files:**
- Create: `src/D4LootFilter/Views/CaptureRegionView.xaml`
- Create: `src/D4LootFilter/Views/CaptureRegionView.xaml.cs`
- Create: `src/D4LootFilter/Views/CalibrationOverlay.xaml`
- Create: `src/D4LootFilter/Views/CalibrationOverlay.xaml.cs`

- [ ] **Step 1: Create CalibrationOverlay**

```xml
<!-- src/D4LootFilter/Views/CalibrationOverlay.xaml -->
<Window x:Class="D4LootFilter.Views.CalibrationOverlay"
        xmlns="http://schemas.microsoft.com/winfx/2006/xaml/presentation"
        xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml"
        WindowStyle="None" AllowsTransparency="True"
        Background="#44000000" Topmost="True"
        WindowState="Maximized" Cursor="Cross"
        ShowInTaskbar="False">

    <Canvas x:Name="DrawCanvas">
        <TextBlock Canvas.Left="0" Canvas.Top="0"
                   Text="Draw a rectangle over the tooltip area. ESC to cancel."
                   Foreground="#ffd700" FontSize="18" FontWeight="SemiBold"
                   HorizontalAlignment="Center"
                   x:Name="Instructions"/>
        <Rectangle x:Name="SelectionRect"
                   Stroke="#ffd700" StrokeThickness="2"
                   StrokeDashArray="4 2"
                   Fill="#22ffd700"
                   Visibility="Collapsed"/>
    </Canvas>
</Window>
```

```csharp
// src/D4LootFilter/Views/CalibrationOverlay.xaml.cs
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
```

- [ ] **Step 2: Create CaptureRegionView**

```xml
<!-- src/D4LootFilter/Views/CaptureRegionView.xaml -->
<UserControl x:Class="D4LootFilter.Views.CaptureRegionView"
             xmlns="http://schemas.microsoft.com/winfx/2006/xaml/presentation"
             xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml">

    <StackPanel Margin="4,8">
        <TextBlock Text="Current Capture Region" FontSize="14" FontWeight="SemiBold" Margin="0,0,0,12"/>

        <Border Background="{StaticResource PanelBrush}" BorderBrush="{StaticResource BorderBrush}"
                BorderThickness="1" CornerRadius="4" Padding="16" Margin="0,0,0,16">
            <StackPanel>
                <TextBlock x:Name="RegionInfo" FontSize="13" Margin="0,0,0,8"/>
                <TextBlock x:Name="ResolutionInfo" FontSize="12" Foreground="{StaticResource TextSecondaryBrush}"/>
            </StackPanel>
        </Border>

        <StackPanel Orientation="Horizontal">
            <Button Content="Recalibrate" Style="{StaticResource AccentButton}" Click="OnRecalibrate" Margin="0,0,8,0"/>
            <Button Content="Use Full Screen" Style="{StaticResource SecondaryButton}" Click="OnUseFullScreen"/>
        </StackPanel>
    </StackPanel>
</UserControl>
```

```csharp
// src/D4LootFilter/Views/CaptureRegionView.xaml.cs
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
        {
            RegionInfo.Text = $"Region: ({region.X}, {region.Y}) {region.Width}×{region.Height}";
        }
        else
        {
            RegionInfo.Text = "No region set — using full screen";
        }
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
```

- [ ] **Step 3: Wire into SettingsWindow**

Replace the Capture Region tab placeholder in `SettingsWindow.xaml`:

```xml
        <TabItem Header="Capture Region">
            <local:CaptureRegionView x:Name="CaptureRegionContent"/>
        </TabItem>
```

- [ ] **Step 4: Build to verify**

Run: `dotnet build D:\git\home\src\D4LootFilter\D4LootFilter.csproj`
Expected: Build succeeded.

- [ ] **Step 5: Commit**

```bash
git add src/D4LootFilter/Views/
git commit -m "feat: add Capture Region tab with calibration overlay"
```

---

### Task 8: Settings tab (sliders, checkboxes, save/reset)

**Files:**
- Create: `src/D4LootFilter/Views/SettingsView.xaml`
- Create: `src/D4LootFilter/Views/SettingsView.xaml.cs`
- Create: `src/D4LootFilter/ViewModels/SettingsViewModel.cs`

- [ ] **Step 1: Create SettingsViewModel**

```csharp
// src/D4LootFilter/ViewModels/SettingsViewModel.cs
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
```

- [ ] **Step 2: Create SettingsView XAML**

```xml
<!-- src/D4LootFilter/Views/SettingsView.xaml -->
<UserControl x:Class="D4LootFilter.Views.SettingsView"
             xmlns="http://schemas.microsoft.com/winfx/2006/xaml/presentation"
             xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml">

    <StackPanel Margin="4,8">
        <TextBlock Text="Pipeline Settings" FontSize="14" FontWeight="SemiBold" Margin="0,0,0,12"/>

        <!-- Polling FPS -->
        <DockPanel Margin="0,0,0,12">
            <TextBlock DockPanel.Dock="Right" Width="30" TextAlignment="Right"
                       Text="{Binding PollingFps}" FontSize="13"/>
            <TextBlock Text="Polling FPS" FontSize="13" Margin="0,0,12,0"/>
            <Slider Value="{Binding PollingFps}" Minimum="15" Maximum="60"
                    TickFrequency="5" IsSnapToTickEnabled="True"
                    Style="{StaticResource DarkSlider}"/>
        </DockPanel>

        <!-- OCR Confidence -->
        <DockPanel Margin="0,0,0,12">
            <TextBlock DockPanel.Dock="Right" Width="30" TextAlignment="Right"
                       Text="{Binding OcrConfidence}" FontSize="13"/>
            <TextBlock Text="OCR Confidence" FontSize="13" Margin="0,0,12,0"/>
            <Slider Value="{Binding OcrConfidence}" Minimum="30" Maximum="90"
                    TickFrequency="5" IsSnapToTickEnabled="True"
                    Style="{StaticResource DarkSlider}"/>
        </DockPanel>

        <!-- Fuzzy Match Distance -->
        <DockPanel Margin="0,0,0,12">
            <TextBlock DockPanel.Dock="Right" Width="30" TextAlignment="Right"
                       Text="{Binding FuzzyMatchDistance}" FontSize="13"/>
            <TextBlock Text="Fuzzy Match Distance" FontSize="13" Margin="0,0,12,0"/>
            <Slider Value="{Binding FuzzyMatchDistance}" Minimum="1" Maximum="3"
                    TickFrequency="1" IsSnapToTickEnabled="True"
                    Style="{StaticResource DarkSlider}"/>
        </DockPanel>

        <!-- Overlay Opacity -->
        <DockPanel Margin="0,0,0,16">
            <TextBlock DockPanel.Dock="Right" Width="30" TextAlignment="Right"
                       Text="{Binding OverlayOpacity, StringFormat='{}{0:F2}'}" FontSize="13"/>
            <TextBlock Text="Overlay Opacity" FontSize="13" Margin="0,0,12,0"/>
            <Slider Value="{Binding OverlayOpacity}" Minimum="0.5" Maximum="1.0"
                    TickFrequency="0.05" IsSnapToTickEnabled="True"
                    Style="{StaticResource DarkSlider}"/>
        </DockPanel>

        <Border BorderBrush="{StaticResource BorderBrush}" BorderThickness="0,1,0,0"
                Padding="0,12,0,0" Margin="0,0,0,12">
            <StackPanel>
                <CheckBox Content="Start minimized to tray" IsChecked="{Binding StartMinimized}"
                          Style="{StaticResource DarkCheckBox}" Margin="0,0,0,8"/>
                <CheckBox Content="Auto-start capture on launch" IsChecked="{Binding AutoStartCapture}"
                          Style="{StaticResource DarkCheckBox}"/>
            </StackPanel>
        </Border>

        <DockPanel>
            <Button Content="Reset to Defaults" DockPanel.Dock="Right"
                    Style="{StaticResource SecondaryButton}" Click="OnReset"
                    Foreground="{StaticResource TextSecondaryBrush}"/>
            <Button Content="Save" Style="{StaticResource AccentButton}" Click="OnSave" Width="100"/>
        </DockPanel>
    </StackPanel>
</UserControl>
```

```csharp
// src/D4LootFilter/Views/SettingsView.xaml.cs
using System.Windows;
using System.Windows.Controls;
using D4LootFilter.ViewModels;

namespace D4LootFilter.Views;

public partial class SettingsView : UserControl
{
    public SettingsView()
    {
        InitializeComponent();
    }

    private void OnSave(object sender, RoutedEventArgs e)
    {
        if (DataContext is SettingsViewModel vm) vm.Save();
    }

    private void OnReset(object sender, RoutedEventArgs e)
    {
        if (DataContext is SettingsViewModel vm) vm.ResetToDefaults();
    }
}
```

- [ ] **Step 3: Wire into SettingsWindow**

Replace the Settings tab placeholder in `SettingsWindow.xaml`:

```xml
        <TabItem Header="Settings">
            <local:SettingsView x:Name="SettingsContent"/>
        </TabItem>
```

- [ ] **Step 4: Build to verify**

Run: `dotnet build D:\git\home\src\D4LootFilter\D4LootFilter.csproj`
Expected: Build succeeded.

- [ ] **Step 5: Commit**

```bash
git add src/D4LootFilter/Views/ src/D4LootFilter/ViewModels/
git commit -m "feat: add Settings tab with sliders, checkboxes, save/reset"
```

---

### Task 9: Rewrite App.xaml.cs — wire everything together

**Files:**
- Modify: `src/D4LootFilter/App.xaml.cs`

- [ ] **Step 1: Rewrite App.xaml.cs**

Replace the entire content of `src/D4LootFilter/App.xaml.cs`:

```csharp
// src/D4LootFilter/App.xaml.cs
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
        SetupSettingsWindow(settings);

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

    private void SetupSettingsWindow(AppSettings settings)
    {
        var profilesVm = new ProfilesViewModel(_profileService!, _settingsService!, OnProfileChanged);
        _settingsWindow!.FindName("ProfilesContent")?.GetType()
            .GetProperty("DataContext")?.SetValue(_settingsWindow.FindName("ProfilesContent"), profilesVm);

        var captureView = _settingsWindow.FindName("CaptureRegionContent") as CaptureRegionView;
        captureView?.Init(_settingsService!, OnRegionChanged);

        var settingsVm = new SettingsViewModel(_settingsService!, OnSettingsApplied);
        var settingsView = _settingsWindow.FindName("SettingsContent") as SettingsView;
        if (settingsView != null) settingsView.DataContext = settingsVm;

        var profilesView = _settingsWindow.FindName("ProfilesContent") as ProfilesView;
        if (profilesView != null) profilesView.DataContext = profilesVm;
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
```

- [ ] **Step 2: Remove MainWindow (no longer used)**

Delete `src/D4LootFilter/MainWindow.xaml` and `src/D4LootFilter/MainWindow.xaml.cs`.

- [ ] **Step 3: Build the full solution**

Run: `dotnet build D:\git\home\src\D4LootFilter.sln`
Expected: Build succeeded.

- [ ] **Step 4: Run all tests**

Run: `dotnet test D:\git\home\src\D4LootFilter.sln --filter "Category!=Integration" --verbosity normal`
Expected: All tests PASS.

- [ ] **Step 5: Commit**

```bash
git add src/D4LootFilter/
git commit -m "feat: wire App.xaml.cs to tray, settings window, and pipeline"
```

---

### Task 10: Manual integration test

- [ ] **Step 1: Run the application**

```powershell
dotnet run --project D:\git\home\src\D4LootFilter\D4LootFilter.csproj
```

- [ ] **Step 2: Test checklist**

1. App starts with system tray icon
2. Settings window opens (since no profiles exist)
3. Paste a Mobalytics URL → Import works → profile appears in list
4. Activate profile → tray menu shows profile name
5. Switch to Capture Region tab → shows "Full screen"
6. Click Recalibrate → overlay appears → draw rectangle → region saved
7. Switch to Settings tab → adjust sliders → Save
8. Right-click tray → Pause → pipeline stops → Resume → pipeline starts
9. Right-click tray → Switch Profile → variant changes
10. Close settings window → app stays in tray
11. F12 → app exits

- [ ] **Step 3: Fix any issues found**

- [ ] **Step 4: Commit fixes**

```bash
git add -A
git commit -m "fix: tune UI after integration testing"
```

---

## Summary

| Task | Component | Files |
|---|---|---|
| 1 | SettingsService + AppSettings update | 3 files |
| 2 | PipelineService Pause/Resume/UpdateSettings | 3 files |
| 3 | Dark theme ResourceDictionary | 2 files |
| 4 | SettingsWindow shell with tabs | 2 files |
| 5 | System tray icon + menu | 2 files |
| 6 | Profiles tab (import, list, activate, delete) | 5 files |
| 7 | Capture Region tab + Calibration Overlay | 4 files |
| 8 | Settings tab (sliders, checkboxes, save/reset) | 3 files |
| 9 | App.xaml.cs rewrite — wire everything | 1 file |
| 10 | Manual integration test | — |

**Result:** Fully interactive D4 Loot Filter with system tray, dark-themed settings window, profile management from Mobalytics, capture region calibration, and live pipeline settings.
