"""Live and local-demo PRODES deforestation series."""

from pathlib import Path

import geopandas as gpd
import pandas as pd
import requests

from src.ingest import AREA_CRS

DEMO_YEARS = range(2016, 2025)
DEMO_SERIES_CSV = Path(__file__).parents[1] / "data" / "samples" / "prodes_demo.csv"
DEMO_SERIES_NAME = "Área desmatada (ha)"
LIVE_PRODES_SOURCE = "INPE PRODES (ao vivo)"
DEMO_EMPTY_PRODES_SOURCE = "INPE PRODES (demonstração local — sem dados no recorte)"
DEMO_UNAVAILABLE_PRODES_SOURCE = "INPE PRODES (demonstração local — API indisponível)"
EMPTY_PRODES_SOURCE = "INPE PRODES (sem dados para o recorte)"
UNAVAILABLE_PRODES_SOURCE = (
    "INPE PRODES (serviço indisponível — sem dados para o recorte)"
)


def _empty_deforestation_series() -> pd.Series:
    return pd.Series(dtype=float, name=DEMO_SERIES_NAME)


def load_demo_deforestation_series(area_name: str | None) -> pd.Series | None:
    """Return the local demo series for a known demo area, else None.

    Values come from ``data/samples/prodes_demo.csv`` and are explicitly
    demonstrative: they must never be presented as real PRODES measurements.
    Custom areas without a local entry receive no other area's data.
    """
    if not isinstance(area_name, str) or not area_name.strip():
        return None
    if not DEMO_SERIES_CSV.exists():
        return None
    try:
        table = pd.read_csv(DEMO_SERIES_CSV, comment="#")
    except (OSError, ValueError, pd.errors.ParserError):
        return None
    required = {"area_name", "year", "deforestation_ha"}
    if not required.issubset(table.columns):
        return None
    rows = table[table["area_name"].astype(str).str.strip() == area_name.strip()]
    if rows.empty:
        return None
    series = pd.Series(
        [float(value) for value in rows["deforestation_ha"]],
        index=[int(year) for year in rows["year"]],
        name=DEMO_SERIES_NAME,
        dtype=float,
    ).sort_index()
    if series.empty or (series <= 0).all():
        return None
    return series


def compute_deforestation_series(
    prodes_gdf: gpd.GeoDataFrame, target_area: gpd.GeoDataFrame
) -> pd.Series:
    if prodes_gdf.empty:
        return pd.Series(dtype=float)
    if prodes_gdf.crs != target_area.crs:
        prodes_gdf = prodes_gdf.to_crs(target_area.crs)
    intersections = gpd.overlay(
        prodes_gdf, target_area[["geometry"]], how="intersection"
    )
    area = intersections.to_crs(AREA_CRS).geometry.area / 10000
    years = intersections.get("year", pd.Series(index=intersections.index, dtype=int))
    return area.groupby(years).sum().sort_index()


def prodes_series_with_fallback(
    target_area: gpd.GeoDataFrame,
    fetcher=None,
    years: range = DEMO_YEARS,
    area_name: str | None = None,
) -> tuple[pd.Series, str]:
    """Return PRODES data for an area, or a local demo series when unavailable.

    Priority: live API data first. When the API returns nothing for the
    cutout, or is unreachable, a local demonstrative series is used only for
    known demo areas. Custom areas without a local entry receive an empty
    series, never another area's data. Zero-filled series are never returned
    as if they were observed measurements.
    """
    if fetcher is None:
        from src.ingest import fetch_prodes

        fetcher = fetch_prodes
    bounds = target_area.total_bounds
    try:
        frame = fetcher([bounds[0], bounds[1], bounds[2], bounds[3]], years=years)
        if frame.empty:
            demo = load_demo_deforestation_series(area_name)
            if demo is not None:
                return demo, DEMO_EMPTY_PRODES_SOURCE
            return _empty_deforestation_series(), EMPTY_PRODES_SOURCE
        series = compute_deforestation_series(frame, target_area)
        if series.empty:
            demo = load_demo_deforestation_series(area_name)
            if demo is not None:
                return demo, DEMO_EMPTY_PRODES_SOURCE
            return _empty_deforestation_series(), EMPTY_PRODES_SOURCE
        return series, LIVE_PRODES_SOURCE
    except (OSError, ValueError, requests.RequestException):
        demo = load_demo_deforestation_series(area_name)
        if demo is not None:
            return demo, DEMO_UNAVAILABLE_PRODES_SOURCE
        return _empty_deforestation_series(), UNAVAILABLE_PRODES_SOURCE


def summarize_deforestation_series(series: pd.Series) -> dict[str, object] | None:
    """Summarize an annual deforestation series in hectares.

    Returns None for an empty series; otherwise the period total, the peak
    value with its year, and the first/last values with their years, all in
    chronological order.
    """
    if series is None or getattr(series, "empty", True):
        return None
    clean = pd.to_numeric(series, errors="coerce").dropna()
    if clean.empty:
        return None
    ordered = clean.sort_index()
    years = [int(year) for year in ordered.index]
    values = [float(value) for value in ordered.to_numpy()]
    peak_pos = int(ordered.to_numpy().argmax())
    return {
        "total_ha": float(sum(values)),
        "peak_ha": float(values[peak_pos]),
        "peak_year": years[peak_pos],
        "last_ha": float(values[-1]),
        "last_year": years[-1],
        "first_ha": float(values[0]),
        "first_year": years[0],
        "count_years": len(values),
    }


def interpret_deforestation_series(
    series: pd.Series, is_demo: bool = False
) -> str | None:
    """Build a plain-language comparison between series start and end.

    Returns None for an empty series. A relative difference below 5% reads as
    stable. Demo series always carry an explicit demo note and never state a
    real-world increase or decrease.
    """
    summary = summarize_deforestation_series(series)
    if summary is None:
        return None
    first = float(summary["first_ha"])
    last = float(summary["last_ha"])
    if first == 0:
        stable = last == 0
    else:
        stable = abs(last - first) / abs(first) < 0.05
    if stable:
        text = (
            "Os valores variam ao longo do período, "
            "sem mudança clara entre o início e o fim."
        )
    elif last < first:
        text = "O último valor da série está abaixo do primeiro registro do período."
    else:
        text = "O último valor da série está acima do primeiro registro do período."
    if is_demo:
        text += (
            " Essa comparação pertence à demonstração local e não representa "
            "uma conclusão real sobre o território."
        )
    return text
