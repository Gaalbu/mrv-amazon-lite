"""Streamlit dashboard for the Diagnóstico Territorial Preliminar (MVP)."""

import json
from datetime import UTC, datetime
from pathlib import Path

import folium
import requests
import streamlit as st
from streamlit_folium import st_folium

from src.diagnosis import (
    add_icmbio_evidence,
    add_overlap_evidence,
    build_preliminary_diagnosis,
)
from src.ingest import (
    fetch_icmbio_priority_areas,
    fetch_icmbio_ucs,
    prodes_series_with_fallback,
    read_and_validate_geojson,
    summarize_icmbio_overlap,
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

prodes_series, prodes_source = prodes_series_with_fallback(area)

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

if "fallback" in prodes_source:
    prodes_status = "unavailable"
elif prodes_series.empty or "sem dados" in prodes_source:
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
overlap_uc = int((icmbio_overlap or {}).get("count", 0))
overlap_priority = int((priority_overlap or {}).get("count", 0))
overlap_total = overlap_uc + overlap_priority

st.subheader("Resumo inicial")
c1, c2, c3, c4 = st.columns(4)
c1.metric("Área analisada", area_name)
c1.caption(f"Área calculada: {area_ha:,.2f} ha")
c2.metric("Status do desmatamento", STATUS_LABELS[prodes_status])
c2.caption("INPE PRODES")
if icmbio_available and priority_available:
    c3.metric("Sobreposições encontradas", str(overlap_total))
    c3.caption("UCs + áreas prioritárias")
else:
    c3.metric("Sobreposições", "não verificadas")
    c3.caption("fonte(s) indisponível(is)")
c4.metric("Fontes consultadas", "3")
c4.caption("PRODES: " + STATUS_LABELS[prodes_status])
uc_status = "disponível" if icmbio_available else "indisponível na consulta"
priority_status = "disponível" if priority_available else "indisponível na consulta"
st.write(f"UCs federais: **{uc_status}** · Áreas prioritárias: **{priority_status}**")

st.subheader("Histórico de desmatamento consultado")
if prodes_status != "ok":
    st.warning(
        "Não foi possível obter uma série real nesta consulta. O gráfico abaixo "
        "representa ausência de dados, não ausência de desmatamento."
    )
st.line_chart(prodes_series)
st.caption(f"Fonte: {prodes_source}")

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
    st.caption(
        f"Fonte: {evidence.source} · Período: {evidence.period} · "
        f"Status: {STATUS_LABELS[evidence.status]}"
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
