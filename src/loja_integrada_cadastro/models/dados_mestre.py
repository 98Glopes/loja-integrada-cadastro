from __future__ import annotations

import unicodedata
from collections.abc import Mapping
from dataclasses import dataclass


def _normalizar(texto: str) -> str:
    """Remove acentuação (NFKD) e caixa, para comparação de marca insensível a ambos."""
    sem_acento = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("ascii")
    return sem_acento.casefold()


@dataclass(frozen=True)
class DadosMestre:
    """Lista mestre de marcas, cores, tamanhos e categorias de referência do catálogo.

    Extraída da exportação real da loja (ver `scripts/extrair_dados_mestre.py` e
    `recursos/dados_mestre.yaml`), usada pelo validador e pelos prompts de copywriting.
    """

    marcas_canonicas: Mapping[str, tuple[str, ...]]
    marcas_proibidas: Mapping[str, str]
    cores: frozenset[str]
    tamanhos: frozenset[str]
    categorias_referencia: frozenset[str]

    def marca_canonica(self, texto: str) -> str | None:
        """Resolve a grafia canônica de `texto`, ignorando caixa e acentuação.

        Aceita tanto a própria grafia canônica quanto qualquer alias conhecido.
        """
        alvo = _normalizar(texto)
        for canonica, aliases in self.marcas_canonicas.items():
            if _normalizar(canonica) == alvo:
                return canonica
            if any(_normalizar(alias) == alvo for alias in aliases):
                return canonica
        return None

    def motivo_marca_proibida(self, texto: str) -> str | None:
        """Devolve o motivo pelo qual `texto` é uma marca proibida, ou `None` se não for."""
        alvo = _normalizar(texto)
        for nome, motivo in self.marcas_proibidas.items():
            if _normalizar(nome) == alvo:
                return motivo
        return None

    def cor_valida(self, texto: str) -> bool:
        """Confere `texto` contra a lista mestre de cores — comparação exata (decisão estrita)."""
        return texto in self.cores

    def tamanho_valido(self, texto: str) -> bool:
        """Confere `texto` contra a lista mestre de tamanhos — comparação exata (estrita)."""
        return texto in self.tamanhos

    def categoria_conhecida(self, caminho: str) -> bool:
        """Confere se `caminho` está entre as categorias observadas na exportação real.

        Apenas referência/aviso — categoria não é validada contra lista fechada
        (`docs/brutos/dados_mestre.md` §3).
        """
        return caminho in self.categorias_referencia
