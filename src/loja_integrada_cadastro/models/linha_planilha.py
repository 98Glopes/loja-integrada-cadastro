from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Literal

from loja_integrada_cadastro.models.exceptions.erro_planilha_saida import ErroPlanilhaSaida
from loja_integrada_cadastro.models.layout_planilha_loja_integrada import (
    COLUNAS_PLANILHA_SAIDA,
)

TipoLinhaPlanilha = Literal["com-variacao", "variacao"]


@dataclass(frozen=True)
class LinhaPlanilha:
    """Uma linha (pai ou filha) da planilha de saída — só as colunas que ela preenche.

    `valores` guarda apenas as colunas com conteúdo; o restante das 54 fica em branco quando a
    linha é escrita (`services/ports/escritor_planilha_saida.py`).
    """

    tipo: TipoLinhaPlanilha
    valores: Mapping[str, object]

    def __post_init__(self) -> None:
        desconhecidas = set(self.valores) - set(COLUNAS_PLANILHA_SAIDA)
        if desconhecidas:
            raise ErroPlanilhaSaida(
                f"coluna(s) fora do layout da planilha de saída: {sorted(desconhecidas)}"
            )
