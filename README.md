# MRV Amazon Lite

MVP educacional pós-COP30 para estimar ARR, consultar ingestão PRODES/DETER e avaliar regras simplificadas de TFFF/PlaNAU.

## Como rodar

```bash
python -m venv .venv && . .venv/bin/activate
python -m pip install -r requirements.txt
streamlit run web/app.py
```

Testes: `python -m pytest tests/ -v` · lint: `ruff check src tests web`.

As estimativas não substituem certificação VCS/Gold Standard nem validação técnica, fundiária ou ambiental. As APIs externas podem mudar ou ficar indisponíveis.
