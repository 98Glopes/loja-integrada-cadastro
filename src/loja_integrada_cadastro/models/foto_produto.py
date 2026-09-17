from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class FotoProduto:
    """Uma foto processada de um produto, pronta para publicação (`docs/ARQUITETURA.md` §5).

    Não tem cor: vale para o produto inteiro (a Loja Integrada só aceita imagem no pai).
    """

    sku_pai: str
    ordem: int
    arquivo_origem: Path
    nome: str
    chave: str
    url: str | None = None
    bytes: int | None = None
