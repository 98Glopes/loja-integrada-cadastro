from __future__ import annotations

from pathlib import Path
from typing import Protocol

from loja_integrada_cadastro.models.estado_produto import EstadoProduto
from loja_integrada_cadastro.models.relatorio_lote import Relatorio


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

    def copiar_planilha_entrada(self, planilha: Path) -> None:
        """Copia a planilha recebida para `entrada/`, para auditoria do lote."""
        ...

    def salvar_relatorio(self, relatorio: Relatorio) -> None:
        """Grava `relatorio.md`/`relatorio.json` na raiz do lote."""
        ...

    def diretorio_lote(self) -> Path:
        """Raiz do workspace do lote (`docs/ARQUITETURA.md` §8), para montar caminhos de saída."""
        ...
