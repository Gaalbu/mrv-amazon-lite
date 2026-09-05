# Checklist de Revisão — Diagnóstico Territorial Preliminar

Use este checklist para validar antes do `gh release v0.1.0` e de uma publicação externa.
Marque `[x]` quando o item estiver comprovado por log, screenshot ou arquivo.

> **Atualização 2026-09-05:** a Fase 1 reposiciona o produto como pré-diagnóstico territorial.
> O texto do dashboard, README, checklist, screenshots e metadados agora usam o novo nome.

---

## BLOQUEADORES (não publicar sem todos verdes)

### 1. README completo — `README.md`
- [x] Seção "Inspiração" com atribuição ao projeto CNPq RHAE 443538/2024-7
- [x] Seção "O que faz" com foco em pré-diagnóstico territorial e evidências públicas
- [x] "Como rodar em 3 comandos": `git clone`, `pip install -r requirements.txt`, `streamlit run web/app.py`
- [x] Seção "Fontes": INPE PRODES/DETER, IPCC 2019, TFFF/PlaNAU COP30 e dados territoriais públicos
- [x] Seção "Limitações" com disclaimer de pré-diagnóstico educacional

### 2. Dependências pinadas e buildável — `requirements.txt` + `Dockerfile`
- [x] `requirements.txt` com versões `==` (streamlit, geopandas, rasterio, plotly, etc.)
- [x] `Dockerfile` inclui `gdal-bin libgdal-dev` antes do `pip install`
- [x] Comprovado: `docker build -t mrv-lite:test .` sem erro

### 3. Dashboard demonstrável — `web/app.py`
- [x] Tem gráfico de série PRODES (st.line_chart) — integrado ao API real com fallback demo
- [x] Mapa renderizado (Folium + st_folium/Leaflet)
- [x] Indicadores complementares TFFF + PlaNAU visíveis
- [x] Disclaimer abaixo dos métricos alinhado ao pré-diagnóstico territorial
- [x] Visual funciona com os 3 GeoJSONs + Upload customizado, sem travar por API externa
      (série PRODES com fallback demo; verificado via `scripts/screenshots.py`)

---

## CORREÇÕES MENORES

### 4. Config interna
- [x] `src/config.json` tem `crediting_period_years: 30` e `discount_rate: 0.05`
- [x] `src/tfff.py` lógica de elegibilidade sem redundância (usar limite único <5%)

### 5. Ingest
- [x] `data/mapbiomas_pa_2023.csv` existe (mesmo que vazio com header) OU `fetch_mapbiomas` retorna df mock quando ausente
- [x] Teste cobre o caso `fetch_mapbiomas` sem arquivo

---

## QUALIDADE

### 6. Testes e lint — LOGS OBRIGATÓRIOS (cole os 3 abaixo)
- [x] Log de `python -m pytest tests/ -v` — 14 testes verdes (sem `FAILED`/`ERROR`)
- [x] Log de `ruff check src tests web scripts` — sem warnings
- [x] Log de `ruff format src tests web scripts` — sem alterações pendentes

### 7. Prova visual — DEMO (automatizada, salva no PC)
- [x] Screenshot com **Juruti — UMF V Mamuru-Arapiuns** (indicador de carbono complementar + TFFF elegível + PlaNAU "não se aplica") — `screenshots/01_juruti_mamuru.png`
- [x] Screenshot com **Área urbana pré-diagnóstico** (PlaNAU prioridade alta + déficit árvores) — `screenshots/02_area_urbana_planau.png`
- [x] Screenshot com **Área degradada pré-diagnóstico** (TFFF não elegível) — `screenshots/03_area_degradada_tfff.png`
- [x] Geração automatizada por `scripts/screenshots.py` (Playwright) — roda local (`make screenshots`) e no CI (`screenshots.yml` → artefato)
- [ ] Opcional: GIF <15s dos 3 use cases para o LinkedIn

### 8. Sanitização
- [x] `.gitignore` exclui `__pycache__/`, `.venv/`, `.env`, `.pytest_cache/`, `.ruf_cache/`
- [x] Nenhuma chave/segredo em código ou commit
- [x] `LICENSE` MIT presente e com autor
- [x] `src/mrv.py` relatório tem `demonstração edu` + `checksum_sha256`

---

## GATE FINAL (somente marcar quando os itens acima estiverem verdes)

- [x] Todos os 3 bloqueadores resolvidos (prova visual coberta por automação)
- [x] 4 logs colados (pytest, ruff check, ruff format, docker build)
- [x] 3 screenshots dos use cases gerados e salvos em `screenshots/`
- [x] **Autorizado:** `gh repo create Gaalbu/mrv-amazon-lite --public --source=. --push`
- [x] **Autorizado/executado:** `gh release create v0.1.0` com notes pós-COP30 — https://github.com/Gaalbu/mrv-amazon-lite/releases/tag/v0.1.0
- [ ] Post externo final revisado com a nova identidade territorial

## Evidências — execução em 2026-09-02

```text
$ .venv/bin/python -m pytest tests/ -v
10 passed in 1.54s

$ .venv/bin/ruff check src tests web scripts
All checks passed!

$ .venv/bin/ruff format --check src tests web scripts
10 files already formatted

$ docker build -t mrv-lite:test .
exit code 0; image mrv-lite:test criada; contexto Docker 85.80kB
```

Screenshots gerados e salvos no PC (2026-09-02):
```
screenshots/01_juruti_mamuru.png       (1440x900 PNG)
screenshots/02_area_urbana_planau.png  (1440x900 PNG)
screenshots/03_area_degradada_tfff.png (1440x900 PNG)
```

Prova visual agora é **automatizada** via `scripts/screenshots.py` (Playwright) e roda tanto local
(`make screenshots`) quanto no CI (`.github/workflows/screenshots.yml`, publicada como artefato).
O release v0.1.0 foi publicado após CI verde. O post LinkedIn permanece pendente por exigir
confirmação final de comunicação pública.
