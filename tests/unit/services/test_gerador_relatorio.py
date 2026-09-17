from __future__ import annotations

from decimal import Decimal
from pathlib import Path

from loja_integrada_cadastro.models.estado_produto import EstadoProduto
from loja_integrada_cadastro.models.foto_produto import FotoProduto
from loja_integrada_cadastro.models.produto_entrada import ProdutoEntrada
from loja_integrada_cadastro.models.resultado_validacao import (
    ProblemaValidacao,
    ResultadoValidacao,
)
from loja_integrada_cadastro.models.resumo_lote import ResumoLote
from loja_integrada_cadastro.models.status_produto import StatusProduto
from loja_integrada_cadastro.models.variacao_entrada import VariacaoEntrada
from loja_integrada_cadastro.services.gerador_relatorio import GeradorRelatorio

_APROVADO = ResultadoValidacao(problemas=(), avisos=())


def _produto(sku_pai: str) -> ProdutoEntrada:
    return ProdutoEntrada(
        sku_pai=sku_pai,
        marca="Kiki",
        nome_fornecedor="Conjunto Baby",
        tipo_peca="Conjunto",
        categoria=("Linha Baby", "Menino", "Conjunto"),
        composicao="100% algodão",
        detalhes="Botões na gola",
        colecao=None,
        faixa_tamanho="P ao G",
        variacoes=(
            VariacaoEntrada(
                cor="Beige",
                tamanho="P",
                gtin="7891234567895",
                preco=Decimal("119.90"),
                estoque=10,
            ),
        ),
    )


def _estado_pronto(sku_pai: str) -> EstadoProduto:
    produto = _produto(sku_pai)
    estado = EstadoProduto.registrar_validacao(sku_pai, produto, "hash", _APROVADO)
    foto_selecionada = FotoProduto(
        sku_pai=sku_pai,
        ordem=1,
        arquivo_origem=Path("a.jpg"),
        nome="foto-1.jpg",
        chave=f"produtos/{sku_pai}/foto-1.jpg",
        url=f"https://cdn/{sku_pai}/foto-1.jpg",
        bytes=100,
    )
    foto_nao_usada = FotoProduto(
        sku_pai=sku_pai,
        ordem=2,
        arquivo_origem=Path("b.jpg"),
        nome="foto-2.jpg",
        chave=f"produtos/{sku_pai}/foto-2.jpg",
        url=f"https://cdn/{sku_pai}/foto-2.jpg",
        bytes=100,
    )
    estado.registrar_fotos((foto_selecionada, foto_nao_usada), (foto_selecionada.url,))
    estado.registrar_tentativa(
        {
            "agente": "dummy",
            "usage": {
                "input_tokens": 0,
                "output_tokens": 0,
                "cache_read_tokens": 0,
                "cache_write_tokens": 0,
            },
        }
    )
    estado.registrar_textos(
        {
            "titulo": f"Produto {sku_pai}",
            "descricao_html": "<h2>x</h2>",
            "seo_tag_title": "t",
            "seo_tag_description": "m",
        }
    )
    estado.marcar_pronto()
    return estado


def _estado_reprovado_validacao(sku_pai: str) -> EstadoProduto:
    produto = _produto(sku_pai)
    resultado = ResultadoValidacao(
        problemas=(ProblemaValidacao(sku_pai, "cor", "cor fora da lista mestre"),), avisos=()
    )
    return EstadoProduto.registrar_validacao(sku_pai, produto, "hash", resultado)


def _resumo(estados: list[EstadoProduto]) -> ResumoLote:
    contagens = dict.fromkeys(StatusProduto, 0)
    for estado in estados:
        contagens[estado.status] += 1
    return ResumoLote(
        contagem_por_status=contagens,
        custo_usd_total=Decimal("0"),
        duracao_segundos=1.5,
        caminho_planilha=Path("lotes/lote-1/saida/lote-1.xlsx"),
        caminho_relatorio_md=Path("lotes/lote-1/relatorio.md"),
        caminho_relatorio_json=Path("lotes/lote-1/relatorio.json"),
    )


def test_relatorio_cobre_todas_as_secoes() -> None:
    estados = [_estado_pronto("3254002"), _estado_reprovado_validacao("3254030")]
    resumo = _resumo(estados)

    relatorio = GeradorRelatorio().gerar(estados, resumo)

    assert relatorio.dados["resumo"]["total_produtos"] == 2
    assert relatorio.dados["resumo"]["contagem_por_status"]["pronto"] == 1
    assert relatorio.dados["resumo"]["contagem_por_status"]["reprovado-validacao"] == 1
    assert relatorio.dados["reprovados"][0]["sku_pai"] == "3254030"
    assert "cor fora da lista mestre" in relatorio.dados["reprovados"][0]["motivos"][0]
    assert relatorio.dados["custo_por_agente"]["dummy"]["tentativas"] == 1
    assert relatorio.dados["categorias_usadas"] == ["Linha Baby > Menino > Conjunto"]
    assert relatorio.dados["fotos"]["publicadas"] == 2
    assert relatorio.dados["fotos"]["nao_usadas"] == [{"sku_pai": "3254002", "nome": "foto-2.jpg"}]

    assert "# Relatório do lote" in relatorio.markdown
    assert "3254030" in relatorio.markdown
    assert "Produto 3254002" in relatorio.markdown
