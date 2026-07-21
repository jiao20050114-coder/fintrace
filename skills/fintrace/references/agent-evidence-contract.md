# Agent Evidence Contract

Use this reference when the agent has read source material and should persist its conclusions with `fintrace import-evidence`.

## Format

Write JSON as either an array of evidence items or an object with an `evidence` array. Prefer the wrapped object.

Required item fields:

- `kind`: `support`, `counter`, or `neutral`
- `text`: one atomic factual claim
- `source`: human-readable source name

Optional item fields:

- `url`: source URL
- `observed_at`: ISO date when the evidence was observed or published
- `weight`: `0.0` to `2.0`, where `1.0` is ordinary materiality
- `reason`: why this evidence supports, weakens, or neutrally informs the signal

## Example

```json
{
  "evidence": [
    {
      "kind": "support",
      "text": "AUM increased for the third consecutive month, indicating improving investor demand.",
      "source": "Monthly fund factsheet",
      "url": "https://example.com/factsheet",
      "observed_at": "2026-07-22",
      "weight": 1.3,
      "reason": "This supports the thesis that investor demand is improving."
    }
  ]
}
```

## Import Commands

Preview:

```bash
fintrace import-evidence path/to/signal.json --file path/to/agent_evidence.json --dry-run
```

Import and evaluate:

```bash
fintrace import-evidence path/to/signal.json --file path/to/agent_evidence.json --evaluate
```

By default duplicate evidence with the same text, source, and URL is skipped. Use `--allow-duplicates` only when the same claim should intentionally appear twice.

## Quality Rules

- One item should contain one claim, not a paragraph summary.
- Use `counter` generously for facts that weaken the hypothesis.
- Put interpretation in `reason`, not in `text`.
- Prefer primary sources; use secondary sources only when they reveal or link to primary evidence.
- Do not import investment advice, price targets, or unsupported predictions as evidence.
