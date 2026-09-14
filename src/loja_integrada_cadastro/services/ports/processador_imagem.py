from __future__ import annotations

from pathlib import Path
from typing import Protocol


class ProcessadorImagem(Protocol):
    """Prepara uma foto bruta para publicação (`docs/ARQUITETURA.md` §5.3)."""

    def preparar(self, origem: Path) -> bytes:
        """Abre `origem`, corrige orientação, redimensiona e comprime; devolve o JPEG final."""
        ...
