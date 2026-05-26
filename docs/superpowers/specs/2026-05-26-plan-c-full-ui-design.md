# D4 Loot Filter — Plan C: Full UI

## Overview

Add user-facing UI to the D4 Loot Filter: system tray icon, settings window with three tabs (Profiles, Capture Region, Settings), and a region calibration overlay. Replaces the current hardcoded startup with a fully interactive experience.

**Depends on:** Plan A (pipeline) and Plan B (scraper) — both complete.

## System Tray

Uses `Hardcodet.NotifyIcon.Wpf` NuGet package.

**Icon:** Custom 16x16/32x32 icon. Simple D4-themed design (e.g., a filter/lens icon in gold on dark background). Bundled as embedded resource.

**Tooltip:** "D4 Loot Filter — {status}" where status is `Running`, `Paused`, or `No Profile`.

**Context menu:**
- Status label (non-clickable, shows current profile + variant name)
- Separator
- **Switch Profile →** submenu per profile → submenu per variant (radio check on active)
- Separator
- **Pause / Resume** — toggles pipeline capture
- **Settings...** — opens Settings window
- Separator
- **Exit**

**Double-click** on tray icon → opens Settings window.

**Minimize behavior:** Closing the Settings window hides it (doesn't exit app). Only "Exit" from tray menu actually closes.

## Settings Window

Dark themed WPF window. 550x450px default. Non-resizable. Three tabs.

**Visual style:**
- Background: `#1a1a2e`
- Panel/card backgrounds: `#16213e`
- Accent: `#ffd700` (gold)
- Text: `#e0e0e0` (primary), `#888` (secondary)
- Borders: `#2a2a4a`
- Font: Segoe UI (system default)
- Tab headers: gold underline on active, gray text on inactive

### Tab 1: Profiles

**Import section (top):**
- Text input field (placeholder: "Paste Mobalytics build URL...")
- "Import" button (gold accent)
- On click: async import with progress indicator (spinning/pulsing), disabled input during import
- Error: show inline error message below input (red text), auto-clear after 5s
- Success: new profile appears in list, auto-selected

**Profile list (middle):**
- ListView with columns: Name, Class, Date imported
- Active profile has gold dot indicator
- Single-click to select, shows details below

**Details section (bottom, for selected profile):**
- Profile name + class
- Variant dropdown (ComboBox) — lists all variants from the profile
- "Activate" button — sets this profile + selected variant as active, restarts pipeline matching
- "Delete" button — with confirmation dialog, removes profile file

### Tab 2: Capture Region

**Current region display:**
- Shows coordinates and dimensions: "Region: (400, 200) 500×600 @ 1920×1080"
- Visual mini-preview: small screenshot of current region (captured once when tab opens)

**Actions:**
- "Recalibrate" button — launches the Region Calibration Overlay
- "Use Full Screen" button — sets region to entire screen, restarts pipeline

**Region is keyed by screen resolution** — stored in `settings.json` as `capture_regions: { "1920x1080": { x, y, width, height } }`. When resolution changes, prompts recalibration.

### Tab 3: Settings

Sliders and checkboxes for pipeline parameters:

| Setting | Control | Range | Default |
|---|---|---|---|
| Polling FPS | Slider | 15–60 | 30 |
| OCR Confidence | Slider | 30–90 | 60 |
| Fuzzy Match Distance | Slider (int) | 1–3 | 2 |
| Overlay Opacity | Slider | 0.5–1.0 | 0.85 |
| Start Minimized | Checkbox | — | true |
| Auto-Start Capture | Checkbox | — | false |

"Save" button at bottom. Settings take effect immediately for slider values (live preview), saved to `settings.json` on "Save".

"Reset to Defaults" link — resets all to defaults.

## Region Calibration Overlay

Full-screen semi-transparent window (`Background="#44000000"`). Click-through disabled (captures mouse input).

**Behavior:**
1. Instructions text centered: "Draw a rectangle over the tooltip area. ESC to cancel."
2. User presses mouse button → start point recorded
3. User drags → rectangle preview drawn (gold dashed border)
4. User releases → region saved to settings, overlay closes
5. ESC → cancel, overlay closes, region unchanged

**Visual feedback:**
- Drawn rectangle: gold dashed border (`#ffd700`), semi-transparent gold fill (`#22ffd700`)
- Current mouse position shown as crosshair

## Persistence

**Settings file:** `%AppData%/D4LootFilter/settings.json`

Uses the existing `AppSettings` model from `D4LootFilter.Matching.Models`:
```json
{
  "capture_regions": {
    "1920x1080": { "x": 400, "y": 200, "width": 500, "height": 600 }
  },
  "active_profile_id": "barbarian-whirl-wind-barb",
  "active_variant_id": 0,
  "polling_fps": 30,
  "ocr_confidence_threshold": 60,
  "fuzzy_match_max_distance": 2,
  "overlay_opacity": 0.85,
  "start_minimized": true,
  "auto_start_capture": false
}
```

**Load on startup:** Read settings.json → load active profile → apply capture region → start pipeline (if auto_start_capture).

**Profile persistence:** Already handled by `ProfileService` in `%AppData%/D4LootFilter/profiles/`.

## Startup Flow (replaces current App.xaml.cs)

1. Single-instance check (mutex — already exists)
2. Load `settings.json` (create defaults if missing)
3. Load active profile from `ProfileService` (if `active_profile_id` set)
4. Create overlay window (transparent, click-through — already exists)
5. Create system tray icon
6. If `auto_start_capture` and active profile exists → start pipeline
7. If `start_minimized` → show only tray icon. Otherwise → open Settings window.
8. If no profiles exist → open Settings window on Profiles tab

## App Exit

- F12 global hotkey → exit (keep existing behavior)
- Tray "Exit" → exit
- Exit saves current settings to `settings.json`

## Project Structure Changes

All new UI files go in the existing `D4LootFilter` WPF project:

```
src/D4LootFilter/
├── App.xaml.cs                    # Rewrite startup flow
├── Views/
│   ├── SettingsWindow.xaml        # Main settings window
│   ├── ProfilesView.xaml          # Tab 1 content (UserControl)
│   ├── CaptureRegionView.xaml     # Tab 2 content (UserControl)
│   ├── SettingsView.xaml          # Tab 3 content (UserControl)
│   └── CalibrationOverlay.xaml    # Region drawing overlay
├── ViewModels/
│   ├── SettingsWindowViewModel.cs # Coordinates tabs, holds state
│   ├── ProfilesViewModel.cs       # Import, list, activate, delete
│   ├── CaptureRegionViewModel.cs  # Region display, calibration trigger
│   └── SettingsViewModel.cs       # Sliders, checkboxes, save/reset
├── TrayIcon/
│   ├── TrayIconManager.cs         # NotifyIcon setup, menu building
│   └── tray-icon.ico              # App icon
├── Services/
│   ├── SettingsService.cs         # Load/save AppSettings JSON
│   ├── PipelineService.cs         # Existing (add Pause/Resume)
│   └── FileLogger.cs              # Existing
├── Overlay/
│   ├── OverlayWindow.xaml         # Existing
│   └── OverlayViewModel.cs        # Existing
└── Themes/
    └── DarkTheme.xaml             # Resource dictionary with dark styles
```

## NuGet Packages to Add

- `Hardcodet.NotifyIcon.Wpf` — system tray support

## PipelineService Changes

Add to existing `PipelineService`:
- `bool IsRunning` property
- `void Pause()` — stops capture loop, keeps resources allocated
- `void Resume()` — restarts capture loop
- `void UpdateSettings(int fps, int ocrThreshold, int matchDistance)` — live update parameters

## Testing Strategy

UI components are hard to unit test. Focus on:
- **SettingsService:** Unit tests for load/save/defaults (file I/O with temp dir, like ProfileService tests)
- **ViewModels:** Unit tests for command logic (import triggers, activate, delete) using mocked services
- **Manual testing:** Pipeline pause/resume, import flow, calibration overlay, settings persistence
