# Task 17 — Evals dos agentes e calibração dos prompts

- **Depende de:** 16
- **Modelo recomendado:** opus
- **Leia antes:** `docs/ARQUITETURA.md` §6, §12 (evals); skill `claude-api`, subcomando
  `build-eval` (seguir a entrevista dela: o que avaliar, fonte dos casos, método de
  nota, custo)

## Objetivo

Substituir "achismo" por medição: um conjunto de casos reais com textos de referência, um
script que roda os agentes sobre eles e devolve notas objetivas + julgamento do QA, para
comparar versões de prompt antes de mudar o padrão.

## Escopo

1. `evals/casos/*.json`: ~10 produtos reais (dados de entrada como a dona da loja
   preencheria) com textos de referência aprovados hoje (aproveitar os exemplos da
   `docs/brutos/SKILL.md` e produtos já publicados no site, exportação em `docs/brutos/`).
   Cobrir todas as marcas com perfil e o caso genérico.
2. `evals/rodar.py`: roda `GeradorTextos` em cada caso (API real), grava saída por versão
   (`evals/resultados/<data>-<rotulo>/`), calcula métricas determinísticas (todas as regras
   de `RegrasTexto`, tamanho médio, % aprovados de primeira, custo médio, nº de retries) e
   pede ao `AgenteQa` uma nota 1–5 por campo comparando com a referência (juiz com rubrica).
   Imprime tabela comparativa entre duas rodadas (`--comparar A B`).
3. Uma rodada de calibração: rodar, ler os textos, ajustar `copy.md`/`seo.md`/`qa.md`/`.j2`
   onde o resultado ficar genérico ou fora do tom, rodar de novo, registrar em
   `evals/REGISTRO.md` o que mudou e o efeito nas métricas. Testar também `LLM_MODELO_QA=
   claude-sonnet-5` e registrar se a taxa de reprovação/qualidade se mantém (alavanca de custo).
4. Nenhum eval roda no `pytest` padrão (custo); documentar no README de `evals/`.

## Critério de aceite

- `python evals/rodar.py --rotulo base` executa e produz a tabela; uma segunda rodada com
  mudança de prompt é comparável (`--comparar`).
- `evals/REGISTRO.md` com pelo menos uma iteração documentada e a decisão sobre o modelo do QA.
- Lint e mypy passam (o script de evals também tipado).
