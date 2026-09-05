"""Open-data ingestion helpers with explicit validation and network timeouts."""

from datetime import UTC, datetime, timedelta
from pathlib import Path

import geopandas as gpd
import pandas as pd
import requests
from shapely import get_num_coordinates

WFS_URL = "https://terrabrasilis.dpi.inpe.br/wfs/terrabrasilis"
ICMBIO_WFS_URL = "https://geoservicos.inde.gov.br/geoserver/ICMBio/ows"
ICMBIO_UCS_LAYER = "ICMBio:limiteucsfederais_a"
DEMO_YEARS = range(2016, 2025)
TARGET_CRS = "EPSG:4326"
AREA_CRS = "EPSG:6933"  # Equal-area CRS used only for area calculation.
MAX_UPLOAD_BYTES = 5 * 1024 * 1024
MAX_FEATURES = 1_000
MAX_COORDINATES = 100_000
ICMBIO_EMPTY_COLUMNS = ["name", "geometry"]
ICMBIO_NAME_COLUMNS = ("name", "nome", "nom_uc", "nm_uc")


def validate_upload_size(size: int | None) -> None:
    """Reject empty or oversized uploads before GeoPandas parses them."""
    if size is None or size <= 0:
        raise ValueError("O arquivo está vazio; envie um GeoJSON com dados.")
    if size > MAX_UPLOAD_BYTES:
        limit_mb = MAX_UPLOAD_BYTES // (1024 * 1024)
        raise ValueError(f"O arquivo é grande demais; o limite é {limit_mb} MB.")


def validate_geodataframe(
    frame: gpd.GeoDataFrame,
    *,
    max_features: int = MAX_FEATURES,
    max_coordinates: int = MAX_COORDINATES,
) -> tuple[gpd.GeoDataFrame, float]:
    """Validate, normalize and measure an analysis GeoDataFrame.

    Coordinates are normalized to WGS84 (EPSG:4326). Area is calculated from
    the union in EPSG:6933, an equal-area metric projection, and returned in
    hectares. Conservative feature and coordinate caps limit parser and
    geometry-processing work at the upload boundary.
    """
    if not isinstance(frame, gpd.GeoDataFrame):
        raise TypeError("A entrada precisa ser um GeoDataFrame.")
    if frame.empty:
        raise ValueError("O GeoJSON está vazio; envie ao menos uma feição.")
    if max_features <= 0 or len(frame) > max_features:
        raise ValueError(f"O GeoJSON excede o limite de {max_features} feições.")
    if frame.crs is None:
        raise ValueError("O GeoJSON não informa um CRS reconhecível.")
    if frame.geometry.isna().any() or frame.geometry.is_empty.any():
        raise ValueError("O GeoJSON contém geometria vazia ou ausente.")
    if (~frame.geometry.is_valid).any():
        raise ValueError("O GeoJSON contém geometria inválida.")

    coordinate_count = sum(
        int(get_num_coordinates(geometry)) for geometry in frame.geometry
    )
    if max_coordinates <= 0 or coordinate_count > max_coordinates:
        raise ValueError(f"O GeoJSON excede o limite de {max_coordinates} coordenadas.")

    try:
        normalized = frame.to_crs(TARGET_CRS)
    except Exception as exc:
        raise ValueError("O CRS informado no GeoJSON é inválido.") from exc

    union = normalized.geometry.union_all()
    area_m2 = gpd.GeoSeries([union], crs=TARGET_CRS).to_crs(AREA_CRS).area.iloc[0]
    area_ha = float(area_m2 / 10_000)
    if area_ha <= 0:
        raise ValueError("A geometria tem área igual a zero; envie um polígono.")
    return normalized, area_ha


def read_and_validate_geojson(
    source: str | Path | object, *, file_size: int | None = None
) -> tuple[gpd.GeoDataFrame, float]:
    """Read a GeoJSON source and apply the upload/geometry validation contract."""
    if file_size is not None:
        validate_upload_size(file_size)
    try:
        frame = gpd.read_file(source)
    except Exception as exc:
        raise ValueError("GeoJSON inválido; não foi possível ler o arquivo.") from exc
    return validate_geodataframe(frame)


def _validate_bbox(bbox: list[float]) -> tuple[float, float, float, float]:
    if len(bbox) != 4:
        raise ValueError("bbox must contain west, south, east, north")
    west, south, east, north = map(float, bbox)
    if west >= east or south >= north:
        raise ValueError("bbox coordinates are invalid")
    return west, south, east, north


def _fetch_wfs(layer: str, bbox: list[float], **extra: str) -> gpd.GeoDataFrame:
    west, south, east, north = _validate_bbox(bbox)
    params = {
        "service": "WFS",
        "version": "2.0.0",
        "request": "GetFeature",
        "typeNames": layer,
        "outputFormat": "application/json",
        "bbox": f"{west},{south},{east},{north},{TARGET_CRS}",
        **extra,
    }
    response = requests.get(WFS_URL, params=params, timeout=30)
    response.raise_for_status()
    return gpd.GeoDataFrame.from_features(response.json()["features"], crs=TARGET_CRS)


def fetch_prodes(
    bbox: list[float], years: range = range(2016, 2025)
) -> gpd.GeoDataFrame:
    frame = _fetch_wfs("prodes_para_q", bbox)
    if "year" in frame:
        frame = frame[frame["year"].isin(years)]
    return frame


def _empty_icmbio_ucs() -> gpd.GeoDataFrame:
    return gpd.GeoDataFrame(
        {
            "name": pd.Series(dtype="string"),
            "geometry": gpd.GeoSeries([], crs=TARGET_CRS),
        },
        geometry="geometry",
        crs=TARGET_CRS,
    )


def fetch_icmbio_ucs(bbox: list[float]) -> gpd.GeoDataFrame:
    """Fetch federal conservation units from the official ICMBio WFS."""
    west, south, east, north = _validate_bbox(bbox)
    params = {
        "service": "WFS",
        "version": "2.0.0",
        "request": "GetFeature",
        "typeNames": ICMBIO_UCS_LAYER,
        "outputFormat": "application/json",
        "bbox": f"{west},{south},{east},{north},{TARGET_CRS}",
    }
    response = requests.get(ICMBIO_WFS_URL, params=params, timeout=30)
    response.raise_for_status()
    features = response.json().get("features", [])
    if not features:
        return _empty_icmbio_ucs()
    return gpd.GeoDataFrame.from_features(features, crs=TARGET_CRS)


def summarize_icmbio_overlap(
    icmbio_ucs: gpd.GeoDataFrame, target_area: gpd.GeoDataFrame
) -> dict[str, object]:
    """Summarize spatial overlap without inferring legal eligibility."""
    if icmbio_ucs.crs is None or target_area.crs is None:
        raise ValueError("ICMBio e a área-alvo precisam informar um CRS.")
    if icmbio_ucs.empty or target_area.empty:
        return {"count": 0, "names": [], "overlap_area_ha": 0.0}

    units = icmbio_ucs.to_crs(TARGET_CRS)
    target = target_area.to_crs(TARGET_CRS)
    name_column = next(
        (column for column in ICMBIO_NAME_COLUMNS if column in units.columns), None
    )
    names = units[name_column] if name_column else pd.Series(index=units.index)
    units = gpd.GeoDataFrame(
        {"_source_id": range(len(units)), "_name": names.tolist()},
        geometry=units.geometry.tolist(),
        crs=TARGET_CRS,
    )
    intersections = gpd.overlay(
        units, target[["geometry"]], how="intersection", keep_geom_type=False
    )
    if intersections.empty:
        return {"count": 0, "names": [], "overlap_area_ha": 0.0}

    metric = intersections.to_crs(AREA_CRS)
    positive = metric.geometry.area > 0
    intersections = intersections.loc[positive]
    if intersections.empty:
        return {"count": 0, "names": [], "overlap_area_ha": 0.0}

    overlap = intersections.geometry.union_all()
    overlap_area_ha = float(
        gpd.GeoSeries([overlap], crs=TARGET_CRS).to_crs(AREA_CRS).area.iloc[0] / 10_000
    )
    available_names = []
    for name in intersections["_name"]:
        if name is not None and not pd.isna(name) and str(name).strip():
            text = str(name).strip()
            if text not in available_names:
                available_names.append(text)
    return {
        "count": int(intersections["_source_id"].nunique()),
        "names": available_names,
        "overlap_area_ha": overlap_area_ha,
    }


def prodes_series_with_fallback(
    target_area: gpd.GeoDataFrame,
    fetcher=fetch_prodes,
    years: range = DEMO_YEARS,
) -> tuple[pd.Series, str]:
    """Return PRODES data for an area, or a visible demo fallback on API failure."""
    demo = pd.Series({year: 0.0 for year in years}, name="Área desmatada (ha)")
    bounds = target_area.total_bounds
    try:
        frame = fetcher([bounds[0], bounds[1], bounds[2], bounds[3]], years=years)
        if frame.empty:
            return (
                demo,
                "INPE PRODES (demo — sem dados na bbox; cobertura disponível só para PA)",
            )
        series = compute_deforestation_series(frame, target_area)
        return series.reindex(years).fillna(0.0), "INPE PRODES (ao vivo)"
    except (OSError, ValueError, requests.RequestException):
        return (
            demo,
            "INPE PRODES (fallback demo — API indisponível ou cobertura só para PA)",
        )


def fetch_deter(bbox: list[float], months: int = 12) -> gpd.GeoDataFrame:
    if months <= 0:
        raise ValueError("months must be positive")
    frame = _fetch_wfs("deter_para_q", bbox)
    cutoff = datetime.now(UTC).date() - timedelta(days=months * 31)
    date_column = next(
        (column for column in ("date", "data", "alert_date") if column in frame), None
    )
    if date_column:
        dates = pd.to_datetime(frame[date_column], errors="coerce").dt.date
        frame = frame[dates >= cutoff]
    return frame


def fetch_mapbiomas(
    collection: int = 9, year: int = 2023, state: str = "PA"
) -> pd.DataFrame:
    del collection
    local = Path(__file__).parents[1] / "data" / f"mapbiomas_{state.lower()}_{year}.csv"
    if not local.exists():
        return pd.DataFrame(columns=["state", "year", "class", "area_ha"])
    return pd.read_csv(local)


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
