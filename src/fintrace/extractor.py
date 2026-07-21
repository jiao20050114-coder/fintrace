from __future__ import annotations

import re
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path
from urllib.request import Request, urlopen

from fintrace.schema import EvidenceKind

SUPPORT_TERMS = {
    "accelerate",
    "accelerated",
    "accelerating",
    "beat",
    "beats",
    "expand",
    "expanded",
    "expanding",
    "growth",
    "grew",
    "higher",
    "improve",
    "improved",
    "improving",
    "increase",
    "increased",
    "increasing",
    "raised",
    "record",
    "resilient",
    "strong",
    "stronger",
    "upgraded",
    "上调",
    "创纪录",
    "增长",
    "增加",
    "好于预期",
    "强劲",
    "改善",
    "提升",
    "扩张",
    "订单增长",
    "売上高成長",
    "増加",
    "改善",
    "強い",
    "매출 성장",
    "증가",
    "개선",
    "강한",
}

COUNTER_TERMS = {
    "ban",
    "bottleneck",
    "challenging",
    "competition",
    "compression",
    "decline",
    "declined",
    "decrease",
    "decreased",
    "delay",
    "delayed",
    "downgraded",
    "fell",
    "headwind",
    "lower",
    "miss",
    "missed",
    "pressure",
    "restriction",
    "risk",
    "slowdown",
    "uncertain",
    "weaker",
    "下调",
    "下降",
    "放缓",
    "风险",
    "承压",
    "压力",
    "限制",
    "低于预期",
    "竞争加剧",
    "減少",
    "低下",
    "リスク",
    "圧力",
    "制限",
    "감소",
    "위험",
    "압박",
    "제한",
}

FINANCIAL_TERMS = {
    "backlog",
    "capex",
    "cash flow",
    "demand",
    "earnings",
    "ebitda",
    "free cash flow",
    "gross margin",
    "guidance",
    "inventory",
    "margin",
    "order",
    "orders",
    "profit",
    "revenue",
    "sales",
    "收入",
    "营收",
    "利润",
    "毛利率",
    "订单",
    "需求",
    "库存",
    "指引",
    "现金流",
    "売上高",
    "利益",
    "受注",
    "需要",
    "在庫",
    "가이던스",
    "매출",
    "수익",
    "주문",
    "수요",
    "재고",
}

NEGATION_PATTERNS = (
    "does not",
    "do not",
    "did not",
    "not discuss",
    "not indicate",
    "no evidence",
    "没有",
    "未显示",
    "未提及",
    "没有证据",
    "示していない",
    "언급하지",
)


@dataclass(frozen=True)
class EvidenceCandidate:
    text: str
    kind: EvidenceKind
    weight: float
    score: int


def read_source_text(*, text: str | None, file: str | None, url: str | None) -> str:
    provided = [value is not None for value in (text, file, url)].count(True)
    if provided != 1:
        raise ValueError("Provide exactly one of text, file, or url.")
    if text is not None:
        return text
    if file is not None:
        return Path(file).read_text(encoding="utf-8")
    if url is None:
        raise ValueError("URL is required.")
    request = Request(url, headers={"User-Agent": "FinTrace/0.2"})
    with urlopen(request, timeout=20) as response:
        content_type = response.headers.get("content-type", "")
        raw = response.read().decode(_encoding_from_content_type(content_type), errors="replace")
    if "html" in content_type.lower() or "<html" in raw[:500].lower():
        return strip_html(raw)
    return raw


def extract_evidence_candidates(
    text: str,
    *,
    max_items: int = 8,
    min_score: int = 1,
    support_terms: list[str] | None = None,
    counter_terms: list[str] | None = None,
    finance_terms: list[str] | None = None,
) -> list[EvidenceCandidate]:
    candidates: list[EvidenceCandidate] = []
    seen: set[str] = set()
    support_vocab = SUPPORT_TERMS | set(support_terms or [])
    counter_vocab = COUNTER_TERMS | set(counter_terms or [])
    finance_vocab = FINANCIAL_TERMS | set(finance_terms or [])

    for sentence in split_sentences(text):
        normalized = _normalize_space(sentence)
        if len(normalized) < 4 or normalized.lower() in seen:
            continue
        seen.add(normalized.lower())
        support_score = _term_score(normalized, support_vocab)
        counter_score = _term_score(normalized, counter_vocab)
        finance_score = _term_score(normalized, finance_vocab)
        score = max(support_score, counter_score) + finance_score
        if score < min_score:
            continue

        if support_score > counter_score:
            kind = EvidenceKind.SUPPORT
        elif counter_score > support_score:
            kind = EvidenceKind.COUNTER
        else:
            kind = EvidenceKind.NEUTRAL
        if kind == EvidenceKind.SUPPORT and any(pattern in normalized.lower() for pattern in NEGATION_PATTERNS):
            kind = EvidenceKind.NEUTRAL

        weight = min(2.0, 0.7 + (0.2 * score))
        candidates.append(
            EvidenceCandidate(
                text=normalized,
                kind=kind,
                weight=round(weight, 2),
                score=score,
            )
        )

    candidates.sort(key=lambda item: (item.score, item.weight), reverse=True)
    return candidates[:max_items]


def split_sentences(text: str) -> list[str]:
    normalized = _normalize_space(text)
    if not normalized:
        return []
    return [
        item.strip()
        for item in re.split(r"(?<=[.!?。！？；;])\s*|[，、]\s*|[\r\n]+", normalized)
        if item.strip()
    ]


def strip_html(html: str) -> str:
    parser = _TextExtractor()
    parser.feed(html)
    return _normalize_space(" ".join(parser.parts))


def _term_score(text: str, terms: set[str]) -> int:
    lowered = text.lower()
    return sum(1 for term in terms if _contains_term(lowered, term.lower()))


def _contains_term(text: str, term: str) -> bool:
    if not term:
        return False
    if re.search(r"[\u4e00-\u9fff\u3040-\u30ff\uac00-\ud7af]", term):
        return term in text or _ordered_cjk_match(text, term)
    return re.search(rf"(?<![a-z0-9]){re.escape(term)}(?![a-z0-9])", text) is not None


def _ordered_cjk_match(text: str, term: str) -> bool:
    chars = [char for char in term if re.search(r"[\u4e00-\u9fff\u3040-\u30ff\uac00-\ud7af]", char)]
    if len(chars) < 3:
        return False
    pattern = ".*".join(re.escape(char) for char in chars)
    return re.search(pattern, text) is not None


def _normalize_space(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _encoding_from_content_type(content_type: str) -> str:
    match = re.search(r"charset=([\w-]+)", content_type, flags=re.IGNORECASE)
    return match.group(1) if match else "utf-8"


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []
        self._skip_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"script", "style", "noscript"}:
            self._skip_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style", "noscript"} and self._skip_depth:
            self._skip_depth -= 1

    def handle_data(self, data: str) -> None:
        if not self._skip_depth:
            self.parts.append(data)
