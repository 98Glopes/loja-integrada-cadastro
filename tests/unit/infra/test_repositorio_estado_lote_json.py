from decimal import Decimal
from pathlib import Path

import pytest

from loja_integrada_cadastro.infra.repositorio_estado_lote_json import RepositorioEstadoLoteJson
from loja_integrada_cadastro.models.estado_produto import EstadoProduto
from loja_integrada_cadastro.models.exceptions.erro_estado_lote import ErroEstadoLote
from loja_integrada_cadastro.models.foto_produto import FotoProduto
from loja_integrada_cadastro.models.produto_entrada import ProdutoEntrada
from loja_integrada_cadastro.models.resultado_validacao import (
    ProblemaValidacao,
    ResultadoValidacao,
)
from loja_integrada_cadastro.models.status_produto import StatusProduto
from loja_integrada_cadastro.models.variacao_entrada import VariacaoEntrada


def _entrada() -> ProdutoEntrada:
    return ProdutoEntrada(
        sku_pai="3254002",
        marca="kiki",
        nome_fornecedor="Conjunto Baby Malha e Moletom",
        tipo_peca="Conjunto",
        categoria=("Linha Baby (P ao XG)", "Menino", "Conjunto"),
        composicao="100% algodão",
        detalhes="Botões na gola",
        colecao=None,
        faixa_tamanho="P ao G",
        variacoes=(
            VariacaoEntrada(
                cor="Beige", tamanho="P", gtin="7891234567895", preco=Decimal("119.90"), estoque=10
            ),
        ),
    )


def _estado_completo() -> EstadoProduto:
    resultado = ResultadoValidacao(
        problemas=(), avisos=(ProblemaValidacao("3254002", "marca", "sem perfil próprio"),)
    )
    estado = EstadoProduto.registrar_validacao("3254002", _entrada(), "hash-abc", resultado)
    estado.registrar_fotos(
        fotos=(
            FotoProduto(
                sku_pai="3254002",
                cor="Beige",
                ordem=1,
                arquivo_origem=Path("fotos/3254002/Beige/20250920_113424.jpg"),
                nome="foto-1.jpg",
                chave="produtos/3254002/foto-1.jpg",
                url="https://cdn.example.com/foto-1.jpg",
                bytes=123456,
            ),
        ),
        imagens_pai=("https://cdn.example.com/foto-1.jpg",),
    )
    estado.registrar_tentativa(
        {"agente": "copywriter", "tentativa": 1, "usage": {"input": 100, "output": 50}},
        Decimal("0.1234"),
    )
    estado.registrar_textos(
        {
            "titulo": "Conjunto Kiki",
            "descricao_html": "<h2>x</h2>",
            "seo_tag_title": "Conjunto Kiki",
            "seo_tag_description": "Compre agora",
        }
    )
    estado.marcar_pronto()
    estado.registrar_verificacao({"title_ok": True, "imagens_encontradas": 1})
    return estado


def test_round_trip_preserva_todos_os_campos(tmp_path: Path) -> None:
    repositorio = RepositorioEstadoLoteJson(tmp_path / "2026-09-w38")
    original = _estado_completo()

    repositorio.salvar(original)
    recuperado = repositorio.carregar("3254002")

    assert recuperado == original
    assert isinstance(recuperado.custo_usd_estimado, Decimal)  # type: ignore[union-attr]
    assert recuperado.custo_usd_estimado == Decimal("0.1234")  # type: ignore[union-attr]
    assert recuperado.entrada.variacoes[0].preco == Decimal("119.90")  # type: ignore[union-attr]


def test_carregar_sku_inexistente_devolve_none(tmp_path: Path) -> None:
    repositorio = RepositorioEstadoLoteJson(tmp_path / "2026-09-w38")

    assert repositorio.carregar("inexistente") is None


def test_listar_traz_todos_os_estados_salvos(tmp_path: Path) -> None:
    repositorio = RepositorioEstadoLoteJson(tmp_path / "2026-09-w38")
    primeiro = _estado_completo()
    segundo = EstadoProduto.registrar_validacao(
        "3254010", _entrada(), "hash-xyz", ResultadoValidacao(problemas=(), avisos=())
    )
    repositorio.salvar(primeiro)
    repositorio.salvar(segundo)

    estados = {estado.sku_pai for estado in repositorio.listar()}

    assert estados == {"3254002", "3254010"}


def test_construtor_cria_arvore_do_workspace(tmp_path: Path) -> None:
    lote_dir = tmp_path / "2026-09-w38"

    RepositorioEstadoLoteJson(lote_dir)

    for subpasta in ("entrada", "estado", "fotos-processadas", "saida"):
        assert (lote_dir / subpasta).is_dir()


def test_copiar_planilha_entrada_copia_para_pasta_entrada(tmp_path: Path) -> None:
    origem = tmp_path / "produtos.xlsx"
    origem.write_bytes(b"conteudo-fake")
    lote_dir = tmp_path / "lote"
    repositorio = RepositorioEstadoLoteJson(lote_dir)

    repositorio.copiar_planilha_entrada(origem)

    copia = lote_dir / "entrada" / "produtos.xlsx"
    assert copia.read_bytes() == b"conteudo-fake"


def test_salvar_nao_deixa_arquivo_temporario_para_tras(tmp_path: Path) -> None:
    lote_dir = tmp_path / "lote"
    repositorio = RepositorioEstadoLoteJson(lote_dir)

    repositorio.salvar(_estado_completo())

    arquivos = list((lote_dir / "estado").iterdir())
    assert arquivos == [lote_dir / "estado" / "3254002.json"]


def test_carregar_json_corrompido_levanta_erro_estado_lote(tmp_path: Path) -> None:
    lote_dir = tmp_path / "lote"
    repositorio = RepositorioEstadoLoteJson(lote_dir)
    (lote_dir / "estado" / "3254002.json").write_text("{ isso não é json", encoding="utf-8")

    with pytest.raises(ErroEstadoLote):
        repositorio.carregar("3254002")


def test_carregar_json_com_campo_faltando_levanta_erro_estado_lote(tmp_path: Path) -> None:
    lote_dir = tmp_path / "lote"
    repositorio = RepositorioEstadoLoteJson(lote_dir)
    (lote_dir / "estado" / "3254002.json").write_text('{"sku_pai": "3254002"}', encoding="utf-8")

    with pytest.raises(ErroEstadoLote):
        repositorio.carregar("3254002")


def test_salvar_sobrescreve_estado_existente(tmp_path: Path) -> None:
    repositorio = RepositorioEstadoLoteJson(tmp_path / "lote")
    estado = _estado_completo()
    repositorio.salvar(estado)

    estado.registrar_verificacao({"title_ok": False})
    repositorio.salvar(estado)

    recuperado = repositorio.carregar("3254002")
    assert recuperado.verificacao == {"title_ok": False}  # type: ignore[union-attr]


def test_status_persiste_como_enum_correto(tmp_path: Path) -> None:
    repositorio = RepositorioEstadoLoteJson(tmp_path / "lote")
    estado = EstadoProduto.registrar_validacao(
        "3254002", _entrada(), "hash-1", ResultadoValidacao(problemas=(), avisos=())
    )
    repositorio.salvar(estado)

    recuperado = repositorio.carregar("3254002")

    assert recuperado is not None
    assert recuperado.status is StatusProduto.VALIDADO
