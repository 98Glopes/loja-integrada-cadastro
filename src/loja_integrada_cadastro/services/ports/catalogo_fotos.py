from __future__ import annotations

from pathlib import Path
from typing import Protocol


class CatalogoFotos(Protocol):
    """Enxerga a pasta de fotos (`fotos/<sku-pai>/*`) informada pela dona da loja.

    Fotos não têm cor: valem para o produto inteiro (a Loja Integrada só aceita imagem no
    produto pai, nunca na variação/filha — ver `docs/ARQUITETURA.md` §5).
    """

    def listar(self, sku_pai: str) -> list[Path]:
        """Arquivos de imagem do produto, em ordem alfabética (case-insensitive).

        `sku_pai` sem pasta, ou pasta sem nenhum arquivo de extensão aceita, devolve `[]`.
        """
        ...
