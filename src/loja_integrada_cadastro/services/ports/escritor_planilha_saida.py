from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Protocol

from loja_integrada_cadastro.models.linha_planilha import LinhaPlanilha


class EscritorPlanilhaSaida(Protocol):
    """Grava as linhas montadas no `.xlsx` que a Loja Integrada importa."""

    def escrever(self, linhas: Sequence[LinhaPlanilha], destino: Path) -> None:
        """Escreve `linhas` em `destino`, cabeçalho = layout de 54 colunas."""
        ...
