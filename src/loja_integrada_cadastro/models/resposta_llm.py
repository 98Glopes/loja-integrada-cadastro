from __future__ import annotations

from dataclasses import dataclass

from loja_integrada_cadastro.models.uso_llm import UsoLlm


@dataclass(frozen=True)
class RespostaLlm[T]:
    """Resposta estruturada de uma chamada ao modelo (`docs/ARQUITETURA.md` §6.3).

    `saida` é a instância do dataclass de domínio pedido como esquema. `texto` é o JSON bruto
    que o modelo devolveu — é o que volta como turno `assistant` no retry com feedback (§6.2).
    `modelo` é o modelo que **respondeu** (pode diferir do pedido quando há fallback por
    refusal); `request_id` serve para suporte da Anthropic.
    """

    saida: T
    texto: str
    uso: UsoLlm
    modelo: str
    request_id: str | None
    stop_reason: str
