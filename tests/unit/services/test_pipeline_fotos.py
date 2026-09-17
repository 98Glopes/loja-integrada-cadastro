from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest

from loja_integrada_cadastro.models.estado_produto import EstadoProduto
from loja_integrada_cadastro.models.exceptions.erro_processamento_imagem import (
    ErroProcessamentoImagem,
)
from loja_integrada_cadastro.models.exceptions.erro_publicacao_imagem import (
    ErroPublicacaoImagem,
)
from loja_integrada_cadastro.models.produto_entrada import ProdutoEntrada
from loja_integrada_cadastro.models.resultado_validacao import ResultadoValidacao
from loja_integrada_cadastro.models.status_produto import StatusProduto
from loja_integrada_cadastro.models.variacao_entrada import VariacaoEntrada
from loja_integrada_cadastro.services.pipeline_fotos import PipelineFotos

_APROVADO = ResultadoValidacao(problemas=(), avisos=())


class _CatalogoFotosFake:
    """Fake do port `CatalogoFotos`: lista em memória, sem tocar o disco."""

    def __init__(self, arquivos: list[Path]) -> None:
        self._arquivos = arquivos

    def listar(self, sku_pai: str) -> list[Path]:
        return self._arquivos


class _ProcessadorImagemFake:
    """Fake do port `ProcessadorImagem`: devolve bytes fixos; pode falhar num arquivo dado."""

    def __init__(self, falhar_em: Path | None = None) -> None:
        self._falhar_em = falhar_em

    def preparar(self, origem: Path) -> bytes:
        if origem == self._falhar_em:
            raise ErroProcessamentoImagem(origem, "arquivo corrompido (fake)")
        return f"jpeg-de-{origem.name}".encode()


class _ArmazenamentoImagensEmMemoria:
    """Fake do port `ArmazenamentoImagens`: dict em memória, sem tocar o disco.

    `falhar_publicar_em`/`inacessivel_em` simulam, respectivamente, `publicar()` levantando
    `ErroPublicacaoImagem` e `existe()` devolvendo `False` para uma chave específica.
    """

    def __init__(
        self,
        falhar_publicar_em: str | None = None,
        inacessivel_em: str | None = None,
    ) -> None:
        self.publicados: dict[str, bytes] = {}
        self._falhar_publicar_em = falhar_publicar_em
        self._inacessivel_em = inacessivel_em

    def publicar(self, chave: str, dados: bytes) -> str:
        if chave == self._falhar_publicar_em:
            raise ErroPublicacaoImagem(chave, "falha de rede (fake)")
        self.publicados[chave] = dados
        return f"file:///fake/{chave}"

    def existe(self, url: str) -> bool:
        chave = url.removeprefix("file:///fake/")
        if chave == self._inacessivel_em:
            return False
        return chave in self.publicados


def _produto(cores: tuple[str, ...] = ("Beige",)) -> ProdutoEntrada:
    return ProdutoEntrada(
        sku_pai="3254002",
        marca="Kiki",
        nome_fornecedor="Conjunto Baby Malha e Moletom",
        tipo_peca="Conjunto",
        categoria=("Linha Baby (P ao XG)", "Menino", "Conjunto"),
        composicao="100% algodão",
        detalhes="Botões na gola",
        colecao=None,
        faixa_tamanho="P ao G",
        variacoes=tuple(
            VariacaoEntrada(
                cor=cor, tamanho="P", gtin="7891234567895", preco=Decimal("119.90"), estoque=10
            )
            for cor in cores
        ),
    )


def _estado(produto: ProdutoEntrada) -> EstadoProduto:
    return EstadoProduto.registrar_validacao(produto.sku_pai, produto, "hash-1", _APROVADO)


class TestProcessar:
    def test_caminho_feliz_nomeia_publica_e_registra_estado(self) -> None:
        produto = _produto()
        arquivos = [Path("fotos/3254002/a.jpg"), Path("fotos/3254002/b.jpg")]
        armazenamento = _ArmazenamentoImagensEmMemoria()
        pipeline = PipelineFotos(
            _CatalogoFotosFake(arquivos), _ProcessadorImagemFake(), armazenamento
        )
        estado = _estado(produto)

        fotos = pipeline.processar(produto, estado)

        assert [foto.nome for foto in fotos] == [
            "kiki-conjunto-baby-malha-e-moletom-1.jpg",
            "kiki-conjunto-baby-malha-e-moletom-2.jpg",
        ]
        assert len(armazenamento.publicados) == 2
        assert estado.status is StatusProduto.FOTOS_PUBLICADAS
        assert estado.fotos == tuple(fotos)
        assert len(estado.imagens_pai) == 2

    def test_sem_fotos_nao_quebra(self) -> None:
        produto = _produto()
        pipeline = PipelineFotos(
            _CatalogoFotosFake([]), _ProcessadorImagemFake(), _ArmazenamentoImagensEmMemoria()
        )
        estado = _estado(produto)

        fotos = pipeline.processar(produto, estado)

        assert fotos == []
        assert estado.status is StatusProduto.FOTOS_PUBLICADAS

    def test_falha_ao_processar_uma_foto_aborta_o_produto(self) -> None:
        produto = _produto()
        arquivo_com_falha = Path("fotos/3254002/b.jpg")
        arquivos = [Path("fotos/3254002/a.jpg"), arquivo_com_falha]
        pipeline = PipelineFotos(
            _CatalogoFotosFake(arquivos),
            _ProcessadorImagemFake(falhar_em=arquivo_com_falha),
            _ArmazenamentoImagensEmMemoria(),
        )
        estado = _estado(produto)

        with pytest.raises(ErroProcessamentoImagem):
            pipeline.processar(produto, estado)

        assert estado.status is StatusProduto.ERRO_FOTOS

    def test_falha_ao_publicar_aborta_o_produto(self) -> None:
        produto = _produto()
        chave = "produtos/3254002/kiki-conjunto-baby-malha-e-moletom-1.jpg"
        arquivos = [Path("fotos/3254002/a.jpg")]
        pipeline = PipelineFotos(
            _CatalogoFotosFake(arquivos),
            _ProcessadorImagemFake(),
            _ArmazenamentoImagensEmMemoria(falhar_publicar_em=chave),
        )
        estado = _estado(produto)

        with pytest.raises(ErroPublicacaoImagem):
            pipeline.processar(produto, estado)

        assert estado.status is StatusProduto.ERRO_FOTOS

    def test_foto_publicada_mas_inacessivel_aborta_o_produto(self) -> None:
        produto = _produto()
        chave = "produtos/3254002/kiki-conjunto-baby-malha-e-moletom-1.jpg"
        arquivos = [Path("fotos/3254002/a.jpg")]
        pipeline = PipelineFotos(
            _CatalogoFotosFake(arquivos),
            _ProcessadorImagemFake(),
            _ArmazenamentoImagensEmMemoria(inacessivel_em=chave),
        )
        estado = _estado(produto)

        with pytest.raises(ErroPublicacaoImagem):
            pipeline.processar(produto, estado)

        assert estado.status is StatusProduto.ERRO_FOTOS
