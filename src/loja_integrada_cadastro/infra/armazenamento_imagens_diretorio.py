from __future__ import annotations

from pathlib import Path
from urllib.parse import urlparse
from urllib.request import url2pathname


class ArmazenamentoImagensDiretorio:
    """Grava fotos em `fotos-processadas/` do workspace; devolve URL `file://` (task 07).

    Implementação provisória de `ArmazenamentoImagens` até o R2 entrar (task 08).
    """

    def __init__(self, raiz: Path) -> None:
        self._raiz = raiz

    def publicar(self, chave: str, dados: bytes) -> str:
        destino = self._raiz / chave
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_bytes(dados)
        return destino.resolve().as_uri()

    def existe(self, url: str) -> bool:
        caminho = Path(url2pathname(urlparse(url).path))
        return caminho.is_file()
