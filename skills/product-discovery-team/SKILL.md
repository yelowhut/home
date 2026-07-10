---
name: product-discovery-team
description: |
  Use when the user wants comprehensive product discovery on an idea or concept:
  - Analyze a new product idea, evaluate market potential and audience
  - Research business viability, positioning, go-to-market, risks
  - Produce structured discovery documentation for a team to version and review

  Output is a local folder of linked Markdown reports plus .drawio diagrams,
  ready to commit to git. No Notion or other external service required.
---

# Product Discovery Team

A multi-agent research system that performs comprehensive product analysis and writes the result
as a **local, git-versionable folder**: linked Markdown reports + native `.drawio` diagrams.
8 specialized agents (Market, Audience, JTBD, Value Proposition, Business, GTM, Creative, Critic)
each produce one report; a final Executive Summary ties them together.

## Workflow Overview

```
User Input (product description)
         │
         ▼
┌─────────────────────┐
│  1. Setup Phase     │
│  - Ask folder name  │
│  - Detect language  │
│  - Create folder +  │
│    diagrams/ subdir │
└─────────────────────┘
         │
         ▼
┌─────────────────────┐
│  2. Research Phase  │  ← 8 agents, each writes one NN_*.md
│  (web search for    │     5 of them also write a .drawio
│   real data)        │
└─────────────────────┘
         │
         ▼
┌─────────────────────┐
│  3. Synthesis       │
│  - 00_EXECUTIVE_    │
│    SUMMARY.md       │
│  - cross-links      │
└─────────────────────┘
```

## Output Layout (git-friendly)

Create the folder in the current working directory (assumed to be a git repo).
Use today's date for the prefix and a short kebab-case slug of the product.

```
YYYY_MM_DD_<product-slug>/
  00_EXECUTIVE_SUMMARY.md      ← parent: key findings + GO/NO-GO + links
  01_market_research.md
  02_audience_analysis.md
  03_jtbd_analysis.md
  04_value_proposition.md
  05_business_analysis.md
  06_gtm_strategy.md
  07_creative_brief.md
  08_risk_assessment.md
  diagrams/
    tam-sam-som.drawio
    value-proposition-canvas.drawio
    gtm-funnel.drawio
    positioning.drawio
    risk-matrix.drawio
```

All cross-references are relative Markdown links: `[Market Research](01_market_research.md)`.
A report embeds its diagram by linking to it: `Схема: [positioning.drawio](diagrams/positioning.drawio)`
(GitHub does not preview `.drawio` inline — it opens in the draw.io app / VS Code extension, which is
the intended workflow).

## Execution Steps

### Step 1: Initialize

1. **Ask for folder name / product name** — Prompt: "Как назвать папку исследования (или название продукта)?"
2. **Detect language** — If the product description contains Cyrillic → all reports in Russian. Otherwise → English.
3. **Create the folder** `YYYY_MM_DD_<slug>/` and its `diagrams/` subdirectory using file tools.

### Step 2: Run Research Agents

Execute each agent in order. Each agent MUST use web search (`WebSearch` / `WebFetch`) for real, current data.

Load agent instructions from `references/` before executing each:

| Order | Agent | Reference File | Writes report | Writes diagram |
|-------|-------|----------------|---------------|----------------|
| 1 | Market Researcher | `references/agent-market.md` | `01_market_research.md` | `diagrams/tam-sam-som.drawio` |
| 2 | Audience Analyst | `references/agent-audience.md` | `02_audience_analysis.md` | — |
| 3 | JTBD Expert | `references/agent-jtbd.md` | `03_jtbd_analysis.md` | — |
| 4 | Value Proposition Architect | `references/agent-value.md` | `04_value_proposition.md` | `diagrams/value-proposition-canvas.drawio` |
| 5 | Business Analyst | `references/agent-business.md` | `05_business_analysis.md` | — |
| 6 | Go To Market Expert | `references/agent-gtm.md` | `06_gtm_strategy.md` | `diagrams/gtm-funnel.drawio` |
| 7 | Creative Strategist | `references/agent-creative.md` | `07_creative_brief.md` | `diagrams/positioning.drawio` |
| 8 | Critical Reviewer | `references/agent-critic.md` | `08_risk_assessment.md` | `diagrams/risk-matrix.drawio` |

**For each agent:**
1. Read the agent's reference file
2. Execute research following the agent's instructions
3. Use web search for market data, competitors, trends (cite sources as links)
4. Write the agent's report as `NN_<name>.md` in the folder
5. If the agent has a diagram (see table): read `references/drawio-kit.md`, fill the matching template, and write the `.drawio` into `diagrams/`

### Step 3: Synthesize Executive Summary

After all agents complete:

1. **Read all 8 reports** to gather insights
2. **Write `00_EXECUTIVE_SUMMARY.md`** with this structure:

```markdown
# [Product Name] — Product Discovery

## Ключевые выводы
[3-5 bullet points with most important findings]

## Рекомендация
**[GO / NO-GO / PIVOT]** — [brief justification]

## Приоритетные сегменты
[Top 2-3 audience segments with potential]

## Оценка потенциала
[Brief market opportunity assessment]

## Следующие шаги
[3-5 recommended actions]

---
### Детальные отчёты
- [Market Research](01_market_research.md)
- [Audience Analysis](02_audience_analysis.md)
- [JTBD Analysis](03_jtbd_analysis.md)
- [Value Proposition](04_value_proposition.md)
- [Business Analysis](05_business_analysis.md)
- [GTM Strategy](06_gtm_strategy.md)
- [Creative Brief](07_creative_brief.md)
- [Risk Assessment](08_risk_assessment.md)

### Схемы
- [TAM / SAM / SOM](diagrams/tam-sam-som.drawio)
- [Value Proposition Canvas](diagrams/value-proposition-canvas.drawio)
- [GTM-воронка](diagrams/gtm-funnel.drawio)
- [Карта позиционирования](diagrams/positioning.drawio)
- [Карта рисков](diagrams/risk-matrix.drawio)
```

## Agent Execution Pattern

When running each agent:

```
1. READ references/agent-{name}.md
2. THINK through the agent's framework
3. WEB SEARCH for real data (2-5 searches per agent)
4. SYNTHESIZE findings into the structured report
5. WRITE NN_{name}.md
6. IF agent has a diagram: READ references/drawio-kit.md → fill template → WRITE diagrams/{slug}.drawio
```

## Diagram Generation

Diagrams are native `.drawio` files (plain XML), generated from the parametric templates in
`references/drawio-kit.md`. **Always read `drawio-kit.md` before writing any `.drawio`** — it holds
the Primo color palette, the per-diagram coordinate formulas, and the required escaping rules.
Do not invent coordinates freehand; fill the template slots so layouts stay clean.

## Language Rules

- If product description contains Cyrillic → Russian output
- Otherwise → English output
- Apply to ALL reports and diagram labels consistently

## Important Notes

- **Always use web search** — every agent must search for real, current data
- **Write real local files** — use file tools; everything lives in the working directory under git
- **Sequential execution** — run agents in order (later agents may reference earlier findings)
- **Cite sources** — include source links in the reports where relevant
- **Be specific** — avoid generic statements, provide concrete data and examples
- **Commit when done** — the folder is plain Markdown + `.drawio`, ready for `git add` and team review via PR
