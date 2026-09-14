from pathlib import Path

from loja_integrada_cadastro.config.composicao import montar_gerador_modelo_entrada
from loja_integrada_cadastro.infra.gerador_modelo_entrada_openpyxl import GeradorModeloEntrada


def test_montar_gerador_modelo_entrada_devolve_gerador_funcional(tmp_path: Path) -> None:
    gerador = montar_gerador_modelo_entrada()

    assert isinstance(gerador, GeradorModeloEntrada)

    destino = tmp_path / "modelo-entrada.xlsx"
    gerador.gerar(destino)

    assert destino.exists()
