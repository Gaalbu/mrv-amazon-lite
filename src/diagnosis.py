"""Serializable contracts for preliminary territorial diagnosis results."""

import math
from dataclasses import dataclass
from typing import Literal

EvidenceStatus = Literal["ok", "empty", "unavailable"]
_EVIDENCE_STATUSES = {"ok", "empty", "unavailable"}


def _require_text(value: str, field_name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty string")


def _require_text_tuple(values: tuple[str, ...], field_name: str) -> None:
    if not isinstance(values, tuple) or any(
        not isinstance(value, str) or not value.strip() for value in values
    ):
        raise ValueError(f"{field_name} must contain only non-empty strings")


@dataclass(frozen=True)
class Evidence:
    """A source-backed observation and its known limits."""

    source: str
    period: str
    status: EvidenceStatus
    summary: str
    limitations: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _require_text(self.source, "source")
        _require_text(self.period, "period")
        _require_text(self.summary, "summary")
        if self.status not in _EVIDENCE_STATUSES:
            raise ValueError("status must be one of: ok, empty, unavailable")
        _require_text_tuple(self.limitations, "limitations")

    def to_dict(self) -> dict[str, object]:
        return {
            "source": self.source,
            "period": self.period,
            "status": self.status,
            "summary": self.summary,
            "limitations": list(self.limitations),
        }


@dataclass(frozen=True)
class DiagnosisResult:
    """Minimal serializable result for a preliminary territorial diagnosis."""

    area_name: str
    area_ha: float
    evidences: tuple[Evidence, ...] = ()
    limitations: tuple[str, ...] = ()
    next_steps: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _require_text(self.area_name, "area_name")
        if (
            isinstance(self.area_ha, bool)
            or not isinstance(self.area_ha, (int, float))
            or not math.isfinite(self.area_ha)
            or self.area_ha < 0
        ):
            raise ValueError("area_ha must be a finite non-negative number")
        if not isinstance(self.evidences, tuple) or any(
            not isinstance(evidence, Evidence) for evidence in self.evidences
        ):
            raise ValueError("evidences must contain only Evidence instances")
        _require_text_tuple(self.limitations, "limitations")
        _require_text_tuple(self.next_steps, "next_steps")

    def to_dict(self) -> dict[str, object]:
        return {
            "area_name": self.area_name,
            "area_ha": self.area_ha,
            "evidences": [evidence.to_dict() for evidence in self.evidences],
            "limitations": list(self.limitations),
            "next_steps": list(self.next_steps),
        }
