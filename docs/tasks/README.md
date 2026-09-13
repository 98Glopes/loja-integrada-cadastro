# Backlog de implementação

Tasks sequenciais e incrementais, uma por arquivo, prontas para serem coladas como prompt
numa sessão do Claude Code. Cada task entrega algo testável isoladamente e o pipeline
continua rodando ponta a ponta (mesmo parcial) ao final dela.

Toda task segue o **ciclo spec → código → spec** do `CLAUDE.md`: ler arquitetura + task +
specs vivas dos módulos; implementar e verificar; gravar `docs/specs/tasks/NN-<nome>.md` e a
spec viva do módulo; atualizar `docs/ARQUITETURA.md` (🔲 → ✅, ADR se mudou decisão); marcar o
**Status** nesta tabela com link para a spec; commitar. A task diz quais seções e arquivos
adicionais ler.

Convenção de status: `pendente` → `em andamento` → `concluída` (com uma linha do que foi
validado) ou `bloqueada` (com o motivo).

Heurística de modelo (de `docs/brutos/PROMPT_CLAUDE_CODE.md`): **opus** para decisões de
contrato, prompt engineering e revisão final; **sonnet** para código determinístico e testes;
**haiku** para tarefas mecânicas.

| # | Task | Depende de | Modelo | Status | Validação |
|---|---|---|---|---|---|
| 01 | [Fundação: configuração, CLI com subcomandos](01-fundacao-configuracao-cli.md) | — | sonnet | pendente | |
| 02 | [Dados mestre e carregador de recursos](02-dados-mestre-recursos.md) | 01 | sonnet | pendente | |
| 03 | [Spike: a importação cria valor de grade?](03-spike-grade-importacao.md) | — | sonnet | pendente | |
| 04 | [Planilha de entrada: modelo, leitor e `modelo-entrada`](04-planilha-entrada.md) | 02 | sonnet | pendente | |
| 05 | [Validador de entrada, catálogo de fotos e `validar`](05-validador-entrada.md) | 03, 04 | sonnet | pendente | |
| 06 | [Workspace e estado do lote](06-estado-lote.md) | 05 | sonnet | pendente | |
| 07 | [Pipeline de fotos: nomeação e compressão](07-pipeline-fotos.md) | 06 | sonnet | pendente | |
| 08 | [Publicação no Cloudflare R2](08-publicacao-r2.md) | 07 | sonnet | pendente | |
| 09 | [Cliente LLM Anthropic e repositório de prompts](09-cliente-llm-prompts.md) | 02 | opus | pendente | |
| 10 | [Recursos de conteúdo: loja, marcas, copy, SEO, QA](10-recursos-conteudo.md) | 09 | opus | pendente | |
| 11 | [Agente Copywriter e regras de texto](11-agente-copywriter.md) | 10 | opus | pendente | |
| 12 | [Agente SEO](12-agente-seo.md) | 11 | opus | pendente | |
| 13 | [Agente QA e orquestração `GeradorTextos`](13-agente-qa-gerador-textos.md) | 12 | opus | pendente | |
| 14 | [Montador da planilha de saída](14-montador-planilha-saida.md) | 06 | sonnet | pendente | |
| 15 | [`ProcessarLote`: orquestração, relatório e comando `processar`](15-processar-lote-relatorio.md) | 08, 13, 14 | sonnet | pendente | |
| 16 | [Evals dos agentes e calibração dos prompts](16-evals-calibracao.md) | 15 | opus | pendente | |
| 17 | [Verificação pós-importação e comando `verificar`](17-verificacao-pos-importacao.md) | 15 | sonnet | pendente | |
| 18 | [Lote piloto real, revisão de arquitetura e relatório final](18-lote-piloto-revisao-final.md) | 16, 17 | opus | pendente | |

Ordem sugerida de execução: 01 → 02 → 03 → 04 → 05 → 06 → 07 → 08 → 09 → 10 → 11 → 12 → 13
→ 14 → 15 → 16 → 17 → 18. As tasks 03 e 09/10 podem ser adiantadas se conveniente (não
dependem da cadeia de fotos).

Regras válidas para toda task:

- Só criar arquivos, ports e abstrações que a task usa (arquitetura evolutiva).
- Se aparecer um caso de negócio não previsto em `ARQUITETURA.md` (dado real inconsistente,
  formato inesperado), **parar**, registrar e perguntar antes de decidir.
- Ao terminar: `ruff check . && ruff format . && mypy src && pytest`; depois
  `/python-clean-architecture:check-quality` na mudança.
- Registrar e commitar conforme o ciclo do `CLAUDE.md` (spec da task, spec viva do módulo,
  arquitetura, status, commit `Task NN: <resultado>`). A coluna **Validação** recebe o link
  `[spec](../specs/tasks/NN-<nome>.md)` e uma linha do que foi validado.
