# Changelog

## 0.9.0

- Added `fintrace source-plan` to generate agent-readable source discovery, triage, and evidence-import plans from natural-language briefs.
- `fintrace from-brief` now writes a `*.source_plan.md` file and embeds structured `agent_source_plan` metadata in `sources.json`.
- Improved `page` ingest with HTML title parsing, boilerplate skipping, same-domain/local link discovery, and linked-page screening.
- Added tests for page link discovery, linked-page evidence extraction, source-plan generation, and CLI source-plan output.

## 0.8.1

- Hardened source-pack CLI error handling for missing parameters and unknown packs.
- Source pack writes now create parent directories automatically.
- `fintrace ingest` now skips failed sources with warnings instead of aborting the whole run.
- `fintrace ingest` now warns clearly when a registry has no configured sources.
- Corrected NVIDIA built-in sources to HTML page sources after verifying the URLs do not return RSS XML.
- Made `import-evidence --dry-run` avoid mutating the in-memory signal object.
- Aligned `import-evidence` with the JSON Schema by rejecting unknown evidence fields.
- Improved ingest relevance matching for CJK query terms and Latin word boundaries.

## 0.8.0

- Added `fintrace source-pack list/show/create`.
- Added built-in source packs for `sec-us`, `hkex`, `nvda`, `dymon-asia`, and generic `fund-manager`.
- Added source-pack tests and skill guidance to prefer source packs for common workflows.

## 0.7.0

- Added first-class `reason` storage on evidence items.
- Added dry-run and duplicate protection to `fintrace import-evidence`.
- Added agent evidence JSON Schema and skill references for agent contracts and adversarial review.
- Added skill UI metadata in `skills/fintrace/agents/openai.yaml`.
- Adjusted mixed-evidence scoring so close support/counter evidence remains `active` instead of prematurely `weakened`.

## 0.6.0

- Added `fintrace import-evidence` for structured evidence produced by agents or LLMs.
- Added wrapped-object and array JSON import formats.
- Added optional post-import signal evaluation.

## 0.5.0

- Added multilingual extraction support with built-in English, Chinese, Japanese, and Korean finance terms.
- Added custom `support_terms`, `counter_terms`, and `finance_terms` for CLI extraction and source registries.
- Improved CJK term matching and sentence splitting for non-English documents.

## 0.4.0

- Added `fintrace from-brief` for Codex, Claude, WorkBuddy, and other agent environments.
- Added natural-language brief parsing for signal title, topic, ticker, include terms, watchlist, source registry scaffold, and agent instructions.
- Added agent-oriented workflow guidance in the bundled skill.

## 0.3.0

- Added `fintrace ingest` for automated source fetching, relevance screening, and evidence extraction.
- Added JSON source registry with source reliability, include terms, and exclude terms.
- Added RSS/Atom feed parsing and local source examples.

## 0.2.0

- Added `fintrace extract` for rule-based evidence extraction from text, files, and URLs.
- Added preview-first extraction workflow with optional `--apply`.
- Added example update text and extractor tests.

## 0.1.0

- Initial signal card schema, evidence ledger, CLI, Markdown report, HTML graph, examples, and skill draft.
