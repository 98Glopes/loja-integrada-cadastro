# Módulo: llm-cliente-prompts

**Responsabilidade:** falar com a API Anthropic atrás de um port tipado (saída estruturada no
dataclass de domínio, cache, uso/custo, erros traduzidos) e renderizar os templates de prompt
em blocos — a infraestrutura comum dos agentes Copywriter/SEO/QA.
**Estado:** implementado pela task 12 · última atualização 2026-09-16 (task 12)

## Arquivos

| Camada | Arquivo |
|---|---|
| models | `models/mensagem_llm.py` (`MensagemLlm`, `PapelMensagem`), `models/pedido_llm.py` (`PedidoLlm`, `EffortLlm`, `EFFORTS_VALIDOS`), `models/uso_llm.py` (`UsoLlm`), `models/resposta_llm.py` (`RespostaLlm[T]`), `models/prompt_renderizado.py` (`PromptRenderizado`), `models/preco_modelo_llm.py` (`PrecoModeloLlm`), `models/tabela_precos_llm.py` (`TabelaPrecosLlm`, `ARQUIVO_PRECOS_LLM`), `models/exceptions/erro_geracao_texto.py`, `models/exceptions/erro_prompt.py` |
| services/ports | `services/ports/cliente_llm.py` (`ClienteLlm`), `services/ports/repositorio_prompts.py` (`RepositorioPrompts`) |
| infra | `infra/cliente_llm_anthropic.py` (`ClienteLlmAnthropic`), `infra/repositorio_prompts_jinja.py` (`RepositorioPromptsJinja`), `infra/carregador_recursos.py` (`precos_llm()`, `montar_tabela_precos_llm()`) |
| recursos | `recursos/precos_llm.yaml`, `recursos/prompts/README.md` (templates reais na task 13) |
| config | `config/composicao.py` (`montar_cliente_llm`, `montar_repositorio_prompts`) |

Dependências: `anthropic>=1.6` (SDK 1.x, `httpx2`), `pydantic>=2`, `jinja2>=3.1`.

## Contratos

```python
class ClienteLlm(Protocol):
    def gerar[T](self, pedido: PedidoLlm, esquema: type[T]) -> RespostaLlm[T]: ...

class RepositorioPrompts(Protocol):
    def renderizar(self, nome: str, contexto: Mapping[str, object]) -> PromptRenderizado: ...

@dataclass(frozen=True)
class PedidoLlm:
    blocos_sistema: tuple[str, ...]; mensagens: tuple[MensagemLlm, ...]
    modelo: str; effort: EffortLlm; max_tokens: int
# MensagemLlm(papel: Literal["user","assistant"], conteudo: str)
# EffortLlm = Literal["low","medium","high","xhigh","max"]; EFFORTS_VALIDOS: frozenset[str]

@dataclass(frozen=True)
class RespostaLlm[T]:
    saida: T; texto: str; uso: UsoLlm; modelo: str; request_id: str | None; stop_reason: str
# UsoLlm(tokens_entrada, tokens_saida, tokens_cache_leitura, tokens_cache_escrita: int,
#        custo_usd_estimado: Decimal)

@dataclass(frozen=True)
class PromptRenderizado: blocos_sistema: tuple[str, ...]; usuario: str

@dataclass(frozen=True)
class TabelaPrecosLlm:
    precos: Mapping[str, PrecoModeloLlm]; data_referencia: date
    def exigir(self, modelo: str) -> PrecoModeloLlm: ...        # ErroRecursos
# PrecoModeloLlm(entrada, saida, cache_leitura, cache_escrita: Decimal  # USD/MTok)
#   .custo(tokens_entrada, tokens_saida, tokens_cache_leitura, tokens_cache_escrita) -> Decimal

class ErroGeracaoTexto(Exception):   # (motivo: str, retentavel: bool = False)
class ErroPrompt(Exception):         # (nome: str, motivo: str)

class ClienteLlmAnthropic:           # (client: anthropic.Anthropic, tabela_precos: TabelaPrecosLlm)
class RepositorioPromptsJinja:       # (loader: jinja2.BaseLoader | None = None)

def montar_cliente_llm(configuracao: Configuracao) -> ClienteLlm
def montar_repositorio_prompts() -> RepositorioPrompts
```

Variáveis de ambiente: `ANTHROPIC_API_KEY` (obrigatória em `montar_cliente_llm`, via
`Configuracao.exigir_anthropic()`). `LLM_MODELO_*`/`LLM_EFFORT_*` são lidas pela `Configuracao`
mas ainda não consumidas aqui — quem monta o `PedidoLlm` (agentes, tasks 14–16) as usa.

`recursos/precos_llm.yaml`:

```yaml
data_referencia: 2026-09-16
modelos:
  claude-opus-5:    {entrada: 5.00, saida: 25.00, cache_leitura: 0.50, cache_escrita: 6.25}
  claude-opus-4-8:  {entrada: 5.00, saida: 25.00, cache_leitura: 0.50, cache_escrita: 6.25}
  claude-sonnet-5:  {entrada: 2.00, saida: 10.00, cache_leitura: 0.20, cache_escrita: 2.50}
  claude-haiku-4-5: {entrada: 1.00, saida: 5.00,  cache_leitura: 0.10, cache_escrita: 1.25}
```

Template de prompt (`recursos/prompts/<nome>.j2`): blocos `sistema_fixo`, `sistema_marca`
(opcional) e `usuario` (obrigatório).

## Comportamento

**`ClienteLlmAnthropic.gerar(pedido, esquema)`**

1. `tabela_precos.exigir(pedido.modelo)` — modelo sem preço é `ErroRecursos` **antes** de gastar.
2. Monta `system` como lista de blocos `{"type":"text","text":…}` na ordem de
   `pedido.blocos_sistema`, `cache_control: {"type":"ephemeral"}` só no último (lista vazia se
   não houver blocos); `messages` a partir de `pedido.mensagens`.
3. `client.beta.messages.parse(model, max_tokens, system, messages, output_format=esquema,
   thinking={"type":"adaptive"}, output_config={"effort": pedido.effort}, fallbacks="default",
   betas=["server-side-fallback-2026-07-01"])`. O SDK gera o JSON Schema do dataclass via
   `pydantic.TypeAdapter` e valida a resposta, devolvendo a instância (aninhados inclusive).
4. `stop_reason`: `max_tokens` → repete **uma** vez com `max_tokens × 2`; se truncar de novo,
   `ErroGeracaoTexto(retentavel=False)`. `refusal` → `ErroGeracaoTexto(retentavel=False)` com
   categoria/explicação de `stop_details` (a cadeia de fallback inteira recusou).
   Resposta sem bloco de texto → `retentavel=True`.
5. Erros do SDK, mais específico primeiro: `AuthenticationError` (cita `ANTHROPIC_API_KEY`) e
   `BadRequestError` (cita modelo/effort/max_tokens) → `retentavel=False`; `RateLimitError` →
   `True`; `APIStatusError` → `status_code >= 500`; `APIConnectionError` → `True`;
   `pydantic.ValidationError` → `True`. Sempre `raise … from erro`. Retries de 429/5xx/rede
   antes disso são do SDK (`max_retries=3`, `timeout=120 s` em `montar_cliente_llm`).
6. `RespostaLlm`: `saida = parsed_output`, `texto` = primeiro bloco de texto, `modelo =
   response.model` (o que respondeu — muda sob fallback), `request_id = response._request_id`,
   `uso` com `cache_*` `None → 0` e `custo_usd_estimado = tabela[response.model].custo(...)`.

**`RepositorioPromptsJinja.renderizar(nome, contexto)`**

`Environment(autoescape=False, undefined=StrictUndefined, trim_blocks=True, lstrip_blocks=True,
keep_trailing_newline=False)` com `PackageLoader("loja_integrada_cadastro", "recursos/prompts")`
por padrão (tests injetam `DictLoader`). Carrega `<nome>.j2`; renderiza cada bloco isolado via
`template.blocks[b](template.new_context(contexto))` e `strip()`; `blocos_sistema` = os de
`sistema_fixo`, `sistema_marca` que existirem e não ficarem vazios; `usuario` obrigatório.
`TemplateNotFound`, `TemplateSyntaxError`, `UndefinedError` e bloco `usuario` ausente →
`ErroPrompt(nome, motivo)` nomeando o bloco.

**`CarregadorRecursos.precos_llm()`** → `montar_tabela_precos_llm(dict)`: exige
`data_referencia` (`date`) e `modelos` (mapa não vazio); cada modelo precisa dos 4 preços
numéricos (bool é inválido); valores viram `Decimal(str(valor))`.

## Limites

- Nenhum agente, prompt real, regra de texto ou retry com feedback — tasks 13–16. Este módulo
  não sabe o que é produto, marca ou campo.
- Não converte `Configuracao.llm_effort_*: str` em `EffortLlm` — quem monta o `PedidoLlm`
  valida com `EFFORTS_VALIDOS` (task 16).
- Não grava uso/custo em `EstadoProduto` nem no relatório (task 16).
- Sem streaming, Batches, tools, imagens; `max_tokens` é do pedido (§6.3 sugere 4096/2048).
- `fallbacks="default"` só existe na API Anthropic direta (não Bedrock/Vertex/Foundry) — não
  há suporte a outros provedores.
- `precos_llm.yaml` é um snapshot manual; não consulta preços ao vivo.

## Testes

- `tests/unit/models/test_tabela_precos_llm.py` — custo dos 4 componentes em `Decimal` exato,
  `exigir` com modelo ausente nomeando os conhecidos.
- `tests/unit/infra/test_cliente_llm_anthropic.py` — **fake do SDK** local (`_SdkFake.beta.
  messages.parse` com roteiro de respostas/exceções reais do SDK sobre `httpx2.Response`):
  system com cache só no último bloco; parâmetros enviados (thinking/effort/fallbacks/betas/
  esquema); histórico user/assistant/user; modelo sem preço não chama o SDK; conversão para
  dataclass aninhado; uso/custo; custo pelo modelo de fallback; JSON fora do esquema e sem
  texto → retentável; `max_tokens` dobra uma vez e falha na segunda; refusal com/sem detalhes;
  parametrizado sobre 7 classes de erro do SDK → `retentavel` e `__cause__`.
- `tests/unit/infra/test_repositorio_prompts_jinja.py` — `DictLoader`: 3 blocos separados e em
  ordem; sem `sistema_marca`; marca vazia omitida; autoescape off; variável faltante, template
  inexistente, sem `usuario`, malformado → `ErroPrompt`; loader padrão aponta para o pacote.
- `tests/unit/infra/test_carregador_recursos.py` — `precos_llm()` do YAML real (4 modelos,
  data) e `montar_tabela_precos_llm` com dicts (Decimal exato, campo ausente, preço não
  numérico/ausente).
- `tests/unit/config/test_composicao.py` — `montar_cliente_llm` sem chave → `ErroConfiguracao`;
  com chave fake devolve `ClienteLlmAnthropic` sem rede; `montar_repositorio_prompts`.
- `tests/integration/test_cliente_llm_anthropic.py` (`@pytest.mark.integration`, skip sem
  `ANTHROPIC_API_KEY`) — duas chamadas reais com system ~4,5k tokens: 2ª com
  `tokens_cache_leitura > 0`, custo > 0 e igual ao recalculado pela tabela.
- Fake disponível para outros módulos: nenhum ainda — a task 14 deve criar `ClienteLlmFake`
  (roteiro de `RespostaLlm`) em `tests/unit/services/` quando o primeiro agente existir.

## Histórico

- Task 12 (2026-09-16): criação do módulo — ports `ClienteLlm`/`RepositorioPrompts`,
  `ClienteLlmAnthropic` (beta `parse` + `fallbacks="default"`), `RepositorioPromptsJinja`,
  `TabelaPrecosLlm` + `recursos/precos_llm.yaml`, `ErroGeracaoTexto`, `ErroPrompt`.
