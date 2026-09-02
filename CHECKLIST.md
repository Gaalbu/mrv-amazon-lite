# Checklist de Revisão — MRV Amazon Lite

Use este checklist para validar antes do `gh release v0.1.0` e do post no LinkedIn.
Marque `[x]` quando o item estiver comprovado por log, screenshot ou arquivo.

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
- [x] Tem gráfico de série PRODES (st.line_chart ou plotly) — não só `st.map`
- [x] Mapa renderizado (st.map ou st_folium)
- [x] Cards TFFF + PlaNAU visíveis
- [x] Disclaimer abaixo dos métrios: `TFFF/PlaNAU: simulação ilustrativa pós-COP30 Belém`
- [ ] Visual funciona com os 3 GeoJSONs (rural/urbano/degradado) — sem dependência de API externa que trave a demo (código e GeoJSONs verificados; renderização visual pendente)

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
- [x] Log de `python -m pytest tests/ -v` — 9 testes verdes (sem `FAILED`/`ERROR`)
- [x] Log de `ruff check src tests web` — sem warnings
- [x] Log de `ruff format src tests web` — sem alterações pendentes

### 7. Prova visual — DEMO
- [ ] Screenshot do dashboard com **Juruti — UMF V Mamuru-Arapiuns** (VCU ~380k + TFFF elegível + PlaNAU "não se aplica") — pendente: navegador indisponível nesta sessão
- [ ] Screenshot com **Área urbana demo** (PlaNAU prioridade alta + déficit árvores) — pendente: navegador indisponível nesta sessão
- [ ] Screenshot com **Área degradada demo** (TFFF não elegível) — pendente: navegador indisponível nesta sessão
- [ ] Opcional: GIF <15s dos 3 use cases para o LinkedIn

### 8. Sanitização
- [x] `.gitignore` exclui `__pycache__/`, `.venv/`, `.env`, `.pytest_cache/`, `.ruf_cache/`
- [x] Nenhuma chave/segredo em código ou commit
- [x] `LICENSE` MIT presente e com autor
- [x] `src/mrv.py` relatório tem `demonstração edu` + `checksum_sha256`

---

## GATE FINAL (somente marcar quando os itens acima estiverem verdes)

- [ ] Todos os 3 bloqueadores resolvidos (prova visual ainda pendente)
- [x] 3 logs colados (pytest, ruff check, ruff format)
- [ ] 3 screenshots dos use cases (navegador indisponível nesta sessão)
- [x] **Autorizado:** `gh repo create Gaalbu/mrv-amazon-lite --public --source=. --push`
- [ ] **Autorizado:** `gh release create v0.1.0` com notes pós-COP30
- [ ] Post LinkedIn final revisado (sem "COP30 vem aí"; usar "COP30 Belém 10-21/11/2025 entregou...")

## Evidências — execução em 2026-09-02

```text
$ .venv/bin/python -m pytest tests/ -v
9 passed in 3.59s

$ .venv/bin/ruff check src tests web
All checks passed!

$ .venv/bin/ruff format --check src tests web
9 files already formatted

$ docker build -t mrv-lite:test .
exit code 0; image mrv-lite:test criada; contexto Docker 85.80kB
```

A prova visual não foi marcada: não havia navegador disponível/conectado na sessão para capturar screenshots reais. O release v0.1.0 e o post no LinkedIn também permanecem deliberadamente pendentes.
