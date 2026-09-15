# Task 11 — `ProcessarLote`: orquestração, relatório e comando `processar`

- **Depende de:** 08, 09, 10
- **Modelo recomendado:** sonnet
- **Leia antes:** `docs/ARQUITETURA.md` §3 (fluxo e tabela de etapas), §8 (workspace,
  reexecução, relatório), §10, §11, §13 (execução sequencial), ADR-007 (dummy provisório)

## Objetivo

Ligar tudo: validar → fotos → textos → montar → relatar, um produto por vez, com
estado persistido a cada etapa, e expor pelo subcomando `processar`. Ao final desta task o
sistema gera uma planilha **importável** com fotos reais no R2 e textos do
`GeradorTextosDummy` (task 09) — o marco intermediário do roadmap. A task 16 troca o dummy
pela IA sem mexer neste orquestrador.

## Escopo

1. `services/processador_lote.py`: `ProcessarLote(validador, pipeline_fotos, gerador_textos,
   montador, escritor, repositorio_estado, gerador_relatorio, politica_reexecucao)` — onde
   `gerador_textos` é o port `GeradorTextos` (task 09), nunca uma implementação concreta —
   com `executar(planilha, fotos, lote, opcoes) -> ResumoLote`:
   - lê e valida; grava estado `validado`/`reprovado-validacao` de todos;
   - ordena os aprovados por marca (cache) e processa **um por vez**, em loop simples:
     fotos → textos → `pronto`, salvando o estado após cada etapa e capturando exceções de
     domínio por produto (uma falha não derruba o lote). Sem threads nem async;
   - `Ctrl+C` (`KeyboardInterrupt`) deixa o estado consistente: o produto em andamento fica
     na última etapa concluída e a reexecução retoma dali; a planilha e o relatório são
     gerados com o que estiver pronto até então;
   - aplica a política de reexecução (pular `pronto`, retomar da etapa que falhou,
     `--refazer-*`);
   - monta e escreve `saida/<lote>.xlsx`; gera `relatorio.md` e `relatorio.json`;
   - devolve `ResumoLote` (contagens por status, custo, duração, caminho dos artefatos).
2. `services/gerador_relatorio.py`: `GeradorRelatorio.gerar(estados, resumo) ->
   Relatorio` (markdown + dict) com as seções de §8: resumo, tabela por produto, reprovados
   com motivos (validação e QA, com o último texto), avisos, custo/tokens por agente, lista
   de categorias usadas, fotos publicadas e não usadas. Com o dummy, a seção de custo/tokens
   mostra `dummy` com zero — a estrutura já prevê os agentes de IA, não a simplificar.
3. Port + infra mínimos para escrever o relatório (`EscritorRelatorio` em disco) — ou
   reutilizar o repositório de estado para gravar no workspace, o que for mais simples.
4. `cli.py`/`config/composicao.py`: `processar --planilha --fotos --lote
   [--incluir-reprovados] [--refazer-textos SKU…] [--refazer-fotos SKU…] [--sem-upload]`.
   Saída no terminal: progresso por produto (SKU, etapa, status) e o resumo final; código de
   saída 0 se todos `pronto`, 1 se houve reprovados/erros (planilha gerada mesmo assim).
   Logging com `logging` (nível por `--verboso`), nunca `print` fora da CLI.
5. Testes do orquestrador com todos os fakes: lote feliz; produto com erro de fotos não
   impede os outros; reexecução pula `pronto`; `--refazer-textos`; relatório contém os
   reprovados. Teste do gerador de relatório com snapshot simples (trechos esperados).

## Fora do escopo

Textos por IA (tasks 12–16 — aqui o `processar` usa o dummy), verificação pós-importação
(task 18), evals (task 17).

## Critério de aceite

- `processar` sobre a fixture do lote piloto, com **gerador dummy** e R2 real (`.env` do
  desenvolvedor): gera `lotes/<lote>/saida/<lote>.xlsx` com os produtos válidos, os 2
  produtos com erro proposital aparecem no relatório, custo total zerado por produto no
  relatório.
- A planilha gerada é importada manualmente no painel da loja (mesma prova da POC) e os
  produtos aparecem com fotos e grades; os produtos são removidos/desativados em seguida
  (textos dummy não ficam no ar).
- Rodar de novo o mesmo comando termina em segundos sem reprocessar fotos (estado).
- Lint, mypy e pytest passam.
