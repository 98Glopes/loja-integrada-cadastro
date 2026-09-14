from dataclasses import FrozenInstanceError
from decimal import Decimal

import pytest

from loja_integrada_cadastro.models.produto_entrada import ProdutoEntrada
from loja_integrada_cadastro.models.variacao_entrada import VariacaoEntrada


def _variacao(cor: str, tamanho: str, gtin: str = "7891234567895") -> VariacaoEntrada:
    return VariacaoEntrada(cor=cor, tamanho=tamanho, gtin=gtin, preco=Decimal("119.90"), estoque=10)


def _produto(variacoes: tuple[VariacaoEntrada, ...]) -> ProdutoEntrada:
    return ProdutoEntrada(
        sku_pai="3254002",
        marca="kiki",
        nome_fornecedor="Conjunto Baby Malha e Moletom",
        tipo_peca="Conjunto",
        categoria=("Linha Baby (P ao XG)", "Menino", "Conjunto"),
        composicao="100% algodão",
        detalhes="Botões na gola",
        colecao=None,
        faixa_tamanho="P ao G",
        variacoes=variacoes,
    )


def test_cores_ficam_distintas_na_ordem_de_aparicao() -> None:
    produto = _produto(
        (
            _variacao("Beige", "P"),
            _variacao("Rosa", "P"),
            _variacao("Beige", "G"),
            _variacao("Rosa", "G"),
        )
    )

    assert produto.cores == ("Beige", "Rosa")


def test_tamanhos_ficam_distintos_na_ordem_de_aparicao() -> None:
    produto = _produto(
        (
            _variacao("Beige", "G"),
            _variacao("Beige", "P"),
            _variacao("Rosa", "G"),
            _variacao("Rosa", "P"),
        )
    )

    assert produto.tamanhos == ("G", "P")


def test_produto_entrada_e_imutavel() -> None:
    produto = _produto((_variacao("Beige", "P"),))

    with pytest.raises(FrozenInstanceError):
        produto.marca = "outra"  # type: ignore[misc]


def test_variacao_entrada_e_imutavel() -> None:
    variacao = _variacao("Beige", "P")

    with pytest.raises(FrozenInstanceError):
        variacao.cor = "Rosa"  # type: ignore[misc]
