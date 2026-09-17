from __future__ import annotations

from collections.abc import Mapping
from typing import Protocol

from loja_integrada_cadastro.models.prompt_renderizado import PromptRenderizado


class RepositorioPrompts(Protocol):
    """Renderiza os templates de prompt dos agentes (`docs/ARQUITETURA.md` §6.4)."""

    def renderizar(self, nome: str, contexto: Mapping[str, object]) -> PromptRenderizado:
        """Renderiza o template `nome` com `contexto`; variável faltante é `ErroPrompt`."""
        ...
