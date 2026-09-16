from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

from loja_integrada_cadastro.models.status_produto import StatusProduto


@dataclass(frozen=True)
class ResumoLote:
    """Números finais de uma execução de `processar` (`docs/ARQUITETURA.md` §8)."""

    contagem_por_status: Mapping[StatusProduto, int]
    custo_usd_total: Decimal
    duracao_segundos: float
    caminho_planilha: Path
    caminho_relatorio_md: Path
    caminho_relatorio_json: Path

    @property
    def todos_prontos(self) -> bool:
        """`True` quando nenhum produto do lote ficou fora do status `pronto`."""
        return not any(
            quantidade > 0
            for status, quantidade in self.contagem_por_status.items()
            if status is not StatusProduto.PRONTO
        )
