---
name: persona-review
description: Use when reviewing a document (any type — spec, infosec policy, contract, regulation, marketing) from the perspective of hostile external personas. Requires a file or folder path. Produces per-persona feedback and a synthesized, pipeline-ready report under .persona-review/ next to the input.
---

# Persona Review

Run a document through a panel of **external, non-allied, deliberately hostile personas** and
produce structured feedback plus a synthesized report. Personas never treat the user as part of
their team. Reproducibility is engineered (see `references/determinism.md`). Professional
language, no formalities. Output language = document language.

## Inputs

A path to a **file or folder** is REQUIRED. If none is given, stop and ask for it. Do not guess.

## References (read as needed)

- `references/document-analysis.md` — phase 2 analysis.
- `references/persona-archetypes.md` — vocabularies, pools, suggested panels.
- `references/determinism.md` — canonicalization, seed, cache, schemas.
- `references/reviewer-protocol.md` — rubric JSON + hostility levels.
- `references/synthesis-protocol.md` — how to merge reviews.
- `references/report-templates.md` — md/html/infographics shapes.

## Pipeline

### Phase 1 — Validate input
Confirm a file/folder path was provided. Else ask for it and stop.

### Phase 2 — Analyze
Follow `document-analysis.md`. Compute `document_type`, `language`, audience, `key_claims`,
`content_hash`. Compute `base = <dir(input)>/.persona-review/<slug(input)>/`. Create it and
`runs/<YYYY-MM-DD_HHMM>/thinking/`. Write `00_input-analysis.md`.

### Phase 3 — Summary + cache check
Show the one-screen summary. Check `base/personas/persona-set.json` per `determinism.md` §3:
- none → phase 4;
- match → offer reuse / add N / rebuild;
- params differ → new panel (suffix file);
- hash differs → warn document changed, offer regenerate / reuse.
If reusing, skip to phase 6.

### Phase 4 — Structured questions (one at a time)
Use `persona-archetypes.md` suggested panel for `document_type` as defaults. Ask, in order:
1. **Audience & purpose (free text, ASK FIRST)** — "Кто читает этот документ и зачем? (своими
   словами)". This is the single highest-leverage input: the same document reviewed by external
   buyers vs by internal budget-owners produces completely different, far more useful personas.
   Use the answer to shape the proposed sectors/roles below and the reviewer framing. Store it as
   `audience_purpose` in `canonical_params` (free text; see `determinism.md` §1.5).
2. Sectors / company types (multi-select from suggested + "other", informed by the audience answer).
3. Age / social groups (from vocabulary).
4. Roles (from suggested + "other", informed by the audience answer).
5. Persona count (integer).
6. Hostility level (1–5, default 3) — TONE, not identity.
Canonicalize answers (`determinism.md` §1). Note: `persona_count` is stored in `persona-set.json`
but is NOT part of `canonical_params` or the seed. Compute the seed (§4).

### Phase 5 — Generate personas (deterministic)
Using the seed and pools in `persona-archetypes.md`, build `persona_count` personas: pick
archetype row, name, company (by sector), core_pain — all via the seed slot rule. Frame every
persona to fit the `audience_purpose` from phase 4 (e.g. "internal budget-owners defending spend"
makes the personas skeptical funders, not generic buyers) — while keeping them external non-allies. Write
`persona-set.json` (with `persona_count` as a top-level field, NOT inside `canonical_params`) and
`NN_<name>.md` profiles. Show a summary table: id, name, role, company, core interest/pain.
Record the active set filename in `runs/<ts>/thinking/active-persona-set.txt`.
For "generate N more": append personas at slot indices `persona_count..persona_count+N-1` using
the same seed, then update the top-level `persona_count` in `persona-set.json`.

### Phase 6 — Review (parallel agents, Opus)
Dispatch ONE agent per persona, in a single message with multiple Agent (Task) calls so they run
concurrently (do NOT use Workflow — no opt-in). Each agent gets: the document (the extracted-text
file from phase 2 for large/HTML inputs), its persona profile, the `audience_purpose` from phase 4,
the selected hostility level, and `reviewer-protocol.md`. Each MUST return the reviewer JSON. Write
each raw JSON to `runs/<ts>/thinking/review-<id>.json`. A failed/empty agent → record it and
continue; the persona is marked "no response" downstream.

**Model: always Opus for reviewers and synthesis.** Quality is the priority — do NOT downgrade to a
faster/cheaper model to save time, even for large panels. A bigger panel just takes longer.

**Progress reporting (avoid the "is it stuck?" feeling).** Spawning N agents prints N technical
"agent launched" console lines and is then quiet for minutes. To keep the user oriented:
1. BEFORE spawning, tell the user plainly: "Сейчас запущу N ревьюеров — будет N технических строк
   о запуске агентов, это нормально. Прогресс буду отмечать здесь по мере готовности."
2. Create a watch-file `runs/<ts>/progress.md` with a checklist of all N personas (☐ per persona)
   and tell the user they can open it to track progress live.
3. As each completion notification arrives, tick that persona in `progress.md` AND post a short
   running tally to the user: "✓ k/N готово (последняя: <id> <имя> — <verdict>)". Do not stay
   silent between completions.

### Phase 7 — Collect feedback
Assemble all reviewer JSON into `reports/persona-feedback.md` and `.html` per
`report-templates.md` (cards + infographics). Color-code verdicts.

### Phase 8 — Synthesize (Opus)
Dispatch one synthesis agent with all reviewer JSON + profiles + `synthesis-protocol.md`. It
returns the six sections and the `synthesis.json` sidecar. Write `reports/synthesis.md`,
`reports/synthesis.html` (with infographics), and `reports/synthesis.json`. Report final paths
to the user.

## Reproducibility reminders
Same path + same canonical params → same personas (cache + seed). Hostility level changes tone
only, never the persona set or the cache key. Keep all intermediate JSON on disk.
