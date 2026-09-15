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
| 01 | [Fundação: configuração, CLI com subcomandos](01-fundacao-configuracao-cli.md) | — | sonnet | concluída | [spec](../specs/tasks/01-fundacao-configuracao-cli.md) — 4 subcomandos retornam 2; `Configuracao.do_ambiente()` com padrões de §11; 26 testes |
| 02 | [Dados mestre e carregador de recursos](02-dados-mestre-recursos.md) | 01 | sonnet | concluída | [spec](../specs/tasks/02-dados-mestre-recursos.md) — YAML com 413 cores/17 tamanhos/45 categorias extraído do `.xlsx` real; `DadosMestre`/`CarregadorRecursos` batem com o critério de aceite; 52 testes |
| 03 | [Spike: a importação cria valor de grade?](03-spike-grade-importacao.md) | — | sonnet | concluída | [spec](../specs/tasks/03-spike-grade-importacao.md) — importação não cria valor novo de grade e não ignora caixa (`beige`≠`Beige`); rejeita a linha com erro explícito; validação estrita de `cor_valida` confirmada sem mudança |
| 04 | [Planilha de entrada: modelo, leitor e `modelo-entrada`](04-planilha-entrada.md) | 02 | sonnet | concluída | [spec](../specs/tasks/04-planilha-entrada.md) — 14 colunas (faixa-tamanho virou campo de entrada, ver ADR-005); leitor acumula erros de linha; modelo gerado com listas suspensas; round-trip com 2 produtos confere; 82 testes |
| 05 | [Validador de entrada, catálogo de fotos e `validar`](05-validador-entrada.md) | 03, 04 | sonnet | concluída | [spec](../specs/tasks/05-validador-entrada.md) — fixture `lote-piloto` com 6 produtos reprova exatamente cor inválida e GTIN inválido, aprova o resto; 120 testes |
| 06 | [Workspace e estado do lote](06-estado-lote.md) | 05 | sonnet | concluída | [spec](../specs/tasks/06-estado-lote.md) — `EstadoProduto` com fábrica `registrar_validacao` + 8 métodos de intenção valida transições; `RepositorioEstadoLoteJson` faz round-trip com `Decimal`/`datetime` e escrita atômica; `PoliticaReexecucao` com 14 casos parametrizados; 165 testes |
| 07 | [Pipeline de fotos: nomeação e compressão](07-pipeline-fotos.md) | 06 | sonnet | concluída | [spec](../specs/tasks/07-pipeline-fotos.md) — `NomeadorFotos`/`SeletorImagensPai` batem com o exemplo literal do §5.2 e o round-robin do §5.3; `ProcessadorImagemPillow` roda sobre `poc/fotos_input/` real (3000×4000) e produz ≤1600px/<500KB sem EXIF, HEIC testado de verdade; `PipelineFotos` fail-fast por produto; 195 testes |
| 08 | [Publicação no Cloudflare R2](08-publicacao-r2.md) | 07 | sonnet | concluída | [spec](../specs/tasks/08-publicacao-r2.md) — `ArmazenamentoImagensR2` (boto3) publica com `Content-Type`/`Cache-Control` corretos e confirma acessibilidade com HEAD real antes de contar a foto; falha em qualquer etapa aborta o produto (`erro-fotos`); contrato do port mantido sem alteração (ADR-006); 206 testes, `pytest -m integration` confirmado contra o bucket R2 real (4 passed) |
| 09 | [Port `GeradorTextos`, `TextosProduto` e gerador dummy](09-gerador-textos-dummy.md) | 06 | sonnet | concluída | [spec](../specs/tasks/09-gerador-textos-dummy.md) — `GeradorTextosDummy` garante os 4 campos dentro dos limites de §6.1 por construção para os 6 produtos de `lote-piloto`; placeholder `[DUMMY]` no título/h2/meta; 231 testes |
| 10 | [Montador da planilha de saída](10-montador-planilha-saida.md) | 06 | sonnet | concluída | [spec](../specs/tasks/10-montador-planilha-saida.md) — produto com 2 cores × 3 tamanhos gera 1 pai + 6 filhas com valores exatos coluna a coluna (GTIN incluído); teste opcional confirmou o layout de 54 colunas contra a exportação real e corrigiu 4 nomes de coluna na documentação; 246 testes |
| 11 | [`ProcessarLote`: orquestração, relatório e comando `processar` (com dummy)](11-processar-lote-relatorio.md) | 08, 09, 10 | sonnet | pendente | |
| 12 | [Cliente LLM Anthropic e repositório de prompts](12-cliente-llm-prompts.md) | 02 | opus | pendente | |
| 13 | [Recursos de conteúdo: loja, marcas, copy, SEO, QA](13-recursos-conteudo.md) | 12 | opus | pendente | |
| 14 | [Agente Copywriter e regras de texto](14-agente-copywriter.md) | 13 | opus | pendente | |
| 15 | [Agente SEO](15-agente-seo.md) | 14 | opus | pendente | |
| 16 | [Agente QA e orquestração `GeradorTextosIa` (substitui o dummy)](16-agente-qa-gerador-textos.md) | 15, 11 | opus | pendente | |
| 17 | [Evals dos agentes e calibração dos prompts](17-evals-calibracao.md) | 16 | opus | pendente | |
| 18 | [Verificação pós-importação e comando `verificar`](18-verificacao-pos-importacao.md) | 11 | sonnet | pendente | |
| 19 | [Lote piloto real, revisão de arquitetura e relatório final](19-lote-piloto-revisao-final.md) | 17, 18 | opus | pendente | |

Ordem sugerida de execução: 01 → 02 → 03 → 04 → 05 → 06 → 07 → 08 → 09 → 10 → 11 → 12 → 13
→ 14 → 15 → 16 → 17 → 18 → 19. As tasks 03 e 12/13 podem ser adiantadas se conveniente (não
dependem da cadeia de fotos).

**Marco intermediário (fim da task 11):** o `processar` gera `lotes/<lote>/saida/<lote>.xlsx`
importável na loja, com fotos reais no R2 e textos do `GeradorTextosDummy` (custo zero, sem
API). Só então entra a integração com LLM (12–16), que troca o dummy pela IA atrás do mesmo
port `GeradorTextos` — ver ADR-007 em `docs/ARQUITETURA.md`. Reordenação feita em 14/09/2026
(antigas 09–13 viraram 12–16; 14→10; 15→11; 16→17; 17→18; 18→19).

Regras válidas para toda task:

- Só criar arquivos, ports e abstrações que a task usa (arquitetura evolutiva).
- Se aparecer um caso de negócio não previsto em `ARQUITETURA.md` (dado real inconsistente,
  formato inesperado), **parar**, registrar e perguntar antes de decidir.
- Ao terminar: `ruff check . && ruff format . && mypy src && pytest`; depois
  `/python-clean-architecture:check-quality` na mudança.
- Registrar e commitar conforme o ciclo do `CLAUDE.md` (spec da task, spec viva do módulo,
  arquitetura, status, commit `Task NN: <resultado>`). A coluna **Validação** recebe o link
  `[spec](../specs/tasks/NN-<nome>.md)` e uma linha do que foi validado.
