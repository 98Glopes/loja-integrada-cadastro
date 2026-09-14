from __future__ import annotations

from pathlib import Path
from typing import Protocol

from loja_integrada_cadastro.models.produto_entrada import ProdutoEntrada


class LeitorPlanilhaEntrada(Protocol):
    """Lê a planilha de entrada preenchida pela dona da loja e monta os produtos."""

    def ler(self, caminho: Path) -> list[ProdutoEntrada]: ...
