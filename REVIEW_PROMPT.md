# Prompt — Revisão de Código: MRV Amazon Lite

Crie este prompt para acionar um agente revisor de código (LLM ou humano) sobre o repositório
`mrv-amazon-lite`. Adapte a primeira linha ("Você é...") ao agente que for usar.

---

Você é um revisor de código experiente em Python, análise geoespacial (GeoPandas/Shapely),
dados ambientais (Amazônia) e aplicações Streamlit. Revise o projeto MRV Amazon Lite de forma
crítica, objetiva e acionável, apontando o que está correto e o que deve mudar, com
prioridades. Não edite o código: apenas reporte.

## O que o projeto faz (contexto obrigatório)

O MRV Amazon Lite é um MVP educacional e open-source pós-COP30 para a Amazônia. Objetivo:
ajudar donos de área (produtores, municípios, comunidades) a estimar o vale de uma floresta em
crédito de carbono e checar elegibilidade para os fundos lançados na COP30 de Belém (TFFF e
PlaNAU), usando dados abertos. Stack: Python + Streamlit + Folium/Leaflet.

Funcionalidades (módulos em `src/`):
- `ingest.py` — puxa séries de desmatamento do INPE (PRODES `prodes_para_q`, DETER
  `deter_para_q`) via WFS, com fallback local para MapBiomas; `compute_deforestation_series`
  cruza PRODES com o polígono alvo.
- `carbon.py` — estimativa ARR simplificada (metodologia "VCS VM0047 lite"), VCUs brutos,
  deduções de leakage/buffer e faixa de incerteza ±30% a partir de tabelas IPCC 2019;
  parâmetros em `config.json`.
- `tfff.py` — elegibilidade simplificada para o Tropical Forests Forever Facility (US$5/ha/ano,
  bônus 1.5x indígena/tradicional, limites de desmatamento).
- `planau.py` — avaliação de déficit de arborização urbana para o Plano Nacional de
  Arborização Urbana (100 árvores/ha alvo, R$500/árvore, prioridade por cobertura).
- `mrv.py` — gera relatório JSON rastreável com checksum SHA-256.
- `web/app.py` — dashboard Streamlit com mapa Folium, série PRODES (real + fallback demo),
  upload de GeoJSON customizado, cards TFFF/PlaNAU e export JSON/texto.
- `scripts/screenshots.py` — automação Playwright dos 3 use cases (gera PNGs dos screenshots).
- CI: `.github/workflows/ci.yml` (lint+test) e `.github/workflows/screenshots.yml` (artefatos).

## Escopo da revisão

Revise o código-fonte e as decisões de arquitetura, com foco em contratos, correção e
qualidade. Dê ênfase a:

1. **Correção técnica e fórmulas**
   - Leads do motor de carbono (`src/carbon.py`) vs. `src/config.json`: as contas de
     gross/leakage/buffer/net e a faixa ±30% estão coerentes? O valor de referência
     (380160 VCU para 100 ha terra firme / 30 anos) bate?
   - `src/ingest.py`: o WFS está correto (bbox/CRS `EPSG:4326`, projeção `EPSG:6933` para
     área em hectares no `compute_deforestation_series`)? Há risco de resultados errados
     para polígonos que cruzam antimeridiano/metadata ausente?
   - Regras de elegibilidade TFFF/PlaNAU (`tfff.py`, `planau.py`) estão consistentes,
     sem lógica redundante ou contraditória?

2. **Robustez e segurança**
   - Chamadas de rede externa (INPE) têm timeout e fallback adequado sem travar a demo?
   - Upload de GeoJSON (`web/app.py`): há risco de carregamento malicioso/muito grande ou
     de leitura de caminho arbitrário? Valida conteúdo/CAPACITY?
   - O relatório (`mrv.py`) serializa objetos de forma segura (sem segredos/Paths)?
   - Tratamento de exceções está com escopo correto (não "engolir" erros reais)?

3. **Qualidade e boas práticas**
   - Testes (`tests/`): cobrem os caminhos críticos? Faltam casos (borda, divisão por zero,
     dados vazios, API indisponível)? Os mocks são adequados?
   - Lint/format consistente (ruff) e tipagem razoável.
   - Estrutura de módulos/imports circular, acoplamento ou duplicação.
   - O script de screenshots (`scripts/screenshots.py`) é frágil a mudanças de DOM do
     Streamlit? Como poderia ficar mais robusto?

4. **Ética e transparência (crítico para o domínio)**
   - O projeto deixa claro em toda parte (app, README, relatório) que é estimativa
     educacional, não certificação VCS/Gold Standard?
   - Não induz a prometer valores de carbono irreais sob regras oficiais complexas?
   - Atribuição correta das fontes (INPE, IPCC, TFFF/PlaNAU COP30)?

## Como validar (rode você mesmo)

Use a venv disponível (`/home/gaalbu/codigos/mrv-amazon-lite/.venv/bin/python`):

```bash
.venv/bin/python -m pytest tests/ -v
.venv/bin/ruff check src tests web scripts
.venv/bin/ruff format --check src tests web scripts
```

Confirme se o dashboard inicia sem erro (`streamlit run web/app.py`) e, se possível, rode
`scripts/screenshots.py --out /tmp/rev_screenshots` para validar os 3 use cases.

## Entregável (formato de resposta)

1. **Resumo executivo** (3-5 linhas: está maduro/revisável para release v0.1.0?)
2. **Achados por severidade**, agrupados:
   - 🔴 Bloqueador (corrompe resultado/segurança/impede release)
   - 🟠 Importante (risco de erro em produção real/uso)
   - 🟡 Sugestão (melhoria/boas práticas)
   - ⚪ Informativo (observação)
   - Para cada achado: arquivo:linha, o problema, por que importa, e a correção sugerida
3. **Decisões que precisam de revisão humana** (ex.: interpretação da metodologia VM0047,
   limites de elegibilidade, política de dados)
4. **Veredito final**: Aprovar / Aprovar com ressalvas / Não aprovar para `gh release v0.1.0`,
   com justificativa.

Seja específico, cite arquivos:linhas, e não faça apenas elogios — o objetivo é endurecer o
MVP antes do release e do uso em contexto real de tomada de decisão.
