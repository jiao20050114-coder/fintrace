from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timezone
from enum import StrEnum
from typing import Any
from uuid import uuid4


class SignalStatus(StrEnum):
    DRAFT = "draft"
    ACTIVE = "active"
    STRENGTHENED = "strengthened"
    WEAKENED = "weakened"
    FALSIFIED = "falsified"


class EvidenceKind(StrEnum):
    SUPPORT = "support"
    COUNTER = "counter"
    NEUTRAL = "neutral"


@dataclass
class Evidence:
    text: str
    source: str
    kind: EvidenceKind = EvidenceKind.SUPPORT
    url: str | None = None
    reason: str | None = None
    observed_at: str = field(default_factory=lambda: date.today().isoformat())
    weight: float = 1.0
    id: str = field(default_factory=lambda: f"ev_{uuid4().hex[:10]}")

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Evidence":
        return cls(
            id=data.get("id") or f"ev_{uuid4().hex[:10]}",
            text=str(data["text"]),
            source=str(data["source"]),
            kind=EvidenceKind(data.get("kind", EvidenceKind.SUPPORT)),
            url=data.get("url"),
            reason=data.get("reason"),
            observed_at=str(data.get("observed_at") or date.today().isoformat()),
            weight=float(data.get("weight", 1.0)),
        )

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["kind"] = self.kind.value
        return data


@dataclass
class WatchItem:
    metric: str
    why: str
    source_hint: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "WatchItem":
        return cls(
            metric=str(data["metric"]),
            why=str(data["why"]),
            source_hint=data.get("source_hint"),
        )


@dataclass
class UpdateEvent:
    previous_status: SignalStatus
    current_status: SignalStatus
    summary: str
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "UpdateEvent":
        return cls(
            previous_status=SignalStatus(data["previous_status"]),
            current_status=SignalStatus(data["current_status"]),
            summary=str(data["summary"]),
            created_at=str(data["created_at"]),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "previous_status": self.previous_status.value,
            "current_status": self.current_status.value,
            "summary": self.summary,
            "created_at": self.created_at,
        }


@dataclass
class Signal:
    title: str
    hypothesis: str
    topic: str | None = None
    ticker: str | None = None
    status: SignalStatus = SignalStatus.DRAFT
    confidence: float = 0.0
    evidence: list[Evidence] = field(default_factory=list)
    watchlist: list[WatchItem] = field(default_factory=list)
    updates: list[UpdateEvent] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    id: str = field(default_factory=lambda: f"sig_{uuid4().hex[:10]}")

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Signal":
        return cls(
            id=data.get("id") or f"sig_{uuid4().hex[:10]}",
            title=str(data["title"]),
            hypothesis=str(data["hypothesis"]),
            topic=data.get("topic"),
            ticker=data.get("ticker"),
            status=SignalStatus(data.get("status", SignalStatus.DRAFT)),
            confidence=float(data.get("confidence", 0.0)),
            evidence=[Evidence.from_dict(item) for item in data.get("evidence", [])],
            watchlist=[WatchItem.from_dict(item) for item in data.get("watchlist", [])],
            updates=[UpdateEvent.from_dict(item) for item in data.get("updates", [])],
            created_at=str(data.get("created_at") or datetime.now(timezone.utc).isoformat()),
            updated_at=str(data.get("updated_at") or datetime.now(timezone.utc).isoformat()),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "hypothesis": self.hypothesis,
            "topic": self.topic,
            "ticker": self.ticker,
            "status": self.status.value,
            "confidence": round(self.confidence, 4),
            "evidence": [item.to_dict() for item in self.evidence],
            "watchlist": [asdict(item) for item in self.watchlist],
            "updates": [item.to_dict() for item in self.updates],
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }
