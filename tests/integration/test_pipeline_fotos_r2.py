from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest

from loja_integrada_cadastro.config.configuracao import Configuracao
from loja_integrada_cadastro.infra.armazenamento_imagens_r2 import ArmazenamentoImagensR2
from loja_integrada_cadastro.infra.catalogo_fotos_diretorio import CatalogoFotosDiretorio
from loja_integrada_cadastro.infra.processador_imagem_pillow import ProcessadorImagemPillow
from loja_integrada_cadastro.models.estado_produto import EstadoProduto
from loja_integrada_cadastro.models.exceptions.erro_configuracao import ErroConfiguracao
from loja_integrada_cadastro.models.produto_entrada import ProdutoEntrada
from loja_integrada_cadastro.models.resultado_validacao import ResultadoValidacao
from loja_integrada_cadastro.models.status_produto import StatusProduto
from loja_integrada_cadastro.models.variacao_entrada import VariacaoEntrada
from loja_integrada_cadastro.services.pipeline_fotos import PipelineFotos

RAIZ = Path(__file__).resolve().parents[2]
FOTOS_LOTE_PILOTO = RAIZ / "tests" / "fixtures" / "lote-piloto" / "fotos"
LADO_MAX_PX = 1600
TAMANHO_MAX_KB = 500


def _configuracao() -> Configuracao:
    configuracao = Configuracao.do_ambiente()
    try:
        configuracao.exigir_r2()
    except ErroConfiguracao as erro:
        pytest.skip(f"R2 não configurado neste ambiente ({erro})")
    return configuracao


def _produto(sku_pai: str, cores: list[str]) -> ProdutoEntrada:
    return ProdutoEntrada(
        sku_pai=sku_pai,
        marca="Kiki",
        nome_fornecedor="Produto do lote piloto",
        tipo_peca="Conjunto",
        categoria=("Linha Baby (P ao XG)", "Menino", "Conjunto"),
        composicao="100% algodão",
        detalhes="Fixture do lote piloto (task 08)",
        colecao=None,
        faixa_tamanho="P ao G",
        variacoes=tuple(
            VariacaoEntrada(
                cor=cor, tamanho="P", gtin="7891234567895", preco=Decimal("119.90"), estoque=10
            )
            for cor in cores
        ),
    )


@pytest.mark.integration
def test_pipeline_sobre_o_lote_piloto_deixa_urls_https_acessiveis() -> None:
    """Critério de aceite da task 08: fotos do lote piloto ficam com URL https:// que responde 200.

    Não apaga os objetos publicados ao final — a regra de lifecycle de 7 dias do bucket R2
    cuida disso (decisão registrada em `docs/specs/tasks/08-publicacao-r2.md`).
    """
    configuracao = _configuracao()
    assert configuracao.r2_bucket is not None
    assert configuracao.r2_account_id is not None
    assert configuracao.r2_access_key_id is not None
    assert configuracao.r2_secret_access_key is not None
    assert configuracao.r2_url_publica is not None

    catalogo = CatalogoFotosDiretorio(FOTOS_LOTE_PILOTO)
    armazenamento = ArmazenamentoImagensR2(
        bucket=configuracao.r2_bucket,
        account_id=configuracao.r2_account_id,
        access_key_id=configuracao.r2_access_key_id,
        secret_access_key=configuracao.r2_secret_access_key,
        url_publica=configuracao.r2_url_publica,
    )
    pipeline = PipelineFotos(
        catalogo=catalogo,
        processador=ProcessadorImagemPillow(LADO_MAX_PX, TAMANHO_MAX_KB),
        armazenamento=armazenamento,
    )

    skus_pai = sorted(item.name for item in FOTOS_LOTE_PILOTO.iterdir() if item.is_dir())
    assert skus_pai, f"nenhum sku encontrado em {FOTOS_LOTE_PILOTO}"

    todas_as_fotos = []
    for sku_pai in skus_pai:
        cores = catalogo.cores_disponiveis(sku_pai)
        produto = _produto(sku_pai, cores)
        estado = EstadoProduto.registrar_validacao(
            sku_pai, produto, "hash-1", ResultadoValidacao(problemas=(), avisos=())
        )

        fotos = pipeline.processar(produto, estado)

        assert estado.status is StatusProduto.FOTOS_PUBLICADAS
        todas_as_fotos.extend(fotos)

    assert todas_as_fotos
    for foto in todas_as_fotos:
        assert foto.url is not None
        assert foto.url.startswith(f"{configuracao.r2_url_publica.rstrip('/')}/")
        assert armazenamento.existe(foto.url) is True
