# Task 04 — Planilha de entrada: modelo de domínio, leitor e comando `modelo-entrada`

- **Depende de:** 02
- **Modelo recomendado:** sonnet
- **Leia antes:** `docs/ARQUITETURA.md` §4 (colunas e agrupamento), §10

## Objetivo

Ler a planilha preenchida pela dona da loja e transformá-la em `ProdutoEntrada` (uma linha por
variação → um produto com N variações), e gerar o modelo `.xlsx` que ela vai preencher.

## Escopo

1. `models/produto_entrada.py`: `ProdutoEntrada` (frozen: `sku_pai`, `marca`,
   `nome_fornecedor`, `tipo_peca`, `categoria: tuple[str, ...]`, `composicao`, `detalhes`,
   `colecao: str | None`, `variacoes: tuple[VariacaoEntrada, ...]`) e, em
   `models/variacao_entrada.py`, `VariacaoEntrada` (`cor`, `tamanho`, `gtin`,
   `preco: Decimal`, `estoque: int`). Propriedades derivadas: `cores` (ordem de aparição),
   `tamanhos`, `faixa_tamanho` ("P ao 3", "1 ao 4", "4" quando único). O modelo carrega
   valores **brutos**, só sem espaços nas pontas; validação de negócio é da task 05.
2. `services/ports/leitor_planilha_entrada.py`: `LeitorPlanilhaEntrada` (Protocol) com
   `ler(caminho: Path) -> list[ProdutoEntrada]`.
3. `infra/leitor_planilha_entrada_openpyxl.py`: implementação. Regras: cabeçalho exato de §4
   (coluna faltante/extra → `ErroPlanilhaEntrada` listando o problema); agrupa por `sku-pai`
   mantendo a ordem de aparição; campos de produto lidos da 1ª linha do grupo e, se
   preenchidos em outra linha com valor diferente, `ErroPlanilhaEntrada` apontando linha e
   coluna; `preco` aceita `119,90` e `119.9`; `categoria` separada por `>`; linhas totalmente
   vazias são ignoradas; célula obrigatória vazia → erro com linha/coluna.
4. `infra/gerador_modelo_entrada_openpyxl.py`: `GeradorModeloEntrada` que escreve
   `modelo-entrada.xlsx` com cabeçalho, uma linha de exemplo por variação (2 linhas), comentário
   por coluna e validação de dados (lista suspensa) para `marca`, `cor` e `tamanho` a partir
   do `DadosMestre`. Ligar ao subcomando `modelo-entrada --destino` via `config/composicao.py`.
5. Testes: fixtures `.xlsx` geradas no próprio teste (openpyxl, em `tmp_path`) cobrindo:
   1 produto com 2 cores × 3 tamanhos; campos de produto só na 1ª linha; conflito de valor;
   coluna faltante; preço com vírgula; linha vazia no meio.

## Fora do escopo

Validação de marca/cor/tamanho/GTIN e de pastas de fotos (task 05).

## Critério de aceite

- `python -m loja_integrada_cadastro modelo-entrada --destino modelo-entrada.xlsx` gera um
  arquivo que abre no Excel com as listas suspensas funcionando.
- Preencher esse modelo com 2 produtos e ler com o leitor devolve 2 `ProdutoEntrada` corretos.
- Lint, mypy e pytest passam.
