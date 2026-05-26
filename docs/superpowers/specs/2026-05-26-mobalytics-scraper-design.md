# D4 Loot Filter — Plan B: Mobalytics Scraper

## Overview

Import build profiles from Mobalytics URLs via their internal GraphQL API. Converts the API response into the existing `BuildProfile` data model and saves profiles to disk for use by the real-time overlay pipeline.

**Spike findings baked into this design:**
- Direct HTTP POST to `https://mobalytics.gg/api/diablo4/v4/graphql/query` works — no Playwright/headless browser needed
- All build variants are returned in a single response (no per-variant navigation)
- Stat IDs are kebab-case slugs (`"cooldown-reduction"`) — Title Case conversion is sufficient for fuzzy OCR matching
- Variant names live in the `content` section under `NgfDocumentCmWidgetContentVariantsV1` widgets
- Entity `type` field distinguishes item categories: `"aspects"` = Legendary, `"uniqueItems"` = Unique

## Architecture

New `D4LootFilter.Scraper` class library with three components:

```
User pastes URL
       │
       ▼
  ┌─────────────┐     ┌────────────────────┐     ┌─────────────────────┐
  │  UrlParser   │ ──▶ │  MobalyticsClient  │ ──▶ │  BuildProfileParser │
  │              │     │                    │     │                     │
  │ URL → slug   │     │ slug → GraphQL     │     │ JSON → BuildProfile │
  └─────────────┘     │ response           │     └─────────────────────┘
                      └────────────────────┘               │
                                                           ▼
                                                   BuildProfile saved
                                                   to %AppData% as JSON
```

### UrlParser

Extracts the build slug from Mobalytics URLs.

**Supported URL formats:**
- `https://mobalytics.gg/diablo-4/builds/barbarian-whirl-wind-barb`
- `https://mobalytics.gg/diablo-4/builds/barbarian-whirl-wind-barb?some=params`
- `mobalytics.gg/diablo-4/builds/barbarian-whirl-wind-barb` (no scheme)

**Output:** The slug string (e.g., `"barbarian-whirl-wind-barb"`).

**Validation:** Must match pattern `/diablo-4/builds/{slug}`. Returns error for non-Mobalytics URLs or missing slug.

### MobalyticsClient

HTTP client that sends the GraphQL query and returns the raw JSON response.

**Request:**
- `POST https://mobalytics.gg/api/diablo4/v4/graphql/query`
- Headers: `User-Agent` (Chrome-like), `Origin: https://mobalytics.gg`, `Referer` (build URL), `Accept: application/json`
- Body: GraphQL query with `slug` and `type: "builds"` variables
- Operation: `Diablo4UgFeaturedDocumentQuery`

**GraphQL query** (from spike — requests only the fields we need):
```graphql
query Diablo4UgFeaturedDocumentQuery($input: Diablo4UserGeneratedDocumentInputBySlug!) {
  game: diablo4 {
    documents {
      userGeneratedDocumentBySlug(input: $input) {
        error
        data {
          id
          slugifiedName
          type
          data {
            name
            buildVariants {
              values {
                id
                genericBuilder {
                  slots {
                    gameSlotSlug
                    gameEntity {
                      slug
                      title
                      type
                      modifiers {
                        gearStats { id isGreater isMasterwork }
                        temperingStats { id isGreater isMasterwork }
                      }
                      entity {
                        ... on D4Aspect { __typename title: name }
                        ... on D4UniqueItem { __typename title: name chaos mythic }
                      }
                    }
                  }
                }
              }
            }
          }
          content
        }
      }
    }
  }
}
```

**Error handling:**
- HTTP non-2xx → throw with status code and message
- GraphQL `error` field non-null → throw with error message
- Network timeout (10s) → throw

### BuildProfileParser

Transforms raw GraphQL JSON into the existing `BuildProfile` model.

**Slot slug → display name mapping:**

| GraphQL `gameSlotSlug` | BuildProfile `Slot` |
|---|---|
| `helm` | `Helm` |
| `chest-armor` | `Chest Armor` |
| `gloves` | `Gloves` |
| `pants` | `Pants` |
| `boots` | `Boots` |
| `amulet` | `Amulet` |
| `ring-1`, `ring-2` | `Ring` |
| `two-handed-weapon`, `dual-wield-weapon-1`, `dual-wield-weapon-2`, `main-hand`, `off-hand-weapon` | `Weapon` |
| `off-hand` | `Off-Hand` |

Unknown slot slugs are Title-Cased as fallback.

**Entity type → category mapping:**

| GraphQL `gameEntity.type` | EquipmentCategory `Name` |
|---|---|
| `aspects` | `Legendary` |
| `uniqueItems` | `Uniques` |
| Other | `Other` |

**Affix name conversion:**
- Split slug on hyphens, capitalize each word: `"cooldown-reduction"` → `"Cooldown Reduction"`
- Strip Mobalytics-specific prefixes if present (e.g., tempering recipe slugs like `"worldly-endurance-armor"` stay as-is — they only appear in `temperingStats`, not `gearStats`)

**Variant handling:**
- Variant IDs from API are strings → convert to sequential integers (0, 1, 2...) for `BuildVariant.Id`
- Variant names extracted from `content` array → `NgfDocumentCmWidgetContentVariantsV1` → `childrenVariants`
- If no variant names found, name them "Variant 1", "Variant 2", etc.
- `ActiveVariantId` defaults to 0 (first variant)

**What gets extracted per item:**
- `gearStats` → affixes with GA markers (`isGreater: true`)
- `temperingStats` are **excluded** from affix matching — tempering affixes don't appear in the standard affix section of tooltips and would produce false matches
- `implicitStats`, `socketStats`, `sealStats`, `charmStats`, `transfiguredStats` → excluded (not relevant for affix matching)

### ProfileService Updates

Add to existing `ProfileService`:

- `async Task<BuildProfile> ImportFromUrlAsync(string url)` — orchestrates: parse URL → call API → parse response → save to disk → set as active
- `SaveProfile(BuildProfile profile)` — serializes to `%AppData%/D4LootFilter/profiles/{id}.json`
- `List<BuildProfile> ListProfiles()` — reads all profiles from the profiles directory
- `DeleteProfile(string id)` — removes profile file

## Data Flow Example

Input URL: `https://mobalytics.gg/diablo-4/builds/barbarian-whirl-wind-barb`

1. `UrlParser` extracts slug: `"barbarian-whirl-wind-barb"`
2. `MobalyticsClient` sends GraphQL query, gets JSON with all variants
3. `BuildProfileParser` transforms:
   - Build name: `"Whirlwind"`
   - Source URL: the input URL
   - Class: extracted from slug prefix (`"barbarian"`) → `"Barbarian"`
   - Variants: each variant's `genericBuilder.slots` → grouped by entity type into categories → items with affixes
   - Example affix: `{ id: "strength", isGreater: false }` → `{ Name: "Strength", IsGa: false }`
4. Saved as `%AppData%/D4LootFilter/profiles/barbarian-whirl-wind-barb.json`

## Project Structure

```
src/
├── D4LootFilter.Scraper/              # New project
│   ├── D4LootFilter.Scraper.csproj
│   ├── UrlParser.cs
│   ├── MobalyticsClient.cs
│   └── BuildProfileParser.cs
│
├── D4LootFilter.Scraper.Tests/        # New test project
│   ├── D4LootFilter.Scraper.Tests.csproj
│   ├── UrlParserTests.cs
│   ├── MobalyticsClientTests.cs
│   ├── BuildProfileParserTests.cs
│   └── TestData/
│       └── whirlwind-barb-response.json   # Saved from spike
│
├── D4LootFilter/                      # Existing — updated
│   └── Services/
│       └── ProfileService.cs          # Add ImportFromUrlAsync, SaveProfile, ListProfiles
│
└── D4LootFilter.Matching/             # Existing — unchanged
    └── Models/
        └── BuildProfile.cs
```

## Testing Strategy

- **UrlParser:** Unit tests with various URL formats, edge cases (no scheme, trailing slashes, query params, invalid URLs)
- **BuildProfileParser:** Unit tests using the real GraphQL response saved from the spike as a test fixture. Verify slot mapping, affix name conversion, GA markers, variant extraction, category grouping.
- **MobalyticsClient:** One integration test that hits the real API (marked `[Trait("Category", "Integration")]` so it can be skipped in CI). Verifies the query still works and the response structure hasn't changed.
- **ProfileService:** Unit tests for save/load/list/delete with temp directory.

## Constraints

1. **API stability** — Mobalytics GraphQL schema is internal and can change without notice. The parser should fail gracefully with clear error messages when the response structure doesn't match expectations.
2. **Rate limiting** — Unknown. Use a single request per import (the API returns all variants at once). No bulk/batch import in this iteration.
3. **No authentication** — The API is public (no login required). If Mobalytics adds auth/bot protection later, Playwright fallback can be added.
