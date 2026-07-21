# FinTrace

FinTrace turns AI-generated financial research into auditable, updateable evidence trails.

Most financial research agents can produce a confident-looking report. FinTrace focuses on the part that matters after the report is written: which evidence supports the signal, which evidence challenges it, whether the signal has strengthened or weakened, and what should be watched next.

## What It Does

FinTrace helps analysts and AI agents maintain structured signal cards:

- Core hypothesis
- Supporting evidence
- Counter evidence
- Watchlist metrics
- Status changes over time
- Markdown reports for human review
- Standalone HTML evidence graphs

The goal is not to replace financial judgment. The goal is to make research claims easier to audit, update, and falsify.

## Quick Demo

```bash
python -m fintrace.cli demo --out-dir examples
```

This creates:

- `examples/nvda_ai_demand.signal.json`
- `examples/nvda_ai_demand.report.md`
- `examples/nvda_ai_demand.graph.html`

Then evaluate the signal again:

```bash
python -m fintrace.cli status examples/nvda_ai_demand.signal.json
```

Example output:

```text
Signal: NVDA AI Demand
Previous: strengthened
Current: strengthened
Confidence: 0.73
Why: Support score 2.3, counter score 0.7, neutral evidence 0. Net evidence points to 'strengthened'.
```

## Install Locally

```bash
git clone https://github.com/jiao20050114-coder/fintrace.git
cd fintrace
python -m pip install -e .
```

Then run:

```bash
fintrace demo --out-dir examples
fintrace status examples/nvda_ai_demand.signal.json
fintrace extract examples/nvda_ai_demand.signal.json --file examples/nvda_update.txt --source "Example update"
fintrace report examples/nvda_ai_demand.signal.json --out examples/nvda_ai_demand.report.md
fintrace graph examples/nvda_ai_demand.signal.json --out examples/nvda_ai_demand.graph.html
```

## Create A Signal Card

```bash
fintrace init examples/robotics.signal.json \
  --title "China Robotics Supply Chain" \
  --topic "Robotics" \
  --hypothesis "Industrial robot demand and policy support are strengthening the domestic supply chain."
```

Add evidence:

```bash
fintrace add-evidence examples/robotics.signal.json \
  --kind support \
  --source "Company announcement" \
  --text "A leading component supplier reported accelerating order growth." \
  --weight 1.2
```

Add counter evidence:

```bash
fintrace add-evidence examples/robotics.signal.json \
  --kind counter \
  --source "Industry channel check" \
  --text "Integrator margins remain under pressure due to price competition." \
  --weight 0.9
```

Add watchlist metrics:

```bash
fintrace add-watch examples/robotics.signal.json \
  --metric "Order backlog growth" \
  --why "Confirms whether demand is converting into near-term revenue" \
  --source-hint "Quarterly reports and investor relations updates"
```

Evaluate:

```bash
fintrace status examples/robotics.signal.json
```

Extract evidence from a text file:

```bash
fintrace extract examples/robotics.signal.json \
  --file examples/robotics_update.txt \
  --source "Industry update"
```

Append the extracted candidates:

```bash
fintrace extract examples/robotics.signal.json \
  --file examples/robotics_update.txt \
  --source "Industry update" \
  --apply
```

Render a report:

```bash
fintrace report examples/robotics.signal.json --out examples/robotics.report.md
```

Render an HTML evidence graph:

```bash
fintrace graph examples/robotics.signal.json --out examples/robotics.graph.html
```

## Signal Status Logic

FinTrace uses a simple transparent scoring model in the first release:

- `draft`: no evidence recorded
- `active`: mixed or early evidence
- `strengthened`: support evidence clearly outweighs counter evidence
- `weakened`: counter evidence is meaningful relative to support evidence
- `falsified`: counter evidence clearly overwhelms support evidence

The model is intentionally simple so analysts can inspect and challenge it. Future versions can add source quality, evidence freshness, topic-specific thresholds, and LLM-assisted extraction.

## Evidence Extraction

`fintrace extract` is a lightweight first step toward semi-automated research tracking. It reads text from one source:

- `--text`
- `--file`
- `--url`

By default it prints candidate evidence without changing the signal card. Add `--apply` to append the candidates.

The current extractor is rule-based and dependency-free. It looks for finance terms plus support or counter-evidence language, then assigns a conservative weight. This keeps the workflow inspectable and makes it easy to replace the extraction backend with an LLM later.

## Why This Exists

AI research tools are getting good at writing. They are still weak at maintaining memory about why a claim was made, what could invalidate it, and whether new facts change the conclusion.

FinTrace is designed as a small building block for:

- Financial research agents
- Investment memo workflows
- Sector tracking
- Earnings season monitoring
- Agent skills and MCP tools
- Evidence-grounded deep research
- Visual evidence review before publishing a memo

## Roadmap

- JSON schema export
- Evidence freshness decay
- Source reliability scoring
- MCP server wrapper
- Codex/Claude skill package
- LLM-assisted evidence extraction from filings, transcripts, and news
- Batch tracking for industries and watchlists

## Project Status

This is an alpha MVP. Do not use it as investment advice or as a trading system. It is a research workflow tool.

## License

MIT
