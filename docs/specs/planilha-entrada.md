# Módulo: planilha-entrada

**Responsabilidade:** transformar a planilha `.xlsx` que a dona da loja preenche em
`ProdutoEntrada`/`VariacaoEntrada` (domínio puro), e gerar o `.xlsx` modelo que ela preenche.
**Estado:** implementado pela task 04 · última atualização 2026-09-13 (task 04)

## Arquivos

- `models/produto_entrada.py` — `ProdutoEntrada` (frozen)
- `models/variacao_entrada.py` — `VariacaoEntrada` (frozen)
- `models/layout_planilha_entrada.py` — nomes das 14 colunas e quais são obrigatórias
- `models/problema_linha_planilha.py` — `ProblemaLinhaPlanilha` (linha/coluna/motivo)
- `models/exceptions/erro_planilha_entrada.py` — `ErroPlanilhaEntrada`
- `services/ports/leitor_planilha_entrada.py` — `LeitorPlanilhaEntrada` (Protocol)
- `infra/leitor_planilha_entrada_openpyxl.py` — `LeitorPlanilhaEntradaOpenpyxl`
- `infra/gerador_modelo_entrada_openpyxl.py` — `GeradorModeloEntrada`
- `config/composicao.py` — `montar_gerador_modelo_entrada()`
- `cli.py` — subcomando `modelo-entrada --destino <arquivo>`

## Contratos

```python
@dataclass(frozen=True)
class VariacaoEntrada:
    cor: str
    tamanho: str
    gtin: str
    preco: Decimal
    estoque: int

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
    faixa_tamanho: str                      # texto livre, lido da planilha
    variacoes: tuple[VariacaoEntrada, ...]

    @property
    def cores(self) -> tuple[str, ...]      # distintas, ordem de aparição na planilha
    @property
    def tamanhos(self) -> tuple[str, ...]   # distintos, ordem de aparição na planilha

COLUNAS_PLANILHA_ENTRADA: tuple[str, ...] = (
    "sku-pai", "marca", "nome-fornecedor", "tipo-peca", "categoria", "composicao",
    "detalhes", "colecao", "faixa-tamanho", "cor", "tamanho", "gtin", "preco", "estoque",
)

@dataclass(frozen=True)
class ProblemaLinhaPlanilha:
    linha: int   # 1-based; cabeçalho = linha 1
    coluna: str
    motivo: str

class ErroPlanilhaEntrada(Exception):
    caminho: Path
    problemas: tuple[ProblemaLinhaPlanilha, ...]

class LeitorPlanilhaEntrada(Protocol):
    def ler(self, caminho: Path) -> list[ProdutoEntrada]: ...

class LeitorPlanilhaEntradaOpenpyxl:
    def ler(self, caminho: Path) -> list[ProdutoEntrada]: ...

class GeradorModeloEntrada:
    def __init__(self, dados_mestre: DadosMestre) -> None: ...
    def gerar(self, destino: Path) -> None: ...

def montar_gerador_modelo_entrada() -> GeradorModeloEntrada: ...
```

## Comportamento

**Leitura (`LeitorPlanilhaEntradaOpenpyxl.ler`)**

1. Abre o `.xlsx` (`read_only=True`); arquivo inexistente/corrompido → `ErroPlanilhaEntrada` com
   um problema na "linha" 1, coluna `"arquivo"`.
2. Valida o cabeçalho (linha 1) **por nome**, em qualquer ordem: coluna obrigatória ausente ou
   coluna desconhecida → `ErroPlanilhaEntrada` imediato, listando todas de uma vez. Sem isso,
   não processa nenhuma linha.
3. Percorre as linhas a partir da 2, agrupando por `sku-pai` na ordem de primeira aparição:
   - Linha totalmente vazia (todas as colunas conhecidas em branco) é ignorada.
   - `sku-pai` vazio numa linha não vazia → problema, linha pulada (não dá pra agrupar).
   - 1ª linha de um `sku-pai`: grava os campos de produto; os obrigatórios (todos menos
     `colecao`) vazios viram problema.
   - Linhas seguintes do mesmo `sku-pai`: campo de produto preenchido e diferente do já lido →
     problema de conflito (cita as duas linhas e os dois valores); vazio ou igual, ok.
   - Toda linha: campos de variação (`cor`, `tamanho`, `gtin`, `preco`, `estoque`) vazios viram
     problema; `preco` aceita vírgula ou ponto (→ `Decimal`); `estoque` precisa ser inteiro;
     falha de parse vira problema de linha, não exceção Python.
4. Todos os problemas de linha encontrados na planilha inteira são acumulados; se houver
   qualquer um, levanta um único `ErroPlanilhaEntrada` com a lista completa ao final — não
   levanta no primeiro problema encontrado.
5. Sem nenhum problema: monta um `ProdutoEntrada` por `sku-pai` (na ordem de aparição),
   convertendo `categoria` (`split(">")`, cada segmento sem espaços nas pontas) e `colecao`
   (vazio → `None`).

Células numéricas puras (ex.: GTIN ou `sku-pai` digitado como número no Excel) são convertidas
para `str` sem sufixo `.0`; zeros à esquerda perdidos por já terem sido digitados como número
não são recuperáveis (mitigado no gerador do modelo, que formata essas colunas como texto).

**Geração do modelo (`GeradorModeloEntrada.gerar`)**

Cria um `.xlsx` com aba `"Entrada"` (cabeçalho com comentário por coluna, 2 linhas de exemplo —
1 produto com 2 variações, `sku-pai`/`gtin` formatados como texto) e uma aba oculta `"Listas"`
com marcas canônicas, cores e tamanhos de `DadosMestre`, usada como origem das 3 listas
suspensas (`DataValidation` tipo `list`) nas colunas `marca`, `cor` e `tamanho` — necessário
porque a lista de cores (413 itens) excede o limite de lista inline do Excel.

## Limites

- Não valida marca/cor/tamanho contra `DadosMestre`, dígito verificador nem unicidade de GTIN,
  unicidade de `sku-pai` no lote, combinação cor×tamanho duplicada, ou existência da pasta de
  fotos — tudo isso é `ValidadorEntrada` (task 05), que consome os `ProdutoEntrada` já lidos.
- Cabeçalho duplicado (mesmo nome de coluna duas vezes) não é detectado explicitamente.
- `config/composicao.py` ainda não liga o leitor a nenhum subcomando (isso entra com `validar`,
  task 05).

## Testes

- `tests/unit/models/test_produto_entrada.py` — `cores`/`tamanhos` deduplicam preservando ordem
  de aparição; imutabilidade.
- `tests/unit/infra/test_leitor_planilha_entrada_openpyxl.py` — fixtures `.xlsx` construídas com
  `openpyxl` em `tmp_path`: leitura com múltiplas cores/tamanhos, campos de produto só na 1ª
  linha, conflito de campo de produto, cabeçalho faltando/com coluna extra, ordem de colunas
  livre, preço com vírgula/ponto, linha vazia no meio do grupo, `sku-pai` vazio, estoque/preço
  inválidos, GTIN numérico sem sufixo, múltiplos problemas acumulados num só erro, múltiplos
  produtos preservando ordem, arquivo inexistente/corrompido.
- `tests/unit/infra/test_gerador_modelo_entrada_openpyxl.py` — cabeçalho com as 14 colunas
  corretas, 2 linhas de exemplo do mesmo produto, aba `"Listas"` oculta com dados reais de
  `DadosMestre`, `DataValidation` presente nas 3 colunas, formatação de texto em
  `sku-pai`/`gtin`, round-trip gerar → ler devolvendo o `ProdutoEntrada` esperado.
- `tests/unit/config/test_composicao.py` — `montar_gerador_modelo_entrada()` funcional contra o
  `dados_mestre.yaml` real do pacote.
- Nenhum fake de port disponível ainda para outros módulos — `LeitorPlanilhaEntrada` só tem a
  implementação `openpyxl` real até aqui; a task 05 pode introduzir um fake se precisar isolar
  `ValidadorEntrada` de I/O nos testes.

## Histórico

- Task 04 (2026-09-13): criação do módulo — `ProdutoEntrada`/`VariacaoEntrada`, port e leitor
  `openpyxl`, gerador do modelo com listas suspensas, primeiro `config/composicao.py`, comando
  `modelo-entrada` implementado. `faixa_tamanho` virou coluna de entrada em vez de propriedade
  derivada (ver ADR-005 em `ARQUITETURA.md` §16).
