# MRV Amazon Lite — Implementação (post-COP30 MVP)

Projeto inspirado no projeto CNPq RHAE Green Forest/UFRA/ACC.
Transforma o MRV que seria entregue para COP30 em ferramenta de implementação pós-COP30.

**Stack:** Python + Streamlit + Leaflet
**Tempo estimado:** 4-5h
**Local:** `/home/gaalbu/codigos/mrv-amazon-lite` (repo novo, não mexer em tokidachi)

---

## Etapa 1 — Fundação do repo (15min)

```bash
mkdir -p /home/gaalbu/codigos/mrv-amazon-lite
cd /home/gaalbu/codigos/mrv-amazon-lite
git init
```

Criar estrutura:
```
src/
  ingest.py
  carbon.py
  mrv.py
  tfff.py          # novo — elegibilidade TFFF
  planau.py        # novo — card PlaNAU
data/
  samples/
    juruti_mamuru.geojson   # UMF V Mamuru-Arapiuns
    example_urban.geojson   # exemplo urbano para PlaNAU
    example_degraded.geojson
web/
  app.py            # Streamlit app
requirements.txt
pyproject.toml
Makefile
Dockerfile
.github/workflows/ci.yml
.gitignore
LICENSE
README.md
```

Arquivos-chave a criar na Etapa 1 (só esqueleto vazio ou boilerplate mínimo):
- `requirements.txt` com: streamlit, folium, geopandas, shapely, requests, rasterio, pyproj
- `pyproject.toml` com nome `mrv-amazon-lite`, versão `0.1.0`
- `Makefile` com targets: `install`, `test`, `run` (= `streamlit run web/app.py`), `build`
- `.gitignore` padrão Python + .streamlit
- `LICENSE` MIT

---

## Etapa 2 — Ingestão de dados abertos (60min)

### `src/ingest.py`

**Fontes (todas públicas, sem credencial):**

1. **PRODES/INPE (desmatamento histórico):**
   - WFS: `https://terrabrasilis.dpi.inpe.br/wfs/terrabrasilis`
   - Layer: `prodes_para_q`
   - Returns GeoJSON com geometria + área desmatada por ano
   - Usar `requests.get` com CQL filter para bounding box do polígono de entrada

2. **DETER/INPE (alertas recentes):**
   - WFS: `https://terrabrasilis.dpi.inpe.br/wfs/terrabrasilis`
   - Layer: `deter_para_q`
   - Últimos 12 meses

3. **MapBiomas (cobertura do solo):**
   - API: `https://data.mapbiomas.org/api/v2/`
   - Coleção 9 (2023 é a mais recente estável; coleção 10 sai ~out/2026)
   - Endpoint: `GET /series?query=...` ou fallback: CSV estático baixado uma vez
   - Usar proxy Python se API não responder direto

**Implementação:**
```python
# src/ingest.py
def fetch_prodes(bbox: list[float, float, float, float], years: range = range(2016, 2025)) -> gpd.GeoDataFrame:
    """bbox = [west, south, east, north]. Retorna GeoDataFrame com colunas [geometry, area_ha, year]."""

def fetch_deter(bbox: list[float, float, float, float], months: int = 12) -> gpd.GeoDataFrame:
    """Retorna alertas últimos N meses."""

def fetch_mapbiomas(collection: int = 9, year: int = 2023, state: str = "PA") -> pd.DataFrame:
    """Fallback: lê CSV local em data/mapbiomas_pa_2023.csv."""

def compute_deforestation_series(prodes_gdf: gpd.GeoDataFrame, target_area: gpd.GeoDataFrame) -> pd.Series:
    """Interseção PRODES x polígono alvo → série temporal de área desmatada/ano."""
```

**Polígono Juruti/Mamuru:**
- Criar `data/samples/juruti_mamuru.geojson` com bounding box aproximado da UMF V Glebas Mamuru-Arapiuns
- Coordenadas: Juruti centro ≈ [-56.05, -2.42], raio ~15km
- Usar polígono simplificado retangular para demo (não precisa de shapefile real)
- Aproximação: `[[-56.15, -2.55], [-55.95, -2.55], [-55.95, -2.29], [-56.15, -2.29]]`

**Testes:**
```python
# tests/test_ingest.py
def test_fetch_prodes_returns_gdf():
    """Verifica que fetch_prodes retorna GeoDataFrame com colunas esperadas."""

def test_bbox_validation():
    """bbox com south > north deve levantar ValueError."""

def test_compute_deforestation_series():
    """Mock PRODES data, verificar série por ano."""
```

---

## Etapa 3 — Motor carbono ARR simplificado (60min)

### `src/carbon.py`

**Parâmetros (config JSON em `src/config.json`):**
```json
{
  "methodology": "VCS_VM0047_lite",
  "ipcc_biomass_amazon": {
    "terra_firme": {"mean_tco2e_ha": 220, "min": 150, "max": 300},
    "varzea": {"mean_tco2e_ha": 180, "min": 100, "max": 250},
    "igapo": {"mean_tco2e_ha": 150, "min": 80, "max": 220}
  },
  "vcs_params": {
    "crediting_period_years": 30,
    "leakage_factor": 0.10,
    "buffer_pool": 0.20,
    "discount_rate": 0.05
  },
  "cop30_legacy": {
    "tfff_eligible": true,
    "note": "Parâmetros alinhados ao post-COP30: TFFF exige resultados comprovados em conservação"
  }
}
```

**Implementação:**
```python
# src/carbon.py
@dataclass
class CarbonEstimate:
    area_ha: float
    biomass_type: str  # "terra_firme", "varzea", "igapo"
    baseline_tco2e_ha: float
    restoration_tco2e_ha: float
    gross_vcu: float          # restoration * area * years
    leakage_deduction: float  # gross * leakage_factor
    buffer_deduction: float   # (gross - leakage) * buffer_pool
    net_vcu: float            # gross - leakage - buffer
    uncertainty_range: tuple[float, float]  # (min, max)
    methodology_note: str

def estimate_vcu(
    area_ha: float,
    biomass_type: str = "terra_firme",
    crediting_years: int = 30,
    config: dict | None = None
) -> CarbonEstimate:
    """Estimativa ARR simplificada VCS VM0047 lite."""

def estimate_vcu_range(
    area_ha: float,
    biomass_type: str = "terra_firme",
    crediting_years: int = 30
) -> tuple[CarbonEstimate, CarbonEstimate]:
    """Retorna (estimate_min, estimate_max) usando ranges IPCC."""
```

**Fórmula base:**
```
gross = restoration_rate * area_ha * tco2e_ha * years
  (restoration_rate ≈ 0.8 para Amazônia, conforme IPAM)

leakage = gross * 0.10
pool    = (gross - leakage) * 0.20
net     = gross - leakage - pool

uncertainty: ±30% em cima do net (faixa IPCC)
```

**Testes:**
```python
# tests/test_carbon.py
def test_vcu_100ha_terra_firme():
    """100ha terra firme, 30 anos → ~52.800 net VCU (estimativa)"""
    est = estimate_vcu(100, "terra_firme", 30)
    assert est.net_vcu > 40000
    assert est.net_vcu < 70000

def test_vcu_range():
    """Range não deve ser negativo."""
    lo, hi = estimate_vcu_range(100)
    assert lo.net_vcu > 0
    assert hi.net_vcu > lo.net_vcu

def test_leakage_and_buffer():
    """Verifica que leakage e buffer são deduzidos corretamente."""
    est = estimate_vcu(100, "terra_firme", 30)
    assert est.leakage_deduction > 0
    assert est.buffer_deduction > 0
    assert est.net_vcu < est.gross_vcu
```

---

## Etapa 4 — Módulo TFFF (pós-COP30) (30min)

### `src/tfff.py`

**Regras de elegibilidade TFFF (baseado Green Forest COP30 + gov.br):**
O TFFF paga US$5/ha/ano para países que provem conservação. Para área individual:

```python
# src/tfff.py
@dataclass
class TFFFCheck:
    area_ha: float
    deforestation_pct_10yr: float     # % desmatada nos últimos 10 anos
    is_indigenous_or_traditional: bool
    has_legal_reservation: bool       # RL > 0 (via CAR simulado)
    has_management_plan: bool         # PMFS ou equivalente
    eligible: bool
    estimated_payment_usd_year: float  # ~US$5/ha/ano se elegível
    reasons: list[str]
    source: str  # "TFFF/Belém/COP30 nov 2025"

def check_tfff_eligibility(
    deforestation_pct: float,
    has_indigenous: bool = False,
    has_rl: bool = True,
    has_pmfs: bool = False
) -> TFFFCheck:
    """Verifica elegibilidade simplificada para TFFF."""

TFFF_RATE_USD_HA_YEAR = 5.0
```

**Critérios (simplificados, para MVP):**
1. Desmatamento acumulado 10 anos < 5% da área → OK
2. Se indígena/tradicional → bônus 1.5x
3. Se PMFS ativo → confirma elegibilidade
4. Se desmatamento > 20% → ineligível

**Testes:**
```python
# tests/test_tfff.py
def test_eligible_low_deforestation():
    check = check_tfff_eligibility(0.02)
    assert check.eligible
    assert check.estimated_payment_usd_year == 5.0

def test_ineligible_high_deforestation():
    check = check_tfff_eligibility(0.25)
    assert not check.eligible

def test_indigenous_bonus():
    check_ind = check_tfff_eligibility(0.02, has_indigenous=True)
    assert check_ind.estimated_payment_usd_year == 7.5
```

---

## Etapa 5 — Módulo PlaNAU (pós-COP30) (30min)

### `src/planau.py`

**Regras PlaNAU (baseado Green Forest 17/11/2025):**
O PlaNAU é para áreas urbanas, então verifica se polígono é urbano e calcula déficit de cobertura arbórea:

```python
# src/planau.py
@dataclass
class PlanauCheck:
    area_ha: float
    is_urban: bool
    tree_cover_pct: float             # % cobertura arbórea atual
    tree_count_estimate: int          # ~100 árvores/ha (ref.= 3/rua = ~100/ha)
    deficit_trees: int                # para atingir meta 3 árvores/rua
    area_verde_gap_ha: float          # gap para 360k ha nacionais (proporcional)
    priority_level: str               # "alta", "média", "baixa"
    estimated_cost_brl: float         # ~R$500/árvore plantada (ref)
    source: str                       # "PlaNAU/COP30 nov 2025"

def check_planau_eligibility(
    is_urban: bool,
    tree_cover_pct: float,
    area_ha: float
) -> PlanauCheck | None:
    """ Retorna None se não for urbano. """

PLANAU_TARGET_TREES_PER_HA = 100
PLANAU_COST_PER_TREE_BRL = 500
```

**Critérios:**
- Se `is_urban=False` → retorna None (não se aplica)
- Priority alta: tree_cover < 15% (ilhas de calor)
- Priority média: 15-30%
- Priority baixa: > 30%

**Testes:**
```python
# tests/test_planau.py
def test_non_urban_returns_none():
    assert check_planau_eligibility(False, 0.2, 100) is None

def test_urban_low_cover():
    check = check_planau_eligibility(True, 0.10, 50)
    assert check.priority_level == "alta"
    assert check.deficit_trees > 0
```

---

## Etapa 6 — Dashboard Streamlit (60min)

### `web/app.py`

**Layout:**
```
┌──────────────────────────────────────────────────┐
│  🌳 MRV Amazon Lite — Pós-COP30                  │
│  Polígono: [input] ou seleção pré-definida       │
│  [Juruti/Mamuru] [Urban Demo] [Custom Upload]    │
├──────────────────────────────────────────────────┤
│                                                  │
│  ┌──────────────┐  ┌──────────────────────────┐  │
│  │ MAPA         │  │ GRÁFICO SÉRIE PRODES     │  │
│  │ (Folium)     │  │ (Plotly/Streamlit chart)  │  │
│  │              │  │                           │  │
│  └──────────────┘  └──────────────────────────┘  │
│                                                  │
│  ┌─────────────────────────────────────────────┐ │
│  │ CARBON ESTIMATE CARD                        │ │
│  │ VCU estimado: XX.XXX tCO2e (30 anos)       │ │
│  │ Faixa: XX.XXX - YY.YYY                     │ │
│  │ Método: ARR VCS VM0047 lite                 │ │
│  └─────────────────────────────────────────────┘ │
│                                                  │
│  ┌──────────────────┐ ┌──────────────────────┐  │
│  │ TFFF ELIGIBILITY │ │ PlaNAU ELIGIBILITY   │  │
│  │ (verde/vermelho) │ │ (urbano se aplica)   │  │
│  │ US$X.XXX/ano     │ │ Prioridade: alta     │  │
│  │ Post-COP30 TFFF  │ │ PlaNAU COP30         │  │
│  └──────────────────┘ └──────────────────────┘  │
│                                                  │
│  [Gerar Relatório MRV JSON] [Baixar PDF]         │
└──────────────────────────────────────────────────┘
```

**Implementação:**
```python
# web/app.py
import streamlit as st
import folium
from streamlit_folium import st_folium
import json

st.set_page_config(page_title="MRV Amazon Lite", layout="wide")

# Sidebar
st.sidebar.title("MRV Amazon Lite")
option = st.sidebar.selectbox("Área de análise", [
    "Juruti — UMF V Mamuru-Arapiuns",
    "Área urbana (demo PlaNAU)",
    "Upload customizado"
])

if option == "Juruti — UMF V Mamuru-Arapiuns":
    geojson_path = "data/samples/juruti_mamuru.geojson"
elif option == "Área urbana (demo PlaNAU)":
    geojson_path = "data/samples/example_urban.geojson"

# ... renderizar mapa, gráficos, cards ...

# Botão gerar relatório
if st.button("Gerar Relatório MRV"):
    report = {
        "version": "1.0",
        "generated_at": datetime.now().isoformat(),
        "area": {"name": option, "ha": area_ha},
        "deforestation_series": deforestation_dict,
        "carbon_estimate": asdict(carbon_est),
        "tfff": asdict(tfff_check) if tfff_check else None,
        "planau": asdict(planau_check) if planau_check else None,
        "disclaimer": "Estimativa educacional — não substitui certificação VCS/Gold Standard. Fontes: INPE PRODES/DETER, IPCC 2019, TFFF/COP30 Belém."
    }
    st.download_button("Download JSON", json.dumps(report, indent=2), "mrv_report.json")
```

**GeoJSON samples (dentro de `data/samples/`):**

`juruti_mamuru.geojson`:
```json
{
  "type": "FeatureCollection",
  "features": [{
    "type": "Feature",
    "properties": {"name": "UMF V Mamuru-Arapiuns", "municipality": "Juruti", "state": "PA"},
    "geometry": {
      "type": "Polygon",
      "coordinates": [[[-56.15, -2.55], [-55.95, -2.55], [-55.95, -2.29], [-56.15, -2.29], [-56.15, -2.55]]]
    }
  }]
}
```

`example_urban.geojson`:
```json
{
  "type": "FeatureCollection",
  "features": [{
    "type": "Feature",
    "properties": {"name": "Centro Belém", "is_urban": true, "tree_cover_pct": 0.12},
    "geometry": {
      "type": "Polygon",
      "coordinates": [[[-48.52, -1.47], [-48.47, -1.47], [-48.47, -1.43], [-48.52, -1.43], [-48.52, -1.47]]]
    }
  }]
}
```

`example_degraded.geojson`:
```json
{
  "type": "FeatureCollection",
  "features": [{
    "type": "Feature",
    "properties": {"name": "Área degradada (demo)", "deforestation_pct_10yr": 0.35},
    "geometry": {
      "type": "Polygon",
      "coordinates": [[[-55.5, -3.5], [-55.3, -3.5], [-55.3, -3.3], [-55.5, -3.3], [-55.5, -3.5]]]
    }
  }]
}
```

---

## Etapa 7 — Relatório MRV (20min)

### `src/mrv.py`

Gera relatório JSON rastreável com hash SHA-256:
```python
# src/mrv.py
import hashlib, json
from datetime import datetime, timezone

def generate_report(area_info: dict, deforestation: pd.Series, carbon: CarbonEstimate,
                    tfff: TFFFCheck | None, planau: PlanauCheck | None) -> dict:
    report = {
        "version": "1.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "methodology": "ARR VCS VM0047 lite (educacional)",
        "area": area_info,
        "deforestation": {"series": deforestation.to_dict(), "source": "INPE PRODES"},
        "carbon_estimate": {
            "net_vcu": carbon.net_vcu,
            "uncertainty": list(carbon.uncertainty_range),
            "biomass_type": carbon.biomass_type,
            "period_years": 30,
        },
        "post_cop30": {
            "tfff": {"eligible": tfff.eligible, "payment_usd_year": tfff.estimated_payment_usd_year} if tfff else None,
            "planau": {"priority": planau.priority_level, "deficit_trees": planau.deficit_trees} if planau else None,
        },
        "disclaimer": "Estimativa educacional — não substitui certificação VCS/Gold Standard. "
                       "Fontes: INPE PRODES/DETER, IPCC 2019, TFFF Belém/COP30.",
        "sources": ["INPE PRODES", "INPE DETER", "IPCC 2019", "VCS VM0047", "TFFF COP30 Belém 2025"],
        "inspired_by": "Projeto CNPq RHAE 443538/2024-7 — Green Forest/UFRA/ACC"
    }
    report_bytes = json.dumps(report, sort_keys=True).encode()
    report["checksum_sha256"] = hashlib.sha256(report_bytes).hexdigest()
    return report
```

---

## Etapa 8 — CI + Qualidade (15min)

### `.github/workflows/ci.yml`
```yaml
name: CI
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.11" }
      - run: pip install -r requirements.txt
      - run: pytest tests/ -v
```

### Ruff lint (adicionar ao requirements.txt: `ruff`)
```bash
ruff check src/ tests/
ruff format src/ tests/
```

Rodar na máquina antes de commitar:
```bash
ruff check src/ tests/ && ruff format src/ tests/ && pytest tests/ -v
```

---

## Etapa 9 — README.md (15min)

Conteúdo mínimo:
```markdown
# MRV Amazon Lite

Pós-COP30 MVP: simulador ARR + monitor desmatamento + elegibilidade TFFF/PlaNAU
para áreas na Amazônia, usando dados abertos.

Inspirado no projeto CNPq RHAE 443538/2024-7
(Green Forest / UFRA / Amazon Connection Carbon).

## O que faz

1. Puxa séries PRODES/DETER para qualquer polígono (ou pontos de demo)
2. Calcula VCUs estimados (ARR VCS VM0047 lite, 30 anos)
3. Verifica elegibilidade **TFFF** (Tropical Forests Forever Facility — US$6,7bi, COP30 Belém)
4. Verifica elegibilidade **PlaNAU** (Plano Nacional de Arborização Urbana — COP30)
5. Gera relatório MRV JSON rastreável (hash SHA-256)

## Como rodar

```bash
git clone https://github.com/Gaalbu/mrv-amazon-lite.git
cd mrv-amazon-lite
pip install -r requirements.txt
streamlit run web/app.py
```

## Limitações

- Estimativa **educacional**, não substitui certificação VCS/Gold Standard
- Biomassa baseada em tabelas IPCC 2019 por bioma (não inventário local)
- Elegibilidade TFFF/PlaNAU é simplificada — uso real requer validação técnica
```

---

## Etapa 10 — Commit + GitHub (5min)

```bash
cd /home/gaalbu/codigos/mrv-amazon-lite
git add .
git commit -m "feat: MRV Amazon Lite — post-COP30 MVP

ARR simulator + PRODES/DETER monitoring + TFFF/PlaNAU eligibility
inspired by CNPq RHAE 443538/2024-7 (Green Forest/UFRA/ACC).

COP30 Belém delivered TFFF (US$6.7bi), PlaNAU, Lei 15.190/2025.
This repo operationalizes the MRV platform promised for Q3 2025."

gh repo create Gaalbu/mrv-amazon-lite --public \
  --description="MRV Amazon Lite: ARR simulator + TFFF/PlaNAU post-COP30 — open source PoC" \
  --source=. --push

gh release create v0.1.0 --title "v0.1.0 — Post-COP30 MVP" \
  --notes "ARR simulation + PRODES monitoring + TFFF/PlaNAU eligibility. Inspired by Green Forest/UFRA CNPq project."
```

---

## Etapa 11 — Post LinkedIn (hoje)

```
Amazônia + Dados Abertos + Pós-COP30: lancei o MRV Amazon Lite

A COP30 aconteceu em Belém (10-21/11/2025) e entregou TFFF (US$6,7bi),
PlaNAU e a Lei 15.190/2025. O projeto CNPq RHAE da @Consultoria Green Forest
/ UFRA / ACC previa uma plataforma MRV para apresentação na COP30.

Agora, pós-COP30, transformei aquela ideia em MVP open-source:

• Puxa séries PRODES/DETER para qualquer polígono na Amazônia
• Calcula VCUs estimados (ARR VCS VM0047 lite, 30 anos)
• Verifica elegibilidade TFFF e PlaNAU em minutos
• Gera relatório MRV JSON rastreável

Demo: [link GitHub Pages]
Repo: github.com/Gaalbu/mrv-amazon-lite
Replique: git clone && pip install -r requirements.txt && streamlit run web/app.py

Dados: INPE PRODES/DETER, IPCC 2019, TFFF/Belém.
Ferramenta educacional — não substitui certificação VCS.

Próximo passo: integrar CAR/SIGEF como previsto no projeto CNPq.

@ConsultoriaGreenForest @ufra_oficial @cop30nobrasil

#COP30 #TFFF #PlaNAU #MRV #CarbonoAmazônia #Geotecnologias #OpenSource
```

**Tags:** @ConsultoriaGreenForest, @ufra_oficial, (ACC se tiver LinkedIn)
**Hashtags:** #COP30 #TFFF #PlaNAU #MRV #CarbonoAmazônia #Geotecnologias #OpenSource

---

## Notas

- Se API MapBiomas falhar durante build: usar CSV estático em `data/mapbiomas_pa_2023.csv`
- PRODES 2024 já disponível INPE (set/2025). DETER 2025 tempo real.
- Todas APIs INPE: `https://terrabrasilis.dpi.inpe.br` — não requerem autenticação
- Streamlit app roda em `localhost:8501`, GitHub Pages fica com README estático
