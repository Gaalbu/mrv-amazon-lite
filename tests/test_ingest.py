import geopandas as gpd
import pytest
import requests
from shapely.geometry import LineString, Polygon

from src.ingest import (
    _validate_bbox,
    compute_deforestation_series,
    fetch_icmbio_priority_areas,
    fetch_icmbio_ucs,
    fetch_mapbiomas,
    fetch_prodes,
    load_demo_deforestation_series,
    prodes_series_with_fallback,
    read_and_validate_geojson,
    summarize_icmbio_overlap,
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
    assert series.empty
    assert "indisponível" in source
    assert "demonstração local" not in source


def test_prodes_empty_bbox_returns_defined_source_not_fake_live_data():
    target = gpd.GeoDataFrame(
        geometry=[Polygon([(0, 0), (1, 0), (1, 1), (0, 1)])], crs="EPSG:4326"
    )

    def empty_fetcher(*args, **kwargs):
        return gpd.GeoDataFrame({"year": []}, geometry=[], crs="EPSG:4326")

    series, source = prodes_series_with_fallback(target, fetcher=empty_fetcher)
    assert "sem dados" in source
    assert series.empty
    assert "demonstração local" not in source


def test_prodes_live_series_is_not_padded_with_fake_zeros():
    target = gpd.GeoDataFrame(
        geometry=[Polygon([(-1, -1), (2, -1), (2, 2), (-1, 2)])], crs="EPSG:4326"
    )

    def single_year_fetcher(*args, **kwargs):
        return gpd.GeoDataFrame(
            {"year": [2020]},
            geometry=[Polygon([(0, 0), (1, 0), (1, 1), (0, 1)])],
            crs="EPSG:4326",
        )

    series, source = prodes_series_with_fallback(target, fetcher=single_year_fetcher)
    assert source == "INPE PRODES (ao vivo)"
    assert set(series.index) == {2020}


def _square_target():
    return gpd.GeoDataFrame(
        geometry=[Polygon([(0, 0), (1, 0), (1, 1), (0, 1)])], crs="EPSG:4326"
    )


def _failing_fetcher(*args, **kwargs):
    raise OSError("network unavailable")


def _empty_frame_fetcher(*args, **kwargs):
    return gpd.GeoDataFrame({"year": []}, geometry=[], crs="EPSG:4326")


@pytest.mark.parametrize(
    "area_name",
    ["UMF V Mamuru-Arapiuns", "Centro Belém", "Área degradada (demo)"],
)
def test_load_demo_series_has_nonzero_values_for_demo_areas(area_name):
    series = load_demo_deforestation_series(area_name)

    assert series is not None
    assert len(series) == 9
    assert (series > 0).all()


@pytest.mark.parametrize("area_name", ["Minha área custom", "", "  ", None])
def test_load_demo_series_returns_none_for_unknown_area(area_name):
    assert load_demo_deforestation_series(area_name) is None


def test_prodes_unavailable_api_uses_local_demo_series():
    series, source = prodes_series_with_fallback(
        _square_target(),
        fetcher=_failing_fetcher,
        area_name="UMF V Mamuru-Arapiuns",
    )

    assert (series > 0).all()
    assert source == "INPE PRODES (demonstração local — API indisponível)"


def test_prodes_empty_response_uses_local_demo_series():
    series, source = prodes_series_with_fallback(
        _square_target(),
        fetcher=_empty_frame_fetcher,
        area_name="Centro Belém",
    )

    assert (series > 0).all()
    assert source == "INPE PRODES (demonstração local — sem dados no recorte)"


def test_prodes_custom_area_without_demo_receives_no_other_area_data():
    series, source = prodes_series_with_fallback(
        _square_target(),
        fetcher=_failing_fetcher,
        area_name="Minha área custom",
    )

    assert series.empty
    assert "demonstração local" not in source

    series_empty, source_empty = prodes_series_with_fallback(
        _square_target(),
        fetcher=_empty_frame_fetcher,
        area_name="Minha área custom",
    )

    assert series_empty.empty
    assert "demonstração local" not in source_empty


def test_prodes_live_data_has_priority_over_demo_series():
    def single_year_fetcher(*args, **kwargs):
        return gpd.GeoDataFrame(
            {"year": [2020]},
            geometry=[Polygon([(0, 0), (1, 0), (1, 1), (0, 1)])],
            crs="EPSG:4326",
        )

    series, source = prodes_series_with_fallback(
        _square_target(),
        fetcher=single_year_fetcher,
        area_name="UMF V Mamuru-Arapiuns",
    )

    assert source == "INPE PRODES (ao vivo)"
    assert set(series.index) == {2020}


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


def test_fetch_icmbio_ucs_returns_geojson_in_wgs84(monkeypatch):
    payload = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {"name": "UC teste"},
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [
                        [[-55.0, -2.0], [-54.9, -2.0], [-54.9, -1.9], [-55.0, -2.0]]
                    ],
                },
            }
        ],
    }
    captured = {}

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return payload

    def fake_get(url, **kwargs):
        captured.update(url=url, kwargs=kwargs)
        return FakeResponse()

    monkeypatch.setattr("src.ingest.requests.get", fake_get)

    frame = fetch_icmbio_ucs([-56, -3, -54, -1])

    assert frame.crs.to_epsg() == 4326
    assert list(frame["name"]) == ["UC teste"]
    assert captured["kwargs"]["params"]["typeNames"] == "ICMBio:limiteucsfederais_a"
    assert captured["kwargs"]["params"]["outputFormat"] == "application/json"
    assert captured["kwargs"]["params"]["bbox"].endswith(",EPSG:4326")
    assert captured["kwargs"]["timeout"] == 30


def test_fetch_icmbio_ucs_empty_response_has_predictable_schema(monkeypatch):
    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"type": "FeatureCollection", "features": []}

    monkeypatch.setattr(
        "src.ingest.requests.get", lambda *args, **kwargs: FakeResponse()
    )

    frame = fetch_icmbio_ucs([-56, -3, -54, -1])

    assert frame.empty
    assert list(frame.columns) == ["name", "geometry"]
    assert frame.crs.to_epsg() == 4326


def test_fetch_icmbio_ucs_propagates_api_unavailability(monkeypatch):
    def unavailable(*args, **kwargs):
        raise requests.Timeout("ICMBio unavailable")

    monkeypatch.setattr("src.ingest.requests.get", unavailable)

    with pytest.raises(requests.Timeout):
        fetch_icmbio_ucs([-56, -3, -54, -1])


def test_summarize_icmbio_overlap_counts_names_and_union_area():
    ucs = gpd.GeoDataFrame(
        {"name": ["UC sobreposta", "UC fora"]},
        geometry=[
            Polygon([(0, 0), (1, 0), (1, 1), (0, 1)]),
            Polygon([(2, 2), (3, 2), (3, 3), (2, 3)]),
        ],
        crs="EPSG:4326",
    )
    target = gpd.GeoDataFrame(
        geometry=[Polygon([(0.5, 0.5), (1.5, 0.5), (1.5, 1.5), (0.5, 0.5)])],
        crs="EPSG:4326",
    )

    summary = summarize_icmbio_overlap(ucs, target)

    assert summary["count"] == 1
    assert summary["names"] == ["UC sobreposta"]
    assert summary["overlap_area_ha"] > 0


def test_summarize_icmbio_overlap_returns_empty_summary_without_intersection():
    ucs = gpd.GeoDataFrame(
        {"name": ["UC fora"]},
        geometry=[Polygon([(2, 2), (3, 2), (3, 3), (2, 3)])],
        crs="EPSG:4326",
    )
    target = gpd.GeoDataFrame(
        geometry=[Polygon([(0, 0), (1, 0), (1, 1), (0, 0)])],
        crs="EPSG:4326",
    )

    assert summarize_icmbio_overlap(ucs, target) == {
        "count": 0,
        "names": [],
        "overlap_area_ha": 0.0,
    }


def test_fetch_icmbio_priority_areas_uses_official_layer_and_wgs84(monkeypatch):
    payload = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {"name": "Área prioritária teste"},
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [
                        [[-55.0, -2.0], [-54.9, -2.0], [-54.9, -1.9], [-55.0, -2.0]]
                    ],
                },
            }
        ],
    }
    captured = {}

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return payload

    def fake_get(url, **kwargs):
        captured.update(url=url, kwargs=kwargs)
        return FakeResponse()

    monkeypatch.setattr("src.ingest.requests.get", fake_get)

    frame = fetch_icmbio_priority_areas([-56, -3, -54, -1])

    assert frame.crs.to_epsg() == 4326
    assert list(frame["name"]) == ["Área prioritária teste"]
    assert captured["kwargs"]["params"]["typeNames"] == "ICMBio:amazonia_2a_atualizacao"
    assert captured["kwargs"]["params"]["outputFormat"] == "application/json"
    assert captured["kwargs"]["params"]["bbox"].endswith(",EPSG:4326")
    assert captured["kwargs"]["timeout"] == 30


def test_fetch_icmbio_priority_areas_empty_response_has_predictable_schema(monkeypatch):
    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"type": "FeatureCollection", "features": []}

    monkeypatch.setattr(
        "src.ingest.requests.get", lambda *args, **kwargs: FakeResponse()
    )

    frame = fetch_icmbio_priority_areas([-56, -3, -54, -1])

    assert frame.empty
    assert list(frame.columns) == ["name", "geometry"]
    assert frame.crs.to_epsg() == 4326


def test_fetch_icmbio_priority_areas_propagates_api_failure(monkeypatch):
    def unavailable(*args, **kwargs):
        raise requests.RequestException("ICMBio unavailable")

    monkeypatch.setattr("src.ingest.requests.get", unavailable)

    with pytest.raises(requests.RequestException):
        fetch_icmbio_priority_areas([-56, -3, -54, -1])
