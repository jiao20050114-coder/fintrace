---
name: fintrace
description: Maintain auditable financial research signal cards with evidence, counter-evidence, watchlists, and status updates.
---

# FinTrace Skill

Use this skill when the user asks to create, audit, update, or review a financial research thesis, investment signal, sector-tracking logic, or evidence-backed market view.

## Workflow

1. State the core hypothesis as a falsifiable claim.
2. Separate supporting evidence from counter evidence.
3. Record source, observed date, and evidence weight for every claim.
4. Identify watchlist metrics that could strengthen, weaken, or falsify the signal.
5. Run `fintrace status` after material evidence changes.
6. Render a Markdown report with `fintrace report` when the user needs a human-readable memo.
7. Render an HTML evidence graph with `fintrace graph` when the user needs to inspect the logic visually.

## Commands

Create a signal:

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
- Do not present FinTrace output as investment advice.
