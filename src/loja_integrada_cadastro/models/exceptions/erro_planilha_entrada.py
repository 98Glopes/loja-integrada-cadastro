from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from loja_integrada_cadastro.models.problema_linha_planilha import ProblemaLinhaPlanilha


class ErroPlanilhaEntrada(Exception):
    """Planilha de entrada com cabeçalho inválido ou uma ou mais linhas com problema.

    Acumula todos os problemas encontrados na leitura (não só o primeiro) para que a dona da
    loja corrija tudo de uma vez.
    """

    def __init__(self, caminho: Path, problemas: Sequence[ProblemaLinhaPlanilha]) -> None:
        self.caminho = caminho
        self.problemas = tuple(problemas)
        super().__init__(self._montar_mensagem())

    def _montar_mensagem(self) -> str:
        cabecalho = (
            f"Planilha de entrada inválida: {self.caminho} ({len(self.problemas)} problema(s))"
        )
        detalhes = [
            f"  - linha {problema.linha}, coluna '{problema.coluna}': {problema.motivo}"
            for problema in self.problemas
        ]
        return "\n".join([cabecalho, *detalhes])
