from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from fintrace.ledger import add_evidence, record_evaluation
from fintrace.schema import Evidence, EvidenceKind, Signal, UpdateEvent


@dataclass(frozen=True)
class ImportResult:
    evidence: list[Evidence]
    update_event: UpdateEvent | None


def load_agent_evidence(path: str | Path) -> list[dict[str, Any]]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(data, list):
        raw_items = data
    elif isinstance(data, dict) and isinstance(data.get("evidence"), list):
        raw_items = data["evidence"]
    else:
        raise ValueError("Evidence JSON must be an array or an object with an 'evidence' array.")
    if not all(isinstance(item, dict) for item in raw_items):
        raise ValueError("Every evidence item must be an object.")
    return raw_items


def import_agent_evidence(
    signal: Signal,
    items: list[dict[str, Any]],
    *,
    default_source: str | None = None,
    dedupe: bool = True,
    evaluate: bool = False,
) -> ImportResult:
    imported: list[Evidence] = []
    existing = {_dedupe_key(item.text, item.source, item.url) for item in signal.evidence}
    for item in items:
        text = _required_str(item, "text")
        reason = str(item.get("reason", "")).strip()
        source = str(item.get("source") or default_source or "Agent import")
        url = item.get("url")
        key = _dedupe_key(text, source, url)
        if dedupe and key in existing:
            continue
        evidence = add_evidence(
            signal,
            text=text,
            source=source,
            kind=EvidenceKind(str(item.get("kind", EvidenceKind.NEUTRAL))),
            url=url,
            observed_at=item.get("observed_at"),
            weight=_coerce_weight(item.get("weight", 1.0)),
            reason=reason or None,
        )
        imported.append(evidence)
        existing.add(key)

    update_event = record_evaluation(signal) if evaluate and imported else None
    return ImportResult(evidence=imported, update_event=update_event)


def _required_str(item: dict[str, Any], key: str) -> str:
    value = item.get(key)
    if value is None or not str(value).strip():
        raise ValueError(f"Evidence item is missing required field '{key}'.")
    return str(value).strip()


def _dedupe_key(text: str, source: str, url: object) -> tuple[str, str, str]:
    return (text.strip().lower(), source.strip().lower(), str(url or "").strip())


def _coerce_weight(value: object) -> float:
    weight = float(value)
    if weight < 0 or weight > 2:
        raise ValueError("Evidence weight must be between 0 and 2.")
    return weight
