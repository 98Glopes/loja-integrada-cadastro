from decimal import Decimal

import pytest

from loja_integrada_cadastro.models.estado_produto import EstadoProduto
from loja_integrada_cadastro.models.produto_entrada import ProdutoEntrada
from loja_integrada_cadastro.models.resultado_validacao import (
    ProblemaValidacao,
    ResultadoValidacao,
)
from loja_integrada_cadastro.models.status_produto import StatusProduto
from loja_integrada_cadastro.models.variacao_entrada import VariacaoEntrada
from loja_integrada_cadastro.services.politica_reexecucao import (
    DecisaoReexecucao,
    EtapaLote,
    PoliticaReexecucao,
)

_HASH = "hash-1"
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


def _estado(status: StatusProduto) -> EstadoProduto:
    if status is StatusProduto.REPROVADO_VALIDACAO:
        return EstadoProduto.registrar_validacao("3254002", _entrada(), _HASH, _REPROVADO)

    estado = EstadoProduto.registrar_validacao("3254002", _entrada(), _HASH, _APROVADO)
    if status is StatusProduto.VALIDADO:
        return estado
    if status is StatusProduto.ERRO_FOTOS:
        estado.registrar_erro_fotos()
        return estado

    estado.registrar_fotos(fotos=(), imagens_pai=())
    if status is StatusProduto.FOTOS_PUBLICADAS:
        return estado
    if status is StatusProduto.ERRO_LLM:
        estado.registrar_erro_llm()
        return estado
    if status is StatusProduto.REPROVADO_QA:
        estado.reprovar_qa()
        return estado

    estado.registrar_textos({"titulo": "x"})
    if status is StatusProduto.TEXTOS_GERADOS:
        return estado

    estado.marcar_pronto()
    return estado


CASOS = [
    pytest.param(None, _HASH, False, False, DecisaoReexecucao.RECOMECAR, None, id="sem-estado"),
    pytest.param(
        StatusProduto.PRONTO,
        "hash-diferente",
        False,
        False,
        DecisaoReexecucao.RECOMECAR,
        None,
        id="hash-diferente-vence-tudo",
    ),
    pytest.param(
        StatusProduto.REPROVADO_VALIDACAO,
        _HASH,
        False,
        False,
        DecisaoReexecucao.RETOMAR,
        EtapaLote.VALIDAR,
        id="reprovado-validacao",
    ),
    pytest.param(
        StatusProduto.VALIDADO,
        _HASH,
        False,
        False,
        DecisaoReexecucao.RETOMAR,
        EtapaLote.FOTOS,
        id="validado",
    ),
    pytest.param(
        StatusProduto.ERRO_FOTOS,
        _HASH,
        False,
        False,
        DecisaoReexecucao.RETOMAR,
        EtapaLote.FOTOS,
        id="erro-fotos",
    ),
    pytest.param(
        StatusProduto.FOTOS_PUBLICADAS,
        _HASH,
        False,
        False,
        DecisaoReexecucao.RETOMAR,
        EtapaLote.TEXTOS,
        id="fotos-publicadas",
    ),
    pytest.param(
        StatusProduto.ERRO_LLM,
        _HASH,
        False,
        False,
        DecisaoReexecucao.RETOMAR,
        EtapaLote.TEXTOS,
        id="erro-llm",
    ),
    pytest.param(
        StatusProduto.REPROVADO_QA,
        _HASH,
        False,
        False,
        DecisaoReexecucao.RETOMAR,
        EtapaLote.TEXTOS,
        id="reprovado-qa",
    ),
    pytest.param(
        StatusProduto.TEXTOS_GERADOS,
        _HASH,
        False,
        False,
        DecisaoReexecucao.RETOMAR,
        EtapaLote.MONTAR,
        id="textos-gerados",
    ),
    pytest.param(
        StatusProduto.PRONTO,
        _HASH,
        False,
        False,
        DecisaoReexecucao.PULAR,
        None,
        id="pronto-sem-flags",
    ),
    pytest.param(
        StatusProduto.PRONTO,
        _HASH,
        True,
        False,
        DecisaoReexecucao.RETOMAR,
        EtapaLote.TEXTOS,
        id="pronto-refazer-textos",
    ),
    pytest.param(
        StatusProduto.PRONTO,
        _HASH,
        False,
        True,
        DecisaoReexecucao.RETOMAR,
        EtapaLote.FOTOS,
        id="pronto-refazer-fotos",
    ),
    pytest.param(
        StatusProduto.TEXTOS_GERADOS,
        _HASH,
        True,
        False,
        DecisaoReexecucao.RETOMAR,
        EtapaLote.TEXTOS,
        id="textos-gerados-refazer-textos",
    ),
    pytest.param(
        StatusProduto.FOTOS_PUBLICADAS,
        _HASH,
        False,
        True,
        DecisaoReexecucao.RETOMAR,
        EtapaLote.FOTOS,
        id="refazer-fotos-tem-prioridade-sobre-etapa-seguinte",
    ),
    pytest.param(
        StatusProduto.VALIDADO,
        _HASH,
        False,
        True,
        DecisaoReexecucao.RETOMAR,
        EtapaLote.FOTOS,
        id="refazer-fotos-sem-fotos-ainda-nao-muda-nada",
    ),
]


@pytest.mark.parametrize(
    ("status_anterior", "hash_atual", "refazer_textos", "refazer_fotos", "decisao", "a_partir_de"),
    CASOS,
)
def test_politica_reexecucao(
    status_anterior: StatusProduto | None,
    hash_atual: str,
    refazer_textos: bool,
    refazer_fotos: bool,
    decisao: DecisaoReexecucao,
    a_partir_de: EtapaLote | None,
) -> None:
    estado_anterior = _estado(status_anterior) if status_anterior is not None else None

    resultado = PoliticaReexecucao().decidir(
        estado_anterior, hash_atual, refazer_textos=refazer_textos, refazer_fotos=refazer_fotos
    )

    assert resultado.decisao is decisao
    assert resultado.a_partir_de is a_partir_de
