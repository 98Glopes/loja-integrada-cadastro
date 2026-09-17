from __future__ import annotations

from typing import Protocol

from loja_integrada_cadastro.models.pedido_llm import PedidoLlm
from loja_integrada_cadastro.models.resposta_llm import RespostaLlm


class ClienteLlm(Protocol):
    """Chamada a um modelo de linguagem com saída estruturada (`docs/ARQUITETURA.md` §6.3).

    `esquema` é um dataclass do domínio; a conversão de/para o formato do provedor é do
    conector. Falhas viram `ErroGeracaoTexto` (com `retentavel`), nunca exceções do SDK.
    """

    def gerar[T](self, pedido: PedidoLlm, esquema: type[T]) -> RespostaLlm[T]:
        """Envia `pedido` e devolve a saída validada contra `esquema`, com uso e custo."""
        ...
