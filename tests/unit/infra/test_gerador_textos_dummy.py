"""`GeradorTextosDummy` sobre os 6 produtos de `tests/fixtures/lote-piloto` (task 09).

Usa o leitor real (openpyxl) e o `DadosMestre` real do pacote — mesma fixture da task 05
(`tests/unit/test_fixture_lote_piloto.py`) — para confirmar que os limites de
`docs/ARQUITETURA.md` §6.1 valem para dados reais do catálogo, não só para um caso sintético.
"""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path
from re import findall

import pytest

from loja_integrada_cadastro.infra.carregador_recursos import CarregadorRecursos
from loja_integrada_cadastro.infra.gerador_textos_dummy import GeradorTextosDummy
from loja_integrada_cadastro.infra.leitor_planilha_entrada_openpyxl import (
    LeitorPlanilhaEntradaOpenpyxl,
)
from loja_integrada_cadastro.infra.repositorio_estado_lote_json import RepositorioEstadoLoteJson
from loja_integrada_cadastro.models.estado_produto import EstadoProduto
from loja_integrada_cadastro.models.foto_produto import FotoProduto
from loja_integrada_cadastro.models.produto_entrada import ProdutoEntrada
from loja_integrada_cadastro.models.resultado_validacao import ResultadoValidacao

FIXTURE = Path(__file__).resolve().parent.parent.parent / "fixtures" / "lote-piloto"

_APROVADO = ResultadoValidacao(problemas=(), avisos=())
_TAGS_PERMITIDAS = {"h2", "h3", "p", "ul", "li", "strong"}


def _produtos() -> list[ProdutoEntrada]:
    return LeitorPlanilhaEntradaOpenpyxl().ler(FIXTURE / "planilha.xlsx")


def _estado_fotos_publicadas(produto: ProdutoEntrada) -> EstadoProduto:
    estado = EstadoProduto.registrar_validacao(
        produto.sku_pai, produto, f"hash-{produto.sku_pai}", _APROVADO
    )
    foto = FotoProduto(
        sku_pai=produto.sku_pai,
        cor=produto.cores[0],
        ordem=1,
        arquivo_origem=Path(f"fotos/{produto.sku_pai}/{produto.cores[0]}/1.jpg"),
        nome="1.jpg",
        chave=f"produtos/{produto.sku_pai}/1.jpg",
        url="url-1",
        bytes=1000,
    )
    estado.registrar_fotos(fotos=(foto,), imagens_pai=("url-1",))
    return estado


def _gerador() -> GeradorTextosDummy:
    dados_mestre = CarregadorRecursos().dados_mestre()
    return GeradorTextosDummy(dados_mestre)


def _tags_usadas(html: str) -> set[str]:
    return set(findall(r"<(\w+)>", html))


def _contar_palavras(html: str) -> int:
    sem_tags = html
    for tag in _TAGS_PERMITIDAS:
        sem_tags = sem_tags.replace(f"<{tag}>", " ").replace(f"</{tag}>", " ")
    sem_tags = sem_tags.replace("<ul>", " ").replace("</ul>", " ")
    return len(sem_tags.split())


@pytest.mark.parametrize("produto", _produtos(), ids=lambda p: p.sku_pai)
def test_titulo_respeita_limites(produto: ProdutoEntrada) -> None:
    estado = _estado_fotos_publicadas(produto)
    textos = _gerador().gerar(produto, estado)

    assert len(textos.titulo) <= 68
    assert textos.titulo.startswith("[DUMMY] ")
    assert produto.faixa_tamanho in textos.titulo


@pytest.mark.parametrize("produto", _produtos(), ids=lambda p: p.sku_pai)
def test_descricao_respeita_estrutura_tags_e_palavras(produto: ProdutoEntrada) -> None:
    estado = _estado_fotos_publicadas(produto)
    textos = _gerador().gerar(produto, estado)
    html = textos.descricao_html

    assert html.startswith("<h2>[DUMMY] ")
    assert _tags_usadas(html) <= _TAGS_PERMITIDAS
    assert _contar_palavras(html) >= 120

    marca = CarregadorRecursos().dados_mestre().marca_canonica(produto.marca) or produto.marca
    indice_sobre = html.index(f"<h3>Sobre a {marca}</h3>")
    indice_compre = html.index("<h3>Compre na Kmilaa Modas</h3>")
    assert indice_sobre < indice_compre


@pytest.mark.parametrize("produto", _produtos(), ids=lambda p: p.sku_pai)
def test_tag_title_respeita_limites(produto: ProdutoEntrada) -> None:
    estado = _estado_fotos_publicadas(produto)
    textos = _gerador().gerar(produto, estado)

    assert len(textos.seo_tag_title) <= 60
    assert not textos.seo_tag_title.endswith("| Kmilaa Modas")
    assert not textos.seo_tag_title.startswith("[DUMMY]")


@pytest.mark.parametrize("produto", _produtos(), ids=lambda p: p.sku_pai)
def test_meta_description_respeita_limites(produto: ProdutoEntrada) -> None:
    estado = _estado_fotos_publicadas(produto)
    textos = _gerador().gerar(produto, estado)

    assert 140 <= len(textos.seo_tag_description) <= 155
    assert textos.seo_tag_description.startswith("[DUMMY] ")


def test_determinismo_mesma_entrada_mesmo_resultado() -> None:
    produto = _produtos()[0]
    gerador = _gerador()

    textos_1 = gerador.gerar(produto, _estado_fotos_publicadas(produto))
    textos_2 = gerador.gerar(produto, _estado_fotos_publicadas(produto))

    assert textos_1 == textos_2


def test_registra_exatamente_uma_tentativa_com_custo_zero() -> None:
    produto = _produtos()[0]
    estado = _estado_fotos_publicadas(produto)

    _gerador().gerar(produto, estado)

    assert len(estado.tentativas) == 1
    tentativa = estado.tentativas[0]
    assert tentativa["agente"] == "dummy"
    assert tentativa["modelo"] == "dummy"
    assert tentativa["tentativa"] == 1
    assert estado.custo_usd_estimado == Decimal("0")


def test_como_mapa_registrar_textos_round_trip_pelo_repositorio(tmp_path: Path) -> None:
    produto = _produtos()[0]
    estado = _estado_fotos_publicadas(produto)
    textos = _gerador().gerar(produto, estado)

    estado.registrar_textos(textos.como_mapa())

    repositorio = RepositorioEstadoLoteJson(tmp_path / "lote")
    repositorio.salvar(estado)
    recarregado = repositorio.carregar(produto.sku_pai)

    assert recarregado is not None
    assert recarregado.textos == textos.como_mapa()
