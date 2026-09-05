import geopandas as gpd
import pytest
from shapely.geometry import LineString, Polygon

from src.ingest import (
    _validate_bbox,
    compute_deforestation_series,
    fetch_mapbiomas,
    fetch_prodes,
    prodes_series_with_fallback,
    read_and_validate_geojson,
    validate_geodataframe,
    validate_upload_size,
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


def test_validate_geodataframe_normalizes_crs_and_calculates_area():
    frame = gpd.GeoDataFrame(
        geometry=[
            Polygon([(-55.0, -2.0), (-54.99, -2.0), (-54.99, -1.99), (-55.0, -1.99)])
        ],
        crs="EPSG:4326",
    )

    normalized, area_ha = validate_geodataframe(frame)

    assert normalized.crs.to_epsg() == 4326
    assert area_ha > 0


def test_validate_geodataframe_accepts_multiple_features():
    frame = gpd.GeoDataFrame(
        geometry=[
            Polygon([(-55.0, -2.0), (-54.99, -2.0), (-54.99, -1.99), (-55.0, -1.99)]),
            Polygon([(-55.02, -2.0), (-55.01, -2.0), (-55.01, -1.99), (-55.02, -1.99)]),
        ],
        crs="EPSG:4326",
    )

    normalized, area_ha = validate_geodataframe(frame)

    assert len(normalized) == 2
    assert area_ha > 0


@pytest.mark.parametrize(
    "frame, message",
    [
        (gpd.GeoDataFrame(geometry=[], crs="EPSG:4326"), "vazio"),
        (
            gpd.GeoDataFrame(
                geometry=[Polygon([(0, 0), (1, 1), (0, 1), (1, 0), (0, 0)])],
                crs="EPSG:4326",
            ),
            "inválida",
        ),
        (
            gpd.GeoDataFrame(
                geometry=[LineString([(0, 0), (1, 0)])],
                crs="EPSG:4326",
            ),
            "área",
        ),
    ],
)
def test_validate_geodataframe_rejects_empty_invalid_and_zero_area(frame, message):
    with pytest.raises(ValueError, match=message):
        validate_geodataframe(frame)


def test_validate_geodataframe_rejects_missing_crs():
    frame = gpd.GeoDataFrame(geometry=[Polygon([(0, 0), (1, 0), (1, 1), (0, 0)])])

    with pytest.raises(ValueError, match="CRS"):
        validate_geodataframe(frame)


def test_validate_geodataframe_rejects_feature_and_coordinate_limits():
    frame = gpd.GeoDataFrame(
        geometry=[Polygon([(0, 0), (1, 0), (1, 1), (0, 0)])] * 2,
        crs="EPSG:4326",
    )

    with pytest.raises(ValueError, match="feições"):
        validate_geodataframe(frame, max_features=1)
    with pytest.raises(ValueError, match="coordenadas"):
        validate_geodataframe(frame, max_coordinates=3)


def test_read_and_validate_geojson_rejects_empty_upload():
    with pytest.raises(ValueError, match="vazio"):
        read_and_validate_geojson(b"", file_size=0)


def test_validate_upload_size_rejects_oversized_upload():
    with pytest.raises(ValueError, match="grande"):
        validate_upload_size(5 * 1024 * 1024 + 1)
