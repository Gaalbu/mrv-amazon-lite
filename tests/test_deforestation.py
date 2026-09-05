import geopandas as gpd
import pandas as pd
import pytest
from shapely.geometry import Polygon

from src.deforestation import (
    compute_deforestation_series,
    interpret_deforestation_series,
    load_demo_deforestation_series,
    prodes_series_with_fallback,
    summarize_deforestation_series,
)


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


def test_summarize_deforestation_series_demo_juruti():
    series = load_demo_deforestation_series("UMF V Mamuru-Arapiuns")

    summary = summarize_deforestation_series(series)

    assert summary is not None
    assert summary["total_ha"] == pytest.approx(1420.0)
    assert summary["peak_ha"] == pytest.approx(240.0)
    assert summary["peak_year"] == 2019
    assert summary["last_ha"] == pytest.approx(110.0)
    assert summary["last_year"] == 2024
    assert summary["first_ha"] == pytest.approx(120.0)
    assert summary["first_year"] == 2016
    assert summary["count_years"] == 9


def test_summarize_deforestation_series_sorts_unordered_index():
    series = pd.Series(
        {2024: 110.0, 2016: 120.0, 2019: 240.0}, name="Área desmatada (ha)"
    )

    summary = summarize_deforestation_series(series)

    assert summary is not None
    assert summary["first_year"] == 2016
    assert summary["last_year"] == 2024
    assert summary["peak_year"] == 2019


def test_summarize_deforestation_series_empty_returns_none():
    assert summarize_deforestation_series(pd.Series(dtype=float)) is None


def test_interpret_last_below_first():
    series = load_demo_deforestation_series("UMF V Mamuru-Arapiuns")

    text = interpret_deforestation_series(series, is_demo=False)

    assert text == (
        "O último valor da série está abaixo do primeiro registro do período."
    )


def test_interpret_last_above_first():
    series = pd.Series({2020: 50.0, 2021: 80.0})

    text = interpret_deforestation_series(series, is_demo=False)

    assert text == (
        "O último valor da série está acima do primeiro registro do período."
    )


def test_interpret_stable_when_close():
    series = pd.Series({2020: 100.0, 2021: 102.0})

    text = interpret_deforestation_series(series, is_demo=False)

    assert text == (
        "Os valores variam ao longo do período, "
        "sem mudança clara entre o início e o fim."
    )


def test_interpret_demo_appends_demo_note_without_causal_claims():
    series = load_demo_deforestation_series("UMF V Mamuru-Arapiuns")

    text = interpret_deforestation_series(series, is_demo=True)

    assert text is not None
    assert "abaixo do primeiro registro" in text
    assert "demonstração local" in text
    assert "não representa uma conclusão real sobre o território" in text
    for claim in ["caiu", "aumentou", "queda", "aumento", "reduziu"]:
        assert claim not in text.lower()


def test_interpret_empty_returns_none():
    assert interpret_deforestation_series(pd.Series(dtype=float)) is None
