from __future__ import annotations

import pytest

from loja_integrada_cadastro.models.exceptions.erro_planilha_saida import ErroPlanilhaSaida
from loja_integrada_cadastro.models.linha_planilha import LinhaPlanilha


def test_aceita_colunas_validas_do_layout() -> None:
    linha = LinhaPlanilha(tipo="com-variacao", valores={"sku": "3254002", "ativo": "S"})

    assert linha.valores["sku"] == "3254002"


def test_rejeita_coluna_fora_do_layout() -> None:
    with pytest.raises(ErroPlanilhaSaida):
        LinhaPlanilha(tipo="variacao", valores={"coluna-inexistente": "x"})
