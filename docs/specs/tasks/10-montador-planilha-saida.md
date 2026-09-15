# Spec as-built — Task 10: Montador da planilha de saída (Loja Integrada)

- **Data:** 2026-09-14 · **Task:** `docs/tasks/10-montador-planilha-saida.md` · **Módulos:**
  `planilha-saida`

## Entregue

O layout de 54 colunas versionado como constante, o value object de uma linha da planilha, o
service que transforma um `EstadoProduto` pronto em linhas pai/filha, e o escritor `.xlsx` de
aba única. Fecha o gap de GTIN que a POC deixava em branco. Comando que roda:
`pytest tests/unit/models/test_layout_planilha_loja_integrada.py
tests/unit/models/test_linha_planilha.py tests/unit/services/test_montador_planilha.py
tests/unit/infra/test_escritor_planilha_saida_openpyxl.py`.

## Arquivos

| Camada | Criados | Alterados |
|---|---|---|
| models | `models/layout_planilha_loja_integrada.py`, `models/linha_planilha.py`, `models/padroes_fisicos.py`, `models/exceptions/erro_planilha_saida.py` | — |
| services | `services/montador_planilha.py`, `services/ports/escritor_planilha_saida.py` | — |
| infra | `infra/escritor_planilha_saida_openpyxl.py` | — |
| config | — | `config/composicao.py` (`montar_montador_planilha`) |
| tests | `tests/unit/models/test_layout_planilha_loja_integrada.py`, `tests/unit/models/test_linha_planilha.py`, `tests/unit/services/test_montador_planilha.py`, `tests/unit/infra/test_escritor_planilha_saida_openpyxl.py` | `tests/unit/config/test_composicao.py` |

## Contratos

```python
# models/layout_planilha_loja_integrada.py
COLUNAS_PLANILHA_SAIDA: tuple[str, ...]  # 54 colunas
COLUNAS_PREENCHIDAS_KMILAA: frozenset[str]

# models/linha_planilha.py
TipoLinhaPlanilha = Literal["com-variacao", "variacao"]


@dataclass(frozen=True)
class LinhaPlanilha:
    tipo: TipoLinhaPlanilha
    valores: Mapping[str, object]  # valida no __post_init__ contra COLUNAS_PLANILHA_SAIDA


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

## Regras de negócio implementadas

- Linha pai: 1 por produto, com título/SEO/descrição de `estado.textos`, marca já canônica de
  `entrada.marca`, categoria em até 5 níveis, até 5 imagens de `estado.imagens_pai`.
- Linha filha: 1 por `VariacaoEntrada` real da entrada (não recombina cor×tamanho), com
  `sku = <sku-pai>-<cor-slug>-<tamanho-slug>`, `gtin` da variação, preço/estoque da variação,
  peso/dimensões fixos de `PadroesFisicos`, grades de cor e tamanho.
- `montar` não muda `estado.status`.
- `montar_lote` inclui sempre `pronto`; com `incluir_reprovados=True` também incluiria
  `reprovado-qa`, mas só quando `estado.textos` não for `None` (hoje nunca ocorre — ver
  "Desvios e decisões").
- `LinhaPlanilha` rejeita qualquer coluna fora do layout de 54.
- `EscritorPlanilhaSaidaOpenpyxl` grava aba única `Sheet1`, cabeçalho = `COLUNAS_PLANILHA_SAIDA`,
  e recusa lotes com mais de 9.997 linhas sem gravar nada.

## Desvios e decisões

| Pedido (task/arquitetura) | Feito | Motivo |
|---|---|---|
| Constante chamada `COLUNAS` | `COLUNAS_PLANILHA_SAIDA` (+ `COLUNAS_PREENCHIDAS_KMILAA` para "o conjunto que a Kmilaa preenche") | Segue a convenção já usada em `models/layout_planilha_entrada.py::COLUNAS_PLANILHA_ENTRADA` — nome mais específico, mesmo padrão do módulo irmão. |
| `MontadorPlanilha(padroes_fisicos, ativo)` sem especificar o tipo de `padroes_fisicos` | Novo VO `models/padroes_fisicos.py::PadroesFisicos` (4 `Decimal`) | ADR-004 já decidiu que os 4 valores vêm de `Configuracao`, mas nenhum service recebe `Configuracao` inteira (ver `montar_validador_entrada`/`montar_gerador_textos` em `config/composicao.py`, que sempre extraem objetos pequenos). Um VO pequeno mantém `services` desacoplado de `config`. |
| "Filhas por variação na ordem da planilha de entrada" | Implementado iterando `entrada.variacoes` diretamente, sem recombinar cor×tamanho como a POC fazia | `VariacaoEntrada` já é o par cor+tamanho concreto (preço/estoque/GTIN por variação); recombinar geraria variações que não existiram na entrada. |
| `montar_lote(estados, incluir_reprovados)` "filtra pronto, opcionalmente reprovado-qa" | `reprovado-qa` só é incluído quando `estado.textos is not None` — hoje isso nunca acontece | Confirmado com o usuário (13/09/2026): `EstadoProduto.reprovar_qa()` (task 06) não guarda o último texto tentado; isso só chega na task 16 (`docs/tasks/16-agente-qa-gerador-textos.md`: "o texto fica no estado para o relatório"). Escopo reduzido agora — o parâmetro é aceito e testado, mas hoje é um no-op para produtos reprovados; documentado como pendência, não como bug. |
| `docs/regras-planilha-loja-integrada.md` §2, colunas 42–46 | Corrigidos os nomes para `grade-tamanho-de-calca`, `grade-tamanho-de-camisacamiseta`, `grade-tamanho-de-capacete`, `grade-tamanho-de-tenis` (a doc tinha esses 4 nomes sem o `-de-`) | O teste opcional contra `docs/brutos/produtos-2026-09-10-*.xlsx` (arquivo presente localmente) pegou a divergência entre a doc e a exportação real; corrigido na fonte de verdade. |
| `montar()` "monta" o produto (linguagem da task) | `montar()` não chama `estado.marcar_pronto()` | A task 06 já define `marcar_pronto` como "produto foi montado na planilha de saída"; como `montar_lote` reusa `montar()` para recompor o `.xlsx` inteiro a partir de estados já `pronto` (não só do produto recém-processado), a transição de status precisa ficar fora do service — quem chama `montar()` pela primeira vez (o orquestrador do lote, task 11) decide quando marcar `pronto`. |

## Verificação executada

- `ruff check . && ruff format . && mypy src && pytest` → todos passando (246 testes, 4
  deselecionados por `@pytest.mark.integration`).
- `/python-clean-architecture:check-quality` sobre os arquivos desta task → 1 achado aceito
  (Regra 5, parâmetro flag `incluir_reprovados`), sem correção — assinatura exigida pela task e
  pelo futuro flag `--incluir-reprovados` da CLI (task 11).

## Pendências para tasks futuras

- `incluir_reprovados=True` não produz linhas extras até a task 16 popular
  `estado.textos`/texto de fallback para produtos `reprovado-qa`.
- Nenhum wiring em `cli.py` ainda — sem consumidor até a task 11 (`ProcessarLote`), que decide
  quando chamar `montar`/`montar_lote` e quando marcar `estado.marcar_pronto()`.
- Nenhum fake de `EscritorPlanilhaSaida` extraído — sem segundo consumidor até aqui.
