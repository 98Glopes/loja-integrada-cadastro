# Spec as-built — Task 09: Port `GeradorTextos`, `TextosProduto` e gerador dummy

- **Data:** 2026-09-14 · **Task:** `docs/tasks/09-gerador-textos-dummy.md` · **Módulos:**
  `geracao-textos`

## Entregue

O seam entre o pipeline e a geração de textos: port `GeradorTextos.gerar(produto, estado) ->
TextosProduto` e sua primeira implementação, `GeradorTextosDummy` — determinística, sem rede,
que respeita os limites de §6.1 por construção e marca todo texto visível com o placeholder
`[DUMMY]`. `config/composicao.montar_gerador_textos(configuracao)` monta o wiring. Comando que
roda: `pytest tests/unit/infra/test_gerador_textos_dummy.py` (parametrizado sobre os 6 produtos
de `tests/fixtures/lote-piloto`).

## Arquivos

| Camada | Criados | Alterados |
|---|---|---|
| models | `models/textos_produto.py` | — |
| services/ports | `services/ports/gerador_textos.py` | — |
| infra | `infra/gerador_textos_dummy.py` | — |
| config | — | `config/composicao.py` (`montar_gerador_textos`) |
| tests | `tests/unit/models/test_textos_produto.py`, `tests/unit/infra/test_gerador_textos_dummy.py` | `tests/unit/config/test_composicao.py` |

## Contratos

```python
# models/textos_produto.py
@dataclass(frozen=True)
class TextosProduto:
    titulo: str
    descricao_html: str
    seo_tag_title: str
    seo_tag_description: str

    def como_mapa(self) -> Mapping[str, str]: ...  # {"titulo", "descricao_html", "seo_tag_title", "seo_tag_description"}

# services/ports/gerador_textos.py
class GeradorTextos(Protocol):
    def gerar(self, produto: ProdutoEntrada, estado: EstadoProduto) -> TextosProduto: ...

# infra/gerador_textos_dummy.py
class GeradorTextosDummy:
    def __init__(self, dados_mestre: DadosMestre) -> None: ...
    def gerar(self, produto: ProdutoEntrada, estado: EstadoProduto) -> TextosProduto: ...

# config/composicao.py
def montar_gerador_textos(configuracao: Configuracao) -> GeradorTextos: ...
```

## Regras de negócio implementadas

- Título (`nome`) ≤ 68 caracteres, formato `[DUMMY] {tipo_peca} {marca} {detalhe principal}
  {faixa_tamanho}`; só o detalhe é truncado (em fronteira de palavra), nunca marca/faixa/tipo.
- Descrição HTML (`descricao-completa`) ≥ 120 palavras (contadas sem as tags), estrutura fixa
  `h2 (com [DUMMY]) → p → p → ul(4 li) → h3 "Sobre a {marca}" → p → h3 "Compre na Kmilaa
  Modas" → p`, só usa as tags `h2 h3 p ul li`.
- Tag title (`seo-tag-title`) ≤ 60 caracteres, com tipo e marca, sem `[DUMMY]` e sem sufixo
  `| Kmilaa Modas`.
- Meta description (`seo-tag-description`) entre 140 e 155 caracteres, com `[DUMMY] ` no
  início; completada com um sufixo fixo se curta, cortada em fronteira de palavra se longa.
- Marca resolvida por `DadosMestre.marca_canonica`; se não encontrada, usa o valor bruto da
  planilha (nunca lança).
- Cada chamada registra exatamente uma tentativa em `estado` (`agente="dummy"`,
  `tentativa=1`, `modelo="dummy"`, `usage` zerado, `custo_usd=Decimal("0")`), sem mudar o
  status do produto.
- Determinismo: mesma entrada → mesmo `TextosProduto`.

## Desvios e decisões

| Pedido (task/arquitetura) | Feito | Motivo |
|---|---|---|
| "`[DUMMY]` no início do `h2` e da meta" | `[DUMMY]` também no início do **título** (`nome`) | Confirmado com o usuário no início da sessão — deixa o texto ainda mais visível como não publicável; o custo é reduzir em 8 caracteres o orçamento do detalhe no título, absorvido pelo truncamento em fronteira de palavra. |
| "contém a marca com grafia canônica" (§6.1) | Marca usada literalmente como `DadosMestre.marca_canonica` devolve (ex.: `kiki`, `somnii`, minúsculo — sem title-case) | Confirmado com o usuário: é a "grafia canônica" ao pé da letra, sem regra de formatação extra não pedida pela task; como o dummy nunca vai ao ar, a inconsistência visual não é um risco real. |
| Estrutura `h2 → p → p → ul → h3 Sobre a [Marca] → h3 Compre na Kmilaa Modas` (§6.1, notação compacta) | Cada `h3` final ganhou um `<p>` de corpo logo em seguida (`h2, p, p, ul, h3, p, h3, p`) | Confirmado com o usuário: mesmo formato do `poc/gerar_planilha_poc.py`, que a loja já importou com sucesso; a notação da task lista só os elementos "de âncora", não exclui parágrafos de corpo. |
| `montar_gerador_textos(configuracao) -> GeradorTextos` | `configuracao: Configuracao` recebido mas não usado pelo dummy | A task já definia essa assinatura para a troca de wiring da task 16 ser só isso — `GeradorTextosDummy` não precisa de nenhum campo de `Configuracao`, mas o parâmetro fica para não trocar a assinatura depois. |
| "detalhe principal de `detalhes`" | Primeiro segmento de `detalhes` antes da primeira vírgula (`.split(",", 1)[0]`) | Não especificado pela task; heurística determinística e simples, coerente com o formato de `detalhes` observado na fixture (`"Botões na gola, acabamento em ribana"`). |

## Verificação executada

- `ruff check . && ruff format . && mypy src && pytest` → todos passando (231 testes, 4
  deselecionados por `@pytest.mark.integration`).
- `/python-clean-architecture:check-quality` sobre os arquivos desta task → nenhum achado.

## Pendências para tasks futuras

- `models/regras_texto.py` (validador de regra reutilizável) — task 14; o dummy garante os
  limites por construção, não valida.
- `GeradorTextosIa` troca o wiring de `montar_gerador_textos` — task 16; `GeradorTextosDummy`
  sai de `infra/` (vira fake em `tests/` se ainda útil ao teste de `ProcessarLote`, ou é
  apagado), conforme ADR-007.
- `ProcessarLote` (task 11) ainda não consome este port.
