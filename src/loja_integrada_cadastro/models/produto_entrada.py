from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from loja_integrada_cadastro.models.variacao_entrada import VariacaoEntrada


@dataclass(frozen=True)
class ProdutoEntrada:
    """Um produto (família `sku-pai`) e suas variações, lido da planilha de entrada.

    Uma linha da planilha por variação; campos de produto vêm da primeira linha do grupo.
    Valores brutos: só sem espaços nas pontas. Validação de negócio (marca/cor/tamanho/GTIN,
    pastas de fotos) é da task 05.
    """

    sku_pai: str
    marca: str
    nome_fornecedor: str
    tipo_peca: str
    categoria: tuple[str, ...]
    composicao: str
    detalhes: str
    colecao: str | None
    faixa_tamanho: str
    variacoes: tuple[VariacaoEntrada, ...]

    @property
    def cores(self) -> tuple[str, ...]:
        """Cores distintas das variações, na ordem em que aparecem na planilha."""
        return _distintos_em_ordem(variacao.cor for variacao in self.variacoes)

    @property
    def tamanhos(self) -> tuple[str, ...]:
        """Tamanhos distintos das variações, na ordem em que aparecem na planilha."""
        return _distintos_em_ordem(variacao.tamanho for variacao in self.variacoes)


def _distintos_em_ordem(valores: Iterable[str]) -> tuple[str, ...]:
    vistos: list[str] = []
    for valor in valores:
        if valor not in vistos:
            vistos.append(valor)
    return tuple(vistos)
