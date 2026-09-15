from __future__ import annotations

from decimal import Decimal

from loja_integrada_cadastro.models.estado_produto import EstadoProduto
from loja_integrada_cadastro.models.padroes_fisicos import PadroesFisicos
from loja_integrada_cadastro.models.produto_entrada import ProdutoEntrada
from loja_integrada_cadastro.models.resultado_validacao import ResultadoValidacao
from loja_integrada_cadastro.models.status_produto import StatusProduto
from loja_integrada_cadastro.models.variacao_entrada import VariacaoEntrada
from loja_integrada_cadastro.services.montador_planilha import MontadorPlanilha

_APROVADO = ResultadoValidacao(problemas=(), avisos=())
_TEXTOS = {
    "titulo": "Conjunto Baby Malha e Moletom Kiki",
    "descricao_html": "<h2>Conjunto</h2><p>Descrição.</p>",
    "seo_tag_title": "Conjunto Baby Malha e Moletom",
    "seo_tag_description": "Compre o Conjunto Baby Malha e Moletom Kiki na Kmilaa Modas.",
}
_PADROES = PadroesFisicos(
    peso_kg=Decimal("0.1"),
    altura_cm=Decimal("4"),
    largura_cm=Decimal("22"),
    comprimento_cm=Decimal("22"),
)
_IMAGENS_PAI = ("https://cdn.exemplo.com/beige.jpg", "https://cdn.exemplo.com/rosa.jpg")


def _produto_com_grade(
    cores: tuple[str, ...], tamanhos: tuple[str, ...], sku_pai: str = "3254002"
) -> ProdutoEntrada:
    variacoes = tuple(
        VariacaoEntrada(
            cor=cor,
            tamanho=tamanho,
            gtin=f"789000000{indice:04d}",
            preco=Decimal("119.90") + Decimal(indice),
            estoque=10 + indice,
        )
        for indice, (cor, tamanho) in enumerate(
            (cor, tamanho) for cor in cores for tamanho in tamanhos
        )
    )
    return ProdutoEntrada(
        sku_pai=sku_pai,
        marca="Kiki",
        nome_fornecedor="Conjunto Baby Malha e Moletom",
        tipo_peca="Conjunto",
        categoria=("Linha Baby (P ao XG)", "Menino", "Conjunto"),
        composicao="100% algodão",
        detalhes="Botões na gola",
        colecao=None,
        faixa_tamanho="P ao G",
        variacoes=variacoes,
    )


def _estado_fotos_publicadas(produto: ProdutoEntrada) -> EstadoProduto:
    estado = EstadoProduto.registrar_validacao(produto.sku_pai, produto, "hash-1", _APROVADO)
    estado.registrar_fotos(fotos=(), imagens_pai=_IMAGENS_PAI)
    return estado


def _estado_textos_gerados(produto: ProdutoEntrada) -> EstadoProduto:
    estado = _estado_fotos_publicadas(produto)
    estado.registrar_textos(_TEXTOS)
    return estado


class TestMontar:
    def test_produto_com_duas_cores_e_tres_tamanhos_gera_um_pai_e_seis_filhas(self) -> None:
        produto = _produto_com_grade(("Beige", "Rosa"), ("P", "M", "G"))
        estado = _estado_textos_gerados(produto)
        montador = MontadorPlanilha(_PADROES, ativo="S")

        linhas = montador.montar(estado)

        assert len(linhas) == 7
        assert linhas[0].tipo == "com-variacao"
        assert all(linha.tipo == "variacao" for linha in linhas[1:])

    def test_linha_pai_tem_os_valores_esperados(self) -> None:
        produto = _produto_com_grade(("Beige", "Rosa"), ("P", "M", "G"))
        estado = _estado_textos_gerados(produto)
        montador = MontadorPlanilha(_PADROES, ativo="S")

        pai = montador.montar(estado)[0]

        assert pai.valores == {
            "tipo": "com-variacao",
            "sku": "3254002",
            "ativo": "S",
            "usado": "N",
            "destaque": "N",
            "nome": _TEXTOS["titulo"],
            "seo-tag-title": _TEXTOS["seo_tag_title"],
            "seo-tag-description": _TEXTOS["seo_tag_description"],
            "descricao-completa": _TEXTOS["descricao_html"],
            "preco-sob-consulta": "N",
            "marca": "Kiki",
            "categoria-nome-nivel-1": "Linha Baby (P ao XG)",
            "categoria-nome-nivel-2": "Menino",
            "categoria-nome-nivel-3": "Conjunto",
            "imagem-1": _IMAGENS_PAI[0],
            "imagem-2": _IMAGENS_PAI[1],
        }

    def test_linha_filha_tem_os_valores_esperados_incluindo_gtin(self) -> None:
        produto = _produto_com_grade(("Beige",), ("P",))
        variacao = produto.variacoes[0]
        estado = _estado_textos_gerados(produto)
        montador = MontadorPlanilha(_PADROES, ativo="S")

        filha = montador.montar(estado)[1]

        assert filha.valores == {
            "tipo": "variacao",
            "sku-pai": "3254002",
            "sku": "3254002-beige-p",
            "ativo": "S",
            "usado": "N",
            "destaque": "N",
            "gtin": variacao.gtin,
            "estoque-gerenciado": "S",
            "estoque-quantidade": variacao.estoque,
            "estoque-situacao-em-estoque": "imediata",
            "estoque-situacao-sem-estoque": "indisponivel",
            "preco-sob-consulta": "N",
            "preco-custo": 0.0,
            "preco-cheio": float(variacao.preco),
            "preco-promocional": 0.0,
            "peso-em-kg": 0.1,
            "altura-em-cm": 4.0,
            "largura-em-cm": 22.0,
            "comprimento-em-cm": 22.0,
            "grade-produto-com-uma-cor": "Beige",
            "grade-tamanho-infantil": "P",
        }


class TestMontarLote:
    def test_filtra_so_pronto_por_padrao(self) -> None:
        produto_pronto = _produto_com_grade(("Beige",), ("P",))
        estado_pronto = _estado_textos_gerados(produto_pronto)
        estado_pronto.marcar_pronto()

        produto_em_textos = _produto_com_grade(("Rosa",), ("M",), sku_pai="3254010")
        estado_em_textos = _estado_textos_gerados(produto_em_textos)

        montador = MontadorPlanilha(_PADROES, ativo="S")

        linhas = montador.montar_lote([estado_pronto, estado_em_textos])

        assert {linha.valores.get("sku-pai") or linha.valores.get("sku") for linha in linhas} == {
            "3254002"
        }
        assert estado_em_textos.status is StatusProduto.TEXTOS_GERADOS

    def test_incluir_reprovados_nao_adiciona_linha_quando_texto_nao_foi_guardado(self) -> None:
        produto = _produto_com_grade(("Beige",), ("P",))
        estado = _estado_fotos_publicadas(produto)
        estado.reprovar_qa()
        assert estado.status is StatusProduto.REPROVADO_QA
        assert estado.textos is None  # gap conhecido: task 16 vai preencher isso

        montador = MontadorPlanilha(_PADROES, ativo="S")

        linhas = montador.montar_lote([estado], incluir_reprovados=True)

        assert linhas == []
