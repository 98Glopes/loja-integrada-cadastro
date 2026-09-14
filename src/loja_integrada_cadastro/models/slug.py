from __future__ import annotations

import re
import unicodedata

_NAO_ALFANUMERICO = re.compile(r"[^a-z0-9]+")


def slugificar(texto: str) -> str:
    """Normaliza texto livre para nome de arquivo/SKU/URL (`docs/ARQUITETURA.md` §5.2).

    Minúsculas, sem acento, apenas `[a-z0-9-]`, hífens únicos, sem hífen nas pontas.
    """
    sem_acento = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("ascii")
    slug = _NAO_ALFANUMERICO.sub("-", sem_acento.lower())
    return slug.strip("-")
