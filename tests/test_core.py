import hashlib
import json

import pandas as pd
import pytest

from src.carbon import estimate_vcu, estimate_vcu_range
from src.diagnosis import DiagnosisResult, Evidence
from src.mrv import generate_report
from src.planau import check_planau_eligibility
from src.tfff import check_tfff_eligibility


def test_vcu_100ha_terra_firme():
    result = estimate_vcu(100)
    assert result.net_vcu == pytest.approx(12672)


def test_vcu_range_and_deductions():
    low, high = estimate_vcu_range(100)
    assert low.net_vcu > 0 and high.net_vcu > low.net_vcu
    assert low.leakage_deduction > 0 and low.buffer_deduction > 0


def test_tfff_rules_and_indigenous_bonus():
    assert check_tfff_eligibility(0.02).eligible
    assert check_tfff_eligibility(0.25).eligible is False
    assert (
        check_tfff_eligibility(0.02, has_indigenous=True).estimated_payment_usd_year
        == 7.5
    )


def test_planau():
    assert check_planau_eligibility(False, 0.2, 100) is None
    result = check_planau_eligibility(True, 0.1, 50)
    assert result and result.priority_level == "alta" and result.deficit_trees > 0


def test_report_has_checksum():
    carbon = estimate_vcu(1)
    report = generate_report(
        {"name": "demo"}, pd.Series({2023: 1.2}), carbon, None, None
    )
    assert len(report["checksum_sha256"]) == 64


def test_report_serializes_explicit_territorial_diagnosis():
    carbon = estimate_vcu(1)
    diagnosis = DiagnosisResult(
        area_name="Área teste",
        area_ha=1.0,
        evidences=(Evidence("INPE PRODES", "2024", "empty", "Sem alertas."),),
        limitations=("Pré-diagnóstico educacional.",),
        next_steps=("Realizar vistoria técnica.",),
    )

    report = generate_report(
        {"name": "Área teste", "area_ha": 1.0},
        pd.Series({2023: 1.2}),
        carbon,
        None,
        None,
        diagnosis,
    )

    assert report["diagnosis"] == diagnosis.to_dict()
    assert report["diagnosis"]["evidences"][0]["status"] == "empty"


def test_report_checksum_covers_diagnosis_block():
    carbon = estimate_vcu(1)
    diagnosis = DiagnosisResult(
        area_name="Área A",
        area_ha=1.0,
        evidences=(Evidence("Fonte A", "2024", "ok", "Evidência A"),),
    )
    report = generate_report(
        {"name": "Área A", "area_ha": 1.0},
        pd.Series({2023: 1.2}),
        carbon,
        None,
        None,
        diagnosis,
    )

    payload = {key: value for key, value in report.items() if key != "checksum_sha256"}
    expected = hashlib.sha256(
        json.dumps(payload, sort_keys=True, default=str).encode()
    ).hexdigest()

    assert report["checksum_sha256"] == expected


def test_invalid_inputs():
    with pytest.raises(ValueError):
        estimate_vcu(-1)
    with pytest.raises(ValueError):
        check_tfff_eligibility(1.1)


def test_zero_area_vcu_is_zero():
    assert estimate_vcu(0).net_vcu == 0


def test_failed_tfff_criteria_do_not_claim_pmfs_confirmation():
    result = check_tfff_eligibility(0.25, has_pmfs=True)
    assert result.eligible is False
    assert "PMFS ativo confirma a análise de manejo" not in result.reasons
