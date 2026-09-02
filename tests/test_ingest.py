import geopandas as gpd
import pytest
from shapely.geometry import Polygon

from src.ingest import _validate_bbox, compute_deforestation_series, fetch_mapbiomas


def test_bbox_validation():
    with pytest.raises(ValueError):
        _validate_bbox([-1, 1, 1, -1])


def test_compute_deforestation_series():
    prodes = gpd.GeoDataFrame(
        {"year": [2020, 2021]},
        geometry=[
            Polygon([(0, 0), (1, 0), (1, 1), (0, 1)]),
            Polygon([(0, 0), (0.5, 0), (0.5, 0.5), (0, 0.5)]),
        ],
        crs="EPSG:4326",
    )
    target = gpd.GeoDataFrame(
        geometry=[Polygon([(-1, -1), (2, -1), (2, 2), (-1, 2)])], crs="EPSG:4326"
    )
    series = compute_deforestation_series(prodes, target)
    assert set(series.index) == {2020, 2021}
    assert series[2020] > series[2021]


def test_fetch_mapbiomas_fallback_has_schema():
    frame = fetch_mapbiomas(collection=9, year=2099, state="XX")
    assert list(frame.columns) == ["state", "year", "class", "area_ha"]
