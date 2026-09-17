from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PromptRenderizado:
    """Resultado de renderizar um template de prompt (`docs/ARQUITETURA.md` §6.3/§6.4).

    `blocos_sistema` são os blocos estáveis do system prompt na ordem do template
    (`sistema_fixo`, `sistema_marca`) — separados para o cache da API; `usuario` é o turno
    com os dados variáveis do produto.
    """

    blocos_sistema: tuple[str, ...]
    usuario: str
