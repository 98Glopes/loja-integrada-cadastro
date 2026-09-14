from __future__ import annotations

from loja_integrada_cadastro.models.status_produto import StatusProduto


class ErroTransicaoEstadoInvalida(Exception):
    """Método de intenção chamado num `EstadoProduto` que não está no status esperado por ele."""

    def __init__(self, sku_pai: str, status_atual: StatusProduto, metodo: str) -> None:
        self.sku_pai = sku_pai
        self.status_atual = status_atual
        self.metodo = metodo
        super().__init__(
            f"'{metodo}' não é válido para o produto '{sku_pai}' no status '{status_atual.value}'"
        )
