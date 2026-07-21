from __future__ import annotations

import json
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urldefrag, urljoin, urlparse
from urllib.request import Request, urlopen

from fintrace.extractor import EvidenceCandidate, _contains_term, extract_evidence_candidates, strip_html
from fintrace.schema import Signal

PAGE_LINK_TERMS = {
    "10-k",
    "10-q",
    "8-k",
    "annual report",
    "announcement",
    "earnings",
    "factsheet",
    "filing",
    "financial results",
    "financial statements",
    "investor presentation",
    "monthly report",
    "quarterly report",
    "results",
    "transcript",
    "业绩",
    "公告",
    "年报",
    "月报",
    "基金",
    "财报",
    "监管",
}


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


@dataclass(frozen=True)
class PageLink:
    title: str
    url: str
    score: int


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
    warnings: list[str] | None = None,
) -> list[IngestedEvidence]:
    query_terms = build_query_terms(signal, query=query)
    ingested: list[IngestedEvidence] = []

    for source in sources:
        try:
            documents = fetch_documents(source, limit=per_source_limit, query_terms=query_terms)
        except (OSError, ET.ParseError, UnicodeError, ValueError) as exc:
            if warnings is not None:
                warnings.append(f"Skipped source '{source.name}' ({source.url}): {exc}")
            continue
        for document in documents:
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


def fetch_documents(source: Source, *, limit: int = 8, query_terms: set[str] | None = None) -> list[Document]:
    raw = _read_url_or_file(source.url)
    if source.kind == "page":
        return parse_page(raw, source=source, limit=limit, query_terms=query_terms or set())
    return parse_feed(raw, source=source, limit=limit)


def parse_page(
    html_text: str,
    *,
    source: Source,
    limit: int = 8,
    query_terms: set[str] | None = None,
) -> list[Document]:
    parser = _PageParser()
    parser.feed(html_text)
    parser.close()
    page_title = parser.title or source.name
    main_text = _clean_page_text(parser.text_parts)
    documents = [Document(title=page_title, url=source.url, text=main_text, source=source)]

    terms = _page_discovery_terms(source=source, query_terms=query_terms or set())
    links = discover_page_links(parser.links, base_url=source.url, terms=terms, limit=max(0, limit - 1))
    for link in links:
        try:
            linked_raw = _read_url_or_file(link.url)
        except (OSError, UnicodeError, ValueError):
            continue
        linked_parser = _PageParser()
        linked_parser.feed(linked_raw)
        linked_parser.close()
        linked_text = _clean_page_text(linked_parser.text_parts) or strip_html(linked_raw)
        documents.append(
            Document(
                title=linked_parser.title or link.title,
                url=link.url,
                text=linked_text,
                source=source,
            )
        )
    return documents[:limit]


def discover_page_links(
    raw_links: list[tuple[str, str]],
    *,
    base_url: str,
    terms: set[str],
    limit: int = 6,
) -> list[PageLink]:
    links: list[PageLink] = []
    seen: set[str] = set()
    for href, label in raw_links:
        resolved = _resolve_link(base_url, href)
        if not resolved or resolved in seen:
            continue
        if not _is_fetchable_page_link(base_url, resolved):
            continue
        score = _score_link(label=label, url=resolved, terms=terms)
        if score <= 0:
            continue
        seen.add(resolved)
        links.append(PageLink(title=label or resolved, url=resolved, score=score))
    links.sort(key=lambda item: (item.score, len(item.title)), reverse=True)
    return links[:limit]


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
    terms.update(part for part in re.findall(r"[\u4e00-\u9fff\u3040-\u30ff\uac00-\ud7af]{2,}", text))
    if signal.ticker:
        terms.add(signal.ticker.lower())
    return terms


def score_relevance(document: Document, *, source: Source, query_terms: set[str]) -> int:
    text = f"{document.title} {document.text}".lower()
    if any(_contains_term(text, term.lower()) for term in source.exclude_terms):
        return 0

    score = 0
    score += sum(1 for term in query_terms if _contains_term(text, term.lower()))
    score += 2 * sum(1 for term in source.include_terms if _contains_term(text, term.lower()))
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


def _page_discovery_terms(*, source: Source, query_terms: set[str]) -> set[str]:
    terms = set(PAGE_LINK_TERMS)
    terms.update(query_terms)
    terms.update(item.lower() for item in source.include_terms)
    terms.update(item.lower() for item in source.support_terms)
    terms.update(item.lower() for item in source.counter_terms)
    terms.update(item.lower() for item in source.finance_terms)
    return {term for term in terms if term}


def _resolve_link(base_url: str, href: str) -> str | None:
    href = href.strip()
    if not href or href.startswith(("#", "mailto:", "tel:", "javascript:")):
        return None
    href, _fragment = urldefrag(href)
    parsed_base = urlparse(base_url)
    parsed_href = urlparse(href)
    if parsed_href.scheme:
        return href
    if parsed_base.scheme in {"http", "https"}:
        return urljoin(base_url, href)
    if parsed_base.scheme == "file":
        return str((Path(parsed_base.path).parent / href).resolve())
    return str((Path(base_url).parent / href).resolve())


def _is_fetchable_page_link(base_url: str, url: str) -> bool:
    parsed_base = urlparse(base_url)
    parsed = urlparse(url)
    if parsed.scheme in {"http", "https"}:
        if parsed_base.scheme in {"http", "https"} and parsed.netloc != parsed_base.netloc:
            return False
    elif parsed.scheme not in {"", "file"}:
        return False

    path = parsed.path.lower()
    if re.search(r"\.(jpg|jpeg|png|gif|webp|svg|zip|xlsx?|pptx?|docx?|mp4|mov|mp3)$", path):
        return False
    if re.search(r"\.(pdf)$", path):
        return False
    return True


def _score_link(*, label: str, url: str, terms: set[str]) -> int:
    haystack = f"{label} {url}".lower()
    score = 0
    score += sum(1 for term in terms if _contains_term(haystack, term.lower()))
    if re.search(r"(investor|ir|filing|results|earnings|factsheet|announcement|report)", haystack):
        score += 2
    if re.search(r"(login|privacy|terms|cookie|careers|contact|subscribe)", haystack):
        score -= 3
    return score


def _clean_page_text(parts: list[str]) -> str:
    raw_lines = []
    for part in parts:
        for line in part.splitlines():
            cleaned = re.sub(r"\s+", " ", line).strip()
            if cleaned:
                raw_lines.append(cleaned)

    lines: list[str] = []
    seen: set[str] = set()
    for line in raw_lines:
        lowered = line.lower()
        if lowered in seen:
            continue
        seen.add(lowered)
        if len(line) < 3:
            continue
        if re.fullmatch(r"[\W_]+", line):
            continue
        lines.append(line)
    return " ".join(lines)


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


class _PageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.title = ""
        self.text_parts: list[str] = []
        self.links: list[tuple[str, str]] = []
        self._skip_depth = 0
        self._section_skip_depth = 0
        self._in_title = False
        self._current_href: str | None = None
        self._current_anchor_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attrs_dict = {key.lower(): value for key, value in attrs if value is not None}
        if tag in {"script", "style", "noscript", "svg"}:
            self._skip_depth += 1
            return
        if tag in {"nav", "header", "footer", "aside", "form"}:
            self._section_skip_depth += 1
            return
        if tag == "title":
            self._in_title = True
            return
        if self._skip_depth or self._section_skip_depth:
            return
        if tag == "a":
            self._current_href = attrs_dict.get("href")
            self._current_anchor_parts = []
        if tag in {"p", "div", "section", "article", "li", "tr", "h1", "h2", "h3", "h4", "br"}:
            self.text_parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style", "noscript", "svg"} and self._skip_depth:
            self._skip_depth -= 1
            return
        if tag in {"nav", "header", "footer", "aside", "form"} and self._section_skip_depth:
            self._section_skip_depth -= 1
            return
        if tag == "title":
            self._in_title = False
            return
        if self._skip_depth or self._section_skip_depth:
            return
        if tag == "a" and self._current_href:
            label = re.sub(r"\s+", " ", " ".join(self._current_anchor_parts)).strip()
            self.links.append((self._current_href, label))
            self._current_href = None
            self._current_anchor_parts = []
        if tag in {"p", "div", "section", "article", "li", "tr", "h1", "h2", "h3", "h4"}:
            self.text_parts.append("\n")

    def handle_data(self, data: str) -> None:
        if self._skip_depth or self._section_skip_depth:
            return
        cleaned = re.sub(r"\s+", " ", data).strip()
        if not cleaned:
            return
        if self._in_title:
            self.title = f"{self.title} {cleaned}".strip()
            return
        if self._current_href is not None:
            self._current_anchor_parts.append(cleaned)
        self.text_parts.append(cleaned)
