# MRV Amazon Lite — Implementação (post-COP30 MVP)

> **Estado: IMPLEMENTADO e VERIFICADO (2026-09-02).** Este PLAN documenta o que foi construído
> e como reproduzir/validar. Divergências vs. o esboço original (Folium, Upload, PRODES, PDF,
> screenshots) foram resolvidas e estão registradas abaixo. O plano não é mais um roadmap, é um
> registro do sistema entregue + guia de manutenção.

Projeto inspirado no projeto CNPq RHAE Green Forest/UFRA/ACC.
Transforma o MRV que seria entregue para COP30 em ferramenta de implementação pós-COP30.

**Stack:** Python + Streamlit + Folium/Leaflet
**Local:** `/home/gaalbu/codigos/mrv-amazon-lite`

---

## Etapa 1 — Fundação do repo — ✅ CONCLUÍDA

Estrutura:
```
src/
  ingest.py
  carbon.py
  mrv.py
  tfff.py
  planau.py
  config.json
scripts/
  screenshots.py      # novo — automação de screenshots (Playwright)
data/
  samples/
    juruti_mamuru.geojson
    example_urban.geojson
    example_degraded.geojson
  mapbiomas_pa_2023.csv
web/
  app.py
tests/
  test_core.py
  test_ingest.py
requirements.txt
pyproject.toml
Makefile
Dockerfile
.github/workflows/ci.yml
.github/workflows/screenshots.yml   # novo — prova visual em CI (artefato)
.gitignore
LICENSE
README.md
```

- `pyproject.toml` com nome `mrv-amazon-lite`, versão `0.1.0` ✅
- `Makefile` targets: `install`, `test`, `run` (= `streamlit run web/app.py`), `build`, `screenshots` ✅
- `requirements.txt` com versões `==` pinadas ✅
- `LICENSE` MIT com autor (2026 Gabriel Alencar) ✅

---

## Etapa 2 — Ingestão de dados abertos — ✅ CONCLUÍDA

### `src/ingest.py`

- **PRODES/INPE:** `fetch_prodes(bbox, years)`, layer `prodes_para_q`, via WFS 2.0.0
  `https://terrabrasilis.dpi.inpe.br/wfs/terrabrasilis` com parâmetro `bbox` (não CQL —
  escolha de implementação; funcionalmente equivalente).
- **DETER/INPE:** `fetch_deter(bbox, months=12)`, layer `deter_para_q`, corte por data.
- **MapBiomas:** `fetch_mapbiomas(collection=9, year=2023, state="PA")` — fallback para CSV
  local `data/mapbiomas_pa_2023.csv` (header `state,year,class,area_ha`); se ausente, retorna
  DataFrame vazio com o schema.
- `compute_deforestation_series(prodes_gdf, target_area)` — overlay de interseção + área em
  `EPSG:6933` / ha, agrupado por ano.
- `_validate_bbox(bbox)` — valida `west<east` e `south<north`, lança `ValueError`.

**GeoJSON samples** (1:1 com o especificado):
- `data/samples/juruti_mamuru.geojson` — UMF V Mamuru-Arapiuns, Juruti/PA
- `data/samples/example_urban.geojson` — Centro Belém (is_urban, tree_cover 0.12)
- `data/samples/example_degraded.geojson` — área degradada (deforestation 0.35)

**Testes:** `tests/test_ingest.py` — `test_bbox_validation`, `test_fetch_prodes_returns_gdf`
(mock WFS, novo), `test_compute_deforestation_series`, `test_fetch_mapbiomas_fallback_has_schema`.

---

## Etapa 3 — Motor carbono ARR — ✅ CONCLUÍDA

### `src/config.json`
```json
{
  "methodology": "VCS_VM0047_lite",
  "ipcc_biomass_amazon": {
    "terra_firme": {"mean_tco2e_ha": 220, "min": 150, "max": 300},
    "varzea": {"mean_tco2e_ha": 180, "min": 100, "max": 250},
    "igapo": {"mean_tco2e_ha": 150, "min": 80, "max": 220}
  },
  "vcs_params": {"crediting_period_years": 30, "leakage_factor": 0.10, "buffer_pool": 0.20, "discount_rate": 0.05, "restoration_rate": 0.8},
  "cop30_legacy": {"tfff_eligible": true, "note": "Parâmetros alinhados ao post-COP30: TFFF exige resultados comprovados em conservação"}
}
```

### `src/carbon.py`
- `CarbonEstimate` (dataclass frozen, 10 campos)
- `estimate_vcu(area_ha, biomass_type, crediting_years, config)` — valida entradas
- `estimate_vcu_range(...)` → `(min, max)` via ranges IPCC

Fórmula:
```
gross = restoration_rate * area * tco2e_ha * years   # restoration_rate = 0.8
leakage = gross * 0.10
pool    = (gross - leakage) * 0.20
net     = gross - leakage - pool
uncertainty: ±30% sobre o net
```

> **Nota de precisão:** o esboço original dizia "100ha terra firme 30 anos → ~52.800 VCU".
> Isso é **incorreto** perante a fórmula. O valor real é `0.8 * 100 * 220 * 30 = 528.000 gross`
> → **380.160 net** (para `conservação`). O PLAN está corrigido; `tests/test_core.py:12`
> valida `380160`.

---

## Etapa 4 — Módulo TFFF — ✅ CONCLUÍDA

### `src/tfff.py`
- `TFFF_RATE_USD_HA_YEAR = 5.0`
- `TFFFCheck` (dataclass, 9 campos)
- `check_tfff_eligibility(deforestation_pct, has_indigenous, has_rl, has_pmfs, area_ha=1.0)`
  — `area_ha` foi adicionada à assinatura (melhoria retrocompatível, default 1.0)
  para o pagamento `area * 5 * multiplicador`.

Critérios: `eligible = desmate < 5% and has_rl`; `≥20%` → ineligível; bônus indígena `1.5x`.

---

## Etapa 5 — Módulo PlaNAU — ✅ CONCLUÍDA

### `src/planau.py`
- `PLANAU_TARGET_TREES_PER_HA = 100`, `PLANAU_COST_PER_TREE_BRL = 500`
- `PlanauCheck` (dataclass, 9 campos)
- `check_planau_eligibility(is_urban, tree_cover_pct, area_ha)` → `None` se não urbano

Prioridade: `alta <15%`, `média 15–30%`, `baixa >30%`.

---

## Etapa 6 — Dashboard Streamlit — ✅ CONCLUÍDA (com ajustes)

### `web/app.py`

Layout implementado:
- Título `🌳 MRV Amazon Lite — Pós-COP30`, `layout="wide"`
- **Sidebar:** `Área de análise` (combobox) + `Área (ha)` + `Tipo de biomassa`
- **4 opções de área:** Juruti/Mamuru, Área urbana (PlaNAU), Área degradada (TFFF) e
  **Upload customizado** (carrega GeoJSON próprio via `file_uploader`)
- **Mapa Folium/Leaflet** via `st_folium` + camada `folium.GeoJson`
- **Série PRODES** em `st.line_chart`, integrada ao **API real** com fallback:
  - Se `fetch_prodes`+`compute_deforestation_series` retornam dados → série real
  - Se falhar ou vazio → série demo (zeros), com `st.caption` indicando a fonte
- **Cards de métricas:** VCU líquido (30 anos) + Faixa IPCC; TFFF estimado/ano + Elegível/Não
- **PlaNAU:** prioridade/déficit/custo, ou `st.info` "PlaNAU não se aplica"
- **Disclaimer** (`st.caption`): "TFFF/PlaNAU: simulação ilustrativa pós-COP30 Belém"
- **Relatório:** botão "Gerar relatório MRV" → download JSON + download versão texto.
  O "Baixar PDF" do esboço foi substituído por export texto (leve, sem dependência pesada de PDF).

> **Decisões vs. esboço original:**
> - **Mapa:** usa `folium`+`st_folium` (não `st.map`), conforme `requirements.txt:2-3`.
> - **Upload:** adicionado como 4ª opção, mantendo as 3 demos.
> - **PRODES:** plugado ao API real com fallback de demo (a demo nunca trava por API externa).
> - **PDF→texto:** substituído por download `.txt` para não inflar dependências.

---

## Etapa 7 — Relatório MRV — ✅ CONCLUÍDA

### `src/mrv.py`
`generate_report(area_info, deforestation, carbon, tfff, planau)` → dict com:
- `version`, `generated_at` (UTC ISO), `methodology`
- `area`, `deforestation` (`series` + `source`), `carbon_estimate` (via `asdict`)
- `post_cop30.tfff` / `post_cop30.planau`
- `disclaimer`, `source`, `inspired_by` (CNPq RHAE 443538/2024-7 — Green Forest/UFRA/ACC)
- `checksum_sha256` (SHA-256 de `json.dumps(sort_keys=True)`)

---

## Etapa 8 — CI + Qualidade — ✅ CONCLUÍDA (estendida)

### `.github/workflows/ci.yml`
`lint`: `ruff check src tests web` · `tests`: `pytest tests/ -v` (Python 3.11).

### `.github/workflows/screenshots.yml` — NOVO
Roda sob demanda (`workflow_dispatch`), instala Playwright+chromium, executa
`scripts/screenshots.py` e faz **upload dos PNGs como artefato** (GitHub Actions → Downloads).

Comandos de qualidade (validados 2026-09-02):
```bash
python -m pytest tests/ -v        # 10 passed
ruff check src tests web scripts   # All checks passed!
ruff format src tests web scripts  # already formatted
```

---

## Etapa 9 — README.md — ✅ CONCLUÍDA

Documenta: inspirado por (CNPq), O que faz (ARR/PRODES-DETER/TFFF/PlaNAU/MRV), Como rodar em
3 comandos, Fontes, Limitações (com disclaimer exato), testes/lint.

---

## Etapa 10 — Commit + GitHub — ✅ CÓDIGO FEITO / RELEASE PENDENTE

`git log`: `a6a4cb7`, `d6014fb`, `317bef2` — branch `main` sincronizada com `origin/main`.
**Pendente:** `gh release create v0.1.0` (decisão editorial — ver CHECKLIST).

---

## Etapa 11 — Post LinkedIn — ⏸️ PENDENTE (editorial)

Ainda não publicado. Template em CHECKLIST.md; pendente revisão final.

---

## NOVA Etapa 12 — Screenshots automatizadas — ✅ CONCLUÍDA

### `scripts/screenshots.py` (Playwright + playwright-chromium)

Gera os 3 PNGs dos use cases do dashboard diretamente no seu PC local:
```
01_juruti_mamuru.png      → Juruti (VCU ~380k + TFFF elegível + PlaNAU N/A)
02_area_urbana_planau.png → Prioridade alta + déficit de árvores
03_area_degradada_tfff.png→ TFFF não elegível
```

**Como rodar (local):**
```bash
.venv/bin/pip install playwright
.venv/bin/python -m playwright install chromium
make screenshots            # == python scripts/screenshots.py --out screenshots
```

Comportamento:
1. Inicia o Streamlit em subprocesso headless (`--server.port`, default 8501)
2. Espera o servidor responder (healthcheck com timeout)
3. Abre o app no Chromium (viewport 1440x900)
4. Para cada use case: seleciona a opção no combobox (clicando no input `[role="combobox"]`,
   digitando um filtro e clicando no `[role="option"]` correspondente — necessário porque o
   Streamlit 1.63 usa combobox, não `<select>` nativo)
5. **Verifica** que o marcador esperado apareceu no body (ex.: "Não elegível") antes de salvar
6. Salva `full_page` PNG em `--out` (default `screenshots/`)

**Validação automática no CI:** `.github/workflows/screenshots.yml` faz o mesmo e publica como
artefato, permitindo baixar os PNGs pelo GitHub Actions sem ter browser local.

> **Nota:** `screenshots/` está no `.gitignore` (artefatos gerados local). Para versionar os PNGs
> no repo, remover a linha `screenshots/` do `.gitignore`.

---

## Notas de manutenção

- **PRODES/DETER:** API INPE não requer autenticação, mas pode ficar lenta/indisponível — o app
  roda o fallback demo sem travar (ver `web/app.py` try/except com `# noqa: BLE001`).
- **Streamlit selectbox:** versões ≥1.5x usam combobox (não `<select>`); o script de screenshots
  já trata isso. Se o Streamlit mudar a estrutura DOM, atualizar `select_area` em `screenshots.py`.
- **Dockerfile (3.12)** vs **CI (3.11):** ambos atendem `requires-python >=3.11`.
- **PDF:** não gerado; export em JSON e texto. Se necessário futuramente, adicionar `reportlab`
  em `requirements.txt` e um botão extra.
