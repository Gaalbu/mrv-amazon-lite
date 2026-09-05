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
gross = restoration_rate * area * tco2e_ha * (years / baseline_years)   # restoration_rate = 0.8
leakage = gross * 0.10
pool    = (gross - leakage) * 0.20
net     = gross - leakage - pool
uncertainty: ±30% sobre o net
```

> **Correção metodológica (2026-09):** `tco2e_ha` (tabela IPCC) representa o **estoque** de
> carbono acumulado ao final do período-base de créditos (`crediting_period_years` = 30 em
> `config.json`), não uma taxa anual. A fórmula anterior multiplicava esse estoque pelo número
> de anos (`* years`), inflando o resultado em ~30x. A fórmula corrigida escala linearmente só
> quando `years` difere do período-base. Para 100ha terra firme, 30 anos:
> `gross = 0.8 * 100 * 220 * (30/30) = 17.600` → **net = 12.672 tCO2e** (antes: 380.160).
> `tests/test_core.py:12` valida `12672`.

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

`git log`: branch `main` sincronizada com `origin/main`.
**Concluído:** release `v0.1.0` publicada em https://github.com/Gaalbu/mrv-amazon-lite/releases/tag/v0.1.0.

---

## Etapa 11 — Post LinkedIn — ⏸️ PENDENTE (editorial)

Ainda não publicado. Template em CHECKLIST.md; requer confirmação final antes da comunicação pública.

---

## NOVA Etapa 12 — Screenshots automatizadas — ✅ CONCLUÍDA

### `scripts/screenshots.py` (Playwright + playwright-chromium)

Gera os 3 PNGs dos use cases do dashboard diretamente no seu PC local:
```
01_juruti_mamuru.png      → Juruti (VCU ~12,7k + TFFF elegível + PlaNAU N/A)
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

## NOVA Etapa 13 — Code review (REVIEW_PROMPT.md) — 🔧 CORREÇÕES PENDENTES

Duas rodadas de revisão seguindo `REVIEW_PROMPT.md` (critérios: correção técnica/fórmulas,
robustez/segurança, qualidade, ética/transparência). Veredito da 2ª rodada: **Aprovar** para
`gh release v0.1.0` — nenhum bloqueador. Já corrigidos nesta sessão (não repetir):

- ✅ `src/carbon.py` — fórmula de `gross_vcu` corrigida (não multiplica mais estoque IPCC ×
  `crediting_years` direto; agora escala por `crediting_years / baseline_years`). Teste
  `tests/test_core.py:12` validado com `12672` (era `380160`).
- ✅ `src/planau.py:45` — `area_verde_gap_ha` agora deriva de `deficit / PLANAU_TARGET_TREES_PER_HA`
  em vez de constante desconectada.
- ✅ `web/app.py:39-60` — leitura/reprojeção do GeoJSON de upload envolvida em `try/except`
  com mensagens amigáveis (`st.error` + `st.stop()`), incluindo checagem de `area.crs is None`.
- ✅ Referências desatualizadas a "VCU ~380k" corrigidas para "~12,7k" em
  `scripts/screenshots.py:11`, `CHECKLIST.md:58`, `PLAN.md:230`.

**Pendente — instruções para o próximo agente corrigir tudo abaixo, um item por vez, rodando
`pytest tests/ -v`, `ruff check src tests web scripts` e `ruff format --check src tests web
scripts` depois de cada mudança:**

1. 🟠 **`src/ingest.py:41`** — `fetch_prodes` usa `typeName` fixo `"prodes_para_q"`, que pelo
   nome parece restrito à camada do **Pará**, não à Amazônia Legal inteira. Hoje, se a área
   analisada estiver fora dessa cobertura, `fetch_prodes` retorna vazio e o app cai
   silenciosamente no fallback demo sem avisar o usuário que a área está fora de cobertura real.
   **Correção:** adicionar aviso explícito na UI (`web/app.py`, no bloco do `prodes_source`)
   quando a série vier vazia por falta de cobertura, e documentar a limitação (só-PA) no
   README/CHECKLIST. Se houver uma camada WFS nacional/Amazônia Legal disponível no
   TerraBrasilis, avaliar trocar `prodes_para_q` por ela.

2. 🟡 **`src/tfff.py:40-41`** — quando `has_pmfs=True` mas `eligible=False` (reprovado por outro
   critério), a razão "PMFS ativo confirma a análise de manejo" ainda é adicionada à lista de
   motivos, soando contraditório numa lista de reprovação. **Correção:** condicionar essa razão
   a `eligible=True`, ou mover para uma lista separada de "fatores positivos" independente do
   veredito final.

3. 🟡 **`.github/workflows/ci.yml`** — roda só `ruff check src tests web` + `pytest`; não inclui
   `ruff format --check` nem lint de `scripts/`, divergindo da validação descrita no
   `REVIEW_PROMPT.md`. **Correção:** adicionar `ruff check scripts` e um step
   `ruff format --check src tests web scripts` ao workflow.

4. ⚪ **Testes de borda faltando** em `tests/test_core.py` (ou novo arquivo `tests/test_edge_cases.py`):
   - `compute_deforestation_series` com `prodes_gdf` vazio ou sem interseção com `target_area`
     (deve retornar série vazia, não lançar exceção).
   - `estimate_vcu(area_ha=0)` — deve retornar `net_vcu=0`, não erro.
   - Fallback do `web/app.py` quando `fetch_prodes` lança exceção (hoje só coberto
     indiretamente via `ingest`, não via um teste que simule falha de rede no fluxo do app).

5. ⚪ **`scripts/screenshots.py`** — usa `wait_for_timeout` fixo (400/600/1500/2000/3000ms) em
   vez de esperas condicionais, frágil a mudanças de versão do Streamlit ou variação de latência
   em CI. **Correção (opcional, baixa prioridade):** trocar por
   `expect(locator).to_be_visible()`/`to_contain_text()` da API do Playwright onde possível.

---

## Notas de manutenção

- **PRODES/DETER:** API INPE não requer autenticação, mas pode ficar lenta/indisponível — o app
  roda o fallback demo sem travar (ver `web/app.py` try/except com `# noqa: BLE001`).
- **Streamlit selectbox:** versões ≥1.5x usam combobox (não `<select>`); o script de screenshots
  já trata isso. Se o Streamlit mudar a estrutura DOM, atualizar `select_area` em `screenshots.py`.
- **Dockerfile (3.12)** vs **CI (3.11):** ambos atendem `requires-python >=3.11`.
- **PDF:** não gerado; export em JSON e texto. Se necessário futuramente, adicionar `reportlab`
  em `requirements.txt` e um botão extra.

---

## Etapa 14 — Pivotagem para Diagnóstico Territorial Preliminar — 🗺️ PLANEJADA

O projeto será refatorado para um pré-diagnóstico ambiental e territorial aberto,
com foco em evidências geoespaciais públicas, qualidade dos dados, limitações
explícitas e próximos passos técnicos. Ele será complementar às soluções
profissionais existentes no ecossistema Green Forest/ACC, sem alegar que essas
organizações não possuam iniciativas semelhantes.

O plano executável, com contrato, fases, critérios de aceitação, checkpoints e
protocolo de commits/pushes, está em `tasks/plan.md`. A lista operacional está
em `tasks/todo.md`. O próximo agente deve começar pela Fase 0, criar uma branch
`codex/`, seguir a ordem definida e não publicar uma nova release sem autorização
explícita.
