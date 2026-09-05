# Diagnóstico Territorial Preliminar

Um protótipo educacional de leitura preliminar de contexto territorial usando dados
ambientais públicos. O projeto responde a uma pergunta limitada:

> "O que os dados públicos disponíveis indicam, de forma preliminar, sobre este território?"

Inspirado no projeto CNPq RHAE 443538/2024-7. Este repositório não declara autoria da
Green Forest, da UFRA ou da ACC.

## O que faz

- Seleciona um território de demonstração ou carrega um GeoJSON próprio.
- Calcula a área do polígono em hectares (normalizado para EPSG:4326).
- Consulta o histórico de desmatamento PRODES/INPE quando há cobertura disponível.
- Verifica sobreposição indicativa com **unidades de conservação federais** (ICMBio).
- Verifica sobreposição indicativa com **áreas prioritárias para conservação** (ICMBio).
- Exibe um resumo textual das evidências, com fonte, período, resultado e limitação.
- Exibe explicitamente o que a análise **não** responde.
- Gera um relatório JSON e texto com checksum SHA-256.
- Gera screenshots automatizadas com Playwright.

## O que NÃO faz

Este projeto **não** calcula:

- estimativa de carbono em toneladas;
- faixa de incerteza IPCC;
- pagamento ou elegibilidade TFFF;
- prioridade, déficit de árvores ou custo do PlaNAU;
- qualquer indicador de decisão oficial.

O objetivo é oferecer uma primeira leitura do território, não uma avaliação ambiental,
jurídica ou financeira. Os módulos `carbon`, `tfff` e `planau` foram preservados no
repositório como funcionalidades futuras documentadas, mas estão **fora do fluxo** da
aplicação.

## Como rodar

```bash
git clone https://github.com/Gaalbu/mrv-amazon-lite.git
pip install -r requirements.txt
streamlit run web/app.py
```

## Como rodar os testes

```bash
python -m pytest tests/ -v
ruff check src tests web scripts
ruff format --check src tests web scripts
```

## Como gerar screenshots

```bash
pip install playwright && python -m playwright install chromium
python scripts/screenshots.py --out screenshots
```

Também disponível como workflow manual em `.github/workflows/screenshots.yml` (os PNGs são
publicados como artefato do GitHub Actions).

## Fontes consultadas

- **INPE PRODES** — série histórica de desmatamento, via WFS TerraBrasilis.
- **ICMBio — unidades de conservação federais** — camada `limiteucsfederais_a`, via WFS INDE.
- **ICMBio — áreas prioritárias para a conservação da biodiversidade (Amazônia)** — camada
  `amazonia_2a_atualizacao`, via WFS INDE.

## Fallback e limitações das APIs externas

- A camada PRODES integrada está limitada ao **Pará** (`prodes_para_q`); áreas fora dessa
  cobertura retornam "sem dados", e essa ausência é exibida como **ausência de dados**, nunca
  como desmatamento zero.
- Se a API estiver indisponível, o painel exibe uma série de referência identificada como
  *demo* e explica que ela representa ausência de dados.
- As APIs externas podem mudar, ficar lentas ou indisponíveis; o painel funciona mesmo assim,
  mostrando a limitação em vez de inventar dados.

## Limitações

Pré-diagnóstico educacional — não substitui certificação, parecer jurídico, licenciamento,
CAR, vistoria de campo ou regularização fundiária. A sobreposição cartográfica é indicativa.
O checksum SHA-256 identifica o conteúdo gerado; não certifica a qualidade dos dados.