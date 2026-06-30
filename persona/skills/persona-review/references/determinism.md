# Determinism & Reproducibility

The pipeline must produce maximally similar results across runs with the same parameters.
We do NOT rely on model temperature (no lever in Claude Code). We rely on the mechanisms below.

## 1. Canonicalization of parameters

Before anything is keyed or seeded, canonicalize the user's phase-4 answers:

1. Trim whitespace; collapse internal runs of whitespace to single spaces.
2. For matching only, lowercase.
3. Map each free-text or picked value to the **fixed vocabulary** in `persona-archetypes.md`
   (sector ids, social-group ids, role ids). Unmapped "other" values are kept verbatim but
   slugified (kebab-case) and appended after the mapped ones.
4. Sort every list ascending by id, de-duplicate.
5. `audience_purpose` (the phase-4 free-text answer: who reads the document and why) is kept
   verbatim for framing, and canonicalized for keying only by trim + whitespace-collapse +
   lowercase. It is FREE TEXT by nature, so the cache hits only on the same wording — substantive
   rewording is a deliberate reframe and correctly produces a new panel.
6. Result is `canonical_params`: `{ sectors:[], social_groups:[], roles:[], audience_purpose:"" }`.

`persona_count` is recorded separately in `persona-set.json`, NOT inside `canonical_params` — so it is excluded from the cache key and the seed. This lets "generate N more" append personas at higher slot indices using the SAME seed, without disturbing existing personas.

Hostility level is NOT part of `canonical_params` (it is review tone, see `reviewer-protocol.md`).

## 2. Cache key & `persona-set.json`

Cache key = `document_path` + `canonical_params`. Stored at
`<base>/personas/persona-set.json`:

```json
{
  "schema_version": 1,
  "document_path": "relative/or/abs/path/to/input",
  "document_content_hash": "sha256-hex",
  "persona_count": 4,
  "canonical_params": {
    "sectors": ["banking", "fintech"],
    "social_groups": ["mid-career-professional"],
    "roles": ["ciso", "compliance-lawyer"],
    "audience_purpose": "внутренний документ для защиты бюджета перед владельцами"
  },
  "seed": "hex-digest",
  "personas": [
    {
      "id": "01", "name": "...", "role": "...", "company": "...",
      "sector": "...", "social_group": "...",
      "core_interest": "...", "core_pain": "...", "archetype_id": "..."
    }
  ]
}
```

## 3. Cache hit / miss logic

- **No `persona-set.json`** → generate (phase 5).
- **Exists, `document_content_hash` matches current input AND `canonical_params` matches** →
  offer: reuse / generate N more (appends personas at slot indices persona_count..persona_count+N-1 using the same seed, then updates the top-level persona_count) / rebuild from scratch.
- **Exists, `canonical_params` differ** → this is a different panel; generate a new set.
  (Multiple panels per document are allowed; do not overwrite — see naming note below.)
- **Exists, hash differs (document changed)** → warn: "document content changed; personas were
  chosen for the previous version." Offer: regenerate / reuse as-is.

Naming note: if a second distinct `canonical_params` panel is created for the same document,
suffix the personas file: `persona-set.json`, `persona-set-2.json`, … The active run records
which file it used in its `runs/<ts>/thinking/active-persona-set.txt`.

## 4. Seed

`seed = sha256( document_path + "\n" + json.dumps(canonical_params, sort_keys=True) )` (hex, independent of persona_count, which is not in canonical_params).

The seed deterministically drives every random-ish choice during persona generation: which
archetype row, which name, which company, which "core pain". Selection rule for a pool of
length L at slot `i` (a distinct integer per decision — e.g. persona 0 archetype, persona 0 name, persona 0 company, persona 0 core_pain, persona 1 archetype, …): compute `slot_digest = sha256( seed + ":" + str(i) )` (hex) and `index = int( slot_digest[:8], 16 ) % L`. Re-hashing per slot gives unlimited deterministic slots; the same seed + same slot `i` + same pool always yields the same pick. See `persona-archetypes.md` for pools.

## 5. Content hash

`document_content_hash = sha256` of the input bytes. For a folder input: sha256 over the
concatenation of each included file's relative path + its bytes, files sorted by path.

## 6. Output schema discipline

Reviewer agents and the synthesis agent MUST return the exact JSON schemas defined in
`reviewer-protocol.md` and `synthesis-protocol.md`. Schema adherence — not temperature — is
what keeps structure and conclusions stable across runs.
