"""Streamlit dashboard for the MRV Amazon Lite educational MVP."""

import json
from datetime import UTC, datetime
from pathlib import Path

import folium
import geopandas as gpd
import pandas as pd
import streamlit as st
from streamlit_folium import st_folium

from src.carbon import estimate_vcu, estimate_vcu_range
from src.ingest import compute_deforestation_series, fetch_prodes
from src.mrv import generate_report
from src.planau import check_planau_eligibility
from src.tfff import check_tfff_eligibility

st.set_page_config(page_title="MRV Amazon Lite", page_icon="🌳", layout="wide")
st.title("🌳 MRV Amazon Lite — Pós-COP30")
st.caption("MVP educacional: resultados indicativos, não certificação de carbono.")

SAMPLES_DIR = Path(__file__).parents[1] / "data" / "samples"
options = {
    "Juruti — UMF V Mamuru-Arapiuns": str(SAMPLES_DIR / "juruti_mamuru.geojson"),
    "Área urbana (demo PlaNAU)": str(SAMPLES_DIR / "example_urban.geojson"),
    "Área degradada (demo TFFF)": str(SAMPLES_DIR / "example_degraded.geojson"),
    "Upload customizado": None,
}

selection = st.sidebar.selectbox("Área de análise", list(options))

uploaded = st.sidebar.file_uploader(
    "Carregar GeoJSON próprio",
    type=["geojson", "json"],
    disabled=selection != "Upload customizado",
)

if selection == "Upload customizado" and uploaded is not None:
    area = gpd.read_file(uploaded)
else:
    area = gpd.read_file(options[selection])

if area.empty:
    st.error("Polígono vazio — carregue um GeoJSON com ao menos um feature.")
    st.stop()

area = area.to_crs("EPSG:4326")
properties = area.iloc[0].to_dict()
area_ha = st.sidebar.number_input("Área (ha)", min_value=0.0, value=100.0, step=10.0)
biomass = st.sidebar.selectbox("Tipo de biomassa", ["terra_firme", "varzea", "igapo"])
deforestation = float(properties.get("deforestation_pct_10yr", 0.02))
tree_cover = float(properties.get("tree_cover_pct", 0.0))
is_urban = bool(properties.get("is_urban", False))

carbon = estimate_vcu(area_ha, biomass)
low, high = estimate_vcu_range(area_ha, biomass)
tfff = check_tfff_eligibility(deforestation, area_ha=area_ha)
planau = check_planau_eligibility(is_urban, tree_cover, area_ha)

demo_series = pd.Series(
    {year: 0.0 for year in range(2016, 2025)}, name="Área desmatada (ha)"
)
try:
    total_bounds = area.total_bounds
    bbox = [total_bounds[0], total_bounds[1], total_bounds[2], total_bounds[3]]
    prodes = fetch_prodes(bbox)
    if not prodes.empty:
        series = compute_deforestation_series(prodes, area)
        series = series.reindex(range(2016, 2025)).fillna(0.0)
        series.name = "Área desmatada (ha)"
        prodes_series = series
        prodes_source = "INPE PRODES (ao vivo)"
    else:
        prodes_series = demo_series
        prodes_source = "INPE PRODES (demo — sem dados na bbox)"
except Exception:  # noqa: BLE001 - fallback deliberado p/ API externa indisponível
    prodes_series = demo_series
    prodes_source = "INPE PRODES (fallback demo — API indisponível)"

left, right = st.columns(2)
left.metric("VCU líquido estimado (30 anos)", f"{carbon.net_vcu:,.0f} tCO₂e")
left.write(f"Faixa IPCC: {low.net_vcu:,.0f} – {high.net_vcu:,.0f} tCO₂e")
right.metric("TFFF estimado / ano", f"US$ {tfff.estimated_payment_usd_year:,.2f}")
right.write("Elegível" if tfff.eligible else "Não elegível")
st.caption("TFFF/PlaNAU: simulação ilustrativa pós-COP30 Belém")

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
st_folium(m, width="100%", height=420)

st.subheader("PlaNAU")
if planau:
    st.write(
        f"Prioridade: **{planau.priority_level}** · déficit: **{planau.deficit_trees:,} árvores** · custo estimado: R$ {planau.estimated_cost_brl:,.2f}"
    )
else:
    st.info("PlaNAU não se aplica: a área selecionada não está marcada como urbana.")


def text_report(report: dict) -> str:
    lines = [
        "MRV Amazon Lite — Relatório educacional",
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
    lines.append(f"VCU líquido (30 anos): {ce['net_vcu']:,.0f} tCO₂e")
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
