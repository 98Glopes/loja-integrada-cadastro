from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class VariacaoEntrada:
    """Uma variação (cor × tamanho) de um produto, lida de uma linha da planilha de entrada.

    Valores brutos: só sem espaços nas pontas. Validação de negócio (grade, GTIN) é da task 05.
    """

    cor: str
    tamanho: str
    gtin: str
    preco: Decimal
    estoque: int
