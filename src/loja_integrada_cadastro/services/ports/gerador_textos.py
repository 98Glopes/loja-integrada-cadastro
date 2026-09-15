from __future__ import annotations

from typing import Protocol

from loja_integrada_cadastro.models.estado_produto import EstadoProduto
from loja_integrada_cadastro.models.produto_entrada import ProdutoEntrada
from loja_integrada_cadastro.models.textos_produto import TextosProduto


class GeradorTextos(Protocol):
    """Produz os 4 campos de texto de um produto (`docs/ARQUITETURA.md` §6.1/§6.2).

    Implementações registram as próprias tentativas em `estado` (`registrar_tentativa`); quem
    chama `gerar` registra o resultado (`estado.registrar_textos`). Mesma assinatura que
    `GeradorTextosIa` (task 16) vai implementar — a troca de `GeradorTextosDummy` (task 09,
    provisório, ADR-007) para a implementação de IA é só wiring em
    `config/composicao.montar_gerador_textos`.
    """

    def gerar(self, produto: ProdutoEntrada, estado: EstadoProduto) -> TextosProduto:
        """Gera os 4 campos de texto para `produto`; pode registrar tentativas em `estado`."""
        ...
