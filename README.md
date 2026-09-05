# Diagnóstico Territorial Preliminar

Protótipo aberto de pré-diagnóstico territorial e ambiental, inspirado no projeto CNPq RHAE 443538/2024-7.

## Inspiração

Projeto CNPq RHAE 443538/2024-7. Este repositório não declara autoria da Green Forest, da UFRA ou da ACC.

## O que faz

- Recebe um GeoJSON e organiza um pré-diagnóstico territorial rastreável.
- Consulta séries históricas PRODES e alertas DETER por bounding box.
- Resume evidências públicas e limitações do dado disponível.
- Mantém indicadores complementares de uso educacional para TFFF e PlaNAU.
- Gera relatório JSON e texto com checksum SHA-256.

## Como rodar

```bash
git clone https://github.com/Gaalbu/mrv-amazon-lite.git
pip install -r requirements.txt
streamlit run web/app.py
```

## Fontes

INPE PRODES/DETER, IPCC 2019, referências TFFF/PlaNAU COP30 e dados públicos territoriais usados no protótipo.

O endpoint demonstrativo atual usa a camada `prodes_para_q`, portanto a cobertura PRODES
integrada está limitada ao Pará; áreas sem retorno exibem fallback demo identificado na tela.

## Limitações

Pré-diagnóstico educacional — não substitui certificação, parecer jurídico, licenciamento, CAR ou regularização fundiária. TFFF/PlaNAU aqui são simulações ilustrativas, não elegibilidade oficial.

Testes: `python -m pytest tests/ -v` · lint: `ruff check src tests web scripts`.

Screenshots do dashboard (automatizadas): `make screenshots` gera os PNGs dos 3 use cases em
`screenshots/` (requer `pip install playwright && python -m playwright install chromium`).
Também disponível como workflow manual em `.github/workflows/screenshots.yml`.

As estimativas não substituem certificação VCS/Gold Standard nem validação técnica, fundiária ou ambiental. As APIs externas podem mudar ou ficar indisponíveis.
