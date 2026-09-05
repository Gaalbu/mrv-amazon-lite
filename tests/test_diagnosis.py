import pandas as pd
import pytest

from src.diagnosis import (
    DiagnosisResult,
    Evidence,
    add_icmbio_evidence,
    add_overlap_evidence,
    build_preliminary_diagnosis,
)


def test_evidence_accepts_ok_and_serializes_to_json_ready_dict():
    evidence = Evidence(
        source="INPE PRODES",
        period="2016-2024",
        status="ok",
        summary="Série consultada para a área analisada.",
        limitations=("Cobertura validada apenas no escopo disponível.",),
    )

    assert evidence.to_dict() == {
        "source": "INPE PRODES",
        "period": "2016-2024",
        "status": "ok",
        "summary": "Série consultada para a área analisada.",
        "limitations": ["Cobertura validada apenas no escopo disponível."],
    }


@pytest.mark.parametrize("status", ["empty", "unavailable"])
def test_evidence_accepts_non_positive_states(status):
    evidence = Evidence("Fonte pública", "2024", status, "Sem evidência conclusiva.")

    assert evidence.status == status


@pytest.mark.parametrize(
    "kwargs",
    [
        {"source": "", "period": "2024", "status": "ok", "summary": "Resumo"},
        {"source": "Fonte", "period": "", "status": "ok", "summary": "Resumo"},
        {"source": "Fonte", "period": "2024", "status": "ok", "summary": ""},
        {
            "source": "Fonte",
            "period": "2024",
            "status": "pending",
            "summary": "Resumo",
        },
    ],
)
def test_evidence_rejects_invalid_required_fields(kwargs):
    with pytest.raises(ValueError):
        Evidence(**kwargs)


def test_diagnosis_result_serializes_evidences_and_metadata():
    evidence = Evidence("INPE PRODES", "2024", "empty", "Nenhuma feição retornada.")
    result = DiagnosisResult(
        area_name="Área teste",
        area_ha=12.5,
        evidences=(evidence,),
        limitations=("Resultado preliminar.",),
        next_steps=("Solicitar análise técnica.",),
    )

    assert result.to_dict() == {
        "area_name": "Área teste",
        "area_ha": 12.5,
        "evidences": [evidence.to_dict()],
        "limitations": ["Resultado preliminar."],
        "next_steps": ["Solicitar análise técnica."],
    }


@pytest.mark.parametrize(
    "kwargs",
    [
        {"area_name": "", "area_ha": 1},
        {"area_name": "Área", "area_ha": -1},
        {"area_name": "Área", "area_ha": 1, "evidences": ("not evidence",)},
    ],
)
def test_diagnosis_result_rejects_invalid_fields(kwargs):
    with pytest.raises(ValueError):
        DiagnosisResult(**kwargs)


@pytest.mark.parametrize(
    ("status", "series", "summary_fragment", "next_step_fragment"),
    [
        ("ok", pd.Series({2023: 4.2}), "contém dados", "Revisar"),
        ("empty", pd.Series(dtype=float), "Nenhum registro", "Confirmar"),
        (
            "unavailable",
            pd.Series(dtype=float),
            "não esteve disponível",
            "Tentar novamente",
        ),
    ],
)
def test_build_preliminary_diagnosis_maps_ingestion_status(
    status, series, summary_fragment, next_step_fragment
):
    result = build_preliminary_diagnosis(
        "Área teste", 12.5, series, "INPE PRODES", status
    )

    assert result.area_name == "Área teste"
    assert result.area_ha == 12.5
    assert len(result.evidences) == 1
    assert result.evidences[0].status == status
    assert summary_fragment in result.evidences[0].summary
    assert next_step_fragment in result.next_steps[0]
    assert result.limitations


def test_build_preliminary_diagnosis_infers_period_from_series():
    result = build_preliminary_diagnosis(
        "Área teste", 1, pd.Series({2021: 1.0, 2024: 2.0}), "Fonte", "ok"
    )

    assert result.evidences[0].period == "2021-2024"


def test_build_preliminary_diagnosis_rejects_invalid_status():
    with pytest.raises(ValueError):
        build_preliminary_diagnosis(
            "Área teste", 1, pd.Series(dtype=float), "Fonte", "pending"
        )


def _base_diagnosis():
    return DiagnosisResult("Área teste", 10.0)


@pytest.mark.parametrize(
    ("summary", "status"),
    [
        ({"count": 2, "names": ["UC A", "UC B"], "overlap_area_ha": 15.5}, "ok"),
        ({"count": 0, "names": [], "overlap_area_ha": 0.0}, "empty"),
    ],
)
def test_add_icmbio_evidence_classifies_overlap(summary, status):
    result = add_icmbio_evidence(
        _base_diagnosis(),
        "ICMBio WFS",
        "consulta atual",
        summary,
    )

    evidence = result.evidences[0]
    assert evidence.status == status
    assert evidence.source == "ICMBio WFS"
    assert evidence.period == "consulta atual"
    assert f"{summary['overlap_area_ha']:.2f} ha" in evidence.summary
    assert result.limitations and result.next_steps


def test_add_icmbio_evidence_marks_failed_request_unavailable():
    result = add_icmbio_evidence(
        _base_diagnosis(),
        "ICMBio WFS",
        "consulta atual",
        None,
        available=False,
    )

    assert result.evidences[0].status == "unavailable"
    assert "indisponível" in result.evidences[0].summary
    assert result.evidences[0].limitations


def test_add_icmbio_evidence_does_not_mutate_original_result():
    original = _base_diagnosis()

    enriched = add_icmbio_evidence(
        original,
        "ICMBio WFS",
        "consulta atual",
        {"count": 1, "names": ["UC A"], "overlap_area_ha": 2.0},
    )

    assert original.evidences == ()
    assert len(enriched.evidences) == 1


def test_add_overlap_evidence_supports_priority_area_label():
    result = add_overlap_evidence(
        _base_diagnosis(),
        "ICMBio — Áreas Prioritárias para a Conservação da Biodiversidade - Amazônia",
        "consulta atual",
        {"count": 2, "names": ["Área A", "Área B"], "overlap_area_ha": 15.5},
        subject_label="área prioritária",
    )

    evidence = result.evidences[0]
    assert evidence.status == "ok"
    assert "área prioritária" in evidence.summary
    assert "Área A, Área B" in evidence.summary
