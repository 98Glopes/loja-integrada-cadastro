from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

PapelMensagem = Literal["user", "assistant"]


@dataclass(frozen=True)
class MensagemLlm:
    """Um turno da conversa enviada ao modelo (`docs/ARQUITETURA.md` §6.2).

    O retry com feedback reenvia a conversa anterior: o turno `assistant` é a resposta
    anterior do modelo, e um novo turno `user` traz os problemas apontados.
    """

    papel: PapelMensagem
    conteudo: str
