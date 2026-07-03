# PB-Wiki Modularization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Split the monolithic `tools/pb-wiki/index.html` (205 lines CSS + ~398 lines inline JS) into one CSS file and five focused JS files, so editing any UI concern reads a ~80-line file instead of the whole 45 KB monolith.

**Architecture:** Pure behavior-preserving code move. Classic `<script src>` tags (NOT ES modules — those are CORS-blocked over `file://`) share one global lexical scope, so splitting the single `<script>` into ordered external files is identical to concatenation — no cross-reference rewriting. The page still opens by double-click.

**Tech Stack:** Plain HTML/CSS/JS, no build step, no runtime, no dependencies. Verification is browser-based (open `index.html`, check console + features) plus a mechanical line-set equality gate.

## Global Constraints

- Classic scripts only — **never** add `type="module"` (breaks `file://` via CORS).
- **Do not** introduce a `window.PB` namespace or rename/rewrite any identifier — this is a move, not a refactor.
- **Do not** touch `data.js` or `extract.py`.
- Each new `.js` file MUST begin with `"use strict";` (the original single script was strict; preserve that per-file).
- Script load order in `index.html` is fixed: `data.js` → `core.js` → `filters.js` → `list.js` → `detail.js` → `interactions.js`.
- The boot line `readURL(); applyURL();` MUST remain the last executed statement (ends up at the bottom of `interactions.js`).
- Line numbers below refer to the **pre-refactor** `index.html` (651 lines). Because the plan is incremental, later tasks reference the *original* ranges — always locate code by its content/section marker, not by re-counting after edits.

---

## Task 0 (fold into Task 1): Preserve the original for the mechanical gate

Before any edit, save a pristine copy used by the final equality check:

```bash
cd /d/git/home/tools/pb-wiki
cp index.html /c/Users/yelow/AppData/Local/Temp/claude/D--git-home/d623c1ce-4ee4-4c4f-9abf-1cc651ba85fe/scratchpad/index.orig.html
```

---

### Task 1: Extract CSS → `styles.css`

CSS is independent of JS — safest first move and a clean warm-up.

**Files:**
- Create: `tools/pb-wiki/styles.css`
- Modify: `tools/pb-wiki/index.html` (replace `<style>…</style>`, original lines 7–212)

**Interfaces:**
- Consumes: nothing.
- Produces: `styles.css` containing all rules; `index.html` links it in `<head>`.

- [ ] **Step 0:** Run the Task 0 copy command above.

- [ ] **Step 1: Create `styles.css`** with the exact contents of original `index.html` lines **8–211** (everything *between* `<style>` and `</style>`, exclusive). No `<style>` tags in the file. Do not alter any rule.

- [ ] **Step 2: Edit `index.html`** — replace the entire block from `<style>` (line 7) through `</style>` (line 212) inclusive with a single line inside `<head>`:

```html
<link rel="stylesheet" href="styles.css">
```

- [ ] **Step 3: Verify in browser.** Open `index.html` by double-click (`file://`). Expected: page looks **pixel-identical** to before (dark theme, sidebar, table). Open DevTools Console — expected: **no errors**, no 404 for `styles.css`.

- [ ] **Step 4: Commit**

```bash
cd /d/git/home
git add tools/pb-wiki/styles.css tools/pb-wiki/index.html
git commit -m "refactor(pb-wiki): extract CSS to styles.css"
```

---

### Task 2: Extract `core.js` (shared foundation)

**Files:**
- Create: `tools/pb-wiki/core.js`
- Modify: `tools/pb-wiki/index.html`

**Interfaces:**
- Consumes: `window.PB_DATA` (from `data.js`).
- Produces (visible to all later files via shared global scope): constants `D, SM, IC, RARN, RARC, HIDE, LOWER_BETTER, RANGES`; helpers `esc, icon, SLOTLBL, barMax`; derived globals `MNFS, CATS, BOUNDS`; state object `state`; functions `writeURL, readURL, inRanges, matchItem, facetCount, fmtStat, statColor, statName, statIcon`.

- [ ] **Step 1: Create `core.js`.** First line `"use strict";`, then paste **verbatim**, in this order, these original ranges:
  - lines **253–261** — constants + helpers (`D`, `SM`, `IC`, `esc`, `icon`, `RARN`, `RARC`, `SLOTLBL`, `HIDE`, `LOWER_BETTER`)
  - lines **262–276** — prep block (item/module preprocessing, `MNFS`, `CATS`, `BOUNDS`, `barMax`)
  - lines **277–309** — state + URL (`RANGES`, `state`, `writeURL`, `readURL`)
  - lines **310–327** — matching + counts (`inRanges`, `matchItem`, `facetCount`)
  - lines **499–507** — formatting (`fmtStat`, `statColor`, `statName`, `statIcon`)

  (Formatting is relocated earlier than its original position; safe because all four are function declarations, hoisted, and only read `SM`/`IC`.)

- [ ] **Step 2: Edit `index.html`** — remove those exact lines from the inline `<script>`, and add the tag immediately after the `data.js` tag:

```html
<script src="data.js"></script>
<script src="core.js"></script>
```

- [ ] **Step 3: Verify in browser.** Reload `index.html`. Console: **no errors** (a `ReferenceError` here would mean a range was missed). Page still renders the full table, filters populate with counts. Type in search — results filter.

- [ ] **Step 4: Commit**

```bash
cd /d/git/home
git add tools/pb-wiki/core.js tools/pb-wiki/index.html
git commit -m "refactor(pb-wiki): extract core.js (data, state, matching, formatting)"
```

---

### Task 3: Extract `filters.js` (left panel + columns)

**Files:**
- Create: `tools/pb-wiki/filters.js`
- Modify: `tools/pb-wiki/index.html`

**Interfaces:**
- Consumes from core.js: `state, D, SM, IC, BOUNDS, MNFS, CATS, esc, matchItem, facetCount, render, writeURL`.
- Produces: `COLLAPSED`; functions `buildFilters, fgroup, optHTML, rangeHTML, bindRanges, buildCountsOnly, resetBtn, resetFilters, activeColumns` (+ constants `COL_WEAPON, COL_ARMOR, COL_BACK`); attaches the `#filters` click listener.

- [ ] **Step 1: Create `filters.js`.** First line `"use strict";`, then paste **verbatim**:
  - lines **328–396** — filters UI (`buildFilters`, `COLLAPSED`, `fgroup`, `optHTML`, `rangeHTML`, `bindRanges`, `buildCountsOnly`, `resetBtn`, `resetFilters`, and the `document.getElementById('filters').addEventListener(...)` block)
  - lines **397–413** — columns (`COL_WEAPON`, `COL_ARMOR`, `COL_BACK`, `activeColumns`)

- [ ] **Step 2: Edit `index.html`** — remove those lines from the inline script; add the tag after `core.js`:

```html
<script src="core.js"></script>
<script src="filters.js"></script>
```

- [ ] **Step 3: Verify in browser.** Reload. Console clean. Click facet options (Тип, Набор, Вес, Категория, Производитель) → list filters and counts update. Drag a range slider → list narrows, counts refresh. Collapse/expand a filter group. Click "Сбросить фильтры" → all clear.

- [ ] **Step 4: Commit**

```bash
cd /d/git/home
git add tools/pb-wiki/filters.js tools/pb-wiki/index.html
git commit -m "refactor(pb-wiki): extract filters.js (facets, ranges, columns)"
```

---

### Task 4: Extract `list.js` (center: table, cards, chips)

**Files:**
- Create: `tools/pb-wiki/list.js`
- Modify: `tools/pb-wiki/index.html`

**Interfaces:**
- Consumes from core/filters: `state, D, SM, esc, icon, barMax, fmtStat, statColor, activeColumns, matchItem, buildFilters, writeURL, renderMods, openItem, openMod, toggleCmp, syncSel`.
- Produces: functions `getList, render, renderChips, plural, statCell, tableHTML, cardsHTML`; attaches the `#chips` and `#scroll` click listeners.

- [ ] **Step 1: Create `list.js`.** First line `"use strict";`, then paste **verbatim** original lines **414–498** — render pipeline (`getList`, `render`, `renderChips`, `plural`, the `#chips` click listener, `statCell`, `tableHTML`, `cardsHTML`, the `#scroll` click listener).

- [ ] **Step 2: Edit `index.html`** — remove those lines; add tag after `filters.js`:

```html
<script src="filters.js"></script>
<script src="list.js"></script>
```

- [ ] **Step 3: Verify in browser.** Reload. Console clean. Table renders with stat bars. Click a column header → sorts; click again → reverses (arrow flips). Toggle to cards view (⊞) → cards render; back to table (≣). Active-filter chips appear when filtering; click a chip's × → removes that filter.

- [ ] **Step 4: Commit**

```bash
cd /d/git/home
git add tools/pb-wiki/list.js tools/pb-wiki/index.html
git commit -m "refactor(pb-wiki): extract list.js (table, cards, chips)"
```

---

### Task 5: Extract `detail.js` (right panel + modules)

**Files:**
- Create: `tools/pb-wiki/detail.js`
- Modify: `tools/pb-wiki/index.html`

**Interfaces:**
- Consumes: `state, D, SM, IC, esc, icon, RARN, RARC, SLOTLBL, HIDE, fmtStat, statColor, statName, statIcon, barMax, writeURL, syncSel`.
- Produces: functions `openPanel, closePanel, openItem, closeDetail, syncSel, renderDetail, drawStats, drawSlots, renderMods, openMod`.

- [ ] **Step 1: Create `detail.js`.** First line `"use strict";`, then paste **verbatim**:
  - lines **508–555** — detail panel (`openPanel`, `closePanel`, `openItem`, `closeDetail`, `syncSel`, `renderDetail`, `drawStats`, `drawSlots`)
  - lines **556–584** — modules (`renderMods`, `openMod`)

- [ ] **Step 2: Edit `index.html`** — remove those lines; add tag after `list.js`:

```html
<script src="list.js"></script>
<script src="detail.js"></script>
```

- [ ] **Step 3: Verify in browser.** Reload. Console clean. Click a table row → detail panel opens on the right (list not overlapped). Drag the level slider (1–99) → HP/Barrier/Damage recompute and show ↑. Click rarity buttons (Обычное/Необычное/Редкое) → module slots lock/unlock with color. Switch to "Модификации" tab → module family cards render; click one → module detail with tiers. Close panel (×).

- [ ] **Step 4: Commit**

```bash
cd /d/git/home
git add tools/pb-wiki/detail.js tools/pb-wiki/index.html
git commit -m "refactor(pb-wiki): extract detail.js (item + module detail panel)"
```

---

### Task 6: Extract `interactions.js` (compare, tooltip, tabs, boot) + finalize `index.html`

This empties the inline `<script>` entirely. The boot line moves to the bottom of `interactions.js` and stays last.

**Files:**
- Create: `tools/pb-wiki/interactions.js`
- Modify: `tools/pb-wiki/index.html`

**Interfaces:**
- Consumes: `state, D, SM, HIDE, LOWER_BETTER, esc, fmtStat, statName, SLOTLBL, activeColumns, syncSel, writeURL, buildFilters, render, closeDetail, openPanel, closePanel, renderDetail, openMod, buildCountsOnly, readURL`.
- Produces: functions `toggleCmp, updateCmp, setTab, setView, applyURL, openModRaw`; attaches `#cmpits`/`#cmpclr`/`#cmpgo`/`#modal` listeners, `#scroll` mouseover/mousemove/mouseout tooltip listeners, `.tab`/`.viewtoggle`/`#q` listeners, `keydown` and `popstate`; runs boot `readURL(); applyURL();`.

- [ ] **Step 1: Create `interactions.js`.** First line `"use strict";`, then paste **verbatim** original lines **585–648**:
  - 585–605 comparison, 606–622 tooltip, 623–636 tabs/view/search, 637–648 boot (ending with `readURL(); applyURL();`).

- [ ] **Step 2: Edit `index.html`** — the inline `<script> "use strict"; … </script>` block is now empty of code; delete the entire inline `<script>…</script>` element and add the final tag. The script section must read exactly:

```html
<script src="data.js"></script>
<script src="core.js"></script>
<script src="filters.js"></script>
<script src="list.js"></script>
<script src="detail.js"></script>
<script src="interactions.js"></script>
</body>
</html>
```

- [ ] **Step 3: Verify in browser.** Reload. Console clean. Select 2+ items via the compare checkbox → compare bar appears → "Сравнить →" opens modal with best/worst highlighting. Hover a row → tooltip follows cursor. Press `/` → search focuses. Press `Esc` → closes modal/panel/blur. This is the full app on modular files.

- [ ] **Step 4: Commit**

```bash
cd /d/git/home
git add tools/pb-wiki/interactions.js tools/pb-wiki/index.html
git commit -m "refactor(pb-wiki): extract interactions.js + finalize modular index.html"
```

---

### Task 7: Mechanical equality gate + full verification + README

**Files:**
- Modify: `tools/pb-wiki/README.md`

- [ ] **Step 1: Mechanical line-set equality.** Prove no JS line was added, dropped, or altered — only moved. Compare the original inline JS body against the concatenation of all five new files (each minus its added `"use strict";` prologue), as sorted trimmed non-empty line sets:

```bash
cd /d/git/home/tools/pb-wiki
SCRATCH=/c/Users/yelow/AppData/Local/Temp/claude/D--git-home/d623c1ce-4ee4-4c4f-9abf-1cc651ba85fe/scratchpad
# original inline JS body = lines 253..648 of the pristine copy
sed -n '253,648p' "$SCRATCH/index.orig.html" | sed 's/[[:space:]]*$//' | grep -v '^[[:space:]]*$' | sort > "$SCRATCH/orig.set"
# new: concat the 5 files, drop the leading "use strict"; line from each
for f in core filters list detail interactions; do tail -n +2 "$f.js"; done \
  | sed 's/[[:space:]]*$//' | grep -v '^[[:space:]]*$' | grep -v '^"use strict";$' | sort > "$SCRATCH/new.set"
diff "$SCRATCH/orig.set" "$SCRATCH/new.set" && echo "GATE PASS: identical line set"
```
Expected: `GATE PASS: identical line set` with no diff output. If diff shows lines, a section was mis-cut — fix before proceeding.

- [ ] **Step 2: Full functional checklist in browser** (open `index.html`, DevTools Console open the whole time — must stay error-free):
  1. Facet filters + live counts; "Сбросить всё".
  2. Dual-range sliders (drag, commit, counts refresh).
  3. Table ⇄ cards toggle.
  4. Column sort (click + reverse).
  5. Detail: level slider recomputes stats; rarity toggles slots.
  6. "Модификации" tab + open a module.
  7. Compare: pick ≥2 → modal with best/worst.
  8. Tooltip on hover.
  9. Search: `/` focus, debounce, counts.
  10. **URL round-trip:** apply filters + sort + open an item → copy the address-bar URL → reload → identical state restored; browser Back works.

- [ ] **Step 3: Update `README.md`.** In the "Как открыть" section (original lines 6–9), replace the note that only `data.js` must sit alongside with one covering all companion files. Change the paragraph to:

```markdown
## Как открыть

Просто откройте **`index.html`** двойным кликом. Рядом должны лежать
`data.js`, `styles.css` и файлы `core.js`, `filters.js`, `list.js`,
`detail.js`, `interactions.js` (все — в этой же папке). Ничего
ставить/запускать не нужно.
```

- [ ] **Step 4: Commit**

```bash
cd /d/git/home
git add tools/pb-wiki/README.md
git commit -m "docs(pb-wiki): note companion JS/CSS files in README"
```

- [ ] **Step 5: Cleanup.** Remove the scratchpad copy:

```bash
rm -f /c/Users/yelow/AppData/Local/Temp/claude/D--git-home/d623c1ce-4ee4-4c4f-9abf-1cc651ba85fe/scratchpad/index.orig.html /c/Users/yelow/AppData/Local/Temp/claude/D--git-home/d623c1ce-4ee4-4c4f-9abf-1cc651ba85fe/scratchpad/orig.set /c/Users/yelow/AppData/Local/Temp/claude/D--git-home/d623c1ce-4ee4-4c4f-9abf-1cc651ba85fe/scratchpad/new.set
```

---

## Self-Review

**Spec coverage:** styles.css (Task 1) ✓; core/filters/list/detail/interactions split (Tasks 2–6) ✓; classic-scripts-no-namespace (Global Constraints + every task pastes verbatim) ✓; load order fixed (Task 6 Step 2) ✓; boot last (Task 6) ✓; data.js/extract.py untouched (Global Constraints; no task modifies them) ✓; 10-point verification (Task 7 Step 2) ✓; "use strict" per file (every create step) ✓. No gaps.

**Placeholder scan:** No TBD/TODO. Extraction steps give exact original line ranges + the exact top-level identifiers expected in each file, so completeness is checkable without re-deriving. The mechanical gate (Task 7 Step 1) objectively catches any missed/altered line.

**Type consistency:** Identifier names in the Interfaces blocks match the source verbatim (no renaming is permitted anywhere), so cross-file names are consistent by construction. Load order in every "add tag" step is consistent with the Global Constraints order.
