from __future__ import annotations

import itertools
import shutil
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
FOTOS_POC = RAIZ / "poc" / "fotos_input"
LADO_MAX_PX = 1600
TAMANHO_MAX_KB = 500


def _configuracao() -> Configuracao:
    configuracao = Configuracao.do_ambiente()
    try:
        configuracao.exigir_r2()
    except ErroConfiguracao as erro:
        pytest.skip(f"R2 não configurado neste ambiente ({erro})")
    return configuracao


def _copiar_estrutura_com_fotos_reais(destino: Path) -> Path:
    """Espelha `<sku-pai>/<cor>/` da fixture do lote piloto, mas com fotos reais da POC.

    Os arquivos da fixture (`tests/fixtures/lote-piloto/fotos/`) são propositalmente JPEGs
    "stub" de 22 bytes (task 05, `scripts/gerar_fixture_lote_piloto.py`) — servem só para o
    catálogo/validador conferirem extensão e existência, não para decodificação real. Este
    teste precisa de fotos que o Pillow consiga abrir de verdade, então reaproveita as fotos
    reais da POC (`poc/fotos_input/`, mesmas 4 fotos usadas por `test_pipeline_fotos_poc.py`).
    """
    fotos_poc = sorted(FOTOS_POC.glob("*.jpg"))
    assert fotos_poc, f"nenhuma foto real encontrada em {FOTOS_POC}"
    fotos_ciclicas = itertools.cycle(fotos_poc)

    raiz_fotos = destino / "fotos"
    for sku_dir in sorted(FOTOS_LOTE_PILOTO.iterdir()):
        if not sku_dir.is_dir():
            continue
        for cor_dir in sorted(sku_dir.iterdir()):
            if not cor_dir.is_dir():
                continue
            pasta = raiz_fotos / sku_dir.name / cor_dir.name
            pasta.mkdir(parents=True, exist_ok=True)
            for arquivo_stub in sorted(cor_dir.iterdir()):
                shutil.copyfile(next(fotos_ciclicas), pasta / arquivo_stub.name)
    return raiz_fotos


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
def test_pipeline_sobre_o_lote_piloto_deixa_urls_https_acessiveis(tmp_path: Path) -> None:
    """Critério de aceite da task 08: fotos do lote piloto ficam com URL https:// que responde 200.

    Usa a mesma estrutura `<sku-pai>/<cor>/` da fixture do lote piloto, mas com fotos reais da
    POC no lugar dos JPEGs "stub" da fixture (ver `_copiar_estrutura_com_fotos_reais`) — o
    `ProcessadorImagemPillow` real precisa de bytes de imagem decodificáveis.

    Não apaga os objetos publicados ao final — a regra de lifecycle de 7 dias do bucket R2
    cuida disso (decisão registrada em `docs/specs/tasks/08-publicacao-r2.md`).
    """
    configuracao = _configuracao()
    assert configuracao.r2_bucket is not None
    assert configuracao.r2_account_id is not None
    assert configuracao.r2_access_key_id is not None
    assert configuracao.r2_secret_access_key is not None
    assert configuracao.r2_url_publica is not None

    fotos_lote_piloto = _copiar_estrutura_com_fotos_reais(tmp_path)
    catalogo = CatalogoFotosDiretorio(fotos_lote_piloto)
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

    skus_pai = sorted(item.name for item in fotos_lote_piloto.iterdir() if item.is_dir())
    assert skus_pai, f"nenhum sku encontrado em {fotos_lote_piloto}"

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
