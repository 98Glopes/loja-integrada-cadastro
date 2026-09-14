from __future__ import annotations

from typing import Protocol


class ArmazenamentoImagens(Protocol):
    """Publica o JPEG final e confere disponibilidade (`docs/ARQUITETURA.md` §5.3/§10)."""

    def publicar(self, chave: str, dados: bytes) -> str:
        """Grava/sobrescreve `dados` em `chave`; devolve a URL resultante."""
        ...

    def existe(self, url: str) -> bool:
        """Confirma que `url` está acessível (HEAD real no R2 — task 08; local, checa o arquivo)."""
        ...
