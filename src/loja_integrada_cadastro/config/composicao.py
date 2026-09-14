from __future__ import annotations

from loja_integrada_cadastro.infra.carregador_recursos import CarregadorRecursos
from loja_integrada_cadastro.infra.gerador_modelo_entrada_openpyxl import GeradorModeloEntrada


def montar_gerador_modelo_entrada() -> GeradorModeloEntrada:
    """Composition root do comando `modelo-entrada`."""
    dados_mestre = CarregadorRecursos().dados_mestre()
    return GeradorModeloEntrada(dados_mestre)
