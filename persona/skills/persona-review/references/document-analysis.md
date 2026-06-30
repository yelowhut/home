# Input Analysis

## Scope

- File input → read the file.
- Folder input → read all text-like files (md, txt, docx-as-text, rst, html, pdf-as-text,
  source/config when relevant). Skip binaries. Treat the folder as one logical document.

## Large or structured inputs (HTML, big files) — extract substance first

For HTML, web pages, slide-like documents, or any large/markup-heavy file, do NOT analyze the raw
markup. The CSS, scripts, and embedded UI mockups are noise that drowns the actual content and
blows up context. Extract the human-readable text first, then analyze that:

1. Strip `<style>…</style>` and `<script>…</script>` blocks entirely.
2. Replace embedded iframe `srcdoc="…"` attributes (inline mockups/demos) with a short
   placeholder like `[embedded-ui-mockup]` — their inner HTML is not the document's argument.
3. Strip remaining tags; unescape HTML entities (`&quot;`, `&laquo;`, `&mdash;`, `&ge;`, …).
4. Collapse whitespace; keep non-empty lines.
5. Save the extracted text to `runs/<ts>/thinking/<basename>-extracted.txt` and analyze (and later
   feed reviewers) from THAT file, not the raw markup.

If the input is plain prose (md/txt) and not large, skip extraction and read it directly.

## What to determine

1. **document_type** — classify into one of: `infosec-policy`, `technical-spec`, `contract`,
   `regulation`, `marketing-copy`, or `unknown`. Pick the closest; this drives the suggested
   panel in `persona-archetypes.md`.
2. **language** — detect the dominant natural language of the content. ALL reports and persona
   profiles are written in this language. Russian input → Russian output.
3. **stated_audience** — who the document claims to be for.
4. **key_claims** — 5–12 bullet points: the document's core promises, requirements, or
   obligations. These are what personas will attack or accept.
5. **structure_notes** — sections, length, anything notably missing (e.g. "no rollback plan",
   "no acceptance criteria").
6. **content_hash** — per `determinism.md` §5.

## `00_input-analysis.md` template

```markdown
# Анализ входа: <basename>

- Тип документа: <document_type>
- Язык: <language>
- Заявленная аудитория: <stated_audience>
- Объём: <pages/words/files>
- content_hash: <sha256>

## Ключевые тезисы
1. ...

## Структурные наблюдения
- ...
```

## Summary to user (phase 3)

Keep it to one screen: document_type, language, 3–5 most important key_claims, and the most
obvious gap. Then move to cache check.
