from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

_TOKENS_POR_MILHAO = Decimal(1_000_000)


@dataclass(frozen=True)
class PrecoModeloLlm:
    """Preços de um modelo em USD por 1 milhão de tokens (`recursos/precos_llm.yaml`)."""

    entrada: Decimal
    saida: Decimal
    cache_leitura: Decimal
    cache_escrita: Decimal

    def custo(
        self,
        tokens_entrada: int,
        tokens_saida: int,
        tokens_cache_leitura: int,
        tokens_cache_escrita: int,
    ) -> Decimal:
        """Custo estimado de uma chamada, somando os quatro componentes de `usage`."""
        total = (
            self.entrada * tokens_entrada
            + self.saida * tokens_saida
            + self.cache_leitura * tokens_cache_leitura
            + self.cache_escrita * tokens_cache_escrita
        )
        return total / _TOKENS_POR_MILHAO
