import json

import pytest

from fintrace.agent_import import import_agent_evidence, load_agent_evidence
from fintrace.schema import EvidenceKind, Signal, SignalStatus


def test_load_agent_evidence_accepts_wrapped_object(tmp_path):
    path = tmp_path / "evidence.json"
    path.write_text(json.dumps({"evidence": [{"text": "Revenue grew"}]}), encoding="utf-8")

    items = load_agent_evidence(path)

    assert items == [{"text": "Revenue grew"}]


def test_load_agent_evidence_accepts_array(tmp_path):
    path = tmp_path / "evidence.json"
    path.write_text(json.dumps([{"text": "Revenue grew"}]), encoding="utf-8")

    items = load_agent_evidence(path)

    assert items == [{"text": "Revenue grew"}]


def test_import_agent_evidence_appends_reason_and_evaluates():
    signal = Signal(title="Agent Signal", hypothesis="Demand is improving")
    result = import_agent_evidence(
        signal,
        [
            {
                "kind": "support",
                "text": "Revenue growth accelerated.",
                "source": "Agent source",
                "weight": 2.0,
                "reason": "This directly supports the demand thesis.",
            }
        ],
        evaluate=True,
    )

    assert len(result.evidence) == 1
    assert signal.evidence[0].kind == EvidenceKind.SUPPORT
    assert signal.evidence[0].reason == "This directly supports the demand thesis."
    assert result.update_event is not None
    assert signal.status == SignalStatus.STRENGTHENED


def test_import_agent_evidence_requires_text():
    signal = Signal(title="Agent Signal", hypothesis="Demand is improving")

    with pytest.raises(ValueError, match="text"):
        import_agent_evidence(signal, [{"kind": "support"}])


def test_import_agent_evidence_rejects_out_of_range_weight():
    signal = Signal(title="Agent Signal", hypothesis="Demand is improving")

    with pytest.raises(ValueError, match="between 0 and 2"):
        import_agent_evidence(
            signal,
            [{"kind": "support", "text": "Revenue grew.", "source": "Agent", "weight": 9.0}],
        )


def test_import_agent_evidence_dedupes_by_default():
    signal = Signal(title="Agent Signal", hypothesis="Demand is improving")
    item = {
        "kind": "support",
        "text": "Revenue growth accelerated.",
        "source": "Agent source",
        "weight": 1.0,
    }

    first = import_agent_evidence(signal, [item])
    second = import_agent_evidence(signal, [item])

    assert len(first.evidence) == 1
    assert len(second.evidence) == 0
    assert len(signal.evidence) == 1


def test_import_agent_evidence_can_allow_duplicates():
    signal = Signal(title="Agent Signal", hypothesis="Demand is improving")
    item = {
        "kind": "support",
        "text": "Revenue growth accelerated.",
        "source": "Agent source",
        "weight": 1.0,
    }

    import_agent_evidence(signal, [item])
    second = import_agent_evidence(signal, [item], dedupe=False)

    assert len(second.evidence) == 1
    assert len(signal.evidence) == 2
