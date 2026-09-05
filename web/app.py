"""Streamlit dashboard for the Diagnóstico Territorial Preliminar (MVP)."""

import json
from datetime import UTC, datetime
from pathlib import Path

import folium
import pandas as pd
import requests
import streamlit as st
from streamlit_folium import st_folium

from src.deforestation import (
    interpret_deforestation_series,
    prodes_series_with_fallback,
    summarize_deforestation_series,
)
from src.diagnosis import (
    add_icmbio_evidence,
    add_overlap_evidence,
    build_preliminary_diagnosis,
)
from src.ingest import (
    PRODES_KIND_SHORT,
    classify_prodes_kind,
    fetch_icmbio_priority_areas,
    fetch_icmbio_ucs,
    read_and_validate_geojson,
    summarize_icmbio_overlap,
    summarize_sources,
)
from src.mrv import generate_report, render_text_report

st.set_page_config(
    page_title="Diagnóstico Territorial Preliminar", page_icon="🧭", layout="wide"
)
st.title("🧭 Diagnóstico Territorial Preliminar")
st.caption(
    "Este painel organiza dados públicos para uma leitura preliminar do território. "
    "Ele não substitui uma análise ambiental, jurídica ou técnica."
)

SAMPLES_DIR = Path(__file__).parents[1] / "data" / "samples"
options = {
    "Juruti — UMF V Mamuru-Arapiuns": str(SAMPLES_DIR / "juruti_mamuru.geojson"),
    "Área urbana (pré-diagnóstico)": str(SAMPLES_DIR / "example_urban.geojson"),
    "Área degradada (pré-diagnóstico)": str(SAMPLES_DIR / "example_degraded.geojson"),
    "Upload customizado": None,
}

selection = st.sidebar.selectbox("Área de análise", list(options))

uploaded = st.sidebar.file_uploader(
    "Carregar GeoJSON próprio",
    type=["geojson", "json"],
    disabled=selection != "Upload customizado",
)

try:
    if selection == "Upload customizado" and uploaded is not None:
        area, geometry_area_ha = read_and_validate_geojson(
            uploaded, file_size=uploaded.size
        )
    elif selection == "Upload customizado":
        st.info("Escolha um arquivo GeoJSON para iniciar o pré-diagnóstico.")
        st.stop()
    else:
        area, geometry_area_ha = read_and_validate_geojson(options[selection])
except ValueError as exc:
    st.error(str(exc))
    st.stop()

properties = area.iloc[0].to_dict()
area_name = properties.get("name") or selection
area_ha = round(geometry_area_ha, 2)

prodes_series, prodes_source = prodes_series_with_fallback(area, area_name=area_name)
prodes_kind = classify_prodes_kind(prodes_source)

area_bounds = area.total_bounds.tolist()
icmbio_source = "ICMBio — unidades de conservação federais (WFS)"
try:
    icmbio_ucs = fetch_icmbio_ucs(area_bounds)
    icmbio_overlap = summarize_icmbio_overlap(icmbio_ucs, area)
    icmbio_available = True
except (OSError, ValueError, requests.RequestException):
    icmbio_ucs = None
    icmbio_overlap = None
    icmbio_available = False

priority_source = (
    "ICMBio — Áreas Prioritárias para a Conservação da Biodiversidade - Amazônia"
)
try:
    icmbio_priority_areas = fetch_icmbio_priority_areas(area_bounds)
    priority_overlap = summarize_icmbio_overlap(icmbio_priority_areas, area)
    priority_available = True
except (OSError, ValueError, requests.RequestException):
    icmbio_priority_areas = None
    priority_overlap = None
    priority_available = False

if prodes_kind == "down":
    prodes_status = "unavailable"
elif prodes_kind == "empty":
    prodes_status = "empty"
else:
    prodes_status = "ok"

diagnosis = build_preliminary_diagnosis(
    area_name, area_ha, prodes_series, "INPE PRODES", prodes_status
)
diagnosis = add_icmbio_evidence(
    diagnosis,
    icmbio_source,
    "consulta atual",
    icmbio_overlap,
    available=icmbio_available,
)
diagnosis = add_overlap_evidence(
    diagnosis,
    priority_source,
    "consulta atual",
    priority_overlap,
    subject_label="área prioritária",
    available=priority_available,
)

STATUS_LABELS = {
    "ok": "Dados disponíveis",
    "empty": "Sem dados na consulta",
    "unavailable": "Fonte indisponível",
}
PRODES_KIND_LABELS = {
    "live": "Dados ao vivo",
    "demo": "Demonstração local",
    "empty": "Sem dados para o recorte",
    "down": "Serviço indisponível",
}
overlap_uc = int((icmbio_overlap or {}).get("count", 0))
overlap_priority = int((priority_overlap or {}).get("count", 0))
overlap_total = overlap_uc + overlap_priority
source_summary = summarize_sources(prodes_kind, icmbio_available, priority_available)

st.subheader("Resumo inicial")
c1, c2, c3, c4 = st.columns(4)
c1.metric("Área analisada", area_name)
c1.caption(f"{area_name} · {area_ha:,.2f} ha")
c2.markdown("**Status do desmatamento**")
c2.markdown(f"### {PRODES_KIND_SHORT[prodes_kind]}")
c2.caption(f"{PRODES_KIND_LABELS[prodes_kind]} · INPE PRODES")
if icmbio_available and priority_available:
    c3.metric("Sobreposições encontradas", str(overlap_total))
    c3.caption("UCs + áreas prioritárias")
else:
    c3.metric("Sobreposições", "não verificadas")
    c3.caption("fonte(s) indisponível(is)")
c4.metric(str(source_summary["title"]), str(source_summary["value"]))
c4.caption(str(source_summary["detail"]))
uc_status = "disponível" if icmbio_available else "indisponível na consulta"
priority_status = "disponível" if priority_available else "indisponível na consulta"
st.write(f"UCs federais: **{uc_status}** · Áreas prioritárias: **{priority_status}**")

st.subheader("Desmatamento por ano")
st.caption("Área estimada de desmatamento em cada ano, em hectares.")
deforestation_summary = summarize_deforestation_series(prodes_series)
deforestation_text = interpret_deforestation_series(
    prodes_series, is_demo=(prodes_kind == "demo")
)
if prodes_kind == "demo":
    st.info("Série demonstrativa — ilustra o funcionamento; não é medição real.")
elif prodes_kind == "live":
    st.caption("Fonte: INPE PRODES.")
if deforestation_summary is not None:
    t1, t2, t3 = st.columns(3)
    t1.metric("Total no período", f"{deforestation_summary['total_ha']:,.0f} ha")
    t2.metric(
        "Maior registro",
        f"{deforestation_summary['peak_ha']:,.0f} ha "
        f"em {deforestation_summary['peak_year']}",
    )
    t3.metric(
        "Último ano",
        f"{deforestation_summary['last_ha']:,.0f} ha "
        f"em {deforestation_summary['last_year']}",
    )
    chart_data = pd.DataFrame(
        {
            "Ano": prodes_series.sort_index().index.astype(int),
            "Desmatamento estimado (ha)": prodes_series.sort_index().to_numpy(),
        }
    )
    st.bar_chart(chart_data, x="Ano", y="Desmatamento estimado (ha)")
    st.caption(f"Status: {PRODES_KIND_SHORT[prodes_kind]} · Fonte: {prodes_source}")
    if deforestation_text:
        st.write(deforestation_text)
    st.caption("Fonte e limitações")
    st.caption(
        f"Fonte: {prodes_source} · Limitação: cobertura restrita ao Pará e "
        "sujeita à disponibilidade da API."
    )
else:
    st.info("Não há dados disponíveis para este território no momento.")
    st.caption(
        "Isso não significa ausência de desmatamento; significa apenas que "
        "nenhuma série pôde ser consultada."
    )

st.subheader("Área selecionada")
map_center = [area.union_all().centroid.y, area.union_all().centroid.x]
m = folium.Map(location=map_center, zoom_start=10, tiles="OpenStreetMap")
folium.GeoJson(area.__geo_interface__, name="Área analisada").add_to(m)
if icmbio_ucs is not None and not icmbio_ucs.empty:
    folium.GeoJson(
        icmbio_ucs.__geo_interface__,
        name="Unidades de conservação federais (ICMBio)",
    ).add_to(m)
if icmbio_priority_areas is not None and not icmbio_priority_areas.empty:
    folium.GeoJson(
        icmbio_priority_areas.__geo_interface__,
        name="Áreas prioritárias para conservação (ICMBio)",
    ).add_to(m)
folium.LayerControl().add_to(m)
st_folium(m, width="100%", height=420)

evidence_titles = [
    "Histórico de desmatamento",
    "Unidades de conservação federais",
    "Áreas prioritárias para conservação",
]
st.subheader("Diagnóstico territorial")
for title, evidence in zip(evidence_titles, diagnosis.evidences):
    st.markdown(f"#### {title}")
    st.write(evidence.summary)
    status_label = STATUS_LABELS[evidence.status]
    if title == "Histórico de desmatamento" and prodes_kind == "demo":
        status_label = PRODES_KIND_LABELS["demo"]
    st.caption(
        f"Fonte: {evidence.source} · Período: {evidence.period} · "
        f"Status: {status_label}"
    )
    for limitation in evidence.limitations:
        st.caption(f"Limitação: {limitation}")

st.subheader("Limitações — O que esta análise não responde")
limitations = [
    "não confirma propriedade ou regularidade fundiária;",
    "não substitui licenciamento ambiental;",
    "não substitui vistoria de campo;",
    "não determina elegibilidade oficial para programas ou fundos;",
    "depende da cobertura e disponibilidade das fontes públicas;",
    "sobreposição cartográfica é indicativa, não conclusiva.",
]
for limitation in limitations:
    st.markdown(f"- {limitation}")

st.subheader("Relatório")
if st.button("Gerar relatório"):
    report = generate_report(
        {"name": area_name, "area_ha": area_ha},
        prodes_series,
        diagnosis,
        sources=[
            ("INPE PRODES", prodes_source),
            (icmbio_source, "consulta atual"),
            (priority_source, "consulta atual"),
        ],
        deforestation_source=prodes_source,
    )
    report_json = json.dumps(report, indent=2, default=str)
    st.download_button(
        "Baixar relatório JSON",
        report_json,
        "diagnostico_territorial.json",
        "application/json",
    )
    st.download_button(
        "Baixar versão texto",
        render_text_report(report),
        "diagnostico_territorial.txt",
        "text/plain",
    )

st.caption(f"Exportado: {datetime.now(UTC).isoformat(timespec='seconds')}UTC")
