# Spec as-built — Task 06: Workspace e estado do lote

- **Data:** 2026-09-14 · **Task:** `docs/tasks/06-estado-lote.md` · **Módulos:** `estado-lote`

## Entregue

- `StatusProduto` (`models/status_produto.py`): os 8 status do pipeline.
- `EstadoProduto` (`models/estado_produto.py`), único agregado mutável do sistema: nasce pela
  fábrica `registrar_validacao` (já `validado`/`reprovado-validacao`) e evolui por 8 métodos de
  intenção que validam a transição de status antes de mudar qualquer campo.
- `RepositorioEstadoLote` (port) e `RepositorioEstadoLoteJson` (infra): um JSON por SKU em
  `lotes/<lote>/estado/`, escrita atômica, cria a árvore do workspace no construtor, copia a
  planilha de entrada para `entrada/`.
- `PoliticaReexecucao`: decide `pular`/`retomar de <etapa>`/`recomeçar` a partir do estado
  anterior, do hash da entrada atual e das flags `--refazer-textos`/`--refazer-fotos`.
- `ErroTransicaoEstadoInvalida` e `ErroEstadoLote` (novas exceções de domínio).

## Arquivos

| Camada | Criados | Alterados |
|---|---|---|
| models | `models/status_produto.py`, `models/estado_produto.py` | — |
| models/exceptions | `models/exceptions/erro_transicao_estado_invalida.py`, `models/exceptions/erro_estado_lote.py` | — |
| services/ports | `services/ports/repositorio_estado_lote.py` | — |
| services | `services/politica_reexecucao.py` | — |
| infra | `infra/repositorio_estado_lote_json.py` | — |
| tests | `tests/unit/models/test_estado_produto.py`, `tests/unit/services/test_politica_reexecucao.py`, `tests/unit/infra/test_repositorio_estado_lote_json.py` | — |

Nenhum arquivo de `config/` ou `cli.py` foi alterado (fora do escopo desta task, ver "Fora do
escopo" na task).

## Contratos

Ver `docs/specs/estado-lote.md` §Contratos (assinaturas completas).

## Regras de negócio implementadas

- Grafo de transições de `EstadoProduto` (tabela em `docs/specs/estado-lote.md` §Comportamento):
  cada método de intenção só é aceito a partir da origem correta; fora dela, levanta
  `ErroTransicaoEstadoInvalida` nomeando SKU, status atual e método chamado.
- `registrar_tentativa` acumula `custo_usd_estimado` sem mudar o status.
- `PoliticaReexecucao`: hash diferente sempre recomeça (do zero, a partir de `validar`); com hash
  igual, `pronto` sem flag é pulado, qualquer outro status retoma da etapa que falta/falhou, e
  `--refazer-fotos`/`--refazer-textos` forçam retomar de uma etapa anterior à que o status
  indicaria (`--refazer-fotos` tem prioridade sobre `--refazer-textos` quando os dois aparecem
  juntos, porque retomar de `fotos` já cobre `textos` na sequência).
- `RepositorioEstadoLoteJson`: workspace (`entrada/`, `estado/`, `fotos-processadas/`, `saida/`)
  criado de forma idempotente; escrita de estado atômica (nunca deixa um `.json` parcialmente
  escrito); JSON corrompido ou com campo faltando nunca propaga exceção de biblioteca
  (`json`/`KeyError`), só `ErroEstadoLote`.

## Desvios e decisões

| Pedido (task) | Feito | Motivo |
|---|---|---|
| `registrar_validacao` listado entre os "métodos de intenção" (dando a entender que é método de instância, mutando um `EstadoProduto` já existente) | Implementado como **classmethod de fábrica** — é assim que um `EstadoProduto` nasce; não existe construtor "vazio" | Os 8 status listados pela task não incluem nenhum "pendente"/"novo" anterior à validação, e a arquitetura não previa um. Não havia origem válida de onde `registrar_validacao` pudesse partir como método de instância. Fábrica resolve sem inventar um 9º status que nunca seria persistido de verdade. |
| Task lista `erro-fotos` e `erro-llm` como status, mas nenhum dos 7 métodos nomeados os alcança | Acrescentados `registrar_erro_fotos()` e `registrar_erro_llm()` (mesmo padrão de nome de intenção dos demais) | Sem eles, dois dos oito status do próprio escopo da task seriam inalcançáveis — lacuna de especificação, não uma regra de negócio nova (não muda o que os dados significam, só como o código os alcança). |
| Task não detalha o formato de `mensagem`/motivo de erro para `erro-fotos`/`erro-llm`/`reprovado-qa` | Esses três métodos não recebem parâmetro de mensagem; o motivo de uma reprovação de QA já vive em `tentativas` (chamado a cada rodada via `registrar_tentativa`, antes de `reprovar_qa`) | `docs/ARQUITETURA.md` (ADR-001) só promete "o último texto e os motivos" no relatório, e o schema de `tentativas` (§8) já carrega `veredito_qa`/`veredito_regra`. Evita inventar um campo (`erro: str \| None`) fora da lista de campos que a task pediu para `EstadoProduto`. `erro-fotos` fica sem motivo estruturado por ora — se task 07 precisar, ela acrescenta o campo certo (a task 06 pede explicitamente para não antecipar modelo que a task 07 ainda vai desenhar). |
| Task não define como `custo_usd_estimado` é atualizado | `registrar_tentativa` ganhou um parâmetro opcional `custo_usd: Decimal = Decimal("0")`, somado ao valor acumulado | Único ponto do escopo onde custo por chamada LLM naturalmente se encaixa (é por tentativa que o custo de uma chamada é conhecido); evita um 9º método (`registrar_custo`) não pedido pela task. |
| `PoliticaReexecucao` — task não define a tabela completa de casos, só os princípios (hash diferente recomeça, flags forçam retomada) | Tabela completa com 14 casos desenhada a partir de `docs/ARQUITETURA.md` §3/§8 ("interromper e reexecutar retoma do produto e da etapa onde parou"; "produtos `pronto` são pulados; `erro-*` e `reprovado-*` são reprocessados") e registrada no teste parametrizado | Preenche exatamente a lacuna que a arquitetura deixa implícita, sem introduzir regra nova: todo status "em andamento" (`validado`, `fotos-publicadas`, `textos-gerados`) retoma da etapa seguinte; todo status de erro/reprovação retoma da própria etapa. |
| Rule 5 do `check-quality` (nenhum parâmetro flag) — `PoliticaReexecucao.decidir` tem `refazer_textos`/`refazer_fotos` como booleanos que mudam o caminho | Mantidos como dois parâmetros nomeados (`*`, keyword-only) em vez de 4 métodos por combinação | O próprio texto da task pede "aplica `--refazer-textos`/`--refazer-fotos`" como entrada da mesma decisão — são exatamente as duas flags que a CLI (task 11) recebe e repassa; separar em métodos obrigaria a orquestração a fazer o dispatch que a política deveria fazer. Aceito como exceção documentada à regra. |
| Rule 21 do `check-quality` (nome de método enganoso: `create_X` deveria criar e devolver) aplicada ao contrário — `registrar_X` normalmente só grava em algo existente | `registrar_validacao` grava **e** cria (fábrica) | Nome pedido literalmente pela task; renomear para `criar`/`validar` seria uma divergência maior do texto da task do que manter o nome e documentar a tensão aqui. |

## Verificação executada

- `ruff check . && ruff format . && mypy src && pytest` → tudo passando (165 testes, 45 novos
  desta task; `mypy --strict`: sem problemas em 36 arquivos fonte).
- `/python-clean-architecture:check-quality` sobre os arquivos novos: 1 ajuste aplicado
  (`infra/repositorio_estado_lote_json.py`: `except BaseException` na escrita atômica virou
  `finally` com `unlink(missing_ok=True)`, sem captura nenhuma — regra 16, exceção ampla). Duas
  exceções aceitas e documentadas na tabela acima (regra 5 em `PoliticaReexecucao.decidir`,
  regra 21 em `EstadoProduto.registrar_validacao`). Demais regras sem violação.

## Pendências para tasks futuras

- `fotos`/`textos`/`tentativas`/`verificacao` ganham tipos próprios (`FotoProduto` na task 07;
  `TextosProduto`/registro de tentativa estruturado nas tasks 09/16; verificação estruturada na
  task 18) — a serialização em `infra/repositorio_estado_lote_json.py` precisa acompanhar.
- Wiring em `config/composicao.py` e no subcomando `processar` — task 11, que também precisa de
  um `RepositorioEstadoLoteFake` em memória para testar `ProcessarLote` sem tocar disco.
- Mensagem/motivo estruturado para `erro-fotos` fica em aberto até a task 07 desenhar
  `FotoProduto`/o erro de processamento de imagem.
