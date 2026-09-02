"""Educational ARR carbon estimate."""

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class CarbonEstimate:
    area_ha: float
    biomass_type: str
    baseline_tco2e_ha: float
    restoration_tco2e_ha: float
    gross_vcu: float
    leakage_deduction: float
    buffer_deduction: float
    net_vcu: float
    uncertainty_range: tuple[float, float]
    methodology_note: str


def _config() -> dict:
    return json.loads((Path(__file__).parent / "config.json").read_text())


def estimate_vcu(
    area_ha: float,
    biomass_type: str = "terra_firme",
    crediting_years: int = 30,
    config: dict | None = None,
) -> CarbonEstimate:
    if area_ha < 0 or crediting_years <= 0:
        raise ValueError("area_ha must be non-negative and crediting_years positive")
    settings = config or _config()
    biomass = settings["ipcc_biomass_amazon"].get(biomass_type)
    if biomass is None:
        raise ValueError(f"Unknown biomass type: {biomass_type}")
    params = settings["vcs_params"]
    gross = (
        params["restoration_rate"]
        * area_ha
        * biomass["mean_tco2e_ha"]
        * crediting_years
    )
    leakage = gross * params["leakage_factor"]
    buffer = (gross - leakage) * params["buffer_pool"]
    net = gross - leakage - buffer
    return CarbonEstimate(
        area_ha,
        biomass_type,
        biomass["mean_tco2e_ha"],
        biomass["mean_tco2e_ha"] * params["restoration_rate"],
        gross,
        leakage,
        buffer,
        net,
        (net * 0.7, net * 1.3),
        "Estimativa educacional ARR VCS VM0047 lite",
    )


def estimate_vcu_range(
    area_ha: float, biomass_type: str = "terra_firme", crediting_years: int = 30
) -> tuple[CarbonEstimate, CarbonEstimate]:
    settings = _config()
    biomass = settings["ipcc_biomass_amazon"].get(biomass_type)
    if biomass is None:
        raise ValueError(f"Unknown biomass type: {biomass_type}")
    low = dict(settings)
    low["ipcc_biomass_amazon"] = {biomass_type: {"mean_tco2e_ha": biomass["min"]}}
    high = dict(settings)
    high["ipcc_biomass_amazon"] = {biomass_type: {"mean_tco2e_ha": biomass["max"]}}
    return (
        estimate_vcu(area_ha, biomass_type, crediting_years, low),
        estimate_vcu(area_ha, biomass_type, crediting_years, high),
    )
