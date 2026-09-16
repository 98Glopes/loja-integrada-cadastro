from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from openpyxl import Workbook

from loja_integrada_cadastro.models.exceptions.erro_planilha_saida import ErroPlanilhaSaida
from loja_integrada_cadastro.models.layout_planilha_loja_integrada import (
    COLUNAS_PLANILHA_SAIDA,
)
from loja_integrada_cadastro.models.linha_planilha import LinhaPlanilha

_MAXIMO_LINHAS = 9_997


class EscritorPlanilhaSaidaOpenpyxl:
    """Grava as linhas montadas num `.xlsx` de aba única `Sheet1` (`docs/regras-planilha-loja-
    integrada.md` §1), reaproveitando a lógica validada em `poc/gerar_planilha_poc.py`."""

    def escrever(self, linhas: Sequence[LinhaPlanilha], destino: Path) -> None:
        if len(linhas) > _MAXIMO_LINHAS:
            raise ErroPlanilhaSaida(
                f"lote com {len(linhas)} linhas excede o limite de {_MAXIMO_LINHAS} da loja"
            )

        destino.parent.mkdir(parents=True, exist_ok=True)
        workbook = Workbook()
        aba = workbook.active
        assert aba is not None, "workbook novo sem aba ativa"
        aba.title = "Sheet1"

        aba.append(list(COLUNAS_PLANILHA_SAIDA))
        for linha in linhas:
            aba.append([linha.valores.get(coluna) for coluna in COLUNAS_PLANILHA_SAIDA])

        workbook.save(destino)
