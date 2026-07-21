---
name: fintrace
description: Maintain auditable financial research signal cards with evidence, counter-evidence, watchlists, and status updates.
---

# FinTrace Skill

Use this skill when the user asks to create, audit, update, or review a financial research thesis, investment signal, sector-tracking logic, or evidence-backed market view.

## Workflow

1. Treat the user's natural-language request as the brief.
2. Create a signal workspace with `fintrace from-brief`.
3. Read the generated `*.agent_brief.md`.
4. Locate primary and high-reliability sources when the generated `sources.json` has no URLs.
5. Use `fintrace ingest` to fetch configured sources and screen them automatically.
6. Show candidate evidence before applying it unless the user explicitly asked for automatic updates.
7. Run `fintrace status` after material evidence changes.
8. Render a Markdown report with `fintrace report` when the user needs a human-readable memo.
9. Render an HTML evidence graph with `fintrace graph` when the user needs to inspect the logic visually.

## Commands

Create a signal:

```bash
fintrace from-brief "User's research request" --out-dir path/to/workspace
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

Append ingested evidence:

```bash
fintrace ingest path/to/signal.json --sources path/to/sources.json --query "topic keywords" --apply
```

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
- If sources are missing, find source URLs first, update `sources.json`, then run ingest.
- Do not present FinTrace output as investment advice.
