from __future__ import annotations

from pathlib import Path

EXTENSOES_ACEITAS = frozenset({".jpg", ".jpeg", ".png", ".webp", ".heic"})


class CatalogoFotosDiretorio:
    """Lê a pasta `fotos/<sku-pai>/*` do disco (`docs/ARQUITETURA.md` §5.1)."""

    def __init__(self, raiz: Path) -> None:
        self._raiz = raiz

    def listar(self, sku_pai: str) -> list[Path]:
        diretorio = self._raiz / sku_pai
        if not diretorio.is_dir():
            return []
        arquivos = (
            item
            for item in diretorio.iterdir()
            if item.is_file() and item.suffix.lower() in EXTENSOES_ACEITAS
        )
        return sorted(arquivos, key=lambda arquivo: arquivo.name.lower())
