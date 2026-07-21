---
name: fintrace
description: Maintain auditable financial research signal cards with evidence, counter-evidence, watchlists, and status updates.
---

# FinTrace Skill

Use this skill when the user asks to create, audit, update, or review a financial research thesis, investment signal, sector-tracking logic, or evidence-backed market view.

## Workflow

1. Treat the user's natural-language request as the brief.
2. Create a signal workspace with `fintrace from-brief`.
3. Read the generated `*.agent_brief.md` and `*.source_plan.md`.
4. Prefer `fintrace source-pack` for common source sets; otherwise follow the source plan's search queries and triage rules.
5. Add selected URLs to `sources.json`, then use `fintrace ingest` for feed/page screening.
6. If the agent has semantically read PDFs, tables, portals, or complex pages, write structured evidence JSON and import it with `fintrace import-evidence`.
7. Show candidate evidence before applying it unless the user explicitly asked for automatic updates.
8. Run `fintrace status` after material evidence changes.
9. Render a Markdown report with `fintrace report` when the user needs a human-readable memo.
10. Render an HTML evidence graph with `fintrace graph` when the user needs to inspect the logic visually.

## Commands

Use `fintrace ...` when the CLI is installed. If it is not on `PATH`, run commands from the repository root as:

```bash
PYTHONPATH=src python -m fintrace.cli ...
```

List and create source packs:

```bash
fintrace source-pack list
fintrace source-pack create dymon-asia --out path/to/dymon-asia.sources.json
fintrace source-pack create sec-us --ticker NVDA --cik 1045810 --out path/to/nvda.sources.json
```

Create a signal:

```bash
fintrace from-brief "User's research request" --out-dir path/to/workspace
```

Create only a source discovery plan:

```bash
fintrace source-plan "User's research request" --out path/to/source_plan.md
```

Manual signal creation:

```bash
fintrace init path/to/signal.json --title "Signal title" --hypothesis "Falsifiable hypothesis"
```

Add supporting evidence:

```bash
fintrace add-evidence path/to/signal.json --kind support --source "Source name" --text "Evidence text" --weight 1.0
```

Add counter evidence:

```bash
fintrace add-evidence path/to/signal.json --kind counter --source "Source name" --text "Evidence text" --weight 1.0
```

Evaluate:

```bash
fintrace status path/to/signal.json
```

Extract candidate evidence:

```bash
fintrace extract path/to/signal.json --file path/to/update.txt --source "Source name"
```

Append extracted candidates:

```bash
fintrace extract path/to/signal.json --file path/to/update.txt --source "Source name" --apply
```

Fetch and screen configured sources:

```bash
fintrace ingest path/to/signal.json --sources path/to/sources.json --query "topic keywords"
```

For `page` sources, ingest extracts cleaner page text and follows a small number of relevant same-domain or local links. Treat this as screening, not final semantic understanding.

For non-English briefs or sources, add language-specific terms to `sources.json`:

```json
{
  "support_terms": ["订单增长", "売上高成長", "매출 성장"],
  "counter_terms": ["毛利率承压", "リスク", "위험"],
  "finance_terms": ["收入", "売上高", "매출"]
}
```

Append ingested evidence:

```bash
fintrace ingest path/to/signal.json --sources path/to/sources.json --query "topic keywords" --apply
```

Import structured evidence produced by the agent:

```bash
fintrace import-evidence path/to/signal.json --file path/to/agent_evidence.json --dry-run
fintrace import-evidence path/to/signal.json --file path/to/agent_evidence.json --evaluate
```

For the evidence JSON contract, read `references/agent-evidence-contract.md`.

Render:

```bash
fintrace report path/to/signal.json --out path/to/report.md
```

Render an evidence graph:

```bash
fintrace graph path/to/signal.json --out path/to/graph.html
```

## Guidance

- Keep evidence atomic: one factual claim per evidence item.
- Prefer verifiable primary sources for filings, financial statements, announcements, and transcripts.
- Use counter evidence generously; a useful signal is allowed to be wrong quickly.
- In agent environments, use the user's own words as the starting brief and preserve them in `*.agent_brief.md`.
- Use `*.source_plan.md` as the search and source-triage checklist before browsing.
- Let the agent handle semantic reading for PDFs, tables, portals, and complex pages. Use `import-evidence` to persist the agent's structured conclusions.
- If sources are missing, try `source-pack list` first; otherwise follow `source-plan`, find source URLs, update `sources.json`, then run ingest.
- For any language not covered by built-in terms, add user-language `support_terms`, `counter_terms`, and `finance_terms` before ingesting.
- Do not present FinTrace output as investment advice.

Before finalizing a user-facing result, read `references/adversarial-checklist.md` and resolve any red flags.
