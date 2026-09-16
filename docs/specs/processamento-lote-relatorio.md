# Módulo: processamento-lote-relatorio

**Responsabilidade:** orquestrar o lote inteiro (validar → fotos → textos → montar), um
produto por vez, com estado persistido a cada etapa, e produzir o relatório e a planilha final.
**Estado:** implementado pela task 11 · última atualização 2026-09-16 (task 11)

## Arquivos

- `models/resumo_lote.py` — `ResumoLote`
- `models/relatorio_lote.py` — `Relatorio`
- `services/processador_lote.py` — `OpcoesProcessamento`, `ProcessarLote`
- `services/gerador_relatorio.py` — `GeradorRelatorio`
- `config/composicao.py` — `montar_pipeline_fotos`, `montar_processador_lote`
- `cli.py` — subcomando `processar`

Os métodos `copiar_planilha_entrada`/`salvar_relatorio`/`diretorio_lote` que este módulo usa
pertencem ao port `RepositorioEstadoLote` do módulo `estado-lote` (ver
`docs/specs/estado-lote.md`).

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


# config/composicao.py
def montar_pipeline_fotos(configuracao: Configuracao, fotos: Path) -> PipelineFotos: ...
def montar_processador_lote(
    configuracao: Configuracao, fotos: Path, lote: str
) -> ProcessarLote: ...
```

Subcomando: `processar --planilha <xlsx> --fotos <pasta> --lote <nome> [--incluir-reprovados]
[--refazer-textos SKU…] [--refazer-fotos SKU…] [--verboso]`. Código de saída `0` quando
`resumo.todos_prontos`, `1` (`CODIGO_ERRO_NEGOCIO`) caso contrário, ou se `ErroConfiguracao`
(R2 ausente — primeiro comando a exigir de verdade), `ErroPlanilhaEntrada`, `ErroRecursos` ou
`ErroPlanilhaSaida` ocorrerem antes de terminar.

## Comportamento

**`ProcessarLote.executar(planilha, fotos, lote, opcoes)`**:

1. Copia a planilha para `entrada/` (auditoria) e lê + valida **todos** os produtos (a
   validação em lote é cross-produto: duplicidade de `sku-pai`/GTIN).
2. Para cada produto normalizado, computa um hash determinístico da entrada
   (`_hash_entrada`, `hashlib.sha256` sobre uma representação canônica dos campos — não usa
   `hash()` nativo do Python, que é aleatorizado por processo) e consulta
   `PoliticaReexecucao.decidir` com o estado salvo (se houver):
   - **recomeçar** (sem estado anterior ou hash mudou): cria `EstadoProduto` via
     `registrar_validacao`, com o `ResultadoValidacao` recortado só para aquele `sku_pai`, e
     salva. Produto `reprovado-validacao` fica fora do pipeline a partir daqui.
   - **pular**: reaproveita o estado salvo sem tocar em nada.
   - **retomar**: reaproveita o estado salvo e guarda a etapa (`fotos`/`textos`/`montar`) por
     onde continuar.
3. Ordena os aprovados por marca (cache de prompt) e processa um por vez: fotos → textos →
   montar, pulando as etapas já concluídas conforme a etapa de retomada. Cada etapa concluída
   é salva (`repositorio.salvar`) antes de seguir para a próxima. Uma falha de fotos
   (`ErroProcessamentoImagem`/`ErroPublicacaoImagem`) ou de montagem (`ErroPlanilhaSaida`) é
   capturada, o estado (já em `erro-fotos` pelo próprio `PipelineFotos`, ou inalterado para
   `ErroPlanilhaSaida`) é salvo, e o laço segue para o próximo produto.
4. `KeyboardInterrupt` é capturado em volta do laço inteiro (não por etapa): como o estado só é
   persistido depois de cada etapa concluída, a interrupção nunca deixa um `EstadoProduto`
   salvo pela metade. O fluxo segue direto para o passo 5 com o que houver pronto.
5. Monta e escreve `saida/<lote>.xlsx` a partir de **todos** os estados do workspace
   (`repositorio.listar()`, não só os processados nesta execução — cobre reexecuções parciais),
   gera o `Relatorio` (`GeradorRelatorio`) e grava `relatorio.md`/`relatorio.json`
   (`repositorio.salvar_relatorio`). Devolve `ResumoLote`.

**`GeradorRelatorio.gerar(estados, resumo)`** — monta as duas formas do relatório a partir só
dos dados já em `EstadoProduto`/`ResumoLote` (sem I/O): resumo (contagem por status, linhas
geradas, custo, duração), tabela por produto, reprovados com motivos (problemas de validação ou
último veredito de QA registrado em `tentativas`), avisos (de `estado.validacao.avisos`),
custo/tokens por agente (agregado de `estado.tentativas`), categorias usadas e fotos publicadas
× não usadas no pai (`estado.fotos` cujo `url` não está em `estado.imagens_pai`).

**`montar_pipeline_fotos`** — sempre publica no R2 real (`configuracao.exigir_r2()`); não há
opção de armazenamento local no wiring de `processar` (decisão confirmada com o usuário — ver
"Desvios e decisões" na spec as-built da task).

## Limites

- Não decide qual implementação de `GeradorTextos` usar além do que `montar_gerador_textos`
  já resolve — hoje é sempre `GeradorTextosDummy` (ADR-007); a troca para IA é só wiring
  (task 16), sem mudança neste módulo.
- Não há flag para publicar fotos localmente (`--sem-upload` foi removida do escopo desta
  task); `ArmazenamentoImagensDiretorio` continua existindo só para testes.
- `custo_por_agente` do relatório não tem custo por tentativa individual — só o agregado por
  produto (`EstadoProduto.custo_usd_estimado`). Com o dummy é sempre zero; a task 16 deve
  revisar se `registrar_tentativa` precisa carregar o custo da própria chamada.
- Critério de aceite da task (rodar sobre o lote piloto com R2 real, importar manualmente no
  painel, remover em seguida) é uma verificação manual — não roda no `pytest`.

## Testes

- `tests/unit/services/test_processador_lote.py` — fakes inline de todos os ports/serviços
  injetados (mesma convenção sem `unittest.mock` de `test_pipeline_fotos.py`), incluindo
  `_RepositorioEstadoLoteFake` em memória: lote feliz; erro de fotos não impede os outros
  produtos; reexecução pula `pronto` sem chamar fotos/textos de novo; `--refazer-textos` só
  regenera textos; `--refazer-fotos` reprocessa fotos e textos; produto `reprovado-validacao`
  fica fora do pipeline mas aparece no relatório; `KeyboardInterrupt` ainda gera
  planilha/relatório parciais; hash diferente recomeça mesmo já `pronto`; `_hash_entrada` é
  estável para a mesma entrada e muda quando um campo muda.
- `tests/unit/services/test_gerador_relatorio.py` — um estado `pronto` (com fotos, foto não
  usada, uma tentativa) e um `reprovado-validacao`; confere todas as seções de `dados` e
  trechos do `markdown`.
- `tests/unit/config/test_composicao.py` — `montar_pipeline_fotos` levanta `ErroConfiguracao`
  sem R2 configurado e devolve `PipelineFotos` funcional com R2 configurado;
  `montar_processador_lote` devolve `ProcessarLote` funcional e cria o workspace do lote.
- `tests/unit/test_cli.py` — parsing de `processar` com `--verboso`; `ErroConfiguracao` (R2
  ausente, com `cwd`/env isolados do `.env` real do desenvolvedor) vira código de erro de
  negócio com mensagem clara.

## Histórico

- Task 11 (2026-09-16): criação do módulo — `OpcoesProcessamento`, `ProcessarLote`,
  `GeradorRelatorio`, `ResumoLote`, `Relatorio`, wiring real do subcomando `processar`. Ver
  "Desvios e decisões" na spec as-built (`docs/specs/tasks/11-processar-lote-relatorio.md`).
