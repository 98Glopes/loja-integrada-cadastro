from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass


@dataclass(frozen=True)
class TextosProduto:
    """Os 4 campos de texto gerados para um produto (`docs/ARQUITETURA.md` §6.1).

    Vão, respectivamente, para as colunas `nome`, `descricao-completa`, `seo-tag-title` e
    `seo-tag-description` da planilha de saída (§7) — mas esta classe não conhece colunas,
    só os nomes de campo, para não acoplar `models` ao layout de saída.
    """

    titulo: str
    descricao_html: str
    seo_tag_title: str
    seo_tag_description: str

    def como_mapa(self) -> Mapping[str, str]:
        """Forma que vai para `EstadoProduto.registrar_textos`."""
        return {
            "titulo": self.titulo,
            "descricao_html": self.descricao_html,
            "seo_tag_title": self.seo_tag_title,
            "seo_tag_description": self.seo_tag_description,
        }
