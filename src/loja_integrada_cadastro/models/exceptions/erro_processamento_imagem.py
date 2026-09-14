from __future__ import annotations

from pathlib import Path


class ErroProcessamentoImagem(Exception):
    """Falha ao abrir, decodificar ou comprimir uma foto (`infra/processador_imagem_pillow.py`)."""

    def __init__(self, origem: Path, motivo: str) -> None:
        self.origem = origem
        self.motivo = motivo
        super().__init__(f"Falha ao processar imagem '{origem}': {motivo}")
