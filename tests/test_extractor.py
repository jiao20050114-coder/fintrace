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
