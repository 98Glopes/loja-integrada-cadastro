from __future__ import annotations


class ErroPlanilhaSaida(Exception):
    """Planilha de saída inválida: coluna fora do layout ou lote maior que o limite da loja."""

    def __init__(self, motivo: str) -> None:
        self.motivo = motivo
        super().__init__(motivo)
