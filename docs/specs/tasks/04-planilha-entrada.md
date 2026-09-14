# Spec as-built — Task 04: Planilha de entrada: modelo, leitor e `modelo-entrada`

- **Data:** 2026-09-13 · **Task:** `docs/tasks/04-planilha-entrada.md` · **Módulos:** `planilha-entrada`

## Entregue

- `ProdutoEntrada`/`VariacaoEntrada` (frozen), modelando uma família (`sku-pai`) e suas
  variações (cor × tamanho) lidas da planilha de entrada, com valores brutos (só sem espaços
  nas pontas).
- `LeitorPlanilhaEntrada` (port) e `LeitorPlanilhaEntradaOpenpyxl` (infra): leem um `.xlsx` real
  e devolvem `list[ProdutoEntrada]`, agrupando por `sku-pai` na ordem de aparição. Cabeçalho
  validado por nome (ordem livre); problemas de linha (célula obrigatória vazia, conflito de
  campo de produto entre linhas, valor não numérico) são acumulados e reportados juntos.
- `GeradorModeloEntrada` (infra): gera `modelo-entrada.xlsx` com as 14 colunas, comentário por
  coluna, 2 linhas de exemplo (1 produto, 2 variações) e listas suspensas de marca/cor/tamanho
  (a partir de `DadosMestre`, via uma aba oculta `"Listas"` — a lista de 413 cores excede o
  limite de lista inline do Excel).
- `config/composicao.py` (primeiro arquivo do projeto): `montar_gerador_modelo_entrada()` liga
  `CarregadorRecursos` + `GeradorModeloEntrada`.
- `loja-integrada-cadastro modelo-entrada --destino <arquivo>` funciona de ponta a ponta: gera o
  modelo, e o modelo preenchido volta a ler corretamente com o leitor.

## Arquivos

| Camada | Criados | Alterados |
|---|---|---|
| models | `models/produto_entrada.py`, `models/variacao_entrada.py`, `models/layout_planilha_entrada.py`, `models/problema_linha_planilha.py`, `models/exceptions/erro_planilha_entrada.py` | — |
| services/ports | `services/ports/leitor_planilha_entrada.py` | — |
| infra | `infra/leitor_planilha_entrada_openpyxl.py`, `infra/gerador_modelo_entrada_openpyxl.py` | — |
| config | `config/composicao.py` | — |
| cli | — | `cli.py` (`_modelo_entrada` implementado; `CODIGO_ERRO_NEGOCIO = 1`) |
| tests | `tests/unit/models/test_produto_entrada.py`, `tests/unit/infra/test_leitor_planilha_entrada_openpyxl.py`, `tests/unit/infra/test_gerador_modelo_entrada_openpyxl.py`, `tests/unit/config/test_composicao.py`, `tests/unit/config/__init__.py` (se ausente) | `tests/unit/test_cli.py` |

## Contratos

```python
# models/variacao_entrada.py
@dataclass(frozen=True)
class VariacaoEntrada:
    cor: str
    tamanho: str
    gtin: str
    preco: Decimal
    estoque: int

# models/produto_entrada.py
@dataclass(frozen=True)
class ProdutoEntrada:
    sku_pai: str
    marca: str
    nome_fornecedor: str
    tipo_peca: str
    categoria: tuple[str, ...]
    composicao: str
    detalhes: str
    colecao: str | None
    faixa_tamanho: str                    # texto livre lido da planilha (não é mais calculado)
    variacoes: tuple[VariacaoEntrada, ...]

    @property
    def cores(self) -> tuple[str, ...]     # distintas, ordem de aparição
    @property
    def tamanhos(self) -> tuple[str, ...]  # distintos, ordem de aparição

# models/layout_planilha_entrada.py
COLUNAS_PLANILHA_ENTRADA: tuple[str, ...]          # as 14 colunas, na ordem sugerida
CAMPOS_PRODUTO_OBRIGATORIOS: tuple[str, ...]       # 7 campos (sem colecao)
CAMPO_PRODUTO_OPCIONAL: str                        # "colecao"
CAMPOS_VARIACAO_OBRIGATORIOS: tuple[str, ...]      # cor, tamanho, gtin, preco, estoque

# models/problema_linha_planilha.py
@dataclass(frozen=True)
class ProblemaLinhaPlanilha:
    linha: int      # 1-based; cabeçalho = linha 1
    coluna: str
    motivo: str

# models/exceptions/erro_planilha_entrada.py
class ErroPlanilhaEntrada(Exception):
    caminho: Path
    problemas: tuple[ProblemaLinhaPlanilha, ...]   # TODOS os problemas encontrados

# services/ports/leitor_planilha_entrada.py
class LeitorPlanilhaEntrada(Protocol):
    def ler(self, caminho: Path) -> list[ProdutoEntrada]: ...

# infra/leitor_planilha_entrada_openpyxl.py
class LeitorPlanilhaEntradaOpenpyxl:
    def ler(self, caminho: Path) -> list[ProdutoEntrada]: ...

# infra/gerador_modelo_entrada_openpyxl.py
class GeradorModeloEntrada:
    def __init__(self, dados_mestre: DadosMestre) -> None: ...
    def gerar(self, destino: Path) -> None: ...

# config/composicao.py
def montar_gerador_modelo_entrada() -> GeradorModeloEntrada: ...

# cli.py
CODIGO_ERRO_NEGOCIO = 1   # ErroRecursos ao gerar o modelo (YAML de dados mestre quebrado)
```

Layout da planilha de entrada (14 colunas, cabeçalho validado por nome, ordem livre):
`sku-pai, marca, nome-fornecedor, tipo-peca, categoria, composicao, detalhes, colecao,
faixa-tamanho, cor, tamanho, gtin, preco, estoque`.

## Regras de negócio implementadas

- Cabeçalho validado por **nome** de coluna; ordem das colunas na planilha é livre. Coluna
  obrigatória ausente ou coluna desconhecida no cabeçalho → `ErroPlanilhaEntrada` imediato,
  listando todas as colunas problemáticas de uma vez.
- Linhas agrupadas por `sku-pai`, preservando a ordem de primeira aparição de cada família e de
  cada cor/tamanho dentro dela (`ProdutoEntrada.cores`/`.tamanhos`).
- `sku-pai` obrigatório em toda linha não totalmente vazia (é a chave de agrupamento).
- Campos de produto exigidos só na primeira linha de cada `sku-pai`; se vierem preenchidos numa
  linha seguinte com valor diferente do já lido, é conflito (`ErroPlanilhaEntrada` apontando a
  linha, a coluna e os dois valores). `colecao` é o único campo de produto que pode ficar vazio.
- Campos de variação (`cor`, `tamanho`, `gtin`, `preco`, `estoque`) obrigatórios em toda linha
  não vazia.
- `preco` aceita vírgula ou ponto como separador decimal (`"119,90"` e `"119.9"` → mesmo
  `Decimal`); valor não decimal é erro de linha, não exceção Python.
- `estoque` precisa ser um inteiro; valor não numérico é erro de linha.
- `categoria` é dividida por `>`, com cada segmento sem espaços nas pontas.
- Linha totalmente vazia (todas as colunas conhecidas em branco) é ignorada silenciosamente.
- Célula numérica pura (ex.: GTIN digitado como número no Excel) não fica com sufixo `.0` ao
  virar `str`.
- Todos os problemas de linha encontrados na planilha inteira são acumulados e reportados juntos
  num único `ErroPlanilhaEntrada` (a dona da loja corrige tudo de uma vez); problemas de
  cabeçalho levantam antes de qualquer linha ser processada.
- `GeradorModeloEntrada` usa `DadosMestre.marcas_canonicas`/`.cores`/`.tamanhos` para montar as
  listas suspensas de `marca`/`cor`/`tamanho`; `sku-pai` e `gtin` saem formatados como texto no
  modelo, para reduzir o risco de a dona da loja digitar GTIN como número.

## Desvios e decisões

| Pedido (task/arquitetura) | Feito | Motivo |
|---|---|---|
| `docs/ARQUITETURA.md` §4: `faixa_tamanho` é propriedade **derivada** dos tamanhos das variações; "não está na entrada" | `faixa-tamanho` virou **coluna de entrada nova** (14ª), nível produto, obrigatória, texto livre; `ProdutoEntrada` não tem mais property `faixa_tamanho` calculada | Uma família (`sku-pai`) pode ter variações com tamanhos de escalas diferentes misturadas (letra P/M/G/GG/XG e número 1/2/3/4/6/8/...), o que inviabiliza calcular uma faixa única automaticamente. A dona da loja já sabe a faixa e a escreve como texto livre, usada depois na geração de título/descrição. Decisão tomada com o usuário nesta sessão. Ver ADR-005 em `ARQUITETURA.md` §16. |
| Task 04, escopo 3: regra de erro não detalhada além de "coluna faltante/extra → erro listando o problema" | Erros de **linha** (célula vazia, conflito de produto, valor não numérico) são **acumulados** e reportados num único `ErroPlanilhaEntrada` no final da leitura; erros de **cabeçalho** continuam levantando imediatamente, antes de processar qualquer linha | Decisão tomada com o usuário: melhor a dona da loja corrigir todos os problemas de uma vez do que descobrir um erro por execução. |
| Task 04, escopo 3: ordem das colunas não especificada | Cabeçalho validado por **nome**, ordem livre | Decisão tomada com o usuário: mais tolerante a planilhas reordenadas manualmente, sem perder a validação de nome/presença. |
| Task 04, escopo 1: `sku-pai` obrigatório não é dito explicitamente linha a linha | Exigido em **toda** linha não vazia (não só na 1ª do grupo) | Sem ele não é possível agrupar a linha em nenhuma família; é a chave de agrupamento, não um campo de produto comum. |
| Módulos não previstos no escopo original da task | `models/layout_planilha_entrada.py` (constantes de coluna compartilhadas) e `models/problema_linha_planilha.py` (estrutura do problema individual) | Evita duplicar os 14 nomes de coluna entre leitor e gerador; `ErroPlanilhaEntrada` precisa carregar uma lista de problemas (decisão de acumular erros), diferente do padrão de exceção única de `ErroRecursos`/`ErroConfiguracao`. |
| `docs/tasks/04-planilha-entrada.md`: nenhum port para `GeradorModeloEntrada` | Não criado — `config/composicao.py` instancia `GeradorModeloEntrada` diretamente | Nenhum outro adapter é necessário hoje; criar um `Protocol` sem um segundo consumidor seria antecipar abstração (arquitetura evolutiva, não especulativa). |
| `config/composicao.py` também ligaria o leitor de planilha | Não ligado nesta task | Nenhum subcomando usa o leitor ainda — isso é `validar` (task 05); arquitetura evolutiva. |

Mudança de decisão de arquitetura → ADR-005 em `ARQUITETURA.md` §16 (ver acima).

## Verificação executada

- `ruff check . && ruff format --check . && mypy src && pytest` → tudo passando (82 testes, 31
  novos desta task).
- `/python-clean-architecture:check-quality` → 1 ajuste aplicado: `_registrar_campos_produto`
  tinha um parâmetro booleano `primeira_ocorrencia` que trocava o comportamento do método (Regra
  5 — flag parameter); dividido em `_registrar_primeira_linha_produto` e
  `_conferir_linha_seguinte_produto`, cada um fazendo uma coisa só. Demais regras (nesting,
  nomes, exceções amplas, `with`/`finally` em recursos, tipos) sem violação — `Workbook` do
  `openpyxl` não suporta protocolo de context manager (`__enter__`/`__exit__` ausentes,
  confirmado em runtime), por isso o leitor usa `try/finally` com `.close()` explícito.
- Manual (critério de aceite): `python -m loja_integrada_cadastro modelo-entrada --destino
  modelo-entrada.xlsx` gera o arquivo; teste automatizado (`test_gerador_modelo_entrada_openpyxl.py`)
  confirma as 3 `DataValidation` (marca/cor/tamanho) apontando para a aba oculta `"Listas"`.
  Preenchendo o modelo gerado com um 2º produto (script manual) e lendo com
  `LeitorPlanilhaEntradaOpenpyxl().ler(...)` devolveu os 2 `ProdutoEntrada` esperados, com
  `cores`/`tamanhos`/`faixa_tamanho` corretos.

## Pendências para tasks futuras

- Validação de negócio (marca/cor/tamanho contra `DadosMestre`, GTIN — dígito verificador e
  unicidade no lote, `sku-pai` único no lote, combinação cor×tamanho duplicada, pasta de fotos
  existente) — task 05, via `ValidadorEntrada`.
- Ligar `LeitorPlanilhaEntrada` em `config/composicao.py` e no subcomando `validar` — task 05.
- Cabeçalho duplicado (mesmo nome de coluna duas vezes) não é detectado explicitamente; hoje o
  `dict` de índice fica só com a última ocorrência. Reavaliar se aparecer na prática.
