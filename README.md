# MRV Amazon Lite

MVP educacional pós-COP30 para estimar ARR, consultar ingestão PRODES/DETER e avaliar regras simplificadas de TFFF/PlaNAU.

## Inspirado por

Projeto CNPq RHAE 443538/2024-7 Green Forest/UFRA/ACC.

## O que faz

- Simula restauração ARR e VCUs em três tipos de biomassa amazônica.
- Consulta séries históricas PRODES e alertas DETER por bounding box.
- Avalia critérios simplificados de conservação TFFF.
- Avalia cobertura arbórea e déficit de árvores para PlaNAU urbano.
- Gera relatório MRV JSON com checksum SHA-256.

## Como rodar

```bash
git clone https://github.com/Gaalbu/mrv-amazon-lite.git
pip install -r requirements.txt
streamlit run web/app.py
```

## Fontes

INPE PRODES/DETER, IPCC 2019, VCS VM0047 e referências TFFF/PlaNAU COP30.

O endpoint demonstrativo atual usa a camada `prodes_para_q`, portanto a cobertura PRODES
integrada está limitada ao Pará; áreas sem retorno exibem fallback demo identificado na tela.

## Limitações

Estimativa educacional — não substitui certificação VCS/Gold Standard. TFFF/PlaNAU aqui são simulações ilustrativas, não elegibilidade oficial.

Testes: `python -m pytest tests/ -v` · lint: `ruff check src tests web scripts`.

Screenshots do dashboard (automatizadas): `make screenshots` gera os PNGs dos 3 use cases em
`screenshots/` (requer `pip install playwright && python -m playwright install chromium`).
Também disponível como workflow manual em `.github/workflows/screenshots.yml`.

As estimativas não substituem certificação VCS/Gold Standard nem validação técnica, fundiária ou ambiental. As APIs externas podem mudar ou ficar indisponíveis.
