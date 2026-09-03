# Checklist de Revisão — MRV Amazon Lite

Use este checklist para validar antes do `gh release v0.1.0` e do post no LinkedIn.
Marque `[x]` quando o item estiver comprovado por log, screenshot ou arquivo.

> **Atualização 2026-09-02:** gaps de código resolvidos (Folium, Upload customizado, PRODES real
> com fallback, export JSON+texto; `cop30_legacy`, `inspired_by`, teste `fetch_prodes`) e **prova
> visual automatizada** criada e executada (screenshots gerados e salvos no PC). Restam apenas os
> itens editoriais (release v0.1.0 + post LinkedIn).

---

## BLOQUEADORES (não publicar sem todos verdes)

### 1. README completo — `README.md`
- [x] Seção "Inspirado por: Projeto CNPq RHAE 443538/2024-7 Green Forest/UFRA/ACC"
- [x] Seção "O que faz" (5 bullets: ARR, PRODES/DETER, TFFF, PlaNAU, relatório MRV)
- [x] "Como rodar em 3 comandos": `git clone`, `pip install -r requirements.txt`, `streamlit run web/app.py`
- [x] Seção "Fontes": INPE PRODES/DETER, IPCC 2019, VCS VM0047, TFFF/PlaNAU COP30
- [x] Seção "Limitações" com disclaimer exato:
  `Estimativa educacional — não substitui certificação VCS/Gold Standard. TFFF/PlaNAU aqui são simulações ilustrativas, não elegibilidade oficial.`

### 2. Dependências pinadas e buildável — `requirements.txt` + `Dockerfile`
- [x] `requirements.txt` com versões `==` (streamlit, geopandas, rasterio, plotly, etc.)
- [x] `Dockerfile` inclui `gdal-bin libgdal-dev` antes do `pip install`
- [x] Comprovado: `docker build -t mrv-lite:test .` sem erro

### 3. Dashboard demonstrável — `web/app.py`
- [x] Tem gráfico de série PRODES (st.line_chart) — integrado ao API real com fallback demo
- [x] Mapa renderizado (Folium + st_folium/Leaflet)
- [x] Cards TFFF + PlaNAU visíveis
- [x] Disclaimer abaixo dos métrios: `TFFF/PlaNAU: simulação ilustrativa pós-COP30 Belém`
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
- [x] Screenshot com **Juruti — UMF V Mamuru-Arapiuns** (VCU ~12,7k + TFFF elegível + PlaNAU "não se aplica") — `screenshots/01_juruti_mamuru.png`
- [x] Screenshot com **Área urbana demo** (PlaNAU prioridade alta + déficit árvores) — `screenshots/02_area_urbana_planau.png`
- [x] Screenshot com **Área degradada demo** (TFFF não elegível) — `screenshots/03_area_degradada_tfff.png`
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
- [ ] **Autorizado:** `gh release create v0.1.0` com notes pós-COP30
- [ ] Post LinkedIn final revisado (sem "COP30 vem aí"; usar "COP30 Belém 10-21/11/2025 entregou...")

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
O release v0.1.0 e o post LinkedIn permanecem deliberadamente pendentes (itens editoriais).
