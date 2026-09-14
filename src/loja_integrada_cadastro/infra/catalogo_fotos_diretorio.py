from __future__ import annotations

from pathlib import Path

EXTENSOES_ACEITAS = frozenset({".jpg", ".jpeg", ".png", ".webp", ".heic"})


class CatalogoFotosDiretorio:
    """Lê a pasta `fotos/<sku-pai>/<cor>/*` do disco (`docs/ARQUITETURA.md` §5.1)."""

    def __init__(self, raiz: Path) -> None:
        self._raiz = raiz

    def cores_disponiveis(self, sku_pai: str) -> list[str]:
        diretorio = self._raiz / sku_pai
        if not diretorio.is_dir():
            return []
        return sorted((item.name for item in diretorio.iterdir() if item.is_dir()), key=str.lower)

    def listar(self, sku_pai: str) -> dict[str, list[Path]]:
        return {cor: self._arquivos_da_cor(sku_pai, cor) for cor in self.cores_disponiveis(sku_pai)}

    def _arquivos_da_cor(self, sku_pai: str, cor: str) -> list[Path]:
        diretorio = self._raiz / sku_pai / cor
        arquivos = (
            item
            for item in diretorio.iterdir()
            if item.is_file() and item.suffix.lower() in EXTENSOES_ACEITAS
        )
        return sorted(arquivos, key=lambda arquivo: arquivo.name.lower())
