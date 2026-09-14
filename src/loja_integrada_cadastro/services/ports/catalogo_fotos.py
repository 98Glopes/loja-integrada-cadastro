from __future__ import annotations

from pathlib import Path
from typing import Protocol


class CatalogoFotos(Protocol):
    """Enxerga a pasta de fotos (`fotos/<sku-pai>/<cor>/*`) informada pela dona da loja."""

    def listar(self, sku_pai: str) -> dict[str, list[Path]]:
        """Arquivos de imagem de cada cor do produto, em ordem alfabética (case-insensitive).

        Chave = nome da subpasta (cor) como está no disco; valor vazio se a subpasta existir
        sem nenhum arquivo de extensão aceita. `sku_pai` sem pasta devolve `{}`.
        """
        ...

    def cores_disponiveis(self, sku_pai: str) -> list[str]:
        """Nomes das subpastas de cor existentes para `sku_pai`, sem abrir os arquivos."""
        ...
