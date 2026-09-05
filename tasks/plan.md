# Plano de pivotagem: Diagnóstico Territorial Preliminar

## Objetivo

Transformar o MVP MRV Amazon Lite em uma ferramenta aberta de pré-diagnóstico
ambiental e territorial. O usuário informa ou envia um polígono e recebe um
resumo rastreável de localização, área, evidências geoespaciais públicas,
alertas ambientais e próximos documentos/estudos recomendados.

O produto será complementar a consultorias e plataformas profissionais. Não
emitirá certificação, parecer jurídico, licença, CAR, regularização fundiária
ou elegibilidade oficial para financiamento.

## Nome e posicionamento

- Nome do produto: **Diagnóstico Territorial Preliminar**.
- Repositório/package: migrar gradualmente de `mrv-amazon-lite` para um nome
  técnico estável, preservando redirecionamento e histórico do GitHub quando
  possível.
- Descrição curta: "Pré-diagnóstico ambiental baseado em dados geoespaciais
  públicos para orientar a próxima decisão técnica."
- Evitar alegar que a Green Forest não possui solução semelhante. Explicar que
  este é um protótipo independente, inspirado no contexto do projeto CNPq e
  desenhado como camada preliminar/complementar.

## Contrato funcional mínimo

Entrada: GeoJSON com uma ou mais geometrias válidas e, opcionalmente, nome da
área e metadados básicos.

Saída: relatório JSON e texto contendo:

1. geometria normalizada em EPSG:4326 e área calculada em hectares;
2. bounding box e centroide para visualização;
3. fontes consultadas, período e status de cada fonte;
4. evidências públicas disponíveis (desmatamento/alertas e camadas
   territoriais quando houver dados confiáveis);
5. limitações, dados ausentes e grau de confiança do diagnóstico;
6. checklist de próximos passos, sem afirmar conclusão legal ou ambiental;
7. checksum SHA-256 do relatório.

## Fases e checkpoints

### Fase 0 — Baseline e segurança de entrega

- Criar branch de trabalho com prefixo `codex/`.
- Registrar `git status`, commit atual, versão Python, testes e lint.
- Não reescrever histórico nem apagar a release existente.
- Cada fase terá um commit atômico; push somente após revisão do diff, testes e
  `aislop`.

**Checkpoint 0:** baseline documentado; working tree limpo; testes e lint verdes.

### Fase 1 — Identidade e escopo do produto

- Definir nome, título do dashboard, package metadata, README, Docker e textos
  de exportação.
- Remover linguagem que prometa crédito de carbono como produto principal.
- Preservar a atribuição correta: o produto é inspirado no projeto CNPq
  RHAE 443538/2024-7 e não deve afirmar que foi desenvolvido pela Green Forest,
  UFRA ou ACC.
- Atualizar screenshots, checklist e documentação de release.

**Aceitação:** nenhuma tela ou documento apresenta o antigo MRV Lite como
produto final; o disclaimer e a relação de inspiração estão claros.

**Checkpoint 1:** pytest, ruff, execução do dashboard e revisão textual.

### Fase 2 — Contrato geoespacial e validação de entrada

- Criar funções pequenas e testadas para validar GeoJSON, CRS, geometrias
  vazias/inválidas, múltiplas feições e área zero.
- Normalizar geometrias para EPSG:4326 e calcular área somente em uma projeção
  métrica apropriada, documentando a escolha.
- Impor limites conservadores de tamanho/complexidade no upload e retornar
  erros orientativos.

**Aceitação:** entradas inválidas não derrubam o Streamlit; testes cobrem
  arquivo vazio, CRS ausente, geometria inválida, múltiplas feições e limites.

**Checkpoint 2:** testes unitários e teste manual do upload com amostras válidas
  e inválidas.

### Fase 3 — Núcleo de diagnóstico territorial

- Introduzir um modelo de resultado explícito, com evidência, fonte, período,
  status (`ok`, `empty`, `unavailable`) e limitação.
- Separar ingestão de dados, cálculo espacial e apresentação.
- Reaproveitar PRODES/DETER somente como evidência de desmatamento, sem chamar
  fallback demo de dado real.
- Tratar a camada atualmente parametrizada para o Pará como limitação explícita
  até existir cobertura validada para outras UFs.

**Aceitação:** o relatório diferencia dado real, resultado vazio e API
  indisponível; nenhuma ausência de dado é convertida silenciosamente em
  evidência positiva ou negativa.

### Fase 4 — Camadas territoriais de alto valor

- Implementar primeiro uma camada pública confiável e demonstrável, com fonte,
  data e CRS registrados.
- Prioridade inicial: sobreposição/interseção com áreas protegidas ou outra
  camada territorial oficialmente disponível e adequada ao escopo do Pará.
- Adicionar cada fonte em um adaptador isolado, com timeout, cache/fallback
  identificado e testes de resposta vazia/indisponível.
- Não incluir CAR, terras indígenas, regularização ou restrições legais como
  conclusões sem fonte oficial apropriada e revisão técnica.

**Aceitação:** cada camada aparece no mapa e no relatório com fonte e status;
  a ausência de uma camada não bloqueia as demais.

### Fase 5 — Relatório e experiência de decisão

- Substituir cards de VCU/TFFF/PlaNAU por: área, alertas encontrados, camadas
  consultadas, pendências e próximos passos.
- Manter exportação JSON/texto e checksum, agora com schema versionado e
  `data_quality`/`limitations` explícitos.
- Criar três casos demonstráveis: área rural preservada, área com evidência de
  alteração e área urbana/periurbana.

**Aceitação:** uma pessoa não especialista entende o que foi encontrado, o que
  não foi possível verificar e qual é o próximo passo técnico.

### Fase 6 — Qualidade, segurança e documentação

- Adicionar testes de borda e integração dos adaptadores.
- Atualizar CI para incluir `ruff check src tests web scripts`,
  `ruff format --check` e pytest.
- Tornar screenshots resistentes a mudanças de DOM, usando esperas condicionais.
- Rodar `aislop scan --json` no projeto completo; corrigir findings reais e
  registrar falsos positivos justificados.
- Atualizar README, PLAN, CHECKLIST, release notes e instruções de execução.

**Checkpoint 6:** suite verde, lint/format verdes, scan sem erros, dashboard
  demonstrável e revisão final do diff.

### Fase 7 — Commits, pushes e release

Para cada fase:

1. revisar `git diff` e `git diff --check`;
2. executar os comandos de verificação da fase;
3. rodar `aislop` quando houver código alterado;
4. criar commit atômico com mensagem descritiva;
5. revisar o commit com `git show --stat` e `git show`;
6. fazer push da branch de trabalho;
7. só então abrir/revisar o próximo incremento.

Não fazer push de credenciais, arquivos gerados, screenshots locais ou dados
  pessoais. A release `v0.1.0` existente deve permanecer intacta; a nova
  versão deve receber tag somente depois do checkpoint final e autorização
  explícita para publicar.

## Riscos e decisões

| Risco | Mitigação |
|---|---|
| Duplicar Forestia/NA.IA | Manter escopo de pré-diagnóstico aberto, transparência e preparação de evidências |
| Fonte pública indisponível | Status por fonte, timeout, cache/fallback identificado |
| Interpretação jurídica indevida | Linguagem de indício, não conclusão; disclaimer visível |
| Cobertura geográfica incompleta | Mostrar UF/escopo da camada e não generalizar silenciosamente |
| Upload malicioso ou pesado | Limites de tamanho/complexidade e validação antes do processamento |
| Refatoração grande difícil de reverter | Slices verticais, commits atômicos e checkpoints |

## Ordem imediata de execução

1. Baseline e branch.
2. Fase 1: identidade e escopo.
3. Fase 2: contrato geoespacial.
4. Primeiro checkpoint e revisão.
5. Fase 3: núcleo do diagnóstico.
6. Fases 4–7, uma por vez, com commit e push revisados.
