"""Roda o pipeline real (leitor + catálogo de fotos + dados mestre do pacote) sobre a fixture
`tests/fixtures/lote-piloto/` (gerada por `scripts/gerar_fixture_lote_piloto.py`) e confere o
critério de aceite da task 05: exatamente os dois defeitos propositais reprovam, o resto passa.
"""

from pathlib import Path

from loja_integrada_cadastro.infra.carregador_recursos import CarregadorRecursos
from loja_integrada_cadastro.infra.catalogo_fotos_diretorio import CatalogoFotosDiretorio
from loja_integrada_cadastro.infra.leitor_planilha_entrada_openpyxl import (
    LeitorPlanilhaEntradaOpenpyxl,
)
from loja_integrada_cadastro.services.validador_entrada import ValidadorEntrada

FIXTURE = Path(__file__).resolve().parent.parent / "fixtures" / "lote-piloto"


def test_lote_piloto_reprova_so_os_dois_defeitos_propositais() -> None:
    produtos = LeitorPlanilhaEntradaOpenpyxl().ler(FIXTURE / "planilha.xlsx")
    catalogo_fotos = CatalogoFotosDiretorio(FIXTURE / "fotos")
    dados_mestre = CarregadorRecursos().dados_mestre()
    validador = ValidadorEntrada(dados_mestre, catalogo_fotos)

    _, resultado = validador.validar(produtos)

    assert {problema.sku_pai for problema in resultado.problemas} == {"3254030", "3254040"}
    assert {problema.campo for problema in resultado.problemas} == {"cor", "gtin"}

    problema_cor = next(p for p in resultado.problemas if p.sku_pai == "3254030")
    assert problema_cor.campo == "cor"

    problema_gtin = next(p for p in resultado.problemas if p.sku_pai == "3254040")
    assert problema_gtin.campo == "gtin"

    skus_aprovados = {"3254002", "3254010", "3254020", "3254050"}
    assert not any(p.sku_pai in skus_aprovados for p in resultado.problemas)
