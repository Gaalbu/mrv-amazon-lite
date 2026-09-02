"""Streamlit dashboard for the MRV Amazon Lite educational MVP."""

import json
from pathlib import Path

import geopandas as gpd
import pandas as pd
import streamlit as st

from src.carbon import estimate_vcu, estimate_vcu_range
from src.mrv import generate_report
from src.planau import check_planau_eligibility
from src.tfff import check_tfff_eligibility

st.set_page_config(page_title="MRV Amazon Lite", page_icon="🌳", layout="wide")
st.title("🌳 MRV Amazon Lite — Pós-COP30")
st.caption("MVP educacional: resultados indicativos, não certificação de carbono.")

options = {
    "Juruti — UMF V Mamuru-Arapiuns": "juruti_mamuru.geojson",
    "Área urbana (demo PlaNAU)": "example_urban.geojson",
    "Área degradada (demo TFFF)": "example_degraded.geojson",
}
selection = st.sidebar.selectbox("Área de análise", list(options))
path = Path(__file__).parents[1] / "data" / "samples" / options[selection]
area = gpd.read_file(path)
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
prodes_series = pd.Series(
    {year: 0.0 for year in range(2016, 2025)}, name="Área desmatada (ha)"
)

left, right = st.columns(2)
left.metric("VCU líquido estimado (30 anos)", f"{carbon.net_vcu:,.0f} tCO₂e")
left.write(f"Faixa IPCC: {low.net_vcu:,.0f} – {high.net_vcu:,.0f} tCO₂e")
right.metric("TFFF estimado / ano", f"US$ {tfff.estimated_payment_usd_year:,.2f}")
right.write("Elegível" if tfff.eligible else "Não elegível")
st.caption("TFFF/PlaNAU: simulação ilustrativa pós-COP30 Belém")

st.subheader("Série PRODES")
st.line_chart(prodes_series)

st.subheader("Área selecionada")
st.map(area.to_crs("EPSG:4326").centroid)
st.subheader("PlaNAU")
if planau:
    st.write(
        f"Prioridade: **{planau.priority_level}** · déficit: **{planau.deficit_trees:,} árvores** · custo estimado: R$ {planau.estimated_cost_brl:,.2f}"
    )
else:
    st.info("PlaNAU não se aplica: a área selecionada não está marcada como urbana.")

if st.button("Gerar relatório MRV"):
    report = generate_report(
        {"name": properties.get("name", selection), "area_ha": area_ha},
        pd.Series({"demo": deforestation}),
        carbon,
        tfff,
        planau,
    )
    st.download_button(
        "Baixar relatório JSON",
        json.dumps(report, indent=2, default=str),
        "mrv_report.json",
        "application/json",
    )
