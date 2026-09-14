from __future__ import annotations

from pathlib import Path


class ErroEstadoLote(Exception):
    """Estado de um produto do lote (`estado/<sku-pai>.json`) ilegível ou com campo inválido."""

    def __init__(self, caminho: Path, motivo: str) -> None:
        self.caminho = caminho
        self.motivo = motivo
        super().__init__(f"Estado do lote inválido '{self.caminho}': {self.motivo}")
