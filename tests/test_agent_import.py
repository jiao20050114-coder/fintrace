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
    assert "Reason:" in signal.evidence[0].text
    assert result.update_event is not None
    assert signal.status == SignalStatus.STRENGTHENED


def test_import_agent_evidence_requires_text():
    signal = Signal(title="Agent Signal", hypothesis="Demand is improving")

    with pytest.raises(ValueError, match="text"):
        import_agent_evidence(signal, [{"kind": "support"}])
