from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass


@dataclass(frozen=True)
class Relatorio:
    """Relatório de um lote processado, em duas formas (`docs/ARQUITETURA.md` §8).

    `markdown` vai para `relatorio.md` (leitura humana); `dados` vai para `relatorio.json`
    (mesmo conteúdo, estruturado — base do `verificar` e de evals futuros).
    """

    markdown: str
    dados: Mapping[str, object]
