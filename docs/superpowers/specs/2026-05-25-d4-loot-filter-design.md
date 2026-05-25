# D4 Loot Filter — Design Specification

## Overview

A local Windows desktop application that provides real-time overlay assistance for Diablo 4. It monitors a user-defined screen region for item tooltips, performs OCR to extract affix text, matches it against imported build profiles from Mobalytics, and highlights matching affixes with a transparent click-through overlay.

**Primary goal:** Sub-50ms response from tooltip appearance to overlay render. Invisible to user — no mouse blocking, no FPS impact, no game interference.

## Architecture

Single-process WPF application (.NET 8) with dedicated threads:

```
┌─────────────────────────────────────────────────────────────┐
│                    D4 Loot Filter                           │
│                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │ Capture      │→ │ OCR          │→ │ Match & Overlay   │  │
│  │ Thread       │  │ Thread Pool  │  │ (UI Thread)       │  │
│  │ ~3-5ms/frame │  │ ~10-25ms     │  │ ~2ms match+render │  │
│  └──────────────┘  └──────────────┘  └──────────────────────┘
│                                                             │
│  ┌──────────────────────┐  ┌───────────────┐               │
│  │ Profile Manager      │  │ System Tray   │               │
│  │ (Scraper + Storage)  │  │ (Control UI)  │               │
│  └──────────────────────┘  └───────────────┘               │
└─────────────────────────────────────────────────────────────┘
```

### Thread Model

- **Capture Thread** (high priority): DXGI Desktop Duplication API. Captures frames at 30-60 FPS. Crops to user-defined region. Performs hash-based change detection — skips OCR if frame unchanged.
- **OCR Thread Pool** (2-4 threads): Receives changed frames. Preprocesses image (grayscale → adaptive threshold → inversion). Runs Tesseract 5 OCR. Returns text lines with bounding box coordinates.
- **UI Thread**: WPF dispatcher. Receives match results. Renders overlay and mini-panel. Handles settings window and system tray.

## Screen Capture & Tooltip Detection

### Capture Method

DXGI Desktop Duplication API via Vortice.Windows (modern, maintained .NET bindings).

**Constraint:** Requires Diablo 4 in Borderless Windowed or Windowed mode. Exclusive fullscreen is not supported by Desktop Duplication.

### Region Setup

1. User clicks "Calibrate" → transparent fullscreen overlay appears
2. User draws a rectangle over the area where tooltips appear
3. Region is saved to config, keyed by screen resolution
4. "Recalibrate" available from system tray at any time

### Tooltip Detection (Hybrid)

Within the user-defined region:
1. Detect sharp transition to dark background (D4 tooltip background is near-black, ~RGB 15-25)
2. Find tooltip boundaries by scanning for the dark rectangle edges
3. Quick contrast check — if no high-contrast text present, skip (no tooltip visible)
4. On detection → crop tooltip area → send to OCR pipeline

### Change Detection

Compare perceptual hash (pHash) of current cropped region against previous frame. If hash distance < threshold → tooltip unchanged → skip OCR. This eliminates ~90% of redundant OCR calls while tooltip is stationary.

## OCR Pipeline

### Engine

Tesseract 5 via Tesseract.NET wrapper (`Tesseract` NuGet package).

### Preprocessing

1. Crop to detected tooltip bounds
2. Convert to grayscale
3. Adaptive threshold (Otsu's method)
4. Invert colors (Tesseract works better with black text on white background)
5. Optional: upscale 2x for small text at low resolutions

### Configuration

- Language: `eng` (English only)
- Page segmentation mode: PSM 6 (uniform block of text) or PSM 4 (single column)
- Character whitelist: printable ASCII + common D4 symbols
- Tesseract traineddata: `eng.traineddata` bundled with app (in `lib/tessdata/`)

### Output

List of `OcrLine` objects:
```csharp
record OcrLine(string Text, Rectangle BoundingBox, float Confidence);
```

Lines with confidence < 60% are discarded.

## Affix Matching

### Slot Detection

OCR output is scanned for item type keywords to determine equipment slot:

| Keyword in tooltip | Detected slot |
|---|---|
| Helm | Helm |
| Chest Armor | Chest Armor |
| Gloves | Gloves |
| Pants | Pants |
| Boots | Boots |
| Amulet | Amulet |
| Ring | Ring |
| Sword, Mace, Axe, Polearm, Staff, Bow, Crossbow, Dagger, Scythe, Wand | Weapon |
| Shield, Focus, Totem | Off-Hand |

The detector looks for patterns like "Ancestral Legendary **Helm**", "Unique **Chest Armor**", etc. — the item type line typically appears near the top of the tooltip.

**Fallback when slot is not detected:** If no slot keyword is found in OCR output, match the item's affixes against ALL slots in the active build variant. This is slower but ensures no tooltip is silently skipped due to OCR misread of the type line.

### Normalization

For each OCR line that could be an affix:
1. Strip leading `+` and numeric values (regex: `^[+\-]?[\d,.]+%?\s*`)
2. Trim whitespace
3. Convert to lowercase
4. Result: `"+12.5% Cooldown Reduction"` → `"cooldown reduction"`

### Fuzzy Matching

Compare normalized OCR text against the active build variant's affixes for the detected slot.

**Algorithm:** Levenshtein distance via FuzzySharp library.
- Exact match (distance 0): highest confidence
- Distance ≤ 2: accepted match (accounts for OCR errors like `l`/`1`, `O`/`0`)
- Distance > 2: no match

Additionally, contains-match as fallback: if the normalized OCR text contains the full affix name or vice versa.

### Match Result

```csharp
record AffixMatch(
    string AffixName,
    bool IsGa,
    bool IsMatched,
    Rectangle ScreenPosition,  // bounding box from OCR
    float MatchConfidence
);
```

## Overlay

### Window Properties

- WPF Window: `WindowStyle=None`, `AllowsTransparency=True`, `Topmost=True`, `ShowInTaskbar=False`
- Win32 extended style: `WS_EX_TRANSPARENT | WS_EX_LAYERED` (click-through)
- Background: fully transparent
- Position: covers the tooltip region

### Visual Elements

**Affix highlights** (drawn over each matched affix line):
- **GA match**: semi-transparent gold background (`rgba(255, 215, 0, 0.15)`) + gold left border (3px) + star icon
- **Regular match**: semi-transparent green background (`rgba(76, 175, 80, 0.15)`) + green left border (3px) + checkmark
- **No match**: no overlay (affix line is untouched)

**Mini-panel** (positioned adjacent to tooltip, top-right):
- Build name + detected slot
- Progress bar: `N/M affixes matched`
- GA match count
- List of missing affixes (in red)
- Semi-transparent dark background with border

### Rendering

Overlay updates via WPF dispatcher (`Dispatcher.InvokeAsync`) with `DispatcherPriority.Render`. Positions are mapped from OCR bounding boxes (relative to capture region) to screen coordinates.

Overlay is hidden when no tooltip is detected (change detection returns "no tooltip" for consecutive frames).

## Mobalytics Scraper

### Challenge

Mobalytics uses JavaScript rendering (React) and bot protection (returns 403 for direct HTTP requests). Plain HttpClient + HTML parser will not work.

### Solution: Headless Browser

Use **Playwright for .NET** (`Microsoft.Playwright`) to render the page fully in a headless Chromium instance.

**Alternative strategy (preferred if feasible):** During implementation, inspect browser Network tab to find the internal GraphQL/REST API that the Mobalytics frontend calls. If the API is accessible with proper headers (User-Agent, cookies), we can use HttpClient directly — much faster and lighter. Playwright serves as the fallback.

### Import Flow

1. User pastes a Mobalytics build URL (base or with variant ID)
2. App launches headless browser, navigates to the URL
3. Waits for equipment section to render (DOM ready check)
4. **Variant discovery:** Extract all available variants from the page (tab/button elements with variant names and IDs)
5. Show dialog to user: "Found N variants — select which to import" with checkboxes
6. For each selected variant:
   a. Navigate to URL with `?ws-ngf5-1=activeVariantId,{id}`
   b. Wait for equipment section to re-render
   c. Parse Equipment tabs (Legendary, Uniques, etc.)
   d. For each item: extract slot, name, and affix list
   e. Detect GA markers (likely a CSS class, icon element, or special styling on the affix)
7. Save as JSON profile

### HTML Parsing (post-render)

After Playwright renders the page, extract the DOM using `page.QuerySelectorAllAsync()` or `page.EvaluateAsync()`. The exact CSS selectors will be determined during implementation by inspecting the live page structure.

Key elements to locate:
- Equipment section container
- Equipment sub-tabs (Legendary, Uniques, Tempering, etc.)
- Item cards within each tab
- Affix list within each item card
- GA indicator on affixes

## Data Model

### Profile JSON Structure

Stored in `%AppData%/D4LootFilter/profiles/{id}.json`:

```json
{
  "id": "barbarian-whirl-wind-barb",
  "name": "Barbarian Whirlwind",
  "source_url": "https://mobalytics.gg/diablo-4/builds/barbarian-whirl-wind-barb",
  "class": "Barbarian",
  "imported_at": "2026-05-25T12:00:00Z",
  "variants": [
    {
      "id": 0,
      "name": "Default",
      "equipment": {
        "categories": [
          {
            "name": "Legendary",
            "items": [
              {
                "slot": "Helm",
                "name": "Godslayer Crown",
                "affixes": [
                  { "name": "Cooldown Reduction", "is_ga": true },
                  { "name": "Maximum Life", "is_ga": false },
                  { "name": "Total Armor", "is_ga": false },
                  { "name": "Intelligence", "is_ga": false }
                ]
              }
            ]
          },
          {
            "name": "Uniques",
            "items": [
              {
                "slot": "Amulet",
                "name": "Shako",
                "affixes": [
                  { "name": "Cooldown Reduction", "is_ga": true },
                  { "name": "Resource Cost Reduction", "is_ga": false }
                ]
              }
            ]
          }
        ]
      }
    },
    {
      "id": 1,
      "name": "Pit Push",
      "equipment": {
        "categories": [ ]
      }
    }
  ],
  "active_variant_id": 0
}
```

### Settings JSON

Stored in `%AppData%/D4LootFilter/settings.json`:

```json
{
  "capture_region": {
    "1920x1080": { "x": 400, "y": 200, "width": 500, "height": 600 },
    "2560x1440": { "x": 533, "y": 267, "width": 667, "height": 800 }
  },
  "active_profile_id": "barbarian-whirl-wind-barb",
  "polling_fps": 30,
  "ocr_confidence_threshold": 60,
  "fuzzy_match_max_distance": 2,
  "overlay_opacity": 0.85,
  "start_minimized": true,
  "auto_start_capture": false
}
```

## UI

### System Tray

Application lives in the system tray (NotifyIcon). Context menu:
- Status indicator (Running / Paused)
- **Switch Profile** → submenu with builds → submenu with variants
- Pause / Resume capture
- Recalibrate Region
- Settings (opens settings window)
- Exit

### Settings Window

Three tabs:
1. **Profiles** — list of imported builds, import field (URL input + Import button), activate/delete profiles, variant picker within each profile
2. **Capture Region** — current region preview, resolution binding info, Recalibrate button
3. **Settings** — polling FPS, OCR confidence threshold, fuzzy match distance, overlay opacity, startup behavior

### Import Dialog

Modal dialog shown during import:
- URL being imported
- Progress indicator
- List of discovered variants with checkboxes
- "Import Selected" / "Import All" / "Cancel" buttons

## Technology Stack

| Component | Technology | NuGet Package |
|---|---|---|
| Framework | .NET 8, WPF | — |
| Screen Capture | DXGI Desktop Duplication | Vortice.Direct3D11, Vortice.DXGI |
| OCR | Tesseract 5 | Tesseract (wrapper) |
| Image Processing | OpenCV (preprocessing) | OpenCvSharp4 |
| Web Scraping | Headless Chromium | Microsoft.Playwright |
| HTML Parsing (fallback) | AngleSharp | AngleSharp |
| Fuzzy Matching | Levenshtein distance | FuzzySharp |
| JSON | System.Text.Json | built-in |
| System Tray | Hardcodet.NotifyIcon.Wpf | Hardcodet.NotifyIcon.Wpf |

## Project Structure

```
D4LootFilter/
├── D4LootFilter.sln
├── src/
│   ├── D4LootFilter/                    # WPF App (entry point)
│   │   ├── App.xaml                     # Startup, DI, single instance
│   │   ├── MainWindow.xaml              # Settings window
│   │   ├── Views/
│   │   │   ├── ProfilesView.xaml        # Profiles tab
│   │   │   ├── CaptureRegionView.xaml   # Region configuration
│   │   │   ├── SettingsView.xaml        # General settings
│   │   │   └── ImportDialog.xaml        # Variant picker
│   │   ├── Overlay/
│   │   │   ├── OverlayWindow.xaml       # Transparent click-through
│   │   │   └── OverlayViewModel.cs      # Match results → visual
│   │   └── TrayIcon/
│   │       └── TrayIconManager.cs       # System tray + menu
│   │
│   ├── D4LootFilter.Capture/            # Screen capture library
│   │   ├── DxgiCapture.cs               # Desktop Duplication
│   │   ├── FrameChangeDetector.cs       # pHash-based diff
│   │   └── TooltipDetector.cs           # Boundary detection
│   │
│   ├── D4LootFilter.Ocr/               # OCR pipeline
│   │   ├── TesseractOcrEngine.cs        # Tesseract wrapper
│   │   ├── ImagePreprocessor.cs         # Threshold, crop, invert
│   │   └── TextLineExtractor.cs         # Lines + bounding boxes
│   │
│   ├── D4LootFilter.Matching/          # Affix matching
│   │   ├── AffixMatcher.cs              # Fuzzy match logic
│   │   ├── SlotDetector.cs              # Item type → slot
│   │   └── MatchResult.cs               # Result models
│   │
│   └── D4LootFilter.Scraper/           # Mobalytics import
│       ├── MobalyticsScraper.cs         # Playwright-based scraper
│       ├── VariantDiscovery.cs          # Find all build variants
│       └── AffixExtractor.cs            # Extract items + affixes + GA
│
├── data/
│   └── profiles/                        # Dev/test profile samples
│
└── lib/
    └── tessdata/
        └── eng.traineddata              # Tesseract English model
```

## Constraints & Known Limitations

1. **Borderless Windowed only** — DXGI Desktop Duplication does not capture exclusive fullscreen. App must show a warning if D4 is in exclusive fullscreen.
2. **English only** — OCR and affix matching assume English game client and Mobalytics data.
3. **Mobalytics HTML stability** — Web scraper depends on Mobalytics page structure. Site redesigns will break the scraper. Design the scraper module to be easily updateable.
4. **Playwright size** — Bundling headless Chromium adds ~100-150MB to app size. Consider lazy download on first import, or investigate API-based scraping during implementation.
5. **Anti-cheat** — This app reads screen pixels only (same as any screenshot tool). It does not inject into the game process, modify memory, or intercept game network traffic. This approach is equivalent to a screen recording and should not trigger anti-cheat.
6. **Single monitor** — Initial version supports single monitor. Capture region is defined on the primary display.

## Performance Targets

| Metric | Target |
|---|---|
| Frame capture | < 5ms |
| Change detection | < 1ms |
| OCR (tooltip region) | < 25ms |
| Affix matching | < 2ms |
| Overlay render | < 5ms |
| **Total pipeline** | **< 40ms** |
| CPU usage (idle, no tooltip) | < 1% |
| CPU usage (active scanning) | < 5% |
| Memory usage | < 150MB (excluding Playwright) |
