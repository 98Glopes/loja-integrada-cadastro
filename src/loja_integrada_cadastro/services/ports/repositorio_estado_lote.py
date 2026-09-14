from __future__ import annotations

from typing import Protocol

from loja_integrada_cadastro.models.estado_produto import EstadoProduto


class RepositorioEstadoLote(Protocol):
    """Persiste e recupera o estado de cada produto de um lote (`docs/ARQUITETURA.md` §8)."""

    def carregar(self, sku_pai: str) -> EstadoProduto | None:
        """Estado salvo do produto, ou `None` se ele ainda não tem estado no lote."""
        ...

    def salvar(self, estado: EstadoProduto) -> None:
        """Grava (ou sobrescreve) o estado do produto."""
        ...

    def listar(self) -> list[EstadoProduto]:
        """Todos os estados já salvos no lote."""
        ...
