# Execução — Diagnóstico Territorial Preliminar

## Fase 0

- [x] Registrar baseline, status, commit, versões e comandos verdes.
- [x] Criar branch de trabalho para a pivotagem (`codex-pivot-diagnostico-territorial`).
- [ ] Revisar arquivos gerados e escopo de migração.

## Fase 1 — Identidade

- [ ] Atualizar nome, título, metadata e descrição do projeto.
- [ ] Atualizar README, PLAN, CHECKLIST, screenshots e exportações.
- [ ] Remover a centralidade de VCU/TFFF/PlaNAU sem apagar histórico de decisões.

## Checkpoint 1

- [ ] Testes passam.
- [ ] Ruff check e format passam.
- [ ] Dashboard inicia e textos foram revisados.
- [ ] Diff foi revisado antes do commit/push.

## Fase 2 — Entrada geoespacial

- [ ] Definir contrato e modelo de validação.
- [ ] Cobrir CRS, geometria, múltiplas feições, área e limites.
- [ ] Integrar mensagens de erro no upload.

## Checkpoint 2

- [ ] Testes unitários de entradas válidas e inválidas passam.
- [ ] Upload foi verificado manualmente.

## Fases 3–6

- [ ] Implementar evidências e status por fonte.
- [ ] Adicionar primeira camada territorial com fonte oficial.
- [ ] Atualizar dashboard e relatório.
- [ ] Corrigir CI, screenshots e qualidade.

## Checkpoint final

- [ ] Pytest, ruff, format e aislop passam.
- [ ] Casos demonstráveis funcionam.
- [ ] Diff final e histórico de commits revisados.
- [ ] Release só após autorização explícita.
