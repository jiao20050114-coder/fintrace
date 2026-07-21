# Adversarial Checklist

Use this checklist before telling the user a FinTrace run is complete.

## Evidence Quality

- Every evidence item has a source and, when available, a URL.
- Support and counter evidence are separated.
- Counter evidence was actively searched for, not treated as optional.
- Each item is atomic and factual.
- Agent interpretation is in `reason`, not mixed into `text`.

## Source Quality

- Primary sources were preferred: filings, company IR, exchange notices, regulator publications, factsheets, transcripts.
- Secondary sources were used only when primary sources were unavailable or linked.
- Source reliability in `sources.json` is plausible and not uniformly high.
- Sources from `fintrace discover` were reviewed; weak secondary or social sources were not ingested blindly.
- `exclude_terms` remove obvious noise such as sponsored posts, rumors, events, and generic marketing.
- Built-in source packs were used when applicable, and any `agent_instructions` were followed.

## Workflow Integrity

- User brief was preserved in `*.agent_brief.md`.
- `fintrace import-evidence --dry-run` or `fintrace ingest` preview was shown before applying unless the user explicitly requested automatic application.
- `fintrace status` was run after material evidence changes.
- Markdown report and HTML graph were regenerated after final evidence updates.
- Final files are in the working project, not only terminal output.

## Red Flags

- The signal strengthens with only one weak secondary-source item.
- Evidence relies on unsourced agent memory.
- The same evidence item appears multiple times.
- The report has no counter evidence.
- The source registry contains no primary or high-reliability source candidates.
- A generic source pack was used even though a more specific pack was available.
