# Módulo: estado-lote

**Responsabilidade:** persistir o progresso de cada produto do lote (`EstadoProduto`) para que
uma reexecução pule o que está pronto e retome do ponto de falha, sem repetir etapas caras
(LLM, upload de fotos).
**Estado:** implementado pelas tasks 06, 07, 11 · última atualização 2026-09-16 (task 11)

## Arquivos

- `models/status_produto.py` — `StatusProduto` (Enum)
- `models/estado_produto.py` — `EstadoProduto`
- `models/exceptions/erro_transicao_estado_invalida.py` — `ErroTransicaoEstadoInvalida`
- `models/exceptions/erro_estado_lote.py` — `ErroEstadoLote`
- `services/ports/repositorio_estado_lote.py` — `RepositorioEstadoLote` (Protocol)
- `services/politica_reexecucao.py` — `EtapaLote`, `DecisaoReexecucao`,
  `ResultadoPoliticaReexecucao`, `PoliticaReexecucao`
- `infra/repositorio_estado_lote_json.py` — `RepositorioEstadoLoteJson`

## Contratos

```python
# models/status_produto.py
class StatusProduto(Enum):
    VALIDADO = "validado"
    REPROVADO_VALIDACAO = "reprovado-validacao"
    ERRO_FOTOS = "erro-fotos"
    FOTOS_PUBLICADAS = "fotos-publicadas"
    TEXTOS_GERADOS = "textos-gerados"
    REPROVADO_QA = "reprovado-qa"
    ERRO_LLM = "erro-llm"
    PRONTO = "pronto"

# models/estado_produto.py — único agregado mutável do sistema
@dataclass
class EstadoProduto:
    sku_pai: str
    status: StatusProduto
    entrada: ProdutoEntrada
    hash_entrada: str
    validacao: ResultadoValidacao
    fotos: tuple[FotoProduto, ...] = ()   # tipado desde a task 07 (models/foto_produto.py)
    imagens_pai: tuple[str, ...] = ()
    textos: Mapping[str, str] | None = None
    tentativas: tuple[Mapping[str, object], ...] = ()
    custo_usd_estimado: Decimal = Decimal("0")
    verificacao: Mapping[str, object] | None = None
    atualizado_em: datetime = <agora, UTC>

    @classmethod
    def registrar_validacao(sku_pai, entrada, hash_entrada, resultado) -> EstadoProduto: ...
    def registrar_fotos(fotos: tuple[FotoProduto, ...], imagens_pai) -> None: ...
    def registrar_erro_fotos() -> None: ...
    def registrar_tentativa(tentativa, custo_usd=Decimal("0")) -> None: ...
    def registrar_textos(textos) -> None: ...
    def registrar_erro_llm() -> None: ...
    def reprovar_qa() -> None: ...
    def marcar_pronto() -> None: ...
    def registrar_verificacao(verificacao) -> None: ...

# models/exceptions/erro_transicao_estado_invalida.py
class ErroTransicaoEstadoInvalida(Exception):
    sku_pai: str
    status_atual: StatusProduto
    metodo: str

# models/exceptions/erro_estado_lote.py
class ErroEstadoLote(Exception):
    caminho: Path
    motivo: str

# services/ports/repositorio_estado_lote.py
class RepositorioEstadoLote(Protocol):
    def carregar(self, sku_pai: str) -> EstadoProduto | None: ...
    def salvar(self, estado: EstadoProduto) -> None: ...
    def listar(self) -> list[EstadoProduto]: ...
    def copiar_planilha_entrada(self, planilha: Path) -> None: ...   # task 11
    def salvar_relatorio(self, relatorio: Relatorio) -> None: ...    # task 11
    def diretorio_lote(self) -> Path: ...                            # task 11

# services/politica_reexecucao.py
class EtapaLote(Enum):
    VALIDAR = "validar"; FOTOS = "fotos"; TEXTOS = "textos"; MONTAR = "montar"

class DecisaoReexecucao(Enum):
    PULAR = "pular"; RETOMAR = "retomar"; RECOMECAR = "recomecar"

@dataclass(frozen=True)
class ResultadoPoliticaReexecucao:
    decisao: DecisaoReexecucao
    a_partir_de: EtapaLote | None

class PoliticaReexecucao:
    def decidir(
        self,
        estado_anterior: EstadoProduto | None,
        hash_entrada_atual: str,
        *,
        refazer_textos: bool = False,
        refazer_fotos: bool = False,
    ) -> ResultadoPoliticaReexecucao: ...

# infra/repositorio_estado_lote_json.py
class RepositorioEstadoLoteJson:
    def __init__(self, lote_dir: Path) -> None: ...
    def copiar_planilha_entrada(self, planilha: Path) -> None: ...
    def carregar(self, sku_pai: str) -> EstadoProduto | None: ...
    def salvar(self, estado: EstadoProduto) -> None: ...
    def listar(self) -> list[EstadoProduto]: ...
    def salvar_relatorio(self, relatorio: Relatorio) -> None: ...   # task 11: grava relatorio.md/.json
    def diretorio_lote(self) -> Path: ...                           # task 11: devolve lote_dir
```

## Comportamento

**`EstadoProduto`** — não tem construtor "vazio"/pendente: nasce pela fábrica
`registrar_validacao`, já como `validado` (aprovado) ou `reprovado-validacao` (reprovado). Os
demais 8 métodos são de instância e só mudam o status a partir de uma origem específica; fora
dela, levantam `ErroTransicaoEstadoInvalida`. Grafo de transições:

| Método | Origem válida | Destino |
|---|---|---|
| `registrar_validacao` (fábrica) | — | `validado` / `reprovado-validacao` |
| `registrar_fotos` | `validado`, `erro-fotos`, `fotos-publicadas`, `textos-gerados`, `reprovado-qa`, `erro-llm`, `pronto` | `fotos-publicadas` |
| `registrar_erro_fotos` | (mesmas origens de `registrar_fotos`) | `erro-fotos` |
| `registrar_tentativa` (não muda status) | `fotos-publicadas`, `erro-llm`, `textos-gerados`, `reprovado-qa`, `pronto` | mesmo status |
| `registrar_textos` | `fotos-publicadas`, `erro-llm`, `textos-gerados`, `reprovado-qa`, `pronto` | `textos-gerados` |
| `registrar_erro_llm` | (mesmas origens de `registrar_textos`) | `erro-llm` |
| `reprovar_qa` | (mesmas origens de `registrar_textos`) | `reprovado-qa` |
| `marcar_pronto` | `textos-gerados` | `pronto` |
| `registrar_verificacao` (não muda status) | `pronto` | `pronto` |

Origens de `registrar_fotos`/`registrar_textos` (e dos métodos que compartilham o mesmo
conjunto) foram ampliadas na task 11 além da progressão linear: qualquer status que já passou
pela etapa correspondente também é uma origem válida, para `--refazer-fotos`/`--refazer-textos`
poderem retomar a partir de um produto `pronto` (ou `reprovado-qa`/`erro-llm`/`textos-gerados`),
e para o retomar natural (sem flag) de `reprovado-qa` poder gerar textos de novo. Ver "Desvios e
decisões" em `docs/specs/tasks/11-processar-lote-relatorio.md`.

`registrar_tentativa` também acumula `custo_usd_estimado` (parâmetro `custo_usd`, somado ao
valor atual). Toda mutação atualiza `atualizado_em` para `datetime.now(UTC)`.

**`RepositorioEstadoLoteJson`** — o construtor recebe a raiz do lote (`lotes/<lote>/`) e cria,
de forma idempotente, `entrada/`, `estado/`, `fotos-processadas/` e `saida/`.
`copiar_planilha_entrada` é um método separado (não roda no construtor, já que `carregar`/
`listar`/`salvar` não precisam de uma planilha); promovido ao port na task 11 (antes só existia
na implementação concreta). `diretorio_lote()` devolve a raiz do lote — usado por `ProcessarLote`
(task 11) para montar `saida/<lote>.xlsx` sem precisar conhecer `LOTES_DIR`. `salvar_relatorio`
(task 11) grava `relatorio.md` (texto) e `relatorio.json` (`json.dumps` de `Relatorio.dados`) na
raiz do lote. `salvar` grava
`estado/<sku_pai>.json` por escrita atômica: `tempfile.mkstemp` no próprio diretório de destino
+ `Path.replace`; o arquivo temporário é sempre removido no `finally` (fica no disco só se a
escrita ou a troca falharem antes de completar). `carregar` devolve `None` para SKU sem arquivo;
JSON corrompido ou com campo faltando vira `ErroEstadoLote` (nunca deixa vazar
`json.JSONDecodeError`/`KeyError`). `listar` itera `estado/*.json` em ordem alfabética.

Serialização (funções privadas do módulo, `_para_dict`/`_de_dict`): `StatusProduto` ↔ `.value`;
`Decimal` (`preco` das variações, `custo_usd_estimado`) ↔ `str`; `datetime` (`atualizado_em`) ↔
ISO 8601 (`datetime.fromisoformat`); `ProdutoEntrada`/`VariacaoEntrada`/`ResultadoValidacao`/
`ProblemaValidacao`/`FotoProduto` ↔ dicts aninhados montados campo a campo (não usa
`dataclasses.asdict` genérico, para controlar a conversão de `Decimal`/`Path` dentro dos campos
compostos — `FotoProduto.arquivo_origem: Path` ↔ `str`, `_foto_para_dict`/`_foto_de_dict`, task
07). Os campos ainda sem tipo definido (`textos`, `tentativas`, `verificacao`) continuam
serializados como JSON puro (dict/list/str/int/float/bool/None) enquanto não tiverem um tipo
próprio (tasks 09/16/18).

**`PoliticaReexecucao.decidir`** — hash da entrada diferente do salvo sempre vence
(`recomecar`, ponto de partida `validar`); com hash igual, `refazer_fotos` tem prioridade sobre
`refazer_textos` (ambos retomam de uma etapa e a orquestração — task 11 — percorre em sequência
até o fim, cobrindo a etapa seguinte de qualquer forma); sem flags, o status por si só já indica
a etapa por onde retomar (tabela de casos no teste parametrizado); `pronto` sem nenhuma flag é a
única combinação que resulta em `pular`.

## Limites

- Não orquestra o lote (chamar as etapas na ordem, decidir quando parar) — isso é `ProcessarLote`,
  task 11. Este módulo só decide/persiste, não executa nada.
- `textos`/`tentativas`/`verificacao` ainda ficam com tipo mínimo (`Mapping[str, object]`/
  `Mapping[str, str]`); `fotos` já foi tipado (`FotoProduto`, task 07). As tasks 09/16
  (`TextosProduto`, tentativa estruturada) e 17 (verificação estruturada) substituem os
  restantes por dataclasses próprias — quando isso acontecer, a serialização em
  `infra/repositorio_estado_lote_json.py` precisa ser atualizada junto (mesmo padrão de
  `_foto_para_dict`/`_foto_de_dict` usado para `fotos`).
- `EstadoProduto` é mutável e nada impede reatribuir um campo por fora dos métodos em Python —
  a garantia é de convenção/revisão de código, não do type checker.

## Testes

- `tests/unit/models/test_estado_produto.py` — todas as transições válidas (uma por método,
  incluindo a fábrica com resultado aprovado/reprovado) e inválidas (`ErroTransicaoEstadoInvalida`
  a partir de um status fora da origem esperada); `registrar_tentativa` acumulando custo sem
  mudar status; `atualizado_em` muda a cada mutação.
- `tests/unit/services/test_politica_reexecucao.py` — teste parametrizado com a tabela de casos
  do critério de aceite (14 casos: sem estado anterior, hash diferente, cada status com hash
  igual, `pronto` com cada combinação de `--refazer-textos`/`--refazer-fotos`).
- `tests/unit/infra/test_repositorio_estado_lote_json.py` (`tmp_path`) — round-trip
  `salvar`→`carregar` de um `EstadoProduto` com todos os campos preenchidos (inclusive `Decimal`
  em `preco` e `custo_usd_estimado`, `datetime` em `atualizado_em`, e um `FotoProduto` real com
  `Path` em `arquivo_origem`), `carregar` de SKU inexistente devolve `None`, `listar` traz todos
  os salvos, construtor cria a árvore de pastas, `copiar_planilha_entrada` copia o arquivo,
  escrita atômica não deixa `.tmp` para trás, `ErroEstadoLote` para JSON corrompido e para JSON
  com campo faltando, `salvar` sobrescrevendo um estado existente, status persistido como o
  enum correto.
- `tests/unit/services/test_processador_lote.py` (task 11) — `_RepositorioEstadoLoteFake` em
  memória, inline (mesma convenção de fakes locais de `test_pipeline_fotos.py`), ainda não
  extraído para um módulo compartilhado.

## Histórico

- Task 06 (2026-09-14): criação do módulo — `StatusProduto`, `EstadoProduto` (fábrica
  `registrar_validacao` + 8 métodos de intenção), `RepositorioEstadoLote`/
  `RepositorioEstadoLoteJson`, `PoliticaReexecucao`. Ver "Desvios e decisões" na spec as-built
  (`docs/specs/tasks/06-estado-lote.md`) para os pontos em que o texto da task não especificava
  o suficiente para codar sem decisão de implementação.
- Task 07 (2026-09-14): `fotos` deixa de ser `tuple[Mapping[str, object], ...]` e passa a ser
  `tuple[FotoProduto, ...]` (`models/foto_produto.py`); `registrar_fotos` tipado de acordo;
  serialização em `infra/repositorio_estado_lote_json.py` ganhou
  `_foto_para_dict`/`_foto_de_dict`. `registrar_erro_fotos()` confirmado sem parâmetro de
  motivo (ver `docs/specs/tasks/07-pipeline-fotos.md`).
- Task 11 (2026-09-16): `RepositorioEstadoLote` ganha `copiar_planilha_entrada`,
  `salvar_relatorio`, `diretorio_lote` (wiring real em `config/composicao.py`/`cli.py`, primeiro
  consumidor do módulo). Origens de `registrar_fotos`/`registrar_erro_fotos`/`registrar_textos`/
  `registrar_erro_llm`/`reprovar_qa` ampliadas para cobrir `--refazer-fotos`/`--refazer-textos`
  a partir de um produto já `pronto` e o retomar natural de `reprovado-qa` — lacuna do grafo da
  task 06 exposta ao implementar a orquestração real (ver "Desvios e decisões" em
  `docs/specs/tasks/11-processar-lote-relatorio.md`).
- 2026-09-17 (fix ad-hoc, branch `fix/fix-validation`, sem task numerada — ADR-009 em
  `ARQUITETURA.md`): `FotoProduto` perde o campo `cor` (foto passa a valer para o produto
  inteiro, não por variação); `_foto_para_dict`/`_foto_de_dict` em
  `infra/repositorio_estado_lote_json.py` atualizados. Estado salvo em disco por execuções
  anteriores ao ADR-009 com `fotos` preenchido fica incompatível (`ErroEstadoLote` ao carregar)
  — reprocessar apagando o `estado/<sku>.json` correspondente resolve.
