"""Streamlit dashboard for the Diagnóstico Territorial Preliminar."""

import json
from datetime import UTC, datetime
from pathlib import Path

import folium
import requests
import streamlit as st
from streamlit_folium import st_folium

from src.carbon import estimate_vcu, estimate_vcu_range
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
from src.mrv import generate_report
from src.planau import check_planau_eligibility
from src.tfff import check_tfff_eligibility

st.set_page_config(
    page_title="Diagnóstico Territorial Preliminar", page_icon="🧭", layout="wide"
)
st.title("🧭 Diagnóstico Territorial Preliminar")
st.caption(
    "Pré-diagnóstico territorial educacional, inspirado no projeto CNPq RHAE 443538/2024-7."
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
area_ha = st.sidebar.number_input(
    "Área calculada (ha)", min_value=0.0, value=round(geometry_area_ha, 2), step=10.0
)
biomass = st.sidebar.selectbox("Tipo de biomassa", ["terra_firme", "varzea", "igapo"])
deforestation = float(properties.get("deforestation_pct_10yr", 0.02))
tree_cover = float(properties.get("tree_cover_pct", 0.0))
is_urban = bool(properties.get("is_urban", False))

carbon = estimate_vcu(area_ha, biomass)
low, high = estimate_vcu_range(area_ha, biomass)
tfff = check_tfff_eligibility(deforestation, area_ha=area_ha)
planau = check_planau_eligibility(is_urban, tree_cover, area_ha)

prodes_series, prodes_source = prodes_series_with_fallback(area)
if "fallback" in prodes_source or "sem dados" in prodes_source:
    st.warning(prodes_source)

area_bounds = area.total_bounds.tolist()
icmbio_source = "ICMBio WFS — limiteucsfederais_a"
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

left, right = st.columns(2)
left.metric("Indicador de carbono complementar", f"{carbon.net_vcu:,.0f} tCO₂e")
left.write(f"Faixa IPCC de referência: {low.net_vcu:,.0f} – {high.net_vcu:,.0f} tCO₂e")
right.metric("TFFF estimado / ano", f"US$ {tfff.estimated_payment_usd_year:,.2f}")
right.write("Elegível" if tfff.eligible else "Não elegível")
st.caption(
    "TFFF/PlaNAU: simulação ilustrativa para leitura territorial, não decisão oficial"
)

st.subheader(f"Série PRODES — {prodes_source}")
if prodes_series.sum() > 0:
    st.line_chart(prodes_series)
else:
    st.line_chart(prodes_series)
    st.caption("Série sem dados reais na área: exibindo fallback (zeros).")

st.subheader("Área selecionada")
map_center = [area.union_all().centroid.y, area.union_all().centroid.x]
m = folium.Map(location=map_center, zoom_start=10, tiles="OpenStreetMap")
folium.GeoJson(area.__geo_interface__, name="Polígono").add_to(m)
if icmbio_ucs is not None and not icmbio_ucs.empty:
    folium.GeoJson(icmbio_ucs.__geo_interface__, name="UCs federais — ICMBio").add_to(m)
if icmbio_priority_areas is not None and not icmbio_priority_areas.empty:
    folium.GeoJson(
        icmbio_priority_areas.__geo_interface__,
        name="Áreas prioritárias — ICMBio",
    ).add_to(m)
st_folium(m, width="100%", height=420)

st.subheader("PlaNAU")
if planau:
    st.write(
        f"Prioridade: **{planau.priority_level}** · déficit: **{planau.deficit_trees:,} árvores** · custo estimado: R$ {planau.estimated_cost_brl:,.2f}"
    )
else:
    st.info("PlaNAU não se aplica: a área selecionada não está marcada como urbana.")

if "fallback" in prodes_source:
    prodes_status = "unavailable"
elif prodes_series.empty or "sem dados" in prodes_source:
    prodes_status = "empty"
else:
    prodes_status = "ok"

diagnosis = build_preliminary_diagnosis(
    properties.get("name") or selection,
    area_ha,
    prodes_series,
    "INPE PRODES",
    prodes_status,
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
st.subheader("Diagnóstico territorial")
for evidence in diagnosis.evidences:
    st.write(evidence.summary)
    st.caption(f"Fonte: {evidence.source} · Status: {evidence.status}")
st.write("Limitação: " + "; ".join(diagnosis.limitations))
st.write("Próximo passo: " + "; ".join(diagnosis.next_steps))


def text_report(report: dict) -> str:
    lines = [
        "Diagnóstico Territorial Preliminar — Relatório educacional",
        f"Gerado em: {report['generated_at']}",
        f"Metodologia: {report['methodology']}",
        f"Área: {report['area'].get('name', '')} — {report['area'].get('area_ha')} ha",
        "",
        "Série desmatamento (ha/ano):",
    ]
    for year, value in report["deforestation"]["series"].items():
        lines.append(f"  {year}: {value:,.2f}")
    lines.append("")
    ce = report["carbon_estimate"]
    lines.append(f"Indicador de carbono complementar: {ce['net_vcu']:,.0f} tCO₂e")
    lines.append(
        f"  Faixa IPCC: {ce['uncertainty_range'][0]:,.0f} – {ce['uncertainty_range'][1]:,.0f}"
    )
    pc = report["post_cop30"]
    if pc["tfff"]:
        lines.append(
            f"TFFF elegível: {pc['tfff']['eligible']} — US$ {pc['tfff']['estimated_payment_usd_year']:,.2f}/ano"
        )
    else:
        lines.append("TFFF: não avaliado")
    if pc["planau"]:
        lines.append(
            f"PlaNAU prioridade: {pc['planau']['priority_level']} — déficit {pc['planau']['deficit_trees']:,} árvores"
        )
    else:
        lines.append("PlaNAU: não se aplica (área não urbana)")
    diagnosis_report = report["diagnosis"]
    lines.append("")
    lines.append("Diagnóstico territorial:")
    lines.append(
        f"  Área: {diagnosis_report['area_name']} — {diagnosis_report['area_ha']} ha"
    )
    for evidence in diagnosis_report["evidences"]:
        lines.append(
            f"  Evidência: {evidence['source']} — {evidence['status']} — {evidence['summary']}"
        )
        for limitation in evidence["limitations"]:
            lines.append(f"    Limitação da evidência: {limitation}")
    lines.append("  Limitações: " + "; ".join(diagnosis_report["limitations"]))
    lines.append("  Próximos passos: " + "; ".join(diagnosis_report["next_steps"]))
    lines.append("")
    lines.append(f"Checksum SHA-256: {report['checksum_sha256']}")
    lines.append(report["disclaimer"])
    return "\n".join(lines)


if st.button("Gerar relatório MRV"):
    report = generate_report(
        {"name": properties.get("name", selection), "area_ha": area_ha},
        prodes_series,
        carbon,
        tfff,
        planau,
        diagnosis,
    )
    report_json = json.dumps(report, indent=2, default=str)
    st.download_button(
        "Baixar relatório JSON",
        report_json,
        "mrv_report.json",
        "application/json",
    )

    st.download_button(
        "Baixar versão texto",
        text_report(report),
        "mrv_report.txt",
        "text/plain",
    )


st.caption(f"Exportado: {datetime.now(UTC).isoformat(timespec='seconds')}UTC")
