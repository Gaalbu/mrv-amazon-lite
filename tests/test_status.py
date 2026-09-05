import pytest

from src.ingest import (
    PRODES_KIND_SHORT,
    classify_prodes_kind,
    summarize_sources,
)


def test_demo_series_is_not_counted_as_live_source():
    summary = summarize_sources("demo", True, True)

    assert summary["live_count"] == 2
    assert summary["value"] == "2 de 3"
    assert summary["title"] == "Fontes ao vivo"
    assert "demonstração local" in summary["detail"]


def test_live_series_is_counted_as_live_source():
    summary = summarize_sources("live", True, True)

    assert summary["live_count"] == 3
    assert summary["value"] == "3 de 3"


def test_unavailable_sources_are_distinct_from_demo():
    down = summarize_sources("down", True, True)
    demo = summarize_sources("demo", True, True)

    assert down["live_count"] == 2
    assert "demonstração local" not in down["detail"]
    assert "indisponível" in down["detail"]
    assert down["detail"] != demo["detail"]


@pytest.mark.parametrize(
    ("kind", "icmbio", "priority", "expected"),
    [
        ("empty", False, False, 0),
        ("down", False, False, 0),
        ("empty", True, False, 1),
        ("down", False, True, 1),
        ("demo", False, False, 0),
        ("live", False, False, 1),
    ],
)
def test_empty_and_down_never_inflate_live_count(kind, icmbio, priority, expected):
    assert summarize_sources(kind, icmbio, priority)["live_count"] == expected


@pytest.mark.parametrize(
    ("source", "kind"),
    [
        ("INPE PRODES (ao vivo)", "live"),
        ("INPE PRODES (demonstração local — API indisponível)", "demo"),
        ("INPE PRODES (demonstração local — sem dados no recorte)", "demo"),
        ("INPE PRODES (demonstração local - API indisponivel)", "demo"),
        ("INPE PRODES (serviço indisponível — sem dados para o recorte)", "down"),
        ("INPE PRODES (servico indisponivel — sem dados para o recorte)", "down"),
        ("INPE PRODES (sem dados para o recorte)", "empty"),
        ("qualquer outra fonte", "empty"),
    ],
)
def test_classify_prodes_kind_maps_source_strings(source, kind):
    assert classify_prodes_kind(source) == kind


def test_short_status_labels_fit_narrow_cards():
    assert set(PRODES_KIND_SHORT) == {"live", "demo", "empty", "down"}
    assert all(len(label) <= 12 for label in PRODES_KIND_SHORT.values())


@pytest.mark.parametrize("kind", ["live", "demo", "empty", "down"])
@pytest.mark.parametrize("icmbio", [True, False])
@pytest.mark.parametrize("priority", [True, False])
def test_source_summary_never_mentions_legacy_modules(kind, icmbio, priority):
    summary = summarize_sources(kind, icmbio, priority)
    text = f"{summary['title']} {summary['value']} {summary['detail']}"
    for marker in ["TFFF", "PlaNAU", "tCO2e", "tCO₂e", "US$", "VCU", "carbon"]:
        assert marker not in text
