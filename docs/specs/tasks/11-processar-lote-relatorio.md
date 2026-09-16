# Spec as-built — Task 11: `ProcessarLote`, relatório e comando `processar`

- **Data:** 2026-09-16 · **Task:** `docs/tasks/11-processar-lote-relatorio.md` · **Módulos:**
  `processamento-lote-relatorio`, `estado-lote` (ampliado)

## Entregue

`processar --planilha --fotos --lote [--incluir-reprovados] [--refazer-textos SKU…]
[--refazer-fotos SKU…] [--verboso]` liga validação (05) → fotos/R2 (07/08) → textos dummy (09)
→ montagem (10) num laço sequencial por produto, com estado persistido a cada etapa, gera
`lotes/<lote>/saida/<lote>.xlsx` + `relatorio.md`/`relatorio.json`, e devolve código de saída 0
(todos `pronto`) ou 1 (algum reprovado/erro). `Ctrl+C` no meio do lote encerra o laço e ainda
gera planilha/relatório com o que estiver pronto.

## Arquivos

| Camada | Criados | Alterados |
|---|---|---|
| models | `models/resumo_lote.py`, `models/relatorio_lote.py` | `models/estado_produto.py` (grafo de transições ampliado — ver "Desvios e decisões") |
| services | `services/processador_lote.py`, `services/gerador_relatorio.py` | — |
| services/ports | — | `services/ports/repositorio_estado_lote.py` (+ `copiar_planilha_entrada`, `salvar_relatorio`, `diretorio_lote`) |
| infra | — | `infra/repositorio_estado_lote_json.py` (implementa os 2 métodos novos) |
| config | — | `config/composicao.py` (+ `montar_pipeline_fotos`, `montar_processador_lote`) |
| cli | — | `cli.py` (`_processar` real, flag `--verboso`, tratamento de `ErroConfiguracao`) |
| tests | `tests/unit/services/test_processador_lote.py`, `tests/unit/services/test_gerador_relatorio.py` | `tests/unit/models/test_estado_produto.py`, `tests/unit/config/test_composicao.py`, `tests/unit/test_cli.py` |

## Contratos

```python
# services/processador_lote.py
@dataclass(frozen=True)
class OpcoesProcessamento:
    incluir_reprovados: bool = False
    refazer_textos: frozenset[str] = frozenset()
    refazer_fotos: frozenset[str] = frozenset()


class ProcessarLote:
    def __init__(
        self,
        leitor_planilha_entrada: LeitorPlanilhaEntrada,
        validador: ValidadorEntrada,
        pipeline_fotos: PipelineFotos,
        gerador_textos: GeradorTextos,
        montador: MontadorPlanilha,
        escritor: EscritorPlanilhaSaida,
        repositorio_estado: RepositorioEstadoLote,
        gerador_relatorio: GeradorRelatorio,
        politica_reexecucao: PoliticaReexecucao,
    ) -> None: ...
    def executar(
        self, planilha: Path, fotos: Path, lote: str, opcoes: OpcoesProcessamento
    ) -> ResumoLote: ...


# services/gerador_relatorio.py
class GeradorRelatorio:
    def gerar(self, estados: Sequence[EstadoProduto], resumo: ResumoLote) -> Relatorio: ...


# models/resumo_lote.py
@dataclass(frozen=True)
class ResumoLote:
    contagem_por_status: Mapping[StatusProduto, int]
    custo_usd_total: Decimal
    duracao_segundos: float
    caminho_planilha: Path
    caminho_relatorio_md: Path
    caminho_relatorio_json: Path

    @property
    def todos_prontos(self) -> bool: ...


# models/relatorio_lote.py
@dataclass(frozen=True)
class Relatorio:
    markdown: str
    dados: Mapping[str, object]


# services/ports/repositorio_estado_lote.py (métodos novos)
def copiar_planilha_entrada(self, planilha: Path) -> None: ...
def salvar_relatorio(self, relatorio: Relatorio) -> None: ...
def diretorio_lote(self) -> Path: ...


# config/composicao.py
def montar_pipeline_fotos(configuracao: Configuracao, fotos: Path) -> PipelineFotos: ...
def montar_processador_lote(
    configuracao: Configuracao, fotos: Path, lote: str
) -> ProcessarLote: ...
```

Subcomando: `processar --planilha <xlsx> --fotos <pasta> --lote <nome> [--incluir-reprovados]
[--refazer-textos SKU…] [--refazer-fotos SKU…] [--verboso]`; código de saída `0` se
`resumo.todos_prontos`, `1` (`CODIGO_ERRO_NEGOCIO`) caso contrário ou se `ErroConfiguracao`
(R2 ausente)/`ErroPlanilhaEntrada`/`ErroRecursos`/`ErroPlanilhaSaida` ocorrerem.

## Regras de negócio implementadas

- Lê e valida **todos** os produtos da planilha a cada execução (duplicidade de `sku-pai`/GTIN
  é cross-produto); por produto, decide via `PoliticaReexecucao` entre recomeçar (sem estado
  anterior ou hash mudou), pular (`pronto`, hash igual, sem flags) ou retomar de uma etapa.
- `recomeçar`: cria `EstadoProduto` novo via `registrar_validacao` com o `ResultadoValidacao`
  recortado só para aquele `sku_pai` (o validador devolve o resultado do lote inteiro).
- Produtos aprovados são ordenados por marca (cache de prompt, mesmo com o dummy) antes do
  laço fotos → textos → montar.
- Uma falha de fotos (`ErroProcessamentoImagem`/`ErroPublicacaoImagem`) ou de montagem
  (`ErroPlanilhaSaida`) aborta só aquele produto — o estado já foi atualizado pelo próprio
  método de intenção antes da exceção subir; o laço continua para o próximo produto.
- `Ctrl+C` (`KeyboardInterrupt`) é capturado em volta do laço de produtos (não por etapa); como
  o estado só é persistido depois de cada etapa concluída, a interrupção nunca deixa um estado
  salvo pela metade. O fluxo segue direto para montar a planilha/relatório com o que houver.
- `.xlsx` final e relatório são montados uma única vez, no fim, a partir de
  `repositorio.listar()` (todos os estados do workspace, não só os processados nesta execução).
- Hash da entrada (`_hash_entrada`, `services/processador_lote.py`): `sha256` sobre uma
  representação canônica dos campos do produto normalizado — não usa `hash()` nativo do Python
  (aleatorizado por processo via `PYTHONHASHSEED`, não comparável entre execuções da CLI).

## Desvios e decisões

| Pedido (task/arquitetura) | Feito | Motivo |
|---|---|---|
| Task listava flag `--sem-upload` | Removida — `processar` sempre publica no R2 real | Confirmado com o usuário em plan mode: sem branch para armazenamento local no wiring de `processar`; `ArmazenamentoImagensDiretorio` continua existindo só para testes. |
| Construtor de `ProcessarLote` listado pela task (8 dependências) não incluía nada capaz de ler a planilha, mas `executar(planilha, …)` precisa disso | Acrescentado 9º parâmetro `leitor_planilha_entrada: LeitorPlanilhaEntrada` | Nenhum dos 8 objetos listados lê `.xlsx`; mesmo padrão de preenchimento de lacuna que a task 06 documentou (`registrar_erro_fotos`/`registrar_erro_llm` não listados pela task 06 mas necessários para os 8 status do próprio escopo dela). |
| Parâmetro `fotos` de `executar` | Recebido só para log/registro — não reconstrói nenhum port | `ValidadorEntrada`/`PipelineFotos` já chegam da composição amarrados à mesma pasta `--fotos`; não há necessidade (nem como, dado o formato do construtor) de reconstruí-los dentro de `executar`. |
| `EstadoProduto.registrar_fotos`/`registrar_erro_fotos` (origem: `validado`, `erro-fotos`) e `registrar_textos`/`registrar_erro_llm`/`reprovar_qa` (origem: `fotos-publicadas`, `erro-llm`) — grafo da task 06 | Origens ampliadas: fotos passa a aceitar também `fotos-publicadas`, `textos-gerados`, `reprovado-qa`, `pronto`; textos passa a aceitar também `textos-gerados`, `reprovado-qa`, `pronto` | Bug de especificação herdado da task 06: `PoliticaReexecucao._JA_TEM_FOTOS`/`_JA_TEM_TEXTOS` (já confirmados e testados na task 06, tabela de 14 casos) sempre previram `--refazer-fotos`/`--refazer-textos` retomando a partir de um produto `pronto` (ou `reprovado-qa`/`erro-llm`/`textos-gerados`) — mas o grafo de `EstadoProduto` nunca permitia essa transição de volta. Só percebido ao escrever o teste de `--refazer-textos`/`--refazer-fotos` desta task (`ErroTransicaoEstadoInvalida` inesperado). Não é regra de negócio nova: a regra (refazer funciona mesmo `pronto`) já estava confirmada e testada em `docs/specs/estado-lote.md`; esta task só corrige a mecânica que faltava para cumpri-la. |
| Relatório: task permitia port novo ou reaproveitar o repositório ("o que for mais simples") | Reaproveitado: `RepositorioEstadoLote` ganhou `salvar_relatorio`/`diretorio_lote`/`copiar_planilha_entrada` (o último já existia só em `RepositorioEstadoLoteJson`, sem estar no port — também promovido) | Evita um port + infra novos para duas escritas de arquivo; `docs/tasks/11-processar-lote-relatorio.md` explicitamente permitia essa escolha. |
| Etapa "Montar" (task: "falha → erro de programação, não deve ocorrer") | `montador.montar(estado)` chamado por produto antes de `marcar_pronto()`, capturando `ErroPlanilhaSaida` como as demais etapas | Dá sentido à transição `textos-gerados → pronto` sem esperar o fim do lote para descobrir um problema de montagem de um produto específico; consistente com "uma falha não derruba o lote" pedido pela task para as outras etapas. |

## Verificação executada

- `ruff check . && ruff format . && mypy src && pytest` → tudo passando (265 testes de unidade,
  19 novos desta task + 4 ajustados em `test_estado_produto.py`; `mypy --strict`: sem problemas
  em 61 arquivos fonte).
- `/python-clean-architecture:check-quality` sobre os arquivos novos/alterados: nenhuma
  violação bloqueante. Os únicos parâmetros booleanos (`OpcoesProcessamento.incluir_reprovados`,
  reuso de `refazer_textos`/`refazer_fotos` de `PoliticaReexecucao.decidir`) seguem o mesmo
  padrão já aceito e documentado na task 06 (regra 5, "flag como parâmetro").
- Critério de aceite da task (rodar sobre a fixture do lote piloto com R2 real do `.env`,
  importar manualmente no painel, remover em seguida) **não foi executado nesta sessão** —
  requer ação manual do usuário com credenciais reais; fica registrado como pendência.

## Pendências para tasks futuras

- Rodar `processar` de verdade sobre `tests/fixtures/lote-piloto/` com R2 real e confirmar a
  importação manual no painel (critério de aceite da task) — ação do usuário.
- `custo_por_agente` no relatório não tem um campo de custo por tentativa individual (só o
  agregado por produto em `EstadoProduto.custo_usd_estimado`); com o dummy é sempre zero, mas a
  task 16 (LLM real) deve revisar se `registrar_tentativa` precisa carregar o custo daquela
  chamada dentro da própria tentativa para o relatório atribuir com precisão por agente.
- `verificar` (task 18) segue não implementado.
