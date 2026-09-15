# Task 12 — Cliente LLM Anthropic e repositório de prompts

- **Depende de:** 02
- **Modelo recomendado:** opus
- **Leia antes:** `docs/ARQUITETURA.md` §6.3 (boas práticas), §6.4, §6.5, §10, §11.
  **Invocar a skill `claude-api`** no início da sessão e seguir sua documentação (SDK Python,
  `messages.parse`, prompt caching, thinking/effort, erros) — não escrever chamadas de API
  de memória.

## Objetivo

Um único conector para a API da Anthropic, atrás do port `ClienteLlm`, que entrega saída
estruturada tipada, cache do system prompt, registro de uso/custo e tradução de erros. E um
repositório de prompts Jinja2 sobre os recursos do pacote. Nenhum agente ainda — só a
infraestrutura que os três vão compartilhar.

## Escopo

1. `models/pedido_llm.py`: `PedidoLlm` (frozen): `blocos_sistema: tuple[str, ...]` (estáveis,
   na ordem; o último recebe o breakpoint de cache), `mensagens: tuple[MensagemLlm, ...]`
   (`papel`, `conteudo`) para permitir retry com histórico, `modelo`, `effort`,
   `max_tokens`. `models/resposta_llm.py`: `RespostaLlm[T]` genérico com `saida: T`,
   `uso: UsoLlm` (tokens de entrada/saída/cache leitura/escrita, `custo_usd_estimado`),
   `modelo`, `request_id`, `stop_reason`.
2. `services/ports/cliente_llm.py`: `ClienteLlm` (Protocol):
   `gerar(pedido: PedidoLlm, esquema: type[T]) -> RespostaLlm[T]`. O `esquema` é um tipo do
   domínio (dataclass); a conversão de/para pydantic fica no conector.
3. `infra/esquemas_llm.py`: modelos pydantic base + utilitário que gera o modelo pydantic a
   partir do dataclass de saída (ou mapeamento explícito por agente — escolher o mais simples
   que passe no mypy strict).
4. `infra/cliente_llm_anthropic.py`: `ClienteLlmAnthropic(client, tabela_precos)`:
   - `client.messages.parse(model=…, system=[{text, cache_control no último}], messages=…,
     output_format=<pydantic>, thinking={"type": "adaptive"}, output_config={"effort": …},
     max_tokens=…)`.
   - Confere `stop_reason` (`max_tokens` → uma nova tentativa com o dobro; `refusal` →
     `ErroGeracaoTexto`).
   - Erros: `RateLimitError` (após os retries do SDK) e `APIStatusError ≥ 500` →
     `ErroGeracaoTexto(retentavel=True)`; `BadRequestError`/`AuthenticationError` →
     `ErroGeracaoTexto(retentavel=False)` com mensagem acionável; `APIConnectionError` →
     retentável.
   - Calcula `custo_usd_estimado` a partir de `usage` e de uma tabela de preços em
     `recursos/precos_llm.yaml` (input, output, cache read, cache write por modelo — valores
     da documentação oficial na data; registrar a data no arquivo).
   - Avaliar (e documentar no código) o uso de `fallbacks` server-side para `refusal`
     conforme a skill; adotar se o SDK atual suportar com `parse`.
5. `services/ports/repositorio_prompts.py`: `RepositorioPrompts` (Protocol):
   `renderizar(nome, contexto) -> PromptRenderizado` (`blocos_sistema`, `usuario`).
   `infra/repositorio_prompts_jinja.py`: templates em `recursos/prompts/*.j2` com blocos
   `{% block sistema_fixo %}`, `{% block sistema_marca %}`, `{% block usuario %}`
   (system dividido em blocos estáveis → cache); `autoescape` desligado, `StrictUndefined`
   (variável faltante = erro, não texto vazio).
6. `pyproject.toml`: `anthropic`, `pydantic`, `jinja2`.
7. `config/composicao.py`: fábrica do cliente (`anthropic.Anthropic(max_retries=3,
   timeout=120)`), uma instância por execução.
8. Testes: unitários do conector com um **fake do SDK** mínimo injetado (não mock de
   biblioteca: uma classe local com `messages.parse` que devolve objetos com a mesma forma)
   cobrindo conversão, cálculo de custo, `stop_reason` e tradução de erros; do repositório
   Jinja com template de teste; **integração** (`@pytest.mark.integration`) que chama a API
   real com um esquema trivial e confere `cache_read_input_tokens > 0` na 2ª chamada.

## Fora do escopo

Prompts reais dos agentes (tasks 13–16).

## Critério de aceite

- Teste de integração: duas chamadas seguidas com o mesmo system prompt → a segunda tem
  `cache_read_input_tokens > 0`; `RespostaLlm.uso.custo_usd_estimado` > 0 e coerente.
- `mypy --strict` passa com o genérico `RespostaLlm[T]`.
- Lint e pytest (unitários) passam.
