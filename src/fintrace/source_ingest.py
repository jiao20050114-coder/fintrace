from __future__ import annotations

import json
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from fintrace.extractor import EvidenceCandidate, extract_evidence_candidates, strip_html
from fintrace.schema import EvidenceKind, Signal


@dataclass(frozen=True)
class Source:
    id: str
    name: str
    url: str
    kind: str = "feed"
    reliability: float = 0.7
    include_terms: list[str] = field(default_factory=list)
    exclude_terms: list[str] = field(default_factory=list)
    support_terms: list[str] = field(default_factory=list)
    counter_terms: list[str] = field(default_factory=list)
    finance_terms: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, object], *, base_dir: Path | None = None) -> "Source":
        url = str(data["url"])
        if base_dir is not None:
            parsed = urlparse(url)
            if parsed.scheme == "" and not Path(url).is_absolute():
                url = str(base_dir / url)
        return cls(
            id=str(data["id"]),
            name=str(data["name"]),
            url=url,
            kind=str(data.get("kind", "feed")),
            reliability=float(data.get("reliability", 0.7)),
            include_terms=[str(item) for item in data.get("include_terms", [])],
            exclude_terms=[str(item) for item in data.get("exclude_terms", [])],
            support_terms=[str(item) for item in data.get("support_terms", [])],
            counter_terms=[str(item) for item in data.get("counter_terms", [])],
            finance_terms=[str(item) for item in data.get("finance_terms", [])],
        )


@dataclass(frozen=True)
class Document:
    title: str
    url: str | None
    text: str
    source: Source


@dataclass(frozen=True)
class IngestedEvidence:
    candidate: EvidenceCandidate
    source: Source
    document_title: str
    document_url: str | None
    relevance_score: int
    adjusted_weight: float


def load_sources(path: str | Path) -> list[Source]:
    source_path = Path(path)
    data = json.loads(source_path.read_text(encoding="utf-8"))
    raw_sources = data["sources"] if isinstance(data, dict) and "sources" in data else data
    return [Source.from_dict(item, base_dir=source_path.parent) for item in raw_sources]


def ingest_sources(
    signal: Signal,
    sources: list[Source],
    *,
    query: str | None = None,
    max_items: int = 12,
    per_source_limit: int = 8,
    min_score: int = 1,
) -> list[IngestedEvidence]:
    query_terms = build_query_terms(signal, query=query)
    ingested: list[IngestedEvidence] = []

    for source in sources:
        for document in fetch_documents(source, limit=per_source_limit):
            relevance_score = score_relevance(document, source=source, query_terms=query_terms)
            if relevance_score <= 0:
                continue
            for candidate in extract_evidence_candidates(
                document.text,
                max_items=3,
                min_score=min_score,
                support_terms=source.support_terms,
                counter_terms=source.counter_terms,
                finance_terms=source.finance_terms,
            ):
                adjusted_weight = min(
                    2.0,
                    round(candidate.weight * (0.75 + (0.45 * source.reliability)), 2),
                )
                ingested.append(
                    IngestedEvidence(
                        candidate=candidate,
                        source=source,
                        document_title=document.title,
                        document_url=document.url,
                        relevance_score=relevance_score + candidate.score,
                        adjusted_weight=adjusted_weight,
                    )
                )

    ingested.sort(
        key=lambda item: (
            item.relevance_score,
            item.source.reliability,
            item.adjusted_weight,
        ),
        reverse=True,
    )
    return _dedupe_ingested(ingested)[:max_items]


def fetch_documents(source: Source, *, limit: int = 8) -> list[Document]:
    raw = _read_url_or_file(source.url)
    if source.kind == "page":
        return [Document(title=source.name, url=source.url, text=strip_html(raw), source=source)]
    return parse_feed(raw, source=source, limit=limit)


def parse_feed(xml_text: str, *, source: Source, limit: int = 8) -> list[Document]:
    root = ET.fromstring(xml_text)
    items = root.findall(".//item")
    if not items:
        items = root.findall(".//{*}entry")

    documents: list[Document] = []
    for item in items[:limit]:
        title = _find_text(item, ["title"]) or source.name
        link = _find_text(item, ["link"]) or _find_atom_link(item)
        summary = (
            _find_text(item, ["description"])
            or _find_text(item, ["summary"])
            or _find_text(item, ["content"])
            or ""
        )
        text = strip_html(summary or title)
        documents.append(Document(title=title, url=link, text=text, source=source))
    return documents


def build_query_terms(signal: Signal, *, query: str | None = None) -> set[str]:
    raw_parts = [
        signal.title,
        signal.hypothesis,
        signal.topic or "",
        signal.ticker or "",
        " ".join(item.metric for item in signal.watchlist),
        query or "",
    ]
    text = " ".join(raw_parts).lower()
    terms = {part for part in re.findall(r"[a-zA-Z0-9][a-zA-Z0-9-]{2,}", text)}
    if signal.ticker:
        terms.add(signal.ticker.lower())
    return terms


def score_relevance(document: Document, *, source: Source, query_terms: set[str]) -> int:
    text = f"{document.title} {document.text}".lower()
    if any(term.lower() in text for term in source.exclude_terms):
        return 0

    score = 0
    score += sum(1 for term in query_terms if term in text)
    score += 2 * sum(1 for term in source.include_terms if term.lower() in text)
    score += int(source.reliability * 3)
    return score


def _read_url_or_file(location: str) -> str:
    parsed = urlparse(location)
    if parsed.scheme in {"", "file"}:
        path = Path(parsed.path if parsed.scheme == "file" else location)
        return path.read_text(encoding="utf-8")
    request = Request(location, headers={"User-Agent": "FinTrace/0.3"})
    with urlopen(request, timeout=25) as response:
        content_type = response.headers.get("content-type", "")
        raw = response.read()
    encoding = _encoding_from_content_type(content_type)
    return raw.decode(encoding, errors="replace")


def _find_text(item: ET.Element, names: list[str]) -> str | None:
    for name in names:
        found = item.find(name)
        if found is None:
            found = item.find(f"{{*}}{name}")
        if found is not None and found.text:
            return found.text.strip()
    return None


def _find_atom_link(item: ET.Element) -> str | None:
    for link in item.findall("{*}link"):
        href = link.attrib.get("href")
        if href:
            return href
    return None


def _encoding_from_content_type(content_type: str) -> str:
    match = re.search(r"charset=([\w-]+)", content_type, flags=re.IGNORECASE)
    return match.group(1) if match else "utf-8"


def _dedupe_ingested(items: list[IngestedEvidence]) -> list[IngestedEvidence]:
    seen: set[str] = set()
    deduped: list[IngestedEvidence] = []
    for item in items:
        key = item.candidate.text.lower()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    return deduped
