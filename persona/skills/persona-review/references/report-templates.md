# Report Templates

All HTML is **self-contained**: inline CSS and inline vanilla JS only, no external fonts,
scripts, or images. Charts are drawn with inline `<canvas>` + a small inline script or with
pure CSS/SVG bars. No CDN.

**MANDATORY — every standalone `.html` output MUST be a complete document that begins with a
`<head>` declaring UTF-8, or Cyrillic/non-ASCII text renders as mojibake (e.g. `Ð'ÐµÐµÑ€`) when
opened in a browser. Always start each HTML file with exactly:**

```html
<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>…</title>
</head>
<body>
```

**and close with `</body></html>`.** Write the file as UTF-8 (no BOM). The `<meta charset="utf-8">`
is not optional — it is the single most common defect in generated reports.

## `persona-feedback.md`

```markdown
# Обратная связь персон: <document basename>

> Уровень враждебности: <N> — <level name>. Персон: <count>.

## <id>. <name> — <role>, <company>
**Вердикт:** <verdict> — <stance_line>

**Сильное:** <strengths as bullets>

**Проблемы:**
- [<severity>] <location> — <problem>

**Условия, чтобы перестать сопротивляться** (conditions_to_stop_resisting): <bullets>

**Слепые зоны:** <bullets>

**Оценки (0–10):** ясность <>, полнота <>, реалистичность <>, соответствие интересам <>, доверие <>

---
(repeat per persona; if a persona failed, render: "Персона <id> не дала ответ.")
```

## `persona-feedback.html`

A standalone page with: a header, one card per persona (same data as md), and the infographics
block (below). Inline `<style>` for cards; verdict color-coded (reject=red, conditions=amber,
accept=green).

### `persona-feedback.html` / `synthesis.html` skeleton (self-contained, inline only)

```html
<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Обратная связь персон — persona-review</title>
<style>
  .persona{border:1px solid #ddd;border-radius:8px;padding:12px;margin:12px 0;font:14px system-ui}
  .verdict{font-weight:600;padding:2px 8px;border-radius:4px;color:#fff}
  .reject{background:#c0392b}.accept_with_conditions{background:#d68910}.accept{background:#1e8449}
</style>
</head>
<body>
<h1>Обратная связь персон: <NAME></h1>
<div class="persona">
  <h2>01. <name> — <role>, <company></h2>
  <span class="verdict reject"><verdict> — <stance_line></span>
  <!-- strengths / issues(severity,location,problem) / conditions_to_stop_resisting / blind_spots / axis_scores rendered as lists -->
</div>
<!-- failed persona: --> <div class="persona">Персона 02 не дала ответ.</div>

<h2>Инфографика</h2>
<div id="consensus"></div>
<script>
  // the bar() helper above is reused; feed it data derived from the reviewer JSON array
  bar(document.getElementById('consensus'), [
    {label:'Проблема X', value:3, color:'#c0392b'},
    {label:'Проблема Y', value:2, color:'#d68910'}
  ]);
</script>
</body>
</html>
```

`synthesis.html` uses the same self-contained pattern, rendering the six synthesis sections as cards plus the infographics block.

## `synthesis.md` (skeleton — render the six sections from `synthesis-protocol.md` in order)

```markdown
# Сводный отчёт: <document basename>

## 1. Вердикт панели
accept: <n> · с условиями: <n> · reject: <n> — <одна строка общего вывода>

## 2. Консенсусные проблемы
- [<severity>] <location> — <problem> (подняли: <raised_by>)

## 3. Противоречия
- <персона A> принимает <X>, <персона B> отвергает — <суть>

## 4. Приоритизированный план улучшений
1. <change> — удовлетворяет: <persona ids>

## 5. Слепые зоны
- <blind_spot>

## 6. Сводка по осям
ясность <avg> · полнота <avg> · реалистичность <avg> · соответствие интересам <avg> · доверие <avg> · слабейшая ось: <name>
```

## `synthesis.html`

Standalone page rendering the six synthesis sections + the infographics block. This is the
primary visual handoff.

## Infographics block (required charts)

Drawn from the reviewer JSON array / synthesis sidecar, inline JS over `<canvas>` or CSS/SVG:

1. **Severity heatmap** — rows = personas, columns = critical/major/minor, cell = count, shaded.
2. **Consensus pain points** — horizontal bar chart of issues by how many personas raised them.
3. **Verdict fan** — a small distribution bar/donut of accept / conditions / reject counts.
4. **Axis comparison** — grouped bars (or radar) of the five axis scores per persona, plus the
   panel average line.

Each chart must degrade gracefully: if there is only one persona, still render (single row/bar).

## Reusable inline chart helper (copy into each HTML)

```html
<script>
function bar(el, items){ // items: [{label, value, color}]
  const max = Math.max(1, ...items.map(i=>i.value));
  el.innerHTML = items.map(i=>`<div class="row"><span class="lbl">${i.label}</span>`
    +`<span class="track"><span class="fill" style="width:${100*i.value/max}%;background:${i.color||'#456'}"></span></span>`
    +`<span class="val">${i.value}</span></div>`).join('');
}
</script>
<style>
.row{display:flex;align-items:center;gap:8px;margin:4px 0;font:13px system-ui}
.lbl{width:160px;text-align:right}.track{flex:1;background:#eee;border-radius:4px;height:14px}
.fill{display:block;height:14px;border-radius:4px}.val{width:32px}
</style>
```
