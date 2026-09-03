import geopandas as gpd
import pytest
from shapely.geometry import Polygon

from src.ingest import (
    _validate_bbox,
    compute_deforestation_series,
    fetch_mapbiomas,
    fetch_prodes,
    prodes_series_with_fallback,
)


def test_bbox_validation():
    with pytest.raises(ValueError):
        _validate_bbox([-1, 1, 1, -1])


def test_fetch_prodes_returns_gdf(monkeypatch):
    features = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {"year": 2021, "area_ha": 12},
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [
                        [
                            [-56.1, -2.5],
                            [-56.0, -2.5],
                            [-56.0, -2.4],
                            [-56.1, -2.4],
                            [-56.1, -2.5],
                        ]
                    ],
                },
            }
        ],
    }

    class FakeResponse:
        def json(self):
            return features

        def raise_for_status(self):
            return None

    monkeypatch.setattr("src.ingest.requests.get", lambda *a, **k: FakeResponse())

    frame = fetch_prodes([-56.15, -2.55, -55.95, -2.29], years=range(2016, 2025))
    assert isinstance(frame, gpd.GeoDataFrame)
    assert not frame.empty
    assert {"geometry", "year"}.issubset(frame.columns)
    assert list(frame["year"]) == [2021]


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


def test_empty_prodes_and_non_intersection_return_empty_series():
    target = gpd.GeoDataFrame(
        geometry=[Polygon([(0, 0), (1, 0), (1, 1), (0, 1)])], crs="EPSG:4326"
    )
    empty = gpd.GeoDataFrame({"year": []}, geometry=[], crs="EPSG:4326")
    assert compute_deforestation_series(empty, target).empty
    outside = gpd.GeoDataFrame(
        {"year": [2020]},
        geometry=[Polygon([(2, 2), (3, 2), (3, 3), (2, 3)])],
        crs="EPSG:4326",
    )
    assert compute_deforestation_series(outside, target).empty


def test_prodes_network_failure_returns_visible_fallback():
    target = gpd.GeoDataFrame(
        geometry=[Polygon([(0, 0), (1, 0), (1, 1), (0, 1)])], crs="EPSG:4326"
    )

    def failing_fetcher(*args, **kwargs):
        raise OSError("network unavailable")

    series, source = prodes_series_with_fallback(target, fetcher=failing_fetcher)
    assert len(series) == 9
    assert "fallback demo" in source
