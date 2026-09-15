from pathlib import Path

from loja_integrada_cadastro.config.composicao import (
    montar_gerador_modelo_entrada,
    montar_gerador_textos,
    montar_leitor_planilha_entrada,
    montar_validador_entrada,
)
from loja_integrada_cadastro.config.configuracao import Configuracao
from loja_integrada_cadastro.infra.gerador_modelo_entrada_openpyxl import GeradorModeloEntrada
from loja_integrada_cadastro.infra.gerador_textos_dummy import GeradorTextosDummy
from loja_integrada_cadastro.infra.leitor_planilha_entrada_openpyxl import (
    LeitorPlanilhaEntradaOpenpyxl,
)
from loja_integrada_cadastro.services.validador_entrada import ValidadorEntrada


def test_montar_gerador_modelo_entrada_devolve_gerador_funcional(tmp_path: Path) -> None:
    gerador = montar_gerador_modelo_entrada()

    assert isinstance(gerador, GeradorModeloEntrada)

    destino = tmp_path / "modelo-entrada.xlsx"
    gerador.gerar(destino)

    assert destino.exists()


def test_montar_leitor_planilha_entrada_devolve_leitor_openpyxl() -> None:
    assert isinstance(montar_leitor_planilha_entrada(), LeitorPlanilhaEntradaOpenpyxl)


def test_montar_validador_entrada_devolve_validador_funcional(tmp_path: Path) -> None:
    validador = montar_validador_entrada(tmp_path)

    assert isinstance(validador, ValidadorEntrada)


def test_montar_gerador_textos_devolve_gerador_dummy() -> None:
    gerador = montar_gerador_textos(Configuracao())

    assert isinstance(gerador, GeradorTextosDummy)
