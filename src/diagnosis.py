"""Serializable contracts for preliminary territorial diagnosis results."""

import math
from dataclasses import dataclass, replace
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


def build_preliminary_diagnosis(
    area_name: str,
    area_ha: float,
    deforestation: object,
    source: str,
    status: EvidenceStatus,
) -> "DiagnosisResult":
    """Build a diagnosis summary from an already-ingested deforestation series."""
    series_index = getattr(deforestation, "index", ())
    if getattr(deforestation, "empty", False) or len(series_index) == 0:
        period = "período não informado"
    else:
        period = f"{min(series_index)}-{max(series_index)}"

    messages = {
        "ok": (
            "A série de desmatamento contém dados para análise preliminar.",
            "Revisar as evidências e confirmar a interpretação técnica.",
        ),
        "empty": (
            "Nenhum registro de desmatamento foi retornado para a área.",
            "Confirmar a cobertura e o período consultado antes de concluir.",
        ),
        "unavailable": (
            "A fonte de desmatamento não esteve disponível para esta consulta.",
            "Tentar novamente quando a fonte estiver disponível.",
        ),
    }
    summary, next_step = messages.get(status, ("", ""))
    evidence = Evidence(
        source=source,
        period=period,
        status=status,
        summary=summary,
        limitations=("A evidência depende da cobertura e disponibilidade da fonte.",),
    )
    return DiagnosisResult(
        area_name=area_name,
        area_ha=area_ha,
        evidences=(evidence,),
        limitations=(
            "Resultado preliminar e educacional; não substitui análise técnica ou jurídica.",
        ),
        next_steps=(next_step,),
    )


def add_overlap_evidence(
    diagnosis: "DiagnosisResult",
    source: str,
    period: str,
    overlap_summary: dict[str, object] | None,
    *,
    subject_label: str = "unidade territorial",
    available: bool = True,
) -> "DiagnosisResult":
    """Append a spatial-overlap observation without mutating the diagnosis."""
    _require_text(subject_label, "subject_label")
    if not available:
        status = "unavailable"
        summary = (
            f"A consulta da camada de {subject_label} esteve indisponível; "
            "quantidade, nomes e área sobreposta não puderam ser consultados."
        )
        evidence_limitations = (
            "Nenhuma sobreposição pôde ser verificada nesta consulta.",
        )
        limitation = "A camada consultada precisa ser verificada novamente."
        next_step = "Tentar novamente quando o serviço estiver disponível."
    else:
        summary_data = overlap_summary or {}
        count = int(summary_data.get("count", 0))
        area_ha = float(summary_data.get("overlap_area_ha", 0.0))
        names = [str(name) for name in summary_data.get("names", [])]
        if count > 0:
            status = "ok"
            names_text = ", ".join(names) if names else "não informados"
            summary = (
                f"{count} {subject_label}(s) sobreposta(s), com {area_ha:.2f} ha. "
                f"Nomes disponíveis: {names_text}."
            )
            evidence_limitations = (
                "A sobreposição é indicativa e deve ser confirmada em análise técnica.",
            )
            limitation = "O resultado considera apenas a camada ICMBio consultada."
            next_step = (
                "Revisar a geometria e os nomes com documentação técnica atualizada."
            )
        else:
            status = "empty"
            summary = (
                f"Nenhuma {subject_label} sobreposta foi encontrada na camada "
                f"consultada. Área sobreposta: {area_ha:.2f} ha. "
                "Nomes disponíveis: nenhum."
            )
            evidence_limitations = (
                "A ausência de sobreposição limita-se à camada e ao recorte consultados.",
            )
            limitation = "Outras fontes ou recortes territoriais não foram avaliados."
            next_step = (
                "Confirmar o recorte consultado e revisar fontes complementares."
            )

    evidence = Evidence(
        source=source,
        period=period,
        status=status,
        summary=summary,
        limitations=evidence_limitations,
    )
    return replace(
        diagnosis,
        evidences=diagnosis.evidences + (evidence,),
        limitations=diagnosis.limitations + (limitation,),
        next_steps=diagnosis.next_steps + (next_step,),
    )


def add_icmbio_evidence(
    diagnosis: "DiagnosisResult",
    source: str,
    period: str,
    overlap_summary: dict[str, object] | None,
    *,
    available: bool = True,
) -> "DiagnosisResult":
    """Append an ICMBio conservation-unit observation."""
    return add_overlap_evidence(
        diagnosis,
        source,
        period,
        overlap_summary,
        subject_label="UC federal",
        available=available,
    )


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
