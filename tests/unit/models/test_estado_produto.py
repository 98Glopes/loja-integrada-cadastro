from collections.abc import Callable
from decimal import Decimal

import pytest

from loja_integrada_cadastro.models.estado_produto import EstadoProduto
from loja_integrada_cadastro.models.exceptions.erro_transicao_estado_invalida import (
    ErroTransicaoEstadoInvalida,
)
from loja_integrada_cadastro.models.produto_entrada import ProdutoEntrada
from loja_integrada_cadastro.models.resultado_validacao import (
    ProblemaValidacao,
    ResultadoValidacao,
)
from loja_integrada_cadastro.models.status_produto import StatusProduto
from loja_integrada_cadastro.models.variacao_entrada import VariacaoEntrada

_APROVADO = ResultadoValidacao(problemas=(), avisos=())
_REPROVADO = ResultadoValidacao(
    problemas=(ProblemaValidacao("3254002", "cor", "fora da lista mestre"),), avisos=()
)


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


def _validado() -> EstadoProduto:
    return EstadoProduto.registrar_validacao("3254002", _entrada(), "hash-1", _APROVADO)


def _fotos_publicadas() -> EstadoProduto:
    estado = _validado()
    estado.registrar_fotos(fotos=({"cor": "Beige", "nome": "foto-1.jpg"},), imagens_pai=("url-1",))
    return estado


def _textos_gerados() -> EstadoProduto:
    estado = _fotos_publicadas()
    estado.registrar_textos({"titulo": "Conjunto Kiki", "descricao_html": "<h2>x</h2>"})
    return estado


class TestRegistrarValidacao:
    def test_aprovado_fica_validado(self) -> None:
        estado = EstadoProduto.registrar_validacao("3254002", _entrada(), "hash-1", _APROVADO)

        assert estado.status is StatusProduto.VALIDADO
        assert estado.validacao is _APROVADO

    def test_reprovado_fica_reprovado_validacao(self) -> None:
        estado = EstadoProduto.registrar_validacao("3254002", _entrada(), "hash-1", _REPROVADO)

        assert estado.status is StatusProduto.REPROVADO_VALIDACAO


class TestRegistrarFotos:
    @pytest.mark.parametrize(
        "estado_inicial", [_validado, lambda: _erro_fotos()], ids=["validado", "erro-fotos"]
    )
    def test_transicoes_validas(self, estado_inicial: Callable[[], EstadoProduto]) -> None:
        estado = estado_inicial()

        estado.registrar_fotos(fotos=({"cor": "Beige"},), imagens_pai=("url-1",))

        assert estado.status is StatusProduto.FOTOS_PUBLICADAS
        assert estado.fotos == ({"cor": "Beige"},)
        assert estado.imagens_pai == ("url-1",)

    def test_transicao_invalida_a_partir_de_reprovado_validacao(self) -> None:
        estado = EstadoProduto.registrar_validacao("3254002", _entrada(), "hash-1", _REPROVADO)

        with pytest.raises(ErroTransicaoEstadoInvalida) as excecao:
            estado.registrar_fotos(fotos=(), imagens_pai=())

        assert excecao.value.sku_pai == "3254002"
        assert excecao.value.status_atual is StatusProduto.REPROVADO_VALIDACAO
        assert excecao.value.metodo == "registrar_fotos"


class TestRegistrarErroFotos:
    def test_a_partir_de_validado(self) -> None:
        estado = _validado()

        estado.registrar_erro_fotos()

        assert estado.status is StatusProduto.ERRO_FOTOS

    def test_transicao_invalida_a_partir_de_fotos_publicadas(self) -> None:
        estado = _fotos_publicadas()

        with pytest.raises(ErroTransicaoEstadoInvalida):
            estado.registrar_erro_fotos()


class TestEtapaTextos:
    @pytest.mark.parametrize(
        "estado_inicial",
        [_fotos_publicadas, lambda: _erro_llm()],
        ids=["fotos-publicadas", "erro-llm"],
    )
    def test_registrar_textos_valido(self, estado_inicial: Callable[[], EstadoProduto]) -> None:
        estado = estado_inicial()

        estado.registrar_textos({"titulo": "Conjunto Kiki"})

        assert estado.status is StatusProduto.TEXTOS_GERADOS
        assert estado.textos == {"titulo": "Conjunto Kiki"}

    @pytest.mark.parametrize(
        "estado_inicial",
        [_fotos_publicadas, lambda: _erro_llm()],
        ids=["fotos-publicadas", "erro-llm"],
    )
    def test_registrar_erro_llm_valido(self, estado_inicial: Callable[[], EstadoProduto]) -> None:
        estado = estado_inicial()

        estado.registrar_erro_llm()

        assert estado.status is StatusProduto.ERRO_LLM

    @pytest.mark.parametrize(
        "estado_inicial",
        [_fotos_publicadas, lambda: _erro_llm()],
        ids=["fotos-publicadas", "erro-llm"],
    )
    def test_reprovar_qa_valido(self, estado_inicial: Callable[[], EstadoProduto]) -> None:
        estado = estado_inicial()

        estado.reprovar_qa()

        assert estado.status is StatusProduto.REPROVADO_QA

    def test_registrar_tentativa_nao_muda_status_e_acumula_custo(self) -> None:
        estado = _fotos_publicadas()

        estado.registrar_tentativa({"agente": "copywriter", "tentativa": 1}, Decimal("0.10"))
        estado.registrar_tentativa({"agente": "seo", "tentativa": 1}, Decimal("0.05"))

        assert estado.status is StatusProduto.FOTOS_PUBLICADAS
        assert len(estado.tentativas) == 2
        assert estado.custo_usd_estimado == Decimal("0.15")

    def test_registrar_textos_invalido_a_partir_de_validado(self) -> None:
        estado = _validado()

        with pytest.raises(ErroTransicaoEstadoInvalida):
            estado.registrar_textos({"titulo": "x"})


class TestMarcarPronto:
    def test_a_partir_de_textos_gerados(self) -> None:
        estado = _textos_gerados()

        estado.marcar_pronto()

        assert estado.status is StatusProduto.PRONTO

    def test_invalido_a_partir_de_fotos_publicadas(self) -> None:
        estado = _fotos_publicadas()

        with pytest.raises(ErroTransicaoEstadoInvalida):
            estado.marcar_pronto()


class TestRegistrarVerificacao:
    def test_a_partir_de_pronto(self) -> None:
        estado = _textos_gerados()
        estado.marcar_pronto()

        estado.registrar_verificacao({"title_ok": True})

        assert estado.status is StatusProduto.PRONTO
        assert estado.verificacao == {"title_ok": True}

    def test_invalido_antes_de_pronto(self) -> None:
        estado = _textos_gerados()

        with pytest.raises(ErroTransicaoEstadoInvalida):
            estado.registrar_verificacao({"title_ok": True})


def test_atualizado_em_muda_a_cada_mutacao() -> None:
    estado = _validado()
    primeiro = estado.atualizado_em

    estado.registrar_fotos(fotos=(), imagens_pai=())

    assert estado.atualizado_em >= primeiro


def _erro_fotos() -> EstadoProduto:
    estado = _validado()
    estado.registrar_erro_fotos()
    return estado


def _erro_llm() -> EstadoProduto:
    estado = _fotos_publicadas()
    estado.registrar_erro_llm()
    return estado
