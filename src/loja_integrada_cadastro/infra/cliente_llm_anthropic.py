from __future__ import annotations

import anthropic
import pydantic
from anthropic.types.beta import BetaMessage, BetaMessageParam, BetaTextBlockParam
from anthropic.types.beta.parsed_beta_message import ParsedBetaMessage

from loja_integrada_cadastro.models.exceptions.erro_geracao_texto import ErroGeracaoTexto
from loja_integrada_cadastro.models.pedido_llm import PedidoLlm
from loja_integrada_cadastro.models.resposta_llm import RespostaLlm
from loja_integrada_cadastro.models.tabela_precos_llm import TabelaPrecosLlm
from loja_integrada_cadastro.models.uso_llm import UsoLlm

_BETA_FALLBACKS = "server-side-fallback-2026-07-01"
_TENTATIVAS_MAX_TOKENS = 2


class ClienteLlmAnthropic:
    """Conector da API Anthropic atrás do port `ClienteLlm` (`docs/ARQUITETURA.md` §6.3).

    Usa `client.beta.messages.parse`, que aceita o dataclass de domínio como `output_format`
    (o SDK gera o JSON Schema e valida a resposta via `pydantic.TypeAdapter`), adaptive thinking
    com `effort` por pedido e `cache_control` no último bloco do system prompt.

    `fallbacks="default"` (beta `server-side-fallback-2026-07-01`) está ligado: se o modelo
    pedido recusar por política, a API reexecuta a mesma chamada no modelo de fallback
    recomendado pela Anthropic e devolve a resposta dele — `RespostaLlm.modelo` registra o
    modelo que respondeu e o custo usa a tabela desse modelo. Um `refusal` que chegue aqui
    significa que a cadeia inteira recusou.

    Retries de rede/429/5xx são do próprio SDK (`max_retries` no cliente); o que sobra vira
    `ErroGeracaoTexto` com `retentavel` para a política de retry do agente.
    """

    def __init__(self, client: anthropic.Anthropic, tabela_precos: TabelaPrecosLlm) -> None:
        self._client = client
        self._tabela_precos = tabela_precos

    def gerar[T](self, pedido: PedidoLlm, esquema: type[T]) -> RespostaLlm[T]:
        self._tabela_precos.exigir(pedido.modelo)
        max_tokens = pedido.max_tokens
        for tentativa in range(1, _TENTATIVAS_MAX_TOKENS + 1):
            mensagem = self._chamar(pedido, esquema, max_tokens)
            if mensagem.stop_reason != "max_tokens":
                return self._converter(mensagem, esquema)
            if tentativa < _TENTATIVAS_MAX_TOKENS:
                max_tokens *= 2
        raise ErroGeracaoTexto(
            f"resposta truncada por max_tokens mesmo com {max_tokens} tokens", retentavel=False
        )

    def _chamar[T](
        self, pedido: PedidoLlm, esquema: type[T], max_tokens: int
    ) -> ParsedBetaMessage[T]:
        try:
            return self._client.beta.messages.parse(
                model=pedido.modelo,
                max_tokens=max_tokens,
                system=_blocos_sistema(pedido),
                messages=_mensagens(pedido),
                output_format=esquema,
                thinking={"type": "adaptive"},
                output_config={"effort": pedido.effort},
                fallbacks="default",
                betas=[_BETA_FALLBACKS],
            )
        except anthropic.AuthenticationError as erro:
            raise ErroGeracaoTexto(
                f"chave da API Anthropic rejeitada — confira ANTHROPIC_API_KEY ({erro.message})",
                retentavel=False,
            ) from erro
        except anthropic.BadRequestError as erro:
            raise ErroGeracaoTexto(
                f"pedido rejeitado pela API (modelo '{pedido.modelo}', effort "
                f"'{pedido.effort}', max_tokens {max_tokens}): {erro.message}",
                retentavel=False,
            ) from erro
        except anthropic.RateLimitError as erro:
            raise ErroGeracaoTexto(
                f"limite de requisições da API esgotado: {erro.message}", retentavel=True
            ) from erro
        except anthropic.APIStatusError as erro:
            raise ErroGeracaoTexto(
                f"API respondeu HTTP {erro.status_code}: {erro.message}",
                retentavel=erro.status_code >= 500,
            ) from erro
        except anthropic.APIConnectionError as erro:
            raise ErroGeracaoTexto(
                f"falha de conexão com a API: {erro.message}", retentavel=True
            ) from erro
        except pydantic.ValidationError as erro:
            raise ErroGeracaoTexto(
                f"resposta fora do esquema {esquema.__name__}: {erro}", retentavel=True
            ) from erro

    def _converter[T](self, mensagem: ParsedBetaMessage[T], esquema: type[T]) -> RespostaLlm[T]:
        if mensagem.stop_reason == "refusal":
            raise ErroGeracaoTexto(_motivo_refusal(mensagem), retentavel=False)
        saida = mensagem.parsed_output
        if saida is None:
            raise ErroGeracaoTexto(
                f"resposta sem bloco de texto para o esquema {esquema.__name__} "
                f"(stop_reason={mensagem.stop_reason})",
                retentavel=True,
            )
        return RespostaLlm(
            saida=saida,
            texto=_texto_de(mensagem),
            uso=self._uso_de(mensagem),
            modelo=mensagem.model,
            request_id=mensagem._request_id,
            stop_reason=mensagem.stop_reason or "",
        )

    def _uso_de(self, mensagem: BetaMessage) -> UsoLlm:
        uso = mensagem.usage
        tokens_entrada = uso.input_tokens
        tokens_saida = uso.output_tokens
        tokens_cache_leitura = uso.cache_read_input_tokens or 0
        tokens_cache_escrita = uso.cache_creation_input_tokens or 0
        preco = self._tabela_precos.exigir(mensagem.model)
        return UsoLlm(
            tokens_entrada=tokens_entrada,
            tokens_saida=tokens_saida,
            tokens_cache_leitura=tokens_cache_leitura,
            tokens_cache_escrita=tokens_cache_escrita,
            custo_usd_estimado=preco.custo(
                tokens_entrada, tokens_saida, tokens_cache_leitura, tokens_cache_escrita
            ),
        )


def _blocos_sistema(pedido: PedidoLlm) -> list[BetaTextBlockParam]:
    """Blocos de system na ordem, com o breakpoint de cache só no último (§6.3)."""
    blocos: list[BetaTextBlockParam] = [
        {"type": "text", "text": texto} for texto in pedido.blocos_sistema
    ]
    if blocos:
        blocos[-1]["cache_control"] = {"type": "ephemeral"}
    return blocos


def _mensagens(pedido: PedidoLlm) -> list[BetaMessageParam]:
    return [{"role": m.papel, "content": m.conteudo} for m in pedido.mensagens]


def _texto_de(mensagem: BetaMessage) -> str:
    return next((bloco.text for bloco in mensagem.content if bloco.type == "text"), "")


def _motivo_refusal(mensagem: BetaMessage) -> str:
    detalhes = mensagem.stop_details
    if detalhes is None:
        return "o modelo recusou o pedido (refusal) sem detalhes"
    return (
        f"o modelo recusou o pedido (refusal, categoria "
        f"{detalhes.category or 'desconhecida'}): {detalhes.explanation or 'sem explicação'}"
    )
