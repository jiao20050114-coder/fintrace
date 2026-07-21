from __future__ import annotations

import json
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from string import Template
from typing import Any


@dataclass(frozen=True)
class SourcePack:
    id: str
    description: str
    registry: dict[str, Any]
    required_params: tuple[str, ...] = ()


BUILTIN_PACKS: dict[str, SourcePack] = {
    "sec-us": SourcePack(
        id="sec-us",
        description="SEC EDGAR company filings Atom feed for US-listed issuers.",
        required_params=("cik",),
        registry={
            "sources": [
                {
                    "id": "sec-edgar-${ticker_lc}",
                    "name": "SEC EDGAR ${ticker} filings",
                    "kind": "feed",
                    "url": "https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK=${cik}&owner=exclude&count=40&output=atom",
                    "reliability": 0.98,
                    "include_terms": ["10-K", "10-Q", "8-K", "risk", "revenue", "guidance", "${ticker}"],
                    "exclude_terms": ["ownership", "insider"],
                    "support_terms": ["revenue increased", "guidance raised", "margin improved"],
                    "counter_terms": ["risk", "decline", "decreased", "impairment", "material weakness"],
                    "finance_terms": ["revenue", "margin", "cash flow", "inventory", "guidance"],
                }
            ],
            "agent_instructions": [
                "Use SEC filings as primary evidence for financial, risk, and disclosure claims.",
                "Prefer the filing detail page or filing document URL when importing evidence.",
                "Do not treat form presence alone as evidence; read the filing content first when possible.",
            ],
        },
    ),
    "hkex": SourcePack(
        id="hkex",
        description="HKEX RSS feeds and HKEXnews landing page for Hong Kong market updates.",
        registry={
            "sources": [
                {
                    "id": "hkex-news-releases",
                    "name": "HKEX News Releases RSS",
                    "kind": "feed",
                    "url": "https://www.hkex.com.hk/Services/RSS-Feeds/News-Releases?sc_lang=en",
                    "reliability": 0.9,
                    "include_terms": ["announcement", "listing", "issuer", "results", "rules"],
                    "exclude_terms": ["advertisement", "sponsored"],
                    "support_terms": ["approved", "increase", "growth", "record"],
                    "counter_terms": ["suspension", "delay", "breach", "risk"],
                    "finance_terms": ["results", "listing", "issuer", "turnover", "announcement"],
                },
                {
                    "id": "hkexnews",
                    "name": "HKEXnews",
                    "kind": "page",
                    "url": "https://www.hkexnews.hk/index.htm",
                    "reliability": 0.88,
                    "include_terms": ["announcement", "financial statements", "results", "prospectus"],
                    "exclude_terms": ["advertisement"],
                    "support_terms": ["profit increased", "revenue increased", "approved"],
                    "counter_terms": ["loss", "suspension", "delay", "qualification"],
                    "finance_terms": ["revenue", "profit", "results", "dividend"],
                },
            ],
            "agent_instructions": [
                "Use HKEXnews for issuer-specific announcements and financial reports.",
                "When possible, add issuer-specific HKEX announcement URLs discovered by the agent.",
            ],
        },
    ),
    "nvda": SourcePack(
        id="nvda",
        description="NVIDIA investor relations and newsroom RSS sources.",
        registry={
            "sources": [
                {
                    "id": "nvidia-ir-rss",
                    "name": "NVIDIA Investor Relations RSS",
                    "kind": "feed",
                    "url": "https://investor.nvidia.com/investor-resources/rss/default.aspx",
                    "reliability": 0.95,
                    "include_terms": ["NVIDIA", "revenue", "data center", "AI", "guidance", "earnings"],
                    "exclude_terms": ["webcast reminder"],
                    "support_terms": ["revenue increased", "guidance raised", "demand", "record"],
                    "counter_terms": ["restriction", "export", "risk", "supply", "decline"],
                    "finance_terms": ["revenue", "gross margin", "data center", "guidance", "inventory"],
                },
                {
                    "id": "nvidia-newsroom-rss",
                    "name": "NVIDIA Newsroom RSS",
                    "kind": "feed",
                    "url": "https://nvidianews.nvidia.com/rss",
                    "reliability": 0.82,
                    "include_terms": ["NVIDIA", "AI", "data center", "GPU", "partnership"],
                    "exclude_terms": ["podcast", "event"],
                    "support_terms": ["launch", "partnership", "adoption", "expanded"],
                    "counter_terms": ["restriction", "delay", "risk"],
                    "finance_terms": ["AI", "GPU", "data center", "demand"],
                },
            ],
            "agent_instructions": [
                "Treat IR materials as higher reliability than newsroom marketing.",
                "Use newsroom items as lead indicators only when they contain concrete customer, product, or demand evidence.",
            ],
        },
    ),
    "dymon-asia": SourcePack(
        id="dymon-asia",
        description="Dymon Asia official pages plus agent guidance for fund-manager evidence.",
        registry={
            "sources": [
                {
                    "id": "dymon-asia-official",
                    "name": "Dymon Asia Official Website",
                    "kind": "page",
                    "url": "https://www.dymonasia.com/",
                    "reliability": 0.85,
                    "include_terms": ["Dymon", "Asia", "AUM", "fund", "performance", "risk", "基金表现", "监管风险"],
                    "exclude_terms": ["cookie", "disclaimer", "advertisement"],
                    "support_terms": ["AUM increased", "positive performance", "inflows", "资金流入", "基金表现改善"],
                    "counter_terms": ["outflow", "drawdown", "regulatory risk", "资金流出", "监管风险"],
                    "finance_terms": ["AUM", "performance", "subscriptions", "redemptions", "fund", "策略"],
                },
                {
                    "id": "dymon-asia-private-equity",
                    "name": "Dymon Asia Private Equity",
                    "kind": "page",
                    "url": "https://www.dymonasiaprivateequity.com/",
                    "reliability": 0.75,
                    "include_terms": ["Dymon", "private equity", "investment", "portfolio"],
                    "exclude_terms": ["cookie", "advertisement"],
                    "support_terms": ["successful investment", "portfolio growth", "exit"],
                    "counter_terms": ["impairment", "loss", "regulatory"],
                    "finance_terms": ["portfolio", "investment", "exit", "fund"],
                },
            ],
            "agent_instructions": [
                "Dymon Asia public data can be sparse; use the official website as source context, not as sufficient evidence by itself.",
                "Search for factsheets, allocator updates, regulator records, and reputable financial news before importing evidence.",
                "Treat marketing language as low evidentiary value unless it contains factual metrics.",
            ],
        },
    ),
    "fund-manager": SourcePack(
        id="fund-manager",
        description="Generic asset manager tracking template for AUM, flows, performance, and regulatory risk.",
        registry={
            "sources": [],
            "agent_instructions": [
                "Add official website, investor relations, factsheet, regulator, and reputable news URLs before ingesting.",
                "Prioritize AUM, net subscriptions/redemptions, performance dispersion, drawdown, key-person changes, and regulatory events.",
                "Use import-evidence after semantic reading when data is in PDFs, portals, or non-RSS pages.",
            ],
            "source_template": {
                "id": "manager-official",
                "name": "Manager Official Website",
                "kind": "page",
                "url": "https://example.com/",
                "reliability": 0.8,
                "include_terms": ["AUM", "performance", "fund", "risk", "flows"],
                "exclude_terms": ["cookie", "advertisement", "sponsored"],
                "support_terms": [
                    "AUM increased",
                    "positive performance",
                    "inflows",
                    "gate provisions were not triggered",
                    "performance dispersion narrowed",
                    "platform breadth improved",
                ],
                "counter_terms": [
                    "outflows",
                    "net subscriptions remained negative",
                    "drawdown",
                    "regulatory risk",
                    "key person",
                    "key-person risk",
                    "side pocket",
                    "valuation uncertainty",
                    "limited exit options",
                ],
                "finance_terms": [
                    "AUM",
                    "performance",
                    "subscriptions",
                    "net subscriptions",
                    "redemptions",
                    "fund",
                    "continuation vehicle",
                    "side pocket",
                    "gate provisions",
                    "performance dispersion",
                ],
            },
        },
    ),
}


def list_source_packs() -> list[SourcePack]:
    return [BUILTIN_PACKS[key] for key in sorted(BUILTIN_PACKS)]


def get_source_pack(pack_id: str) -> SourcePack:
    try:
        return BUILTIN_PACKS[pack_id]
    except KeyError as exc:
        available = ", ".join(sorted(BUILTIN_PACKS))
        raise ValueError(f"Unknown source pack '{pack_id}'. Available packs: {available}") from exc


def render_source_pack(
    pack_id: str,
    *,
    ticker: str | None = None,
    cik: str | None = None,
) -> dict[str, Any]:
    pack = get_source_pack(pack_id)
    params = {
        "ticker": ticker or "UNKNOWN",
        "ticker_lc": (ticker or "unknown").lower(),
        "cik": cik or "",
    }
    missing = [name for name in pack.required_params if not params.get(name)]
    if missing:
        raise ValueError(f"Source pack '{pack_id}' requires: {', '.join(missing)}")
    return _render_templates(deepcopy(pack.registry), params)


def write_source_pack(path: str | Path, registry: dict[str, Any]) -> None:
    Path(path).write_text(json.dumps(registry, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _render_templates(value: Any, params: dict[str, str]) -> Any:
    if isinstance(value, str):
        return Template(value).safe_substitute(params)
    if isinstance(value, list):
        return [_render_templates(item, params) for item in value]
    if isinstance(value, dict):
        return {key: _render_templates(item, params) for key, item in value.items()}
    return value
