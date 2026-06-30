# Synthesis Protocol

A single Opus agent merges all persona reviews into a pipeline-ready report. Input: the array of
reviewer JSON objects + the persona profiles. Output: `synthesis.md` (+ html via templates).

Skip null/failed (non-responding) personas: `verdict_counts` and `axis_averages` are computed over responding personas only, and the report states the number of non-responders.

## Goal

The synthesis is consumed by OTHER pipelines that improve the document. So it must be precise,
prioritized, and machine-skimmable. No diplomacy, no filler.

## Required sections (in order)

1. **Вердикт панели** — count of accept / accept_with_conditions / reject; one-line overall read.
2. **Консенсусные проблемы** — issues raised by ≥2 personas, merged and deduplicated, each with:
   merged severity (take the highest), how many personas raised it, affected location.
3. **Противоречия** — where personas disagree (one accepts what another rejects); name both sides.
4. **Приоритизированный план улучшений** — ordered list: critical-consensus first, then
   major-consensus, then high-value single-persona issues. Each item: what to change + which
   personas it satisfies. THIS is the primary handoff to downstream pipelines.
5. **Слепые зоны** — union of `blind_spots`, deduplicated.
6. **Сводка по осям** — average of each `axis_score` across personas + the lowest-scoring axis.

## Output JSON sidecar

Also emit a machine-readable sidecar `synthesis.json` (next to synthesis.md) with:

```json
{
  "verdict_counts": { "accept": 0, "accept_with_conditions": 0, "reject": 0 },
  "consensus_issues": [ { "severity": "critical", "raised_by": 2, "location": "...", "problem": "..." } ],
  "improvement_plan": [ { "priority": 1, "change": "...", "satisfies_personas": ["01","03"] } ],
  "axis_averages": { "clarity": 0, "completeness": 0, "realism": 0, "fit_to_my_interests": 0, "trust": 0 }
}
```

## Ordering (fully deterministic)

Use a fixed severity rank: `critical = 0`, `major = 1`, `minor = 2` (lower sorts first).

- **consensus_issues**: sort by the tuple `(severity_rank ASC, raised_by DESC, location ASC)`, where `location` is compared as a case-sensitive lexicographic (Unicode code-point) string. Fully ordered — no ties left unresolved.
- **improvement_plan**: tier order is critical-consensus, then major-consensus, then high-value single-persona issues. WITHIN a tier, sort by `(severity_rank ASC, raised_by DESC, location ASC)` using the same comparison as above. Assign `priority` as the 1-based position after this total ordering.

Same inputs → byte-identical ordering.
