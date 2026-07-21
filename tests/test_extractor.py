from fintrace.extractor import extract_evidence_candidates, split_sentences, strip_html
from fintrace.schema import EvidenceKind


def test_extract_evidence_candidates_classifies_support_and_counter():
    text = (
        "Revenue growth accelerated as cloud capex increased. "
        "Export restrictions remain a headwind and could pressure sales."
    )

    candidates = extract_evidence_candidates(text, max_items=4)

    kinds = {candidate.kind for candidate in candidates}
    assert EvidenceKind.SUPPORT in kinds
    assert EvidenceKind.COUNTER in kinds
    assert candidates[0].score >= candidates[-1].score


def test_split_sentences_handles_compact_text():
    sentences = split_sentences("Orders increased. Margins declined.")

    assert sentences == ["Orders increased.", "Margins declined."]


def test_strip_html_removes_script_content():
    text = strip_html("<html><script>ignore()</script><body>Revenue growth improved.</body></html>")

    assert "Revenue growth improved" in text
    assert "ignore" not in text


def test_negated_support_sentence_is_neutral():
    candidates = extract_evidence_candidates(
        "The update does not discuss AI infrastructure demand, revenue, or capex."
    )

    assert candidates[0].kind == EvidenceKind.NEUTRAL


def test_extract_chinese_support_and_counter_evidence():
    text = "公司订单增长，收入改善，需求强劲。行业竞争加剧，毛利率承压。"

    candidates = extract_evidence_candidates(text, max_items=4)

    kinds = {candidate.kind for candidate in candidates}
    assert EvidenceKind.SUPPORT in kinds
    assert EvidenceKind.COUNTER in kinds


def test_extract_japanese_support_evidence():
    candidates = extract_evidence_candidates("売上高成長が続き、需要も強い。")

    assert candidates[0].kind == EvidenceKind.SUPPORT


def test_custom_multilingual_terms_are_used():
    candidates = extract_evidence_candidates(
        "客户续约率明显改善。",
        support_terms=["续约率改善"],
        finance_terms=["客户"],
    )

    assert candidates[0].kind == EvidenceKind.SUPPORT
