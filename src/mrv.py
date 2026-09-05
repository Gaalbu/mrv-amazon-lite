"""Traceable JSON report generation."""

import hashlib
import json
from dataclasses import asdict
from datetime import UTC, datetime
from typing import Any

from src.diagnosis import DiagnosisResult, Evidence


def _default_diagnosis(area_info: dict, deforestation: Any) -> DiagnosisResult:
    area_name = area_info.get("name") or "Área analisada"
    area_ha = area_info.get("area_ha", 0.0)
    status = "empty" if getattr(deforestation, "empty", False) else "ok"
    summary = (
        "A série PRODES fornecida não contém registros."
        if status == "empty"
        else "A série PRODES fornecida contém dados para análise preliminar."
    )
    evidence = Evidence(
        source="INPE PRODES",
        period="período da série fornecida",
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
            "Resultado preliminar e educacional; não substitui análise técnica ou jurídica.",
        ),
        next_steps=("Confirmar as fontes e realizar análise técnica da área.",),
    )


def generate_report(
    area_info: dict,
    deforestation: Any,
    carbon: Any,
    tfff: Any | None,
    planau: Any | None,
    diagnosis: DiagnosisResult | None = None,
) -> dict:
    territorial_diagnosis = diagnosis or _default_diagnosis(area_info, deforestation)
    report = {
        "version": "1.0",
        "generated_at": datetime.now(UTC).isoformat(),
        "methodology": "ARR VCS VM0047 lite (educacional)",
        "area": area_info,
        "deforestation": {"series": deforestation.to_dict(), "source": "INPE PRODES"},
        "carbon_estimate": asdict(carbon),
        "post_cop30": {
            "tfff": asdict(tfff) if tfff else None,
            "planau": asdict(planau) if planau else None,
        },
        "diagnosis": territorial_diagnosis.to_dict(),
        "disclaimer": "Estimativa educacional — não substitui certificação VCS/Gold Standard.",
        "demo_note": "demonstração edu; TFFF/PlaNAU são simulações ilustrativas",
        "sources": [
            "INPE PRODES",
            "INPE DETER",
            "IPCC 2019",
            "VCS VM0047",
            "TFFF COP30 Belém 2025",
        ],
        "inspired_by": "Projeto CNPq RHAE 443538/2024-7 — Green Forest/UFRA/ACC",
    }
    digest = hashlib.sha256(
        json.dumps(report, sort_keys=True, default=str).encode()
    ).hexdigest()
    report["checksum_sha256"] = digest
    return report
