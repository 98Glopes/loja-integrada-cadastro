from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class PadroesFisicos:
    """Peso e dimensões fixos aplicados a toda variação (ADR-004, `docs/ARQUITETURA.md` §16).

    Não vêm de `DadosMestre`: são parâmetros de configuração (`config.Configuracao`), não dado
    mestre do catálogo.
    """

    peso_kg: Decimal
    altura_cm: Decimal
    largura_cm: Decimal
    comprimento_cm: Decimal
