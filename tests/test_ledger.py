from fintrace.ledger import add_evidence, evaluate_signal, record_evaluation, render_html_graph
from fintrace.schema import EvidenceKind, Signal, SignalStatus


def test_strengthened_signal_from_supporting_evidence():
    signal = Signal(title="Test", hypothesis="Demand is improving")
    add_evidence(
        signal,
        text="Revenue growth accelerated",
        source="Quarterly report",
        kind=EvidenceKind.SUPPORT,
        url=None,
        observed_at="2026-07-21",
        weight=1.2,
    )
    add_evidence(
        signal,
        text="Guidance increased",
        source="Earnings call",
        kind=EvidenceKind.SUPPORT,
        url=None,
        observed_at="2026-07-21",
        weight=1.0,
    )

    status, confidence, _ = evaluate_signal(signal)

    assert status == SignalStatus.STRENGTHENED
    assert confidence > 0.7


def test_record_evaluation_appends_update_event():
    signal = Signal(title="Test", hypothesis="Margins are stable")
    add_evidence(
        signal,
        text="Margins compressed materially",
        source="Quarterly report",
        kind=EvidenceKind.COUNTER,
        url=None,
        observed_at="2026-07-21",
        weight=2.2,
    )

    event = record_evaluation(signal)

    assert signal.status == SignalStatus.FALSIFIED
    assert event.current_status == SignalStatus.FALSIFIED
    assert len(signal.updates) == 1


def test_render_html_graph_contains_hypothesis_and_evidence():
    signal = Signal(title="Graph Test", hypothesis="Orders are improving")
    add_evidence(
        signal,
        text="Backlog increased",
        source="Company report",
        kind=EvidenceKind.SUPPORT,
        url="https://example.com/report",
        observed_at="2026-07-21",
        weight=1.0,
    )

    html = render_html_graph(signal)

    assert "<!doctype html>" in html
    assert "Orders are improving" in html
    assert "Backlog increased" in html
    assert "https://example.com/report" in html
