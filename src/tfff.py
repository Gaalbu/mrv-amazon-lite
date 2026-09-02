"""Simplified TFFF eligibility rules for the educational MVP."""

from dataclasses import dataclass

TFFF_RATE_USD_HA_YEAR = 5.0


@dataclass(frozen=True)
class TFFFCheck:
    area_ha: float
    deforestation_pct_10yr: float
    is_indigenous_or_traditional: bool
    has_legal_reservation: bool
    has_management_plan: bool
    eligible: bool
    estimated_payment_usd_year: float
    reasons: list[str]
    source: str


def check_tfff_eligibility(
    deforestation_pct: float,
    has_indigenous: bool = False,
    has_rl: bool = True,
    has_pmfs: bool = False,
    area_ha: float = 1.0,
) -> TFFFCheck:
    if not 0 <= deforestation_pct <= 1:
        raise ValueError("deforestation_pct must be between 0 and 1")
    if area_ha < 0:
        raise ValueError("area_ha must be non-negative")
    reasons = []
    eligible = deforestation_pct < 0.05 and has_rl and deforestation_pct <= 0.20
    if deforestation_pct >= 0.20:
        reasons.append("Desmatamento acumulado acima de 20%")
    elif deforestation_pct >= 0.05:
        reasons.append("Desmatamento acumulado não atende ao limite de 5%")
    if not has_rl:
        reasons.append("Reserva Legal não comprovada")
    if has_pmfs:
        reasons.append("PMFS ativo confirma a análise de manejo")
    if eligible and not reasons:
        reasons.append(
            "Conservação e Reserva Legal atendem aos critérios simplificados"
        )
    multiplier = 1.5 if has_indigenous else 1.0
    payment = area_ha * TFFF_RATE_USD_HA_YEAR * multiplier if eligible else 0.0
    return TFFFCheck(
        area_ha,
        deforestation_pct,
        has_indigenous,
        has_rl,
        has_pmfs,
        eligible,
        payment,
        reasons,
        "TFFF/Belém/COP30 nov 2025",
    )
