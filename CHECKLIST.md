# Checklist de Revisão — Diagnóstico Territorial Preliminar (MVP)

Use este checklist para validar o MVP de contexto territorial ambiental. Marque `[x]`
quando o item estiver comprovado por log, screenshot ou arquivo.

> **Atualização 2026-09-05:** o projeto foi enxugado para um MVP de leitura preliminar
> de contexto territorial. Carbono, TFFF e PlaNAU foram retirados do fluxo principal e
> preservados como funcionalidades futuras documentadas.

---

## BLOQUEADORES (não entregar sem todos verdes)

### 1. README completo — `README.md`
- [ ] Seção "Inspiração" com atribuição ao projeto CNPq RHAE 443538/2024-7
- [ ] Seção "O que faz" com foco em pré-diagnóstico territorial e evidências públicas
- [ ] Seção "O que NÃO faz" sem carbono/TFFF/PlaNAU
- [ ] "Como rodar em 3 comandos": `git clone`, `pip install -r requirements.txt`, `streamlit run web/app.py`
- [ ] Seção "Fontes": INPE PRODES e camadas ICMBio (UCs federais + áreas prioritárias)
- [ ] Seção "Limitações" com disclaimer de pré-diagnóstico educacional

### 2. Dependências pinadas e buildável — `requirements.txt` + `Dockerfile`
- [ ] `requirements.txt` com versões `==` e sem dependências não usadas
- [ ] `Dockerfile` inclui `gdal-bin libgdal-dev` antes do `pip install`

### 3. Dashboard demonstrável — `web/app.py`
- [ ] Título e explicação do caráter preliminar
- [ ] Entrada do território: áreas de demonstração + upload GeoJSON + validação + área em ha
- [ ] Resumo inicial com estados compreensíveis (Dados ao vivo / Demonstração local /
      Sem dados para o recorte / Serviço indisponível); "Fontes ao vivo" diferencia
      fonte consultada de fonte com dados reais (demonstração local nunca conta como ao vivo)
- [ ] Série "Histórico de desmatamento consultado" com gráfico preenchido nas 3 áreas de
      demonstração + aviso explícito de demonstração local quando aplicável
- [ ] Sem gráfico inventado para uploads customizados sem dados (estado informativo, sem zeros)
- [ ] Mapa central com polígono, UCs federais e áreas prioritárias (camadas com nome)
- [ ] Seção de evidências com fonte, período, resultado e limitação
- [ ] Seção "Limitações — O que esta análise não responde" sempre visível
- [ ] Sem TFFF, PlaNAU, carbono ou linguagem de decisão oficial
- [ ] Relatório JSON e texto refletem exatamente o dashboard e registram o tipo da série
      (ao vivo / demonstrativa / vazia)

---

## QUALIDADE

### 4. Testes e lint — LOGS OBRIGATÓRIOS
- [ ] Log de `python -m pytest tests/ -v`
- [ ] Log de `ruff check src tests web scripts`
- [ ] Log de `ruff format --check src tests web scripts`
- [ ] Log de `python -m compileall -q src web tests`
- [ ] `git diff --check` sem erros

### 5. Prova visual — DEMO (automatizada)
- [ ] Qualidade dos 3 use cases coberta por `scripts/screenshots.py` (Playwright):
  - `screenshots/01_juruti_contexto.png` (Juruti)
  - `screenshots/02_area_urbana_contexto.png` (área urbana)
  - `screenshots/03_area_degradada_contexto.png` (área degradada)
- [ ] Geração automatizada roda local (`make screenshots`) e no CI (`screenshots.yml`)

### 6. Sanitização
- [ ] Nenhuma chave/segredo em código ou commit
- [ ] `LICENSE` MIT presente e com autor
- [ ] `src/diagnostico.py` relatório tem `checksum_sha256` com nota de que identifica conteúdo,
      não certifica a qualidade dos dados

---

## GATE FINAL (somente marcar quando os itens acima estiverem verdes)

- [ ] Testes, lint, format e compile passam
- [ ] Screenshots dos 3 use cases gerados em `screenshots/`
- [ ] Relatório JSON/texto refletem o dashboard
- [ ] Aplicação executada no navegador sem erros no console
- [ ] Diff revisado manualmente
- [ ] Release somente após autorização explícita