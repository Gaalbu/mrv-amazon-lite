import pytest

from src.diagnosis import DiagnosisResult, Evidence


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
