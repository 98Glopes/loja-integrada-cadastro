# Módulo: planilha-saida

**Responsabilidade:** transformar um `EstadoProduto` pronto (entrada normalizada + textos +
imagens do pai) nas linhas pai/filha do layout de 54 colunas da Loja Integrada, e gravar o
`.xlsx` que a loja importa.
**Estado:** implementado pela task 10 · última atualização 2026-09-16 (consumido pela task 11,
sem mudança de contrato)

## Arquivos

- `models/layout_planilha_loja_integrada.py` — `COLUNAS_PLANILHA_SAIDA`,
  `COLUNAS_PREENCHIDAS_KMILAA`
- `models/linha_planilha.py` — `LinhaPlanilha`, `TipoLinhaPlanilha`
- `models/padroes_fisicos.py` — `PadroesFisicos`
- `models/exceptions/erro_planilha_saida.py` — `ErroPlanilhaSaida`
- `services/montador_planilha.py` — `MontadorPlanilha`
- `services/ports/escritor_planilha_saida.py` — `EscritorPlanilhaSaida` (Protocol)
- `infra/escritor_planilha_saida_openpyxl.py` — `EscritorPlanilhaSaidaOpenpyxl`
- `config/composicao.py` — `montar_montador_planilha`

## Contratos

```python
# models/layout_planilha_loja_integrada.py
COLUNAS_PLANILHA_SAIDA: tuple[str, ...]  # as 54 colunas, ordem exata da exportação real
COLUNAS_PREENCHIDAS_KMILAA: frozenset[str]  # subconjunto que o sistema escreve

# models/linha_planilha.py
TipoLinhaPlanilha = Literal["com-variacao", "variacao"]


@dataclass(frozen=True)
class LinhaPlanilha:
    tipo: TipoLinhaPlanilha
    valores: Mapping[str, object]  # só as colunas preenchidas; valida contra o layout


# models/padroes_fisicos.py
@dataclass(frozen=True)
class PadroesFisicos:
    peso_kg: Decimal
    altura_cm: Decimal
    largura_cm: Decimal
    comprimento_cm: Decimal


# models/exceptions/erro_planilha_saida.py
class ErroPlanilhaSaida(Exception):
    motivo: str


# services/montador_planilha.py
class MontadorPlanilha:
    def __init__(self, padroes_fisicos: PadroesFisicos, ativo: str) -> None: ...
    def montar(self, estado: EstadoProduto) -> list[LinhaPlanilha]: ...
    def montar_lote(
        self, estados: Sequence[EstadoProduto], incluir_reprovados: bool = False
    ) -> list[LinhaPlanilha]: ...


# services/ports/escritor_planilha_saida.py
class EscritorPlanilhaSaida(Protocol):
    def escrever(self, linhas: Sequence[LinhaPlanilha], destino: Path) -> None: ...


# infra/escritor_planilha_saida_openpyxl.py
class EscritorPlanilhaSaidaOpenpyxl:
    def escrever(self, linhas: Sequence[LinhaPlanilha], destino: Path) -> None: ...


# config/composicao.py
def montar_montador_planilha(configuracao: Configuracao) -> MontadorPlanilha: ...
```

## Comportamento

**`MontadorPlanilha.montar(estado)`** — 1 linha pai + 1 linha filha por `VariacaoEntrada` de
`estado.entrada.variacoes` (não recombina cor×tamanho: usa a variação real da entrada).

- **Pai**: `tipo`, `sku=entrada.sku_pai`, `ativo` (do construtor), `usado="N"`, `destaque="N"`,
  `nome`/`seo-tag-title`/`seo-tag-description`/`descricao-completa` de `estado.textos`
  (`titulo`/`seo_tag_title`/`seo_tag_description`/`descricao_html`), `preco-sob-consulta="N"`,
  `marca=entrada.marca` (grafia já canônica — o montador não reconsulta `DadosMestre`),
  `categoria-nome-nivel-{n}` para cada nível de `entrada.categoria` (1 a 5, já validado pela
  task 05), `imagem-{n}` para até 5 URLs de `estado.imagens_pai`.
- **Filha**: `tipo="variacao"`, `sku-pai`, `sku=f"{sku_pai}-{slugificar(cor)}-{slugificar(tamanho)}"`
  (reaproveita `models/slug.py::slugificar`), `ativo`, `usado="N"`, `destaque="N"`,
  `gtin=variacao.gtin`, `estoque-gerenciado="S"`, `estoque-quantidade=variacao.estoque`,
  `estoque-situacao-em-estoque="imediata"`, `estoque-situacao-sem-estoque="indisponivel"`,
  `preco-sob-consulta="N"`, `preco-custo=0.0`, `preco-cheio=float(variacao.preco)`,
  `preco-promocional=0.0`, `peso-em-kg`/`altura-em-cm`/`largura-em-cm`/`comprimento-em-cm` de
  `PadroesFisicos` (fixos para toda variação, ADR-004), `grade-produto-com-uma-cor=cor`,
  `grade-tamanho-infantil=tamanho`.
- Não muda `estado.status` nem chama métodos de intenção — é transformação pura de dados já
  registrados. Marcar o produto como `pronto` é responsabilidade do orquestrador do lote
  (`ProcessarLote`, task 11).

**`MontadorPlanilha.montar_lote(estados, incluir_reprovados)`** — concatena `montar(estado)`
para todo `estado.status is PRONTO`; com `incluir_reprovados=True`, também inclui
`REPROVADO_QA` cujo `estado.textos` não seja `None`. Hoje isso nunca ocorre — ver "Limites".

**`LinhaPlanilha.__post_init__`** — levanta `ErroPlanilhaSaida` se `valores` tiver alguma chave
fora de `COLUNAS_PLANILHA_SAIDA`.

**`EscritorPlanilhaSaidaOpenpyxl.escrever(linhas, destino)`** — cria `destino.parent` se faltar,
grava uma única aba `Sheet1` com `COLUNAS_PLANILHA_SAIDA` no cabeçalho e uma linha por
`LinhaPlanilha` (`valores.get(coluna)`, `None` onde a linha não preenche). Levanta
`ErroPlanilhaSaida` sem gravar nada se `len(linhas) > 9_997` (limite da loja).

**`montar_montador_planilha(configuracao)`** — extrai `PadroesFisicos` dos 4 campos
`peso_kg`/`altura_cm`/`largura_cm`/`comprimento_cm` de `Configuracao` e passa
`configuracao.produto_ativo` como `ativo`.

## Limites

- `incluir_reprovados=True` é aceito mas ainda não muda o resultado: `EstadoProduto.reprovar_qa()`
  (task 06) não guarda o último texto tentado, então `estado.textos` fica `None` para todo
  `REPROVADO_QA` hoje. Fecha quando a task 16 (`ErroReprovacaoQa` com o último `TextosProduto`)
  passar esse texto para o estado antes de reprovar — decisão confirmada com o usuário
  (13/09/2026): escopo reduzido agora, sem falhar nem preencher campo vazio.
- Não decide *quando* rodar nem grava o `.xlsx` final por conta própria — isso é
  `ProcessarLote`/subcomando `processar` (task 11), que injeta `MontadorPlanilha` e
  `EscritorPlanilhaSaida` via `config/composicao.py`.
- Não valida os 4 textos contra limites de caracteres — isso é responsabilidade de quem gera o
  texto (`GeradorTextos`, módulo `geracao-textos`).
- Não reconfirma marca/cor/tamanho/categoria contra `DadosMestre` — confia na validação já
  feita pela task 05 sobre `estado.entrada`.

## Testes

- `tests/unit/models/test_layout_planilha_loja_integrada.py` — 54 colunas, sem duplicatas,
  `COLUNAS_PREENCHIDAS_KMILAA` é subconjunto do layout; comparação com a linha 1 de
  `docs/brutos/produtos-*.xlsx` (`pytest.skip` se o arquivo não existir localmente — foi essa
  comparação que corrigiu `grade-tamanho-de-calca`/`-camisacamiseta`/`-capacete`/`-tenis`, que
  a documentação trazia sem o `-de-`).
- `tests/unit/models/test_linha_planilha.py` — aceita colunas válidas, `ErroPlanilhaSaida` em
  coluna desconhecida.
- `tests/unit/services/test_montador_planilha.py` — produto com 2 cores × 3 tamanhos → 1 pai +
  6 filhas, valores exatos coluna a coluna (incluindo GTIN); `montar_lote` filtra por status;
  `incluir_reprovados=True` com estado `reprovado-qa` sem texto não gera linha (documenta o
  limite acima).
- `tests/unit/infra/test_escritor_planilha_saida_openpyxl.py` — grava em `tmp_path`, relê com
  `openpyxl`: cabeçalho = `COLUNAS_PLANILHA_SAIDA`, aba única `Sheet1`, células numéricas
  corretas; `ErroPlanilhaSaida` acima de 9.997 linhas, nada gravado.
- `tests/unit/config/test_composicao.py` — `montar_montador_planilha` devolve `MontadorPlanilha`.
- Nenhum fake de `EscritorPlanilhaSaida` extraído ainda — sem um segundo consumidor até aqui.

## Histórico

- Task 10 (2026-09-14): criação do módulo — `COLUNAS_PLANILHA_SAIDA`, `LinhaPlanilha`,
  `PadroesFisicos`, `MontadorPlanilha`, `EscritorPlanilhaSaida`/`EscritorPlanilhaSaidaOpenpyxl`,
  `montar_montador_planilha`. Fecha o gap de GTIN deixado pela POC. Ver "Desvios e decisões" na
  spec as-built (`docs/specs/tasks/10-montador-planilha-saida.md`).
- Task 11 (2026-09-16): primeiro consumidor real — `ProcessarLote` chama `montador.montar(estado)`
  por produto (antes de `marcar_pronto()`) e `montador.montar_lote(...)` uma vez no fim,
  escrevendo `saida/<lote>.xlsx` via `EscritorPlanilhaSaidaOpenpyxl` injetado por
  `config/composicao.py::montar_processador_lote`. Nenhuma mudança de contrato neste módulo.
