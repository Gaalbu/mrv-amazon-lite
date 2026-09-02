"""Traceable JSON report generation."""

import hashlib
import json
from dataclasses import asdict
from datetime import UTC, datetime
from typing import Any


def generate_report(
    area_info: dict,
    deforestation: Any,
    carbon: Any,
    tfff: Any | None,
    planau: Any | None,
) -> dict:
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
