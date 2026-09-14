from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ProblemaLinhaPlanilha:
    """Um problema estrutural pontual encontrado ao ler a planilha de entrada."""

    linha: int
    """Número da linha na planilha (1-based; a linha 1 é o cabeçalho)."""

    coluna: str
    """Nome da coluna em que o problema foi encontrado (ex.: `"sku-pai"`)."""

    motivo: str
