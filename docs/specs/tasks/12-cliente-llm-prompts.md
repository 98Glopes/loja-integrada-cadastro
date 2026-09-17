# Spec as-built — Task 12: Cliente LLM Anthropic e repositório de prompts

- **Data:** 2026-09-16 · **Task:** `docs/tasks/12-cliente-llm-prompts.md` · **Módulos:**
  `llm-cliente-prompts`, `dados-mestre-recursos` (só `precos_llm`), `configuracao-cli` (só
  `composicao.py`)

## Entregue

A infraestrutura que os três agentes (tasks 13–16) vão compartilhar, sem nenhum agente ainda:
o port `ClienteLlm.gerar(pedido, esquema) -> RespostaLlm[T]` com o conector
`ClienteLlmAnthropic` (saída estruturada tipada direto no dataclass de domínio, cache do system
prompt, uso/custo por chamada, `stop_reason` conferido, erros do SDK traduzidos para
`ErroGeracaoTexto` com `retentavel`, `fallbacks="default"` para refusal) e o port
`RepositorioPrompts.renderizar(nome, contexto) -> PromptRenderizado` com `RepositorioPromptsJinja`
(blocos `sistema_fixo`/`sistema_marca`/`usuario` renderizados separadamente). A tabela de
preços vive em `recursos/precos_llm.yaml`. Comandos que rodam: `pytest` (34 testes novos) e
`pytest -m integration tests/integration/test_cliente_llm_anthropic.py` (API real).

## Arquivos

| Camada | Criados | Alterados |
|---|---|---|
| models | `mensagem_llm.py`, `pedido_llm.py`, `uso_llm.py`, `resposta_llm.py`, `prompt_renderizado.py`, `preco_modelo_llm.py`, `tabela_precos_llm.py`, `exceptions/erro_geracao_texto.py`, `exceptions/erro_prompt.py` | — |
| services/ports | `cliente_llm.py`, `repositorio_prompts.py` | — |
| infra | `cliente_llm_anthropic.py`, `repositorio_prompts_jinja.py` | `carregador_recursos.py` (`precos_llm()`, `montar_tabela_precos_llm()`, `_yaml()`) |
| recursos | `precos_llm.yaml`, `prompts/README.md` | — |
| config | — | `composicao.py` (`montar_cliente_llm`, `montar_repositorio_prompts`) |
| pyproject | — | `anthropic>=1.6`, `pydantic>=2`, `jinja2>=3.1` |
| tests | `unit/models/test_tabela_precos_llm.py`, `unit/infra/test_cliente_llm_anthropic.py`, `unit/infra/test_repositorio_prompts_jinja.py`, `integration/test_cliente_llm_anthropic.py` | `unit/infra/test_carregador_recursos.py`, `unit/config/test_composicao.py`, `integration/README.md` |

## Contratos

```python
# models
PapelMensagem = Literal["user", "assistant"]
@dataclass(frozen=True)
class MensagemLlm: papel: PapelMensagem; conteudo: str

EffortLlm = Literal["low", "medium", "high", "xhigh", "max"]
EFFORTS_VALIDOS: frozenset[str]
@dataclass(frozen=True)
class PedidoLlm:
    blocos_sistema: tuple[str, ...]      # estáveis, na ordem; o último recebe o cache breakpoint
    mensagens: tuple[MensagemLlm, ...]   # conversa completa (retry com histórico)
    modelo: str
    effort: EffortLlm
    max_tokens: int

@dataclass(frozen=True)
class UsoLlm:
    tokens_entrada: int; tokens_saida: int
    tokens_cache_leitura: int; tokens_cache_escrita: int
    custo_usd_estimado: Decimal

@dataclass(frozen=True)
class RespostaLlm[T]:
    saida: T            # instância do dataclass pedido como esquema
    texto: str          # JSON bruto devolvido (turno assistant no retry)
    uso: UsoLlm
    modelo: str         # modelo que RESPONDEU (pode ser o fallback)
    request_id: str | None
    stop_reason: str

@dataclass(frozen=True)
class PromptRenderizado: blocos_sistema: tuple[str, ...]; usuario: str

@dataclass(frozen=True)
class PrecoModeloLlm:   # USD por 1M tokens
    entrada: Decimal; saida: Decimal; cache_leitura: Decimal; cache_escrita: Decimal
    def custo(self, tokens_entrada, tokens_saida, tokens_cache_leitura, tokens_cache_escrita) -> Decimal

ARQUIVO_PRECOS_LLM = "precos_llm.yaml"
@dataclass(frozen=True)
class TabelaPrecosLlm:
    precos: Mapping[str, PrecoModeloLlm]; data_referencia: date
    def exigir(self, modelo: str) -> PrecoModeloLlm   # ErroRecursos se ausente

class ErroGeracaoTexto(Exception):
    def __init__(self, motivo: str, retentavel: bool = False) -> None
class ErroPrompt(Exception):
    def __init__(self, nome: str, motivo: str) -> None

# services/ports
class ClienteLlm(Protocol):
    def gerar[T](self, pedido: PedidoLlm, esquema: type[T]) -> RespostaLlm[T]: ...
class RepositorioPrompts(Protocol):
    def renderizar(self, nome: str, contexto: Mapping[str, object]) -> PromptRenderizado: ...

# infra
class ClienteLlmAnthropic:
    def __init__(self, client: anthropic.Anthropic, tabela_precos: TabelaPrecosLlm) -> None
class RepositorioPromptsJinja:
    def __init__(self, loader: jinja2.BaseLoader | None = None) -> None  # padrão: PackageLoader recursos/prompts
class CarregadorRecursos:
    def precos_llm(self) -> TabelaPrecosLlm
def montar_tabela_precos_llm(bruto: object) -> TabelaPrecosLlm

# config
def montar_cliente_llm(configuracao: Configuracao) -> ClienteLlm   # Anthropic(max_retries=3, timeout=120)
def montar_repositorio_prompts() -> RepositorioPrompts
```

`recursos/precos_llm.yaml`: `data_referencia: 2026-09-16` + `modelos.<id>.{entrada, saida,
cache_leitura, cache_escrita}` para `claude-opus-5`, `claude-opus-4-8`, `claude-sonnet-5`,
`claude-haiku-4-5` (valores da skill `claude-api`; cache leitura 0,1×, escrita 1,25×).

Template `recursos/prompts/<nome>.j2`: `{% block sistema_fixo %}`, `{% block sistema_marca %}`
(opcional), `{% block usuario %}` (obrigatório).

## Regras de negócio implementadas

- `gerar` chama `tabela_precos.exigir(pedido.modelo)` **antes** da requisição: modelo sem preço
  é `ErroRecursos` sem gastar.
- System vai como lista de blocos de texto; `cache_control: ephemeral` só no último.
- Chamada: `client.beta.messages.parse(output_format=<dataclass>, thinking=adaptive,
  output_config={"effort"}, fallbacks="default", betas=["server-side-fallback-2026-07-01"])`.
- `stop_reason == "max_tokens"` → uma nova tentativa com o dobro de `max_tokens`; na segunda,
  `ErroGeracaoTexto(retentavel=False)`.
- `stop_reason == "refusal"` (cadeia de fallback inteira recusou) → `ErroGeracaoTexto(
  retentavel=False)` com `stop_details.category/explanation` quando existirem.
- Tradução de erros (mais específico primeiro): `AuthenticationError` → não retentável, cita
  `ANTHROPIC_API_KEY`; `BadRequestError` → não retentável, cita modelo/effort/max_tokens;
  `RateLimitError` → retentável; `APIStatusError` → retentável se `status_code >= 500`;
  `APIConnectionError` → retentável; `pydantic.ValidationError` (JSON fora do esquema) e
  resposta sem bloco de texto → retentáveis.
- Custo = tabela do `response.model` (modelo que respondeu, cobre fallback) ×
  `usage.{input, output, cache_read, cache_creation}` (None → 0), em `Decimal` exato.
- `RespostaLlm.request_id = response._request_id`.
- Jinja: `autoescape=False`, `StrictUndefined`, `trim_blocks`/`lstrip_blocks`; cada bloco é
  renderizado separadamente e `strip()`ado; bloco de system vazio é omitido; `usuario` ausente,
  template ausente/malformado e variável faltante → `ErroPrompt` nomeando template e bloco.
- `precos_llm.yaml`: `data_referencia` (date) e `modelos` obrigatórios; preço ausente ou não
  numérico (bool conta como inválido) → `ErroRecursos` nomeando modelo e chave.

## Desvios e decisões

| Pedido (task/arquitetura) | Feito | Motivo |
|---|---|---|
| `infra/esquemas_llm.py` com modelos pydantic base + utilitário dataclass→pydantic | **Não existe.** `beta.messages.parse` aceita o dataclass de domínio direto como `output_format` (internamente `pydantic.TypeAdapter(...)` gera o JSON Schema e valida, inclusive aninhados) | Verificado no SDK 1.6.0: arquivo paralelo seria código morto. É "o mais simples que passa no mypy strict". |
| `RespostaLlm` com `saida, uso, modelo, request_id, stop_reason` | + campo `texto: str` (JSON bruto) | O retry com feedback (§6.2) reenvia a resposta anterior como turno `assistant`; sem o texto bruto o agente teria de reserializar a `saida`. |
| `PedidoLlm.effort` (sem tipo definido) | `EffortLlm = Literal[...]` + `EFFORTS_VALIDOS` | `output_config.effort` do SDK é `Literal`; validar o texto do `.env` na borda (quem monta o pedido, task 16) em vez de `str` solto. |
| "Avaliar `fallbacks` e adotar se o SDK suportar com `parse`" | Adotado `fallbacks="default"` (beta `server-side-fallback-2026-07-01`) em `beta.messages.parse` — confirmado com o usuário em plan mode | SDK 1.6.0 aceita `fallbacks` + `betas` no `parse` beta (não no `messages.parse` estável). Muda §6.3 "refusal → falha registrada": agora refusal só falha se a cadeia inteira recusar → ADR-010. |
| Tabela de preços "em `recursos/precos_llm.yaml`" (sem model) | `models/preco_modelo_llm.py` + `models/tabela_precos_llm.py`; loader em `carregador_recursos.py` | Cálculo de custo é regra pura e testável sem I/O; segue o padrão `DadosMestre`/`montar_dados_mestre`. |
| Modelos na tabela (não especificado) | Opus 5, Opus 4.8, Sonnet 5, Haiku 4.5 — confirmado com o usuário | §6.5 cita os três primeiros; Opus 4.8 é alvo documentado de fallback. |
| Modelo fora da tabela (não especificado) | `ErroRecursos` antes da chamada | Não gastar sem conseguir estimar custo (relatório do lote precisa do número). |
| Exceção para prompts (não prevista) | `ErroPrompt(nome, motivo)` | `ErroRecursos` é para arquivo ausente/malformado; variável faltante e bloco ausente são erros de template e precisam nomear template + bloco. |
| Fake do SDK: "classe local com `messages.parse`" | `_SdkFake.beta.messages.parse` que também valida o JSON com `TypeAdapter` como o SDK faz | Conector usa o namespace beta (por causa de `fallbacks`); a validação no fake mantém o teste de "JSON fora do esquema → retentável" fiel ao comportamento real. |
| `mypy` sobre `tests/` | Não (config `files = ["src"]` mantida); dois `# type: ignore` no fake | Fake não é `anthropic.Anthropic`; injeção estrutural como no teste do R2 (que usa `MagicMock`). |

## Verificação executada

- `ruff check . && ruff format --check . && mypy src && pytest` → 303 passed, 4 deselected
  (integração), mypy 74 arquivos sem erro.
- `pytest -m integration tests/integration/test_cliente_llm_anthropic.py` → 1 passed em 9 s.
  Medido (Opus 5, effort `low`, system ~4,5k tokens): 1ª e 2ª chamadas
  `tokens_entrada=23, tokens_saida=64, tokens_cache_leitura=4499, tokens_cache_escrita=0,
  custo_usd_estimado=0.0039645` — cache já quente na 1ª por rodadas anteriores; segunda
  chamada com `cache_read_input_tokens > 0` confirma o critério de aceite. `request_id`
  preenchido (`req_011Cf89…`), `stop_reason=end_turn`, `saida.texto` em português.
- `/python-clean-architecture:check-quality` sobre os 6 arquivos de código → 1 achado
  (parâmetro `entrada` ambíguo com a chave `"entrada"` em `carregador_recursos.py`),
  corrigido para `precos_brutos`.

## Pendências para tasks futuras

- Task 13: prompts reais `copywriter.j2`/`seo.j2`/`qa.j2` em `recursos/prompts/` e os `.md`
  de loja/copy/seo/qa/marcas.
- Task 14–16: agentes montam `PedidoLlm` (convertendo `Configuracao.llm_effort_*: str` para
  `EffortLlm` via `EFFORTS_VALIDOS`), dataclasses de saída (`TextosCopy`, `TextosSeo`,
  `VeredictoQa`) como `esquema`, e usam `RespostaLlm.texto` no retry com histórico;
  `montar_cliente_llm`/`montar_repositorio_prompts` entram no wiring de `processar` na 16.
- `RespostaLlm.uso` ainda não é gravado em `EstadoProduto` nem somado no relatório (task 16).
- Preços em `precos_llm.yaml` são um snapshot (2026-09-16): rever quando a Anthropic mudar a
  tabela ou um modelo novo entrar em `LLM_MODELO_*`.
