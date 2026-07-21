from __future__ import annotations

import json
import re
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import parse_qs, quote_plus, unquote, urlparse
from urllib.request import Request, urlopen

from fintrace.brief import build_source_plan, infer_include_terms, infer_subject, infer_ticker, infer_topic, slugify

REGULATOR_DOMAINS = {
    "sec.gov",
    "hkex.com.hk",
    "hkexnews.hk",
    "fca.org.uk",
    "mas.gov.sg",
    "sfc.hk",
    "esma.europa.eu",
}

REPUTABLE_NEWS_DOMAINS = {
    "reuters.com",
    "bloomberg.com",
    "ft.com",
    "wsj.com",
    "cnbc.com",
    "marketwatch.com",
    "nikkei.com",
    "asia.nikkei.com",
    "theedgemalaysia.com",
}

WEAK_SOURCE_DOMAINS = {
    "reddit.com",
    "x.com",
    "twitter.com",
    "facebook.com",
    "linkedin.com",
    "medium.com",
    "substack.com",
}

OFFICIAL_PATH_TERMS = {
    "investor",
    "investors",
    "ir",
    "financial-results",
    "results",
    "annual-report",
    "reports",
    "filings",
    "announcements",
    "newsroom",
    "press",
    "factsheet",
}


@dataclass(frozen=True)
class SearchResult:
    title: str
    url: str
    snippet: str
    query: str


@dataclass(frozen=True)
class CandidateSource:
    id: str
    name: str
    url: str
    kind: str
    reliability: float
    category: str
    reasons: list[str]
    query: str
    snippet: str


@dataclass(frozen=True)
class DiscoveryResult:
    registry: dict[str, object]
    candidates: list[CandidateSource]
    warnings: list[str]
    search_queries: list[str]


def discover_sources(
    brief: str,
    *,
    title: str | None = None,
    topic: str | None = None,
    ticker: str | None = None,
    max_results: int = 12,
    max_queries: int = 4,
    search_htmls: list[str] | None = None,
) -> DiscoveryResult:
    subject = title or infer_subject(brief)
    inferred_topic = topic or infer_topic(brief, subject)
    inferred_ticker = ticker or infer_ticker(brief)
    include_terms = infer_include_terms(brief, subject=subject, ticker=inferred_ticker)
    plan = build_source_plan(
        user_brief=brief,
        subject=subject,
        topic=inferred_topic,
        ticker=inferred_ticker,
        include_terms=include_terms,
    )
    queries = plan.search_queries[:max_queries]
    warnings: list[str] = []
    raw_results: list[SearchResult] = []

    if search_htmls:
        for index, html_text in enumerate(search_htmls[:max_queries]):
            query = queries[index] if index < len(queries) else subject
            raw_results.extend(parse_search_results(html_text, query=query))
    else:
        for query in queries:
            try:
                raw_results.extend(fetch_search_results(query))
            except (OSError, UnicodeError, ValueError) as exc:
                warnings.append(f"Search failed for '{query}': {exc}")

    candidates = rank_candidate_sources(
        raw_results,
        subject=subject,
        topic=inferred_topic,
        ticker=inferred_ticker,
        include_terms=include_terms,
        max_results=max_results,
    )
    registry = build_discovery_registry(
        candidates,
        subject=subject,
        topic=inferred_topic,
        ticker=inferred_ticker,
        include_terms=include_terms,
        search_queries=queries,
        warnings=warnings,
    )
    return DiscoveryResult(
        registry=registry,
        candidates=candidates,
        warnings=warnings,
        search_queries=queries,
    )


def fetch_search_results(query: str, *, max_results: int = 10) -> list[SearchResult]:
    encoded = quote_plus(query)
    last_error: Exception | None = None
    for url in (
        f"https://html.duckduckgo.com/html/?q={encoded}",
        f"https://duckduckgo.com/html/?q={encoded}",
        f"https://www.bing.com/search?q={encoded}",
    ):
        request = Request(
            url,
            headers={
                "User-Agent": "FinTrace/0.10 (+https://github.com/jiao20050114-coder/fintrace)",
            },
        )
        try:
            with urlopen(request, timeout=10) as response:
                raw = response.read()
                content_type = response.headers.get("content-type", "")
        except OSError as exc:
            last_error = exc
            continue
        encoding = _encoding_from_content_type(content_type)
        html_text = raw.decode(encoding, errors="replace")
        results = parse_search_results(html_text, query=query)[:max_results]
        if results:
            return results
    if last_error:
        raise last_error
    return []


def parse_search_results(html_text: str, *, query: str) -> list[SearchResult]:
    parser = _SearchParser()
    parser.feed(html_text)
    parser.close()

    results: list[SearchResult] = []
    seen: set[str] = set()
    for link in parser.links:
        url = unwrap_search_url(link.href)
        if not url or url in seen or not _is_http_url(url):
            continue
        if _looks_like_search_chrome(url):
            continue
        seen.add(url)
        results.append(
            SearchResult(
                title=link.text or _domain_label(url),
                url=url,
                snippet="",
                query=query,
            )
        )
    return results


def unwrap_search_url(url: str) -> str | None:
    url = url.strip()
    if not url:
        return None
    parsed = urlparse(url)
    query = parse_qs(parsed.query)
    if "uddg" in query and query["uddg"]:
        return unquote(query["uddg"][0])
    if parsed.netloc.endswith("duckduckgo.com") and parsed.path.startswith("/l/"):
        target = query.get("uddg", [""])[0]
        return unquote(target) if target else None
    if url.startswith("//duckduckgo.com/l/"):
        return unwrap_search_url(f"https:{url}")
    return url


def rank_candidate_sources(
    results: list[SearchResult],
    *,
    subject: str,
    topic: str,
    ticker: str | None,
    include_terms: list[str],
    max_results: int,
) -> list[CandidateSource]:
    candidates: list[CandidateSource] = []
    seen: set[str] = set()
    used_ids: set[str] = set()
    for result in results:
        normalized = _normalize_url(result.url)
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        reliability, category, reasons = score_source_reliability(
            normalized,
            title=result.title,
            snippet=result.snippet,
            subject=subject,
            topic=topic,
            ticker=ticker,
        )
        if reliability < 0.5:
            continue
        source_name = _clean_source_name(result.title, normalized)
        source_id = _unique_id(slugify(_domain_label(normalized) + " " + source_name), used_ids)
        candidates.append(
            CandidateSource(
                id=source_id,
                name=source_name,
                url=normalized,
                kind=_kind_from_url(normalized),
                reliability=reliability,
                category=category,
                reasons=reasons,
                query=result.query,
                snippet=result.snippet,
            )
        )

    candidates.sort(key=lambda item: (item.reliability, _source_specificity(item.url)), reverse=True)
    return candidates[:max_results]


def score_source_reliability(
    url: str,
    *,
    title: str = "",
    snippet: str = "",
    subject: str = "",
    topic: str = "",
    ticker: str | None = None,
) -> tuple[float, str, list[str]]:
    parsed = urlparse(url)
    domain = _registrable_domain(parsed.netloc)
    path = parsed.path.lower()
    haystack = f"{title} {snippet} {url}".lower()
    subject_terms = [term.lower() for term in re.findall(r"[A-Za-z0-9][A-Za-z0-9&.-]{2,}", subject)]
    compact_domain = re.sub(r"[^a-z0-9]", "", domain)
    compact_subject = "".join(re.sub(r"[^a-z0-9]", "", term) for term in subject_terms)
    reasons: list[str] = []
    score = 0.55
    category = "candidate"

    if domain in REGULATOR_DOMAINS or domain.endswith(".gov"):
        score = 0.96
        category = "regulator_or_exchange"
        reasons.append("regulator or exchange domain")
    elif any(term in path for term in OFFICIAL_PATH_TERMS):
        score = 0.86
        category = "official_or_primary"
        reasons.append("official-looking IR, filing, report, or announcement path")
    elif domain in REPUTABLE_NEWS_DOMAINS:
        score = 0.78
        category = "reputable_news"
        reasons.append("recognized financial news domain")
    elif domain in WEAK_SOURCE_DOMAINS:
        score = 0.35
        category = "weak_secondary"
        reasons.append("social, commentary, or user-generated source")

    subject_match = any(term and term in domain.replace("-", "") for term in subject_terms) or any(
        term and term in haystack for term in subject_terms
    )
    if category == "candidate" and "official" in haystack and subject_match:
        score = 0.84
        category = "official_or_primary"
        reasons.append("official-looking result for the subject")
    if category == "candidate" and compact_subject and compact_subject in compact_domain:
        score = 0.84
        category = "official_or_primary"
        reasons.append("domain strongly resembles subject")
    if any(term and term in domain.replace("-", "") for term in subject_terms):
        score += 0.07
        reasons.append("domain resembles subject")
    if any(term and term in haystack for term in subject_terms):
        score += 0.03
        reasons.append("result text mentions subject")
    if category == "candidate" and subject_terms and not any(term and term in haystack for term in subject_terms):
        score -= 0.08
        reasons.append("result text does not mention subject")
    if ticker and ticker.lower() in haystack:
        score += 0.03
        reasons.append("result text mentions ticker")
    if re.search(r"(sponsored|advertisement|coupon|jobs|career|privacy|login)", haystack):
        score -= 0.18
        reasons.append("possible low-signal or non-evidence page")
    if re.search(r"(pdf|annual-report|factsheet|filing|10-k|10-q|8-k|results|earnings|announcement)", haystack):
        score += 0.04
        reasons.append("URL/title points to evidence-bearing material")
    if "reputable financial news" in topic.lower() and domain in REPUTABLE_NEWS_DOMAINS:
        score += 0.02

    score = max(0.0, min(0.99, round(score, 2)))
    if not reasons:
        reasons.append("generic web candidate; agent should verify before import")
    return score, category, reasons


def build_discovery_registry(
    candidates: list[CandidateSource],
    *,
    subject: str,
    topic: str,
    ticker: str | None,
    include_terms: list[str],
    search_queries: list[str],
    warnings: list[str],
) -> dict[str, object]:
    sources = [
        {
            "id": candidate.id,
            "name": candidate.name,
            "kind": candidate.kind,
            "url": candidate.url,
            "reliability": candidate.reliability,
            "include_terms": include_terms[:12],
            "exclude_terms": ["rumor", "sponsored", "advertisement", "coupon", "jobs"],
            "discovery": {
                "query": candidate.query,
                "category": candidate.category,
                "reasons": candidate.reasons,
            },
        }
        for candidate in candidates
    ]
    return {
        "sources": sources,
        "source_discovery": {
            "subject": subject,
            "topic": topic,
            "ticker": ticker,
            "search_queries": search_queries,
            "warnings": warnings,
            "note": "Review discovered sources before applying evidence. Use ingest for screening and import-evidence after semantic reading.",
        },
    }


def write_discovery_registry(path: str | Path, registry: dict[str, object]) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(registry, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _normalize_url(url: str) -> str:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        return ""
    return parsed._replace(fragment="").geturl()


def _kind_from_url(url: str) -> str:
    lowered = url.lower()
    if lowered.endswith((".xml", ".rss", ".atom")) or "rss" in lowered:
        return "feed"
    return "page"


def _source_specificity(url: str) -> int:
    parsed = urlparse(url)
    score = len([part for part in parsed.path.split("/") if part])
    if re.search(r"(filing|results|earnings|factsheet|annual|announcement|report)", parsed.path.lower()):
        score += 3
    return score


def _domain_label(url: str) -> str:
    parsed = urlparse(url)
    domain = _registrable_domain(parsed.netloc)
    return domain or parsed.netloc or "source"


def _clean_source_name(title: str, url: str) -> str:
    cleaned = re.sub(r"\s+", " ", title).strip(" -|")
    domain = _domain_label(url)
    if not cleaned:
        return domain
    if "http" in cleaned.lower() or "›" in cleaned or len(cleaned) > 96:
        return domain
    return cleaned[:96]


def _registrable_domain(netloc: str) -> str:
    host = netloc.lower().split("@")[-1].split(":")[0]
    if host.startswith("www."):
        host = host[4:]
    return host


def _is_http_url(url: str) -> bool:
    return urlparse(url).scheme in {"http", "https"}


def _looks_like_search_chrome(url: str) -> bool:
    parsed = urlparse(url)
    domain = _registrable_domain(parsed.netloc)
    return domain in {"duckduckgo.com", "google.com", "bing.com"} or parsed.path in {"", "/html/"}


def _unique_id(base: str, used: set[str]) -> str:
    candidate = base[:80] or "source"
    if candidate not in used:
        used.add(candidate)
        return candidate
    index = 2
    while f"{candidate}-{index}" in used:
        index += 1
    unique = f"{candidate}-{index}"
    used.add(unique)
    return unique


def _encoding_from_content_type(content_type: str) -> str:
    match = re.search(r"charset=([\w-]+)", content_type, flags=re.IGNORECASE)
    return match.group(1) if match else "utf-8"


@dataclass(frozen=True)
class _ParsedLink:
    href: str
    text: str


class _SearchParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[_ParsedLink] = []
        self._href: str | None = None
        self._parts: list[str] = []
        self._skip_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"script", "style", "noscript"}:
            self._skip_depth += 1
            return
        if self._skip_depth:
            return
        if tag == "a":
            attrs_dict = {key.lower(): value for key, value in attrs if value is not None}
            self._href = attrs_dict.get("href")
            self._parts = []

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style", "noscript"} and self._skip_depth:
            self._skip_depth -= 1
            return
        if self._skip_depth:
            return
        if tag == "a" and self._href:
            text = re.sub(r"\s+", " ", " ".join(self._parts)).strip()
            self.links.append(_ParsedLink(href=self._href, text=text))
            self._href = None
            self._parts = []

    def handle_data(self, data: str) -> None:
        if self._skip_depth or self._href is None:
            return
        cleaned = re.sub(r"\s+", " ", data).strip()
        if cleaned:
            self._parts.append(cleaned)
