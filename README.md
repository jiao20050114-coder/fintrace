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
python -m fintrace.cli demo --out-dir work/demo
```

This creates:

- `work/demo/nvda_ai_demand.signal.json`
- `work/demo/nvda_ai_demand.report.md`
- `work/demo/nvda_ai_demand.graph.html`

Then evaluate the signal again:

```bash
python -m fintrace.cli status work/demo/nvda_ai_demand.signal.json
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
fintrace demo --out-dir work/demo
fintrace from-brief "Track Dymon Asia AUM, fund performance, and regulatory risk" --out-dir work/dymon-asia
fintrace source-plan "Track Dymon Asia AUM, fund performance, and regulatory risk" --out work/dymon-asia/source_plan.md
fintrace source-pack create dymon-asia --out work/dymon-asia/dymon-asia.sources.json
fintrace status work/dymon-asia/dymon-asia.signal.json
fintrace import-evidence work/dymon-asia/dymon-asia.signal.json --file examples/agent_evidence.example.json --dry-run
fintrace extract work/dymon-asia/dymon-asia.signal.json --file examples/nvda_update.txt --source "Example update"
fintrace ingest work/dymon-asia/dymon-asia.signal.json --sources examples/sources.example.json
fintrace report work/dymon-asia/dymon-asia.signal.json --out work/dymon-asia/report.md
fintrace graph work/dymon-asia/dymon-asia.signal.json --out work/dymon-asia/graph.html
```

## Create A Signal Card

For agent and skill use, start from the user's natural-language request:

```bash
fintrace from-brief "Track Dymon Asia AUM, fund performance, and regulatory risk" \
  --out-dir work/dymon-asia
```

This creates:

- `dymon-asia.signal.json`
- `dymon-asia.sources.json`
- `dymon-asia.agent_brief.md`
- `dymon-asia.source_plan.md`

An agent such as Codex, Claude, or WorkBuddy can read the generated agent brief and source plan, locate high-reliability sources, update `sources.json`, then run `fintrace ingest`.

To generate only the search and source-triage plan:

```bash
fintrace source-plan "Track Dymon Asia AUM, fund performance, and regulatory risk" \
  --out work/dymon-asia/dymon-asia.source_plan.md
```

For common source sets, use a built-in source pack:

```bash
fintrace source-pack list
fintrace source-pack create dymon-asia --out work/dymon-asia/dymon-asia.sources.json
```

For US SEC issuer filings:

```bash
fintrace source-pack create sec-us \
  --ticker NVDA \
  --cik 1045810 \
  --out work/nvda/nvda.sources.json
```

If the user already supplied source URLs:

```bash
fintrace from-brief "Track Dymon Asia AUM and risk signals" \
  --out-dir work/dymon-asia \
  --source-url "Official=https://example.com/rss.xml"
```

Manual creation is also supported:

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

For non-English or domain-specific language, add custom terms:

```bash
fintrace extract examples/robotics.signal.json \
  --text "公司订单增长，收入改善，需求强劲。行业竞争加剧，毛利率承压。" \
  --source "Chinese update" \
  --support-term "订单增长" \
  --counter-term "毛利率承压" \
  --finance-term "收入"
```

Automatically fetch and screen configured sources:

```bash
fintrace ingest examples/robotics.signal.json \
  --sources examples/sources.example.json \
  --query "robotics component orders"
```

Apply screened evidence after review:

```bash
fintrace ingest examples/robotics.signal.json \
  --sources examples/sources.example.json \
  --query "robotics component orders" \
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

## Automated Source Ingest

`fintrace ingest` moves one step earlier in the workflow: instead of asking the user to find text first, it fetches configured information sources and screens them before extraction.

Each source can define:

- `kind`: `feed` or `page`
- `url`: RSS/Atom feed, webpage, or local file path
- `reliability`: source quality score from `0.0` to `1.0`
- `include_terms`: terms that raise relevance
- `exclude_terms`: terms that reject noisy documents
- `support_terms`: custom support-evidence terms in any language
- `counter_terms`: custom counter-evidence terms in any language
- `finance_terms`: custom domain terms in any language

Example:

```json
{
  "sources": [
    {
      "id": "company-ir",
      "name": "Company Investor Relations",
      "kind": "feed",
      "url": "https://example.com/rss",
      "reliability": 0.9,
      "include_terms": ["revenue", "guidance", "orders"],
      "exclude_terms": ["sponsored"],
      "support_terms": ["订单增长", "売上高成長", "매출 성장"],
      "counter_terms": ["毛利率承压", "リスク", "위험"],
      "finance_terms": ["收入", "売上高", "매출"]
    }
  ]
}
```

The ingest ranking combines source reliability, signal relevance, configured terms, and extracted evidence score. Like `extract`, it previews results by default and only writes to the ledger with `--apply`.

For `page` sources, FinTrace parses the HTML title, skips common navigation and footer regions, extracts cleaner page text, discovers relevant same-domain or local links, and screens a small number of linked pages. This makes official IR, newsroom, exchange, and fund pages more useful while keeping the behavior inspectable.

FinTrace is Unicode-first and can ingest text in any language. The built-in extractor includes common English, Chinese, Japanese, and Korean finance terms. For other languages or specialized domains, pass custom terms in the CLI or source registry. For deeper cross-language interpretation, pair this workflow with an LLM in the agent layer.

## Source Packs

`fintrace source-pack` provides reusable source registry templates so users do not need to hand-write `sources.json`.

```bash
fintrace source-pack list
fintrace source-pack show nvda
fintrace source-pack create nvda --out work/nvda/nvda.sources.json
```

Built-in packs include:

- `sec-us`: SEC EDGAR Atom feed, parameterized by `--ticker` and `--cik`
- `hkex`: HKEX RSS and HKEXnews sources
- `nvda`: NVIDIA investor relations and newsroom HTML pages
- `dymon-asia`: Dymon Asia official pages and fund-manager guidance
- `fund-manager`: generic asset manager source template

Source packs may include `agent_instructions`. Agents should read those instructions before ingesting or importing evidence.

## Agent And Skill Mode

FinTrace is designed to work inside Codex, Claude, WorkBuddy, and similar agent environments. In that mode the user usually gives a natural-language request, not a perfect CLI command.

Use `from-brief` as the first step. It turns the user request into a small workspace containing a signal card, source registry scaffold, and agent instructions. The agent can then:

- Read `*.source_plan.md` for search queries, source priority, and rejection rules.
- Search for primary and high-reliability sources.
- Add source URLs to the generated `sources.json`.
- Run `fintrace ingest` to screen those sources.
- Show the candidate evidence to the user.
- Apply evidence only after review or explicit instruction.

When the agent has already read and understood source material, use `import-evidence` instead of asking FinTrace to classify language itself:

```bash
fintrace import-evidence work/dymon-asia/dymon-asia.signal.json \
  --file work/dymon-asia/agent_evidence.json \
  --dry-run
```

Then import and evaluate:

```bash
fintrace import-evidence work/dymon-asia/dymon-asia.signal.json \
  --file work/dymon-asia/agent_evidence.json \
  --evaluate
```

Agent evidence JSON can be an array or an object with an `evidence` array:

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

The JSON contract is also captured in `schemas/agent_evidence.schema.json`.

This keeps the architecture simple: the agent handles semantic understanding, while FinTrace stores evidence, updates status, and renders the ledger.

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
