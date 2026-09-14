from __future__ import annotations

import shutil
from decimal import Decimal
from pathlib import Path

import pytest
from PIL import Image

from loja_integrada_cadastro.infra.armazenamento_imagens_diretorio import (
    ArmazenamentoImagensDiretorio,
)
from loja_integrada_cadastro.infra.processador_imagem_pillow import ProcessadorImagemPillow
from loja_integrada_cadastro.models.estado_produto import EstadoProduto
from loja_integrada_cadastro.models.produto_entrada import ProdutoEntrada
from loja_integrada_cadastro.models.resultado_validacao import ResultadoValidacao
from loja_integrada_cadastro.models.status_produto import StatusProduto
from loja_integrada_cadastro.models.variacao_entrada import VariacaoEntrada
from loja_integrada_cadastro.services.pipeline_fotos import PipelineFotos

LADO_MAX_PX = 1600
TAMANHO_MAX_KB = 500
RAIZ = Path(__file__).resolve().parents[2]
FOTOS_INPUT = RAIZ / "poc" / "fotos_input"


class _CatalogoFotosPoc:
    """Expõe `poc/fotos_input/` como uma única cor, para o critério de aceite da task 07."""

    def __init__(self, arquivos: list[Path]) -> None:
        self._arquivos = arquivos

    def listar(self, sku_pai: str) -> dict[str, list[Path]]:
        return {"Beige": self._arquivos}

    def cores_disponiveis(self, sku_pai: str) -> list[str]:
        return ["Beige"]


def _produto() -> ProdutoEntrada:
    return ProdutoEntrada(
        sku_pai="POC-001",
        marca="Kiki",
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


@pytest.mark.integration
def test_pipeline_sobre_fotos_reais_da_poc(tmp_path: Path) -> None:
    arquivos = sorted(FOTOS_INPUT.glob("*.jpg"))
    assert arquivos, f"nenhuma foto encontrada em {FOTOS_INPUT}"

    lote_dir = tmp_path / "lote"
    produto = _produto()
    estado = EstadoProduto.registrar_validacao(
        produto.sku_pai, produto, "hash-1", ResultadoValidacao(problemas=(), avisos=())
    )
    pipeline = PipelineFotos(
        catalogo=_CatalogoFotosPoc(arquivos),
        processador=ProcessadorImagemPillow(LADO_MAX_PX, TAMANHO_MAX_KB),
        armazenamento=ArmazenamentoImagensDiretorio(lote_dir / "fotos-processadas"),
    )

    fotos = pipeline.processar(produto, estado)

    assert len(fotos) == len(arquivos)
    assert estado.status is StatusProduto.FOTOS_PUBLICADAS
    for foto in fotos:
        assert foto.url is not None
        caminho = lote_dir / "fotos-processadas" / "produtos" / produto.sku_pai / foto.nome
        assert caminho.is_file()
        assert caminho.stat().st_size < TAMANHO_MAX_KB * 1024

        imagem = Image.open(caminho)
        assert max(imagem.size) <= LADO_MAX_PX
        assert not imagem.getexif()


@pytest.mark.integration
def test_processamento_encolhe_de_verdade_uma_foto_bruta(tmp_path: Path) -> None:
    """Confirma que o pipeline de fato processa (não só copia) uma foto real da POC."""
    origem = FOTOS_INPUT / "20250920_113424.jpg"
    destino = tmp_path / origem.name
    shutil.copyfile(origem, destino)

    processador = ProcessadorImagemPillow(LADO_MAX_PX, TAMANHO_MAX_KB)
    dados = processador.preparar(destino)

    assert len(dados) < origem.stat().st_size
    assert len(dados) < TAMANHO_MAX_KB * 1024
