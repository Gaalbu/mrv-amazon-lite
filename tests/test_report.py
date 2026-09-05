import hashlib
import json

import pandas as pd
import pytest

from src.diagnosis import DiagnosisResult, Evidence
from src.mrv import generate_report, render_text_report


def _sample_diagnosis() -> DiagnosisResult:
    return DiagnosisResult(
        area_name="Área teste",
        area_ha=1.0,
        evidences=(
            Evidence(
                "INPE PRODES",
                "2016-2024",
                "ok",
                "Série disponível para análise preliminar.",
            ),
            Evidence(
                "ICMBio — UCs federais",
                "consulta atual",
                "ok",
                "1 UC federal sobreposta, com 15.50 ha. Nomes disponíveis: UC A.",
            ),
            Evidence(
                "ICMBio — Áreas Prioritárias",
                "consulta atual",
                "empty",
                "Nenhuma área prioritária sobreposta foi encontrada.",
            ),
        ),
        limitations=("Resultado preliminar e educacional.",),
        next_steps=("Confirmar as fontes e realizar análise técnica.",),
    )


def _report(**kwargs) -> dict:
    default = {
        "area_info": {"name": "Área teste", "area_ha": 1.0},
        "deforestation": pd.Series({2023: 1.2}),
        "diagnosis": None,
        "sources": None,
    }
    default.update(kwargs)
    return generate_report(**default)


def test_report_has_checksum():
    assert len(_report()["checksum_sha256"]) == 64


def test_report_simplified_contract_only():
    assert set(_report()) == {
        "version",
        "generated_at",
        "area",
        "deforestation",
        "diagnosis",
        "sources",
        "preliminary_notice",
        "inspired_by",
        "checksum_sha256",
    }


def test_report_has_no_legacy_financial_and_carbon_fields():
    report = _report()
    for key in ["carbon_estimate", "post_cop30", "methodology", "demo_note"]:
        assert key not in report
    rendered = render_text_report(report)
    for marker in ["TFFF", "PlaNAU", "tCO2e", "tCO₂e", "US$", "VCU"]:
        assert marker not in rendered


def test_report_serializes_to_json():
    report = _report()
    payload = json.dumps(report, indent=2, default=str)
    assert json.loads(payload)["area"]["name"] == "Área teste"


def test_report_serializes_explicit_diagnosis():
    diagnosis = _sample_diagnosis()
    report = _report(diagnosis=diagnosis)
    assert report["diagnosis"] == diagnosis.to_dict()
    assert report["diagnosis"]["evidences"][0]["status"] == "ok"


def test_report_includes_sources_and_preliminary_notice():
    report = _report(
        diagnosis=_sample_diagnosis(),
        sources=[
            ("INPE PRODES", "consulta atual"),
            ("ICMBio — UCs federais", "consulta atual"),
            ("ICMBio — Áreas Prioritárias", "consulta atual"),
        ],
    )
    assert len(report["sources"]) == 3
    assert report["preliminary_notice"]
    assert report["area"] == {"name": "Área teste", "area_ha": 1.0}
    assert report["deforestation"]["source"] == "INPE PRODES"


def test_report_without_diagnosis_builds_default():
    report = _report(diagnosis=None)
    assert report["diagnosis"]["area_name"] == "Área teste"
    assert report["diagnosis"]["evidences"][0]["source"] == "INPE PRODES"


def test_default_diagnosis_flags_empty_series():
    report = generate_report({"name": "X", "area_ha": 1}, pd.Series(dtype=float))
    assert report["diagnosis"]["evidences"][0]["status"] == "empty"


def test_text_report_contains_all_sections():
    text = render_text_report(_report(diagnosis=_sample_diagnosis()))
    for fragment in [
        "Nome da área",
        "Área em hectares",
        "Série de desmatamento consultada",
        "Limitações da análise",
        "Próximos passos",
        "Fontes consultadas",
        "Checksum SHA-256",
    ]:
        assert fragment in text
    assert "Preliminar" in text


def test_report_checksum_covers_full_payload():
    report = _report(diagnosis=_sample_diagnosis())
    payload = {key: value for key, value in report.items() if key != "checksum_sha256"}
    expected = hashlib.sha256(
        json.dumps(payload, sort_keys=True, default=str).encode()
    ).hexdigest()
    assert report["checksum_sha256"] == expected


def test_generate_report_rejects_unknown_sources_shape():
    with pytest.raises(ValueError):
        generate_report(
            {"name": "X", "area_ha": 1},
            pd.Series({2023: 1.0}),
            sources=[("A",)],  # type: ignore[arg-type]
        )
