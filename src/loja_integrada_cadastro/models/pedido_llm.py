from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, get_args

from loja_integrada_cadastro.models.mensagem_llm import MensagemLlm

EffortLlm = Literal["low", "medium", "high", "xhigh", "max"]
EFFORTS_VALIDOS: frozenset[str] = frozenset(get_args(EffortLlm))


@dataclass(frozen=True)
class PedidoLlm:
    """Tudo que uma chamada ao modelo precisa, sem nada do SDK (`docs/ARQUITETURA.md` §6.3).

    `blocos_sistema` são os blocos estáveis do system prompt, na ordem (regras fixas, perfil
    da marca…); o conector coloca o breakpoint de cache no último. `mensagens` é a conversa
    completa, começando por um turno `user`, para permitir retry com histórico. `effort` é
    um dos níveis aceitos pela API (`EFFORTS_VALIDOS`); quem monta o pedido a partir da
    configuração valida o texto do `.env` antes.
    """

    blocos_sistema: tuple[str, ...]
    mensagens: tuple[MensagemLlm, ...]
    modelo: str
    effort: EffortLlm
    max_tokens: int
