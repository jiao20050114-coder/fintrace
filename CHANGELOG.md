# Changelog

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
