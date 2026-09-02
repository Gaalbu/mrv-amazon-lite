"""Simplified PlaNAU urban tree-cover assessment."""

from dataclasses import dataclass

PLANAU_TARGET_TREES_PER_HA = 100
PLANAU_COST_PER_TREE_BRL = 500


@dataclass(frozen=True)
class PlanauCheck:
    area_ha: float
    is_urban: bool
    tree_cover_pct: float
    tree_count_estimate: int
    deficit_trees: int
    area_verde_gap_ha: float
    priority_level: str
    estimated_cost_brl: float
    source: str


def check_planau_eligibility(
    is_urban: bool, tree_cover_pct: float, area_ha: float
) -> PlanauCheck | None:
    if not 0 <= tree_cover_pct <= 1 or area_ha < 0:
        raise ValueError("tree_cover_pct must be 0..1 and area_ha non-negative")
    if not is_urban:
        return None
    current = round(area_ha * PLANAU_TARGET_TREES_PER_HA * tree_cover_pct)
    target = round(area_ha * PLANAU_TARGET_TREES_PER_HA)
    deficit = max(0, target - current)
    priority = (
        "alta"
        if tree_cover_pct < 0.15
        else "média"
        if tree_cover_pct <= 0.30
        else "baixa"
    )
    return PlanauCheck(
        area_ha,
        True,
        tree_cover_pct,
        current,
        deficit,
        max(0.0, 360000 * area_ha / 1000000),
        priority,
        deficit * PLANAU_COST_PER_TREE_BRL,
        "PlaNAU/COP30 nov 2025",
    )
