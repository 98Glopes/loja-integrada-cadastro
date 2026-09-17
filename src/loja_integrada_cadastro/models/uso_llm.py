from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class UsoLlm:
    """Tokens consumidos por uma chamada e o custo estimado pela tabela de preços (§6.3).

    `tokens_entrada` são os tokens de entrada **não** servidos pelo cache; leitura e escrita
    de cache vêm separadas porque têm preços próprios (0,1× e 1,25× da entrada).
    """

    tokens_entrada: int
    tokens_saida: int
    tokens_cache_leitura: int
    tokens_cache_escrita: int
    custo_usd_estimado: Decimal
