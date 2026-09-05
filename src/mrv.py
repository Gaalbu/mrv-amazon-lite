"""Traceable, simplified JSON and text report generation."""

import hashlib
import json
from datetime import UTC, datetime
from typing import Any

from src.diagnosis import DiagnosisResult, Evidence

PRELIMINARY_NOTICE = (
    "Relatório preliminar e educacional baseado em dados públicos. Não substitui "
    "análise ambiental, jurídica ou técnica, licenciamento, vistoria de campo ou "
    "decisão oficial."
)


def _default_diagnosis(area_info: dict, deforestation: Any) -> DiagnosisResult:
    area_name = area_info.get("name") or "Área analisada"
    area_ha = area_info.get("area_ha", 0.0)
    status = "empty" if getattr(deforestation, "empty", False) else "ok"
    summary = (
        "Nenhum registro de desmatamento foi retornado para a área."
        if status == "empty"
        else "A série de desmatamento consultada contém registros para análise preliminar."
    )
    evidence = Evidence(
        source="INPE PRODES",
        period="período da série consultada",
        status=status,
        summary=summary,
        limitations=(
            "A cobertura e a disponibilidade da fonte devem ser confirmadas.",
        ),
    )
    return DiagnosisResult(
        area_name=area_name,
        area_ha=area_ha,
        evidences=(evidence,),
        limitations=(
            (
                "Resultado preliminar e educacional; não substitui análise técnica, "
                "jurídica ou de campo."
            ),
        ),
        next_steps=("Confirmar as fontes e realizar análise técnica da área.",),
    )


def generate_report(
    area_info: dict,
    deforestation: Any,
    diagnosis: DiagnosisResult | None = None,
    *,
    sources: list[tuple[str, str]] | None = None,
) -> dict:
    """Build the simplified preliminary diagnostic report.

    The checksum identifies the generated content; it does not certify the
    quality of the underlying data sources.
    """
    territorial_diagnosis = diagnosis or _default_diagnosis(area_info, deforestation)
    consulted_sources = sources or [("INPE PRODES", "período da série consultada")]
    report = {
        "version": "2.0",
        "generated_at": datetime.now(UTC).isoformat(),
        "area": {
            "name": area_info.get("name") or "Área analisada",
            "area_ha": area_info.get("area_ha", 0.0),
        },
        "deforestation": {
            "series": deforestation.to_dict()
            if hasattr(deforestation, "to_dict")
            else deforestation,
            "source": "INPE PRODES",
        },
        "diagnosis": territorial_diagnosis.to_dict(),
        "sources": [
            {"source": name, "period": period} for name, period in consulted_sources
        ],
        "preliminary_notice": PRELIMINARY_NOTICE,
        "inspired_by": "Projeto CNPq RHAE 443538/2024-7 — Green Forest/UFRA/ACC",
    }
    digest = hashlib.sha256(
        json.dumps(report, sort_keys=True, default=str).encode()
    ).hexdigest()
    report["checksum_sha256"] = digest
    return report


def render_text_report(report: dict) -> str:
    """Render the simplified report as readable plain text."""
    area = report["area"]
    lines = [
        "Diagnóstico Territorial Preliminar — Relatório preliminar",
        f"Gerado em (data da consulta): {report['generated_at']}",
        "",
        f"Nome da área: {area.get('name', '')}",
        f"Área em hectares: {area.get('area_ha')}",
        "",
        "Série de desmatamento consultada (ha/ano):",
    ]
    for year, value in report["deforestation"]["series"].items():
        lines.append(f"  {year}: {value:,.2f}")
    lines.append(f"Fonte da série: {report['deforestation']['source']}")
    lines.append("")
    for evidence in report["diagnosis"]["evidences"]:
        lines.append(f"Evidência — {evidence['source']}")
        lines.append(f"  Status: {evidence['status']}")
        lines.append(f"  Resultado: {evidence['summary']}")
        for limitation in evidence["limitations"]:
            lines.append(f"  Limitação: {limitation}")
    lines.append("")
    lines.append("Limitações da análise:")
    for limitation in report["diagnosis"]["limitations"]:
        lines.append(f"- {limitation}")
    lines.append("Próximos passos:")
    for step in report["diagnosis"]["next_steps"]:
        lines.append(f"- {step}")
    lines.append("")
    lines.append("Fontes consultadas:")
    for entry in report["sources"]:
        lines.append(f"- {entry['source']} ({entry['period']})")
    lines.append("")
    lines.append(f"Checksum SHA-256: {report['checksum_sha256']}")
    lines.append(report["preliminary_notice"])
    return "\n".join(lines)
