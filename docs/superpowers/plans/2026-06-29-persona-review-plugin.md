# Persona Review Plugin Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a portable Claude Code plugin `persona` whose command `/persona:review` runs documents (any type) through a panel of hostile, external personas and produces structured per-persona feedback plus a synthesized report.

**Architecture:** A plugin directory `persona/` with one slash command (`commands/review.md`, thin entry point) and one skill (`skills/persona-review/`) that holds the full pipeline logic in `SKILL.md` plus six reference files. The pipeline is executed by the main session: it analyzes the input, asks structured questions, deterministically generates personas (cached by path next to the document), dispatches one parallel reviewer agent per persona, then synthesizes. All artifacts are plain files under `<dir-of-input>/.persona-review/<slug>/`.

**Tech Stack:** Markdown + YAML frontmatter (Claude Code plugin/skill/command format), JSON (plugin manifest, persona-set cache, reviewer output schema), self-contained HTML (inline CSS/JS, no external resources) for infographics. Reviewer + synthesis agents run on Opus. Parallel reviewer dispatch uses the Agent (Task) tool, not Workflow (no opt-in gate).

## Global Constraints

- **Plugin name:** `persona`; command surface: `/persona:review`. (verbatim from spec §1, §3)
- **Personas are external non-allies** on every hostility level; they never treat the user as part of their team. (spec §2, §6)
- **Reproducibility levers (do not rely on temperature — no lever in Claude Code):** persona cache keyed by `path + canonicalized structured params` (hostility level excluded from key); deterministic seed = hash(path + canonicalized params) drives archetype/name/company selection; strict JSON output schemas for reviewers and synthesis; intermediate thinking written to disk. (spec §2, §5, §9)
- **Hostility level is review TONE applied over fixed personas**, not part of persona identity, not in the cache key, not in the seed. (spec §5, §6, decision)
- **Structured input, not free text:** phase-4 questions PROPOSE options from doc analysis (pick-from-list + "other"); answers are canonicalized before keying. (spec §5 phase 4)
- **Output language = document language** (auto-detected). (spec §2, §5 phase 2)
- **No external services, no web search, no editing the source document.** Local files only. (spec §10)
- **Artifact layout** (verbatim from spec §4):
  ```
  <dir(P)>/.persona-review/<slug(P)>/
    00_input-analysis.md
    personas/persona-set.json
    personas/01_<name>.md ... NN_<name>.md
    runs/<YYYY-MM-DD_HHMM>/thinking/
    reports/persona-feedback.md
    reports/persona-feedback.html
    reports/synthesis.md
    reports/synthesis.html
  ```
- **Plugin root in this repo:** `D:\git\home\persona\` (the portable unit; copyable into any repo).
- **Commit style:** end commit messages with `Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>`.

## Shared identifiers (used across tasks)

These names are fixed here so every task agrees. SKILL.md (Task 8) references all of them.

- **`persona-set.json`** fields: `{ "schema_version": 1, "document_path": str, "document_content_hash": str, "canonical_params": { "sectors": [str], "social_groups": [str], "roles": [str], "persona_count": int }, "seed": str, "personas": [ { "id": "01", "name": str, "role": str, "company": str, "sector": str, "social_group": str, "core_interest": str, "core_pain": str, "archetype_id": str } ] }`
- **Reviewer output JSON schema** (one object per persona; field names fixed): `{ "persona_id": str, "verdict": "accept"|"accept_with_conditions"|"reject", "stance_line": str, "strengths": [str], "issues": [ { "severity": "critical"|"major"|"minor", "location": str, "problem": str } ], "conditions_to_stop_resisting": [str], "blind_spots": [str], "axis_scores": { "clarity": int, "completeness": int, "realism": int, "fit_to_my_interests": int, "trust": int } }` — all `axis_scores` are integers 0–10.
- **Canonicalization** (defined in `determinism.md`): trim, lowercase for matching, sort lists, map free text to a fixed vocabulary in `persona-archetypes.md`.
- **Slug rule:** `slug(P)` = kebab-case of the input file/folder basename without extension.
- **Hostility levels 1–5** named & specified in `reviewer-protocol.md`; default = 3.

---

### Task 1: Plugin scaffold + manifest

**Files:**
- Create: `D:\git\home\persona\.claude-plugin\plugin.json`
- Create (empty dir markers via files in later tasks): `D:\git\home\persona\commands\`, `D:\git\home\persona\skills\persona-review\references\`

**Interfaces:**
- Consumes: nothing.
- Produces: plugin name `persona`, command namespace, the directory tree all later tasks write into.

- [ ] **Step 1: Create the manifest**

Create `D:\git\home\persona\.claude-plugin\plugin.json`:

```json
{
  "name": "persona",
  "version": "0.1.0",
  "description": "Review any document from the perspective of hostile, external personas. /persona:review produces per-persona feedback plus a synthesized, pipeline-ready report.",
  "author": { "name": "Primo RPA" }
}
```

- [ ] **Step 2: Verify manifest is valid JSON with required keys**

Run:
```bash
python -c "import json; d=json.load(open(r'D:\git\home\persona\.claude-plugin\plugin.json', encoding='utf-8')); assert d['name']=='persona'; assert 'description' in d; print('OK', d['name'], d['version'])"
```
Expected: `OK persona 0.1.0`

- [ ] **Step 3: Create the directory tree**

Run:
```bash
mkdir -p "D:/git/home/persona/commands" "D:/git/home/persona/skills/persona-review/references" && ls -R "D:/git/home/persona"
```
Expected: shows `.claude-plugin`, `commands`, `skills/persona-review/references`.

- [ ] **Step 4: Commit**

```bash
git add persona/.claude-plugin/plugin.json
git commit -m "feat(persona): plugin manifest and scaffold

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 2: determinism.md — canonicalization, seed, cache schema

**Files:**
- Create: `D:\git\home\persona\skills\persona-review\references\determinism.md`

**Interfaces:**
- Consumes: shared identifiers (`persona-set.json` shape) from this plan's header.
- Produces: the canonicalization procedure, seed algorithm, and the exact `persona-set.json` schema that Task 3 (archetype selection), Task 8 (SKILL pipeline phases 3/5) rely on.

- [ ] **Step 1: Write the file**

Create `D:\git\home\persona\skills\persona-review\references\determinism.md` with this content:

````markdown
# Determinism & Reproducibility

The pipeline must produce maximally similar results across runs with the same parameters.
We do NOT rely on model temperature (no lever in Claude Code). We rely on the four mechanisms below.

## 1. Canonicalization of parameters

Before anything is keyed or seeded, canonicalize the user's phase-4 answers:

1. Trim whitespace; collapse internal runs of whitespace to single spaces.
2. For matching only, lowercase.
3. Map each free-text or picked value to the **fixed vocabulary** in `persona-archetypes.md`
   (sector ids, social-group ids, role ids). Unmapped "other" values are kept verbatim but
   slugified (kebab-case) and appended after the mapped ones.
4. Sort every list ascending by id, de-duplicate.
5. Result is `canonical_params`: `{ sectors:[], social_groups:[], roles:[], persona_count:int }`.

Hostility level is NOT part of `canonical_params` (it is review tone, see `reviewer-protocol.md`).

## 2. Cache key & `persona-set.json`

Cache key = `document_path` + `canonical_params`. Stored at
`<base>/personas/persona-set.json`:

```json
{
  "schema_version": 1,
  "document_path": "relative/or/abs/path/to/input",
  "document_content_hash": "sha256-hex",
  "canonical_params": {
    "sectors": ["banking", "fintech"],
    "social_groups": ["mid-career-professional"],
    "roles": ["ciso", "compliance-lawyer"],
    "persona_count": 4
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
  offer: reuse / generate N more / rebuild from scratch.
- **Exists, `canonical_params` differ** → this is a different panel; generate a new set.
  (Multiple panels per document are allowed; do not overwrite — see naming note below.)
- **Exists, hash differs (document changed)** → warn: "document content changed; personas were
  chosen for the previous version." Offer: regenerate / reuse as-is.

Naming note: if a second distinct `canonical_params` panel is created for the same document,
suffix the personas file: `persona-set.json`, `persona-set-2.json`, … The active run records
which file it used in its `runs/<ts>/thinking/active-persona-set.txt`.

## 4. Seed

`seed = sha256( document_path + "\n" + json.dumps(canonical_params, sort_keys=True) )` (hex).

The seed deterministically drives every random-ish choice during persona generation: which
archetype row, which name, which company, which "core pain". Selection rule for a pool of
length L at slot i: `index = int(seed[ (i*8) : (i*8)+8 ], 16) % L`. Always slice the seed by
slot index so the same seed + same pools = same picks. See `persona-archetypes.md` for pools.

## 5. Content hash

`document_content_hash = sha256` of the input bytes. For a folder input: sha256 over the
concatenation of each included file's relative path + its bytes, files sorted by path.

## 6. Output schema discipline

Reviewer agents and the synthesis agent MUST return the exact JSON schemas defined in
`reviewer-protocol.md` and `synthesis-protocol.md`. Schema adherence — not temperature — is
what keeps structure and conclusions stable across runs.
````

- [ ] **Step 2: Verify required sections are present**

Run:
```bash
grep -E "^## (1|2|3|4|5|6)\." "D:/git/home/persona/skills/persona-review/references/determinism.md" | wc -l
```
Expected: `6`

- [ ] **Step 3: Verify the embedded persona-set JSON example parses**

Run:
```bash
python - <<'PY'
import re, json
t = open(r'D:\git\home\persona\skills\persona-review\references\determinism.md', encoding='utf-8').read()
block = t.split('```json',1)[1].split('```',1)[0]
d = json.loads(block)
assert d['schema_version'] == 1 and 'canonical_params' in d and 'personas' in d
print('OK persona-set schema parses')
PY
```
Expected: `OK persona-set schema parses`

- [ ] **Step 4: Commit**

```bash
git add persona/skills/persona-review/references/determinism.md
git commit -m "feat(persona): determinism reference (canonicalization, seed, cache schema)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 3: persona-archetypes.md — vocabularies, pools, doc-type → suggestions

**Files:**
- Create: `D:\git\home\persona\skills\persona-review\references\persona-archetypes.md`

**Interfaces:**
- Consumes: seed selection rule and canonicalization from `determinism.md` (Task 2).
- Produces: the fixed vocabularies (sector ids, social-group ids, role ids), name/company pools,
  and the per-document-type suggested sectors/roles that SKILL phase 4 (Task 8) proposes.

- [ ] **Step 1: Write the file**

Create `D:\git\home\persona\skills\persona-review\references\persona-archetypes.md`:

````markdown
# Persona Archetypes & Vocabularies

Fixed vocabularies and pools for deterministic persona generation. Extend by appending rows;
never renumber existing ids (would change seed-based picks).

## Fixed vocabulary — sectors (id : label)

- banking : Банки
- fintech : Финтех
- insurance : Страхование
- manufacturing : Промышленность / производство
- retail : Ритейл / электронная коммерция
- healthcare : Здравоохранение
- public-sector : Госсектор
- telecom : Телеком
- it-services : ИТ-услуги / интеграторы
- energy : Энергетика
- other : (free text, slugified)

## Fixed vocabulary — social groups (id : label)

- early-career : Начинающий специалист (22–28)
- mid-career-professional : Профессионал (29–40)
- senior-leader : Руководитель высшего звена (41–55)
- veteran-expert : Ветеран отрасли (55+)
- skeptical-procurement : Закупщик / контролёр бюджета
- other : (free text, slugified)

## Fixed vocabulary — roles (id : label)

Generic across document types; the suggestion tables below pick subsets.

- ciso : CISO / директор по ИБ
- security-engineer : Инженер по безопасности
- compliance-lawyer : Юрист по комплаенсу
- internal-auditor : Внутренний аудитор
- it-director : ИТ-директор
- procurement-lead : Руководитель закупок
- product-owner : Владелец продукта
- end-user-employee : Рядовой сотрудник-пользователь
- ops-manager : Операционный менеджер
- finance-controller : Финансовый контролёр
- external-consultant : Внешний консультант
- regulator-inspector : Инспектор регулятора
- other : (free text, slugified)

## Suggested panels by document type

SKILL phase 4 proposes (not forces) these. User edits.

| document_type        | suggested sectors                   | suggested roles                                                  |
|----------------------|-------------------------------------|------------------------------------------------------------------|
| infosec-policy       | banking, it-services, public-sector | ciso, compliance-lawyer, internal-auditor, it-director, end-user-employee |
| technical-spec (ТЗ)  | it-services, fintech, manufacturing | it-director, product-owner, security-engineer, procurement-lead, ops-manager |
| contract             | banking, retail, manufacturing      | compliance-lawyer, procurement-lead, finance-controller, ops-manager |
| regulation/regламент | public-sector, manufacturing        | internal-auditor, ops-manager, end-user-employee, compliance-lawyer |
| marketing-copy       | retail, fintech, telecom            | product-owner, end-user-employee, external-consultant, finance-controller |
| (unknown)            | it-services, banking, retail        | it-director, compliance-lawyer, end-user-employee, external-consultant |

## Name pool (deterministic pick by seed slot)

Gender-mixed, locale-neutral-RU. Index via the seed rule in `determinism.md`.

`["Андрей Соколов","Мария Левина","Дмитрий Карпов","Елена Орлова","Сергей Гущин","Ольга Реброва","Игорь Тарасов","Наталья Миронова","Павел Жуков","Анна Кудрина","Роман Беляев","Татьяна Зайцева","Виктор Панин","Юлия Савельева","Алексей Громов","Ирина Лобанова"]`

## Company pool (deterministic pick by seed slot, per sector)

Each sector maps to a pool of plausible fictional company names. Index via seed rule.

- banking: `["Северный Кредит","Аркада Банк","Меридиан Финанс"]`
- fintech: `["ПлатёжниК","Финтейл","Скай Капитал"]`
- insurance: `["Гарант Полис","Защита Плюс","Ренессанс Гарант"]`
- manufacturing: `["МеталлПром","Завод Восход","ТехноЛит"]`
- retail: `["МаркетОдин","Полка","ОптимаТорг"]`
- healthcare: `["МедЛайн","Клиника Вита","ФармаКор"]`
- public-sector: `["Госуслуги Региона","МФЦ Центральный","Ведомство-7"]`
- telecom: `["СвязьОдин","ТелеНорд","МобиКор"]`
- it-services: `["ИнтеграСис","КодБюро","Девком"]`
- energy: `["ЭнергоСеть","ГазТранс","Светополе"]`
- other: `["Компания А","Компания Б","Компания В"]`

## Core-pain pool by role (deterministic pick by seed slot)

One-line "what this role is afraid this document will cost them". Example subset; extend:

- ciso: `["новые векторы атак, за которые отвечать мне","требования без бюджета на их выполнение","ответственность за чужие решения"]`
- compliance-lawyer: `["юридически дырявые формулировки","несоответствие регуляторике","риск штрафов на мне"]`
- procurement-lead: `["скрытые затраты","привязка к одному вендору","сроки, которые сорвут план закупок"]`
- it-director: `["неисполнимые SLA","нагрузка на мою команду","интеграционный ад"]`
- end-user-employee: `["лишняя бюрократия в моей работе","непонятные требования","больше кликов, меньше смысла"]`
- internal-auditor: `["непроверяемые контроли","отсутствие следов аудита","размытая ответственность"]`
- product-owner: `["раздутый скоуп","нечёткие критерии приёмки","риски для срока релиза"]`
- finance-controller: `["непрозрачная стоимость владения","скрытые операционные расходы","ROI на бумаге"]`
- ops-manager: `["рост ручного труда","хрупкие процессы","нет плана отката"]`
- external-consultant: `["неоригинально","не учли рынок","слабая дифференциация"]`
- regulator-inspector: `["несоответствие нормам","недостаточные доказательства","формальная отписка"]`
- security-engineer: `["технически нереализуемо","дыры в архитектуре","нет threat model"]`
````

- [ ] **Step 2: Verify all three vocabularies and the suggestion table exist**

Run:
```bash
grep -cE "^- (banking|ciso|early-career) :" "D:/git/home/persona/skills/persona-review/references/persona-archetypes.md"
```
Expected: `3`

- [ ] **Step 3: Verify name and company pools are valid JSON arrays**

Run:
```bash
python - <<'PY'
import re, json
t=open(r'D:\git\home\persona\skills\persona-review\references\persona-archetypes.md',encoding='utf-8').read()
arrs=re.findall(r'`(\[.*?\])`', t, re.S)
n=0
for a in arrs:
    json.loads(a); n+=1
assert n>=2, n
print('OK arrays parse:', n)
PY
```
Expected: `OK arrays parse:` followed by a number ≥ 13.

- [ ] **Step 4: Commit**

```bash
git add persona/skills/persona-review/references/persona-archetypes.md
git commit -m "feat(persona): archetype vocabularies, pools, doc-type panels

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 4: document-analysis.md — input analysis guidance

**Files:**
- Create: `D:\git\home\persona\skills\persona-review\references\document-analysis.md`

**Interfaces:**
- Consumes: content-hash rule from `determinism.md`.
- Produces: the analysis procedure SKILL phase 2 (Task 8) follows: document_type detection,
  language detection, audience, key claims, and the `00_input-analysis.md` template.

- [ ] **Step 1: Write the file**

Create `D:\git\home\persona\skills\persona-review\references\document-analysis.md`:

````markdown
# Input Analysis

## Scope

- File input → read the file.
- Folder input → read all text-like files (md, txt, docx-as-text, rst, html, pdf-as-text,
  source/config when relevant). Skip binaries. Treat the folder as one logical document.

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
````

- [ ] **Step 2: Verify the six determinations and the template are present**

Run:
```bash
grep -cE "document_type|language|stated_audience|key_claims|structure_notes|content_hash" "D:/git/home/persona/skills/persona-review/references/document-analysis.md"
```
Expected: a number ≥ 6.

- [ ] **Step 3: Commit**

```bash
git add persona/skills/persona-review/references/document-analysis.md
git commit -m "feat(persona): input-analysis reference

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 5: reviewer-protocol.md — rubric schema + 5 hostility levels

**Files:**
- Create: `D:\git\home\persona\skills\persona-review\references\reviewer-protocol.md`

**Interfaces:**
- Consumes: reviewer output JSON schema (this plan's header), persona profile fields.
- Produces: the exact reviewer agent prompt contract, the 5 hostility-level behavior specs, and
  the JSON schema Task 7 (templates) and Task 8 (dispatch) and Task 6 (synthesis) rely on.

- [ ] **Step 1: Write the file**

Create `D:\git\home\persona\skills\persona-review\references\reviewer-protocol.md`:

````markdown
# Reviewer Protocol

Each persona is reviewed by one agent (Opus). The agent wears the persona and returns the
fixed JSON schema below. Hostility level is applied as TONE; the persona identity is unchanged.

## Invariant (all levels)

You are an EXTERNAL person. You are NOT on the author's team. You have your own employer, your
own KPIs, your own risks. This document is a potential cost or threat to you until proven
otherwise. Never speak as a collaborator. Never soften to be nice.

## Hostility levels (apply the one selected; default = 3)

**Level 1 — Нейтральный внешний эксперт.** Judge on merits. Acknowledge strong and weak points
in roughly equal measure. Frame improvements as professional advice. Praise is allowed when
earned.

**Level 2 — Сдержанный скептик.** Presumption of doubt; demand evidence for claims. Praise only
what is genuinely strong. Improvements = "what you'd need to show me to believe this."

**Level 3 — Жёсткий оппонент (default).** Against by default. Praise is sparse and only for the
objectively strong. "What to improve" = the conditions under which you'd stop resisting. Hunt
for blind spots the author cannot see.

**Level 4 — Враждебный критик.** Actively look for things to attack. Blunt phrasing allowed.
Improvements = the minimum, only the critical ones. Emphasize risks to YOUR function personally.

**Level 5 — Максимально враждебный разнос.** Look only for what is wrong. Reject by default.
Improvements are optional and framed as "this won't even save it." Praise nearly absent.

## Output — return EXACTLY this JSON, nothing else

```json
{
  "persona_id": "01",
  "verdict": "accept | accept_with_conditions | reject",
  "stance_line": "one sentence stating your position",
  "strengths": ["..."],
  "issues": [
    { "severity": "critical | major | minor", "location": "section/quote in the doc", "problem": "..." }
  ],
  "conditions_to_stop_resisting": ["..."],
  "blind_spots": ["risks/gaps the author does not see"],
  "axis_scores": {
    "clarity": 0,
    "completeness": 0,
    "realism": 0,
    "fit_to_my_interests": 0,
    "trust": 0
  }
}
```

Rules:
- `axis_scores` are integers 0–10.
- Every `issues[].severity` is exactly one of critical/major/minor.
- Write all free-text fields in the document's language.
- Stay in character; let the hostility level set how harsh `strengths` and `stance_line` are.
- `location` must point at a real place in the document (section name or short quote).
````

- [ ] **Step 2: Verify all 5 levels and the schema are present**

Run:
```bash
grep -cE "^\*\*Level [1-5]" "D:/git/home/persona/skills/persona-review/references/reviewer-protocol.md"
```
Expected: `5`

- [ ] **Step 3: Verify the reviewer JSON schema parses and has the agreed fields**

Run:
```bash
python - <<'PY'
import json
t=open(r'D:\git\home\persona\skills\persona-review\references\reviewer-protocol.md',encoding='utf-8').read()
block=t.split('```json',1)[1].split('```',1)[0]
d=json.loads(block)
for k in ["persona_id","verdict","stance_line","strengths","issues","conditions_to_stop_resisting","blind_spots","axis_scores"]:
    assert k in d, k
for a in ["clarity","completeness","realism","fit_to_my_interests","trust"]:
    assert a in d["axis_scores"], a
print('OK reviewer schema fields present')
PY
```
Expected: `OK reviewer schema fields present`

- [ ] **Step 4: Commit**

```bash
git add persona/skills/persona-review/references/reviewer-protocol.md
git commit -m "feat(persona): reviewer protocol (rubric schema + 5 hostility levels)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 6: synthesis-protocol.md — how to merge reviews

**Files:**
- Create: `D:\git\home\persona\skills\persona-review\references\synthesis-protocol.md`

**Interfaces:**
- Consumes: reviewer output JSON schema (Task 5).
- Produces: the synthesis agent contract + the synthesis output structure Task 7 templates render
  and Task 8 phase 8 invokes.

- [ ] **Step 1: Write the file**

Create `D:\git\home\persona\skills\persona-review\references\synthesis-protocol.md`:

````markdown
# Synthesis Protocol

A single Opus agent merges all persona reviews into a pipeline-ready report. Input: the array of
reviewer JSON objects + the persona profiles. Output: `synthesis.md` (+ html via templates).

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

Determinism: order consensus_issues by (severity rank, raised_by desc, location). Order
improvement_plan by the rule in section 4. Same inputs → same ordering.
````

- [ ] **Step 2: Verify the six sections and the sidecar JSON**

Run:
```bash
grep -cE "^[0-9]\. \*\*" "D:/git/home/persona/skills/persona-review/references/synthesis-protocol.md"
```
Expected: `6`

- [ ] **Step 3: Verify the sidecar JSON parses**

Run:
```bash
python - <<'PY'
import json
t=open(r'D:\git\home\persona\skills\persona-review\references\synthesis-protocol.md',encoding='utf-8').read()
block=t.split('```json',1)[1].split('```',1)[0]
d=json.loads(block)
assert "verdict_counts" in d and "improvement_plan" in d and "axis_averages" in d
print('OK synthesis sidecar parses')
PY
```
Expected: `OK synthesis sidecar parses`

- [ ] **Step 4: Commit**

```bash
git add persona/skills/persona-review/references/synthesis-protocol.md
git commit -m "feat(persona): synthesis protocol

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 7: report-templates.md — md + self-contained html + infographics

**Files:**
- Create: `D:\git\home\persona\skills\persona-review\references\report-templates.md`

**Interfaces:**
- Consumes: reviewer JSON schema (Task 5), synthesis structure (Task 6).
- Produces: the four output files' exact shapes that SKILL phases 7–8 (Task 8) write.

- [ ] **Step 1: Write the file**

Create `D:\git\home\persona\skills\persona-review\references\report-templates.md`:

````markdown
# Report Templates

All HTML is **self-contained**: inline CSS and inline vanilla JS only, no external fonts,
scripts, or images. Charts are drawn with inline `<canvas>` + a small inline script or with
pure CSS/SVG bars. No CDN.

## `persona-feedback.md`

```markdown
# Обратная связь персон: <document basename>

> Уровень враждебности: <N> — <level name>. Персон: <count>.

## <id>. <name> — <role>, <company>
**Вердикт:** <verdict> — <stance_line>

**Сильное:** <strengths as bullets>

**Проблемы:**
- [<severity>] <location> — <problem>

**Условия, чтобы перестать сопротивляться:** <bullets>

**Слепые зоны:** <bullets>

**Оценки (0–10):** ясность <>, полнота <>, реалистичность <>, соответствие интересам <>, доверие <>

---
(repeat per persona; if a persona failed, render: "Персона <id> не дала ответ.")
```

## `persona-feedback.html`

A standalone page with: a header, one card per persona (same data as md), and the infographics
block (below). Inline `<style>` for cards; verdict color-coded (reject=red, conditions=amber,
accept=green).

## `synthesis.md`

Renders the six sections from `synthesis-protocol.md` in order.

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
````

- [ ] **Step 2: Verify the four output shapes and the four charts are described**

Run:
```bash
grep -cE "persona-feedback\.md|persona-feedback\.html|synthesis\.md|synthesis\.html" "D:/git/home/persona/skills/persona-review/references/report-templates.md"
```
Expected: a number ≥ 4.

- [ ] **Step 3: Verify the inline chart helper is valid by smoke-rendering**

Run:
```bash
python - <<'PY'
t=open(r'D:\git\home\persona\skills\persona-review\references\report-templates.md',encoding='utf-8').read()
for marker in ["Severity heatmap","Consensus pain points","Verdict fan","Axis comparison","function bar("]:
    assert marker in t, marker
print('OK templates contain 4 charts + helper')
PY
```
Expected: `OK templates contain 4 charts + helper`

- [ ] **Step 4: Commit**

```bash
git add persona/skills/persona-review/references/report-templates.md
git commit -m "feat(persona): report templates (md + self-contained html + infographics)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 8: SKILL.md — the pipeline orchestrator

**Files:**
- Create: `D:\git\home\persona\skills\persona-review\SKILL.md`

**Interfaces:**
- Consumes: all six reference files (Tasks 2–7) and the shared identifiers.
- Produces: the executable pipeline (phases 1–8) invoked by the command (Task 9).

- [ ] **Step 1: Write the file**

Create `D:\git\home\persona\skills\persona-review\SKILL.md`:

````markdown
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
1. Sectors / company types (multi-select from suggested + "other").
2. Age / social groups (from vocabulary).
3. Roles (from suggested + "other").
4. Persona count (integer).
5. Hostility level (1–5, default 3) — TONE, not identity.
Canonicalize answers (`determinism.md` §1). Compute the seed (§4).

### Phase 5 — Generate personas (deterministic)
Using the seed and pools in `persona-archetypes.md`, build `persona_count` personas: pick
archetype row, name, company (by sector), core_pain — all via the seed slot rule. Write
`persona-set.json` and `NN_<name>.md` profiles. Show a summary table: id, name, role, company,
core interest/pain. Record the active set filename in `runs/<ts>/thinking/active-persona-set.txt`.

### Phase 6 — Review (parallel agents, Opus)
Dispatch ONE agent per persona, in a single message with multiple Agent (Task) calls so they run
concurrently (do NOT use Workflow — no opt-in). Each agent gets: the document, its persona
profile, the selected hostility level, and `reviewer-protocol.md`. Each MUST return the reviewer
JSON. Write each raw JSON to `runs/<ts>/thinking/review-<id>.json`. A failed/empty agent → record
it and continue; the persona is marked "no response" downstream.

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
````

- [ ] **Step 2: Verify frontmatter parses and all 8 phases + 6 references are present**

Run:
```bash
python - <<'PY'
import re
t=open(r'D:\git\home\persona\skills\persona-review\SKILL.md',encoding='utf-8').read()
assert t.startswith('---'), 'frontmatter missing'
fm=t.split('---',2)[1]
assert 'name: persona-review' in fm and 'description:' in fm
phases=len(re.findall(r'^### Phase [1-8]', t, re.M))
refs=len(re.findall(r'references/[a-z-]+\.md', t))
assert phases==8, f'phases={phases}'
assert refs>=6, f'refs={refs}'
print('OK SKILL.md: 8 phases, refs ok')
PY
```
Expected: `OK SKILL.md: 8 phases, refs ok`

- [ ] **Step 3: Verify every referenced file actually exists**

Run:
```bash
cd "D:/git/home/persona/skills/persona-review" && for f in document-analysis persona-archetypes determinism reviewer-protocol synthesis-protocol report-templates; do test -f "references/$f.md" && echo "ok $f" || echo "MISSING $f"; done
```
Expected: six `ok` lines, no `MISSING`.

- [ ] **Step 4: Commit**

```bash
git add persona/skills/persona-review/SKILL.md
git commit -m "feat(persona): pipeline orchestrator SKILL.md

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 9: commands/review.md — slash command entry point

**Files:**
- Create: `D:\git\home\persona\commands\review.md`

**Interfaces:**
- Consumes: the `persona-review` skill (Task 8).
- Produces: the `/persona:review` command surface.

- [ ] **Step 1: Write the file**

Create `D:\git\home\persona\commands\review.md`:

````markdown
---
description: Review a document (file or folder) from the perspective of hostile external personas; produces per-persona feedback + a synthesized report.
argument-hint: <path-to-file-or-folder>
---

A path argument is REQUIRED: `$ARGUMENTS`.

If `$ARGUMENTS` is empty, stop and ask the user for a file or folder path — do not guess or pick
a default.

Otherwise, invoke the `persona-review` skill and run its full pipeline against the given path,
following every phase in order. Treat the personas as external, non-allied reviewers throughout.
````

- [ ] **Step 2: Verify frontmatter + required-path guard**

Run:
```bash
python - <<'PY'
t=open(r'D:\git\home\persona\commands\review.md',encoding='utf-8').read()
assert t.startswith('---')
fm=t.split('---',2)[1]
assert 'description:' in fm and 'argument-hint:' in fm
assert '$ARGUMENTS' in t and 'persona-review' in t
print('OK command frontmatter + guard')
PY
```
Expected: `OK command frontmatter + guard`

- [ ] **Step 3: Commit**

```bash
git add persona/commands/review.md
git commit -m "feat(persona): /persona:review command entry point

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 10: End-to-end smoke test on a sample document

**Files:**
- Create (test fixture, temporary): `C:\Users\yelow\AppData\Local\Temp\claude\D--git-home\d8e7ff20-c801-4cc7-ad85-afec8dd435eb\scratchpad\sample-policy.md`
- No plugin files modified.

**Interfaces:**
- Consumes: the whole plugin (Tasks 1–9).
- Produces: confidence the pipeline runs end-to-end and writes the expected artifacts.

- [ ] **Step 1: Create a tiny sample document**

Create `...\scratchpad\sample-policy.md`:

```markdown
# Политика парольной защиты (черновик)

Все сотрудники обязаны менять пароль каждые 30 дней. Минимальная длина — 8 символов.
Пароли хранятся в общей таблице для удобства администрирования. MFA не требуется.
Нарушение влечёт устное предупреждение.
```

- [ ] **Step 2: Register the plugin locally so `/persona:review` is available**

The plugin lives at `D:\git\home\persona`. Make it loadable for this session. Document the
chosen mechanism (local marketplace dir or settings plugin path) and confirm:

Run (verify discovery — adjust to the actual install command used):
```bash
ls "D:/git/home/persona/.claude-plugin/plugin.json" && ls "D:/git/home/persona/commands/review.md" && ls "D:/git/home/persona/skills/persona-review/SKILL.md"
```
Expected: all three paths listed.

- [ ] **Step 3: Dry-run the deterministic core (seed + canonicalization) without the LLM**

Run (validates the documented seed math is reproducible):
```bash
python - <<'PY'
import hashlib, json
def seed(path, params):
    return hashlib.sha256((path+"\n"+json.dumps(params,sort_keys=True)).encode()).hexdigest()
p="sample-policy.md"
params={"sectors":["banking","it-services"],"social_groups":["mid-career-professional"],"roles":["ciso","internal-auditor"],"persona_count":2}
s1=seed(p,params); s2=seed(p,params)
assert s1==s2, "seed not stable"
# slot picks stable
def pick(seed,i,L): return int(seed[i*8:i*8+8],16)%L
assert pick(s1,0,16)==pick(s2,0,16)
print("OK seed stable:", s1[:12], "picks:", pick(s1,0,16), pick(s1,1,3))
PY
```
Expected: `OK seed stable:` with identical picks on repeat.

- [ ] **Step 4: Run the live pipeline (manual checkpoint)**

Invoke `/persona:review ...\scratchpad\sample-policy.md`. Walk the interactive phases (accept the
suggested infosec-policy panel, 2 personas, hostility 3). Let it complete.

- [ ] **Step 5: Verify artifacts were created**

Run:
```bash
B="$(dirname '/c/Users/yelow/AppData/Local/Temp/claude/D--git-home/d8e7ff20-c801-4cc7-ad85-afec8dd435eb/scratchpad/sample-policy.md')/.persona-review/sample-policy"
ls "$B/00_input-analysis.md" "$B/personas/persona-set.json" "$B/reports/persona-feedback.md" "$B/reports/persona-feedback.html" "$B/reports/synthesis.md" "$B/reports/synthesis.html"
```
Expected: all six artifact paths exist.

- [ ] **Step 6: Verify persona-set.json and synthesis.json are valid and reproducible**

Run:
```bash
python - <<'PY'
import json,glob,os
base=os.path.dirname('/c/Users/yelow/AppData/Local/Temp/claude/D--git-home/d8e7ff20-c801-4cc7-ad85-afec8dd435eb/scratchpad/sample-policy.md')+'/.persona-review/sample-policy'
ps=json.load(open(base+'/personas/persona-set.json',encoding='utf-8'))
assert ps['schema_version']==1 and len(ps['personas'])>=2
print('OK persona-set valid, personas:', len(ps['personas']))
PY
```
Expected: `OK persona-set valid, personas: 2` (or more).

- [ ] **Step 7: Commit any fixes surfaced by the smoke test**

```bash
git add -A persona/
git commit -m "fix(persona): adjustments from end-to-end smoke test

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Notes for the implementer

- These files are PROMPT artifacts. The "tests" validate structure (JSON parses, frontmatter is
  valid, references resolve, sections exist) and a final live smoke test — there is no unit-test
  suite to run.
- Do NOT use the Workflow tool for reviewer dispatch; use parallel Agent (Task) calls (spec/skill
  decision — avoids the opt-in gate). One message, multiple Task calls = concurrent reviewers.
- Keep every report and persona profile in the document's detected language.
- Never let a persona address the user as a teammate, on any hostility level.
