from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

from fintrace.ledger import save_signal
from fintrace.schema import Signal, WatchItem


@dataclass(frozen=True)
class BriefPack:
    signal: Signal
    slug: str
    include_terms: list[str]
    sources: dict[str, object]
    agent_brief: str


DEFAULT_WATCHLIST = [
    WatchItem(
        metric="Primary-source updates",
        why="Checks whether the core thesis is supported by filings, official releases, or direct company materials",
        source_hint="Company IR, regulator filings, exchange announcements",
    ),
    WatchItem(
        metric="Revenue, AUM, order, or guidance change",
        why="Tracks whether the thesis is translating into measurable operating or financial change",
        source_hint="Earnings releases, factsheets, management commentary",
    ),
    WatchItem(
        metric="Risk and counter-evidence",
        why="Surfaces facts that could weaken or falsify the signal",
        source_hint="Risk disclosures, regulator actions, reputable news",
    ),
]

STOPWORDS = {
    "and",
    "for",
    "from",
    "into",
    "recent",
    "signal",
    "signals",
    "the",
    "track",
    "with",
}

CHINESE_STOP_TERMS = {
    "帮我",
    "跟踪",
    "分析",
    "研究",
    "关注",
    "重点",
    "支持",
    "削弱",
    "证据",
    "以及",
}


def create_brief_pack(
    brief: str,
    *,
    out_dir: str | Path,
    slug: str | None = None,
    title: str | None = None,
    topic: str | None = None,
    ticker: str | None = None,
    source_urls: list[str] | None = None,
) -> BriefPack:
    subject = title or infer_subject(brief)
    inferred_topic = topic or infer_topic(brief, subject)
    inferred_ticker = ticker or infer_ticker(brief)
    inferred_slug = slug or slugify(subject)
    include_terms = infer_include_terms(brief, subject=subject, ticker=inferred_ticker)
    hypothesis = (
        f"Material developments related to {subject} can be tracked through primary-source updates, "
        "credible market information, and explicit counter-evidence."
    )
    signal = Signal(
        title=subject,
        hypothesis=hypothesis,
        topic=inferred_topic,
        ticker=inferred_ticker,
        watchlist=list(DEFAULT_WATCHLIST),
    )
    sources = build_source_registry(source_urls or [], include_terms=include_terms)
    agent_brief = render_agent_brief(
        user_brief=brief,
        signal=signal,
        slug=inferred_slug,
        include_terms=include_terms,
        has_sources=bool(source_urls),
    )

    target_dir = Path(out_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    save_signal(signal, target_dir / f"{inferred_slug}.signal.json")
    (target_dir / f"{inferred_slug}.sources.json").write_text(
        json.dumps(sources, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    (target_dir / f"{inferred_slug}.agent_brief.md").write_text(agent_brief, encoding="utf-8")

    return BriefPack(
        signal=signal,
        slug=inferred_slug,
        include_terms=include_terms,
        sources=sources,
        agent_brief=agent_brief,
    )


def infer_subject(brief: str) -> str:
    cleaned = re.sub(r"\s+", " ", brief).strip()
    quoted = re.search(r"['\"“”‘’]([^'\"“”‘’]{2,80})['\"“”‘’]", cleaned)
    if quoted:
        return quoted.group(1).strip()

    after_action = re.search(
        r"^(?:track|monitor|analyze|analyse|research|follow|watch)\s+(.+?)(?:\s+(?:recent|aum|fund|performance|risk|signals?|updates?|news|filings?|公告|风险|变化|表现)\b|[,，。.]|$)",
        cleaned,
        flags=re.IGNORECASE,
    )
    if after_action:
        candidate = after_action.group(1).strip()
        if candidate:
            return candidate

    latin_chunks = re.findall(r"\b[A-Z][A-Za-z0-9&.-]*(?:\s+[A-Z][A-Za-z0-9&.-]*){0,4}\b", cleaned)
    ignored = {"I", "AI", "ETF", "SEC", "RSS", "MCP", "CLI", "URL", "Track", "Monitor", "Analyze"}
    for chunk in latin_chunks:
        if chunk not in ignored and not re.fullmatch(r"[A-Z]{1,5}", chunk):
            return chunk.strip()

    chinese_match = re.search(r"(?:跟踪|分析|研究|关注|监控)([^，。,.]{2,24})", cleaned)
    if chinese_match:
        return chinese_match.group(1).strip()

    return cleaned[:60] if cleaned else "Untitled Signal"


def infer_topic(brief: str, subject: str) -> str:
    lowered = brief.lower()
    if any(term in lowered for term in ["fund", "aum", "hedge", "asset management", "dymon"]):
        return "asset management"
    if any(term in lowered for term in ["ai", "semiconductor", "chip", "gpu", "算力", "半导体"]):
        return "ai infrastructure"
    if any(term in lowered for term in ["robot", "机器人"]):
        return "robotics"
    if any(term in lowered for term in ["bank", "insurance", "broker", "金融"]):
        return "financial services"
    return subject.lower()


def infer_ticker(brief: str) -> str | None:
    matches = re.findall(r"\b[A-Z]{2,6}\b", brief)
    ignored = {"AI", "SEC", "RSS", "MCP", "CLI", "URL", "AUM", "ETF"}
    for match in matches:
        if match not in ignored:
            return match
    return None


def infer_include_terms(brief: str, *, subject: str, ticker: str | None) -> list[str]:
    raw_terms = [subject, brief]
    if ticker:
        raw_terms.append(ticker)
    text = " ".join(raw_terms)
    terms = {
        term
        for term in re.findall(r"[A-Za-z0-9][A-Za-z0-9&.-]{2,}", text)
        if term.lower() not in STOPWORDS
    }
    terms.update(_extract_chinese_terms(text))
    terms.update({"revenue", "guidance", "risk", "filing", "announcement", "AUM"})
    return sorted(terms, key=lambda item: (item.lower(), item))


def _extract_chinese_terms(text: str) -> set[str]:
    normalized = re.sub(r"[，。；;,.]", "、", text)
    normalized = re.sub(r"(重点关注|帮我|请|需要|围绕|关于|支持或削弱)", "、", normalized)
    normalized = re.sub(r"[的和与及]|以及", "、", normalized)
    candidates = set()
    for raw in normalized.split("、"):
        for chunk in re.findall(r"[\u4e00-\u9fff]{2,12}", raw):
            cleaned = chunk.strip()
            for stop in CHINESE_STOP_TERMS:
                cleaned = cleaned.replace(stop, "")
            if 2 <= len(cleaned) <= 12 and cleaned not in CHINESE_STOP_TERMS:
                candidates.add(cleaned)
    if "平台实力" in text:
        candidates.add("平台实力")
    return candidates


def build_source_registry(source_urls: list[str], *, include_terms: list[str]) -> dict[str, object]:
    sources = []
    for index, raw in enumerate(source_urls, start=1):
        name, url = parse_source_url(raw, index=index)
        sources.append(
            {
                "id": slugify(name),
                "name": name,
                "kind": "feed" if url.endswith((".xml", ".rss", ".atom")) or "rss" in url.lower() else "page",
                "url": url,
                "reliability": 0.8,
                "include_terms": include_terms[:12],
                "exclude_terms": ["rumor", "sponsored", "advertisement"],
            }
        )
    return {"sources": sources}


def parse_source_url(raw: str, *, index: int) -> tuple[str, str]:
    if "=" in raw:
        name, url = raw.split("=", 1)
        return name.strip() or f"Source {index}", url.strip()
    return f"Source {index}", raw.strip()


def render_agent_brief(
    *,
    user_brief: str,
    signal: Signal,
    slug: str,
    include_terms: list[str],
    has_sources: bool,
) -> str:
    sources_note = (
        "The user supplied initial source URLs. Run `fintrace ingest` first, then inspect candidates before applying."
        if has_sources
        else "No source URLs were supplied. First locate primary and high-reliability sources, then add them to the generated sources JSON."
    )
    return f"""# FinTrace Agent Brief: {signal.title}

## User Input

{user_brief}

## Generated Signal

- Signal file: `{slug}.signal.json`
- Sources file: `{slug}.sources.json`
- Topic: `{signal.topic or "n/a"}`
- Ticker: `{signal.ticker or "n/a"}`
- Hypothesis: {signal.hypothesis}

## Source Plan

{sources_note}

Prioritize sources in this order:

1. Company, fund, exchange, regulator, or issuer primary sources.
2. Official filings, factsheets, announcements, and transcripts.
3. Reputable financial news with named sources.
4. Secondary commentary only when it points to primary evidence.

Suggested include terms:

{", ".join(include_terms[:20])}

Avoid applying evidence automatically unless the user requested it. Preview with:

```bash
fintrace ingest {slug}.signal.json --sources {slug}.sources.json
```

Apply only after review:

```bash
fintrace ingest {slug}.signal.json --sources {slug}.sources.json --apply
```
"""


def slugify(value: str) -> str:
    lowered = value.lower()
    slug = re.sub(r"[^a-z0-9\u4e00-\u9fff]+", "-", lowered).strip("-")
    return slug or "signal"
