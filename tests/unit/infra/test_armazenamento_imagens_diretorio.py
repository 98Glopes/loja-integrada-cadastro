from __future__ import annotations

from pathlib import Path

from loja_integrada_cadastro.infra.armazenamento_imagens_diretorio import (
    ArmazenamentoImagensDiretorio,
)


def test_publicar_grava_arquivo_e_devolve_url_file(tmp_path: Path) -> None:
    armazenamento = ArmazenamentoImagensDiretorio(tmp_path)

    url = armazenamento.publicar("produtos/SKU1/foto-1.jpg", b"conteudo-jpeg")

    assert url.startswith("file://")
    destino = tmp_path / "produtos" / "SKU1" / "foto-1.jpg"
    assert destino.is_file()
    assert destino.read_bytes() == b"conteudo-jpeg"


def test_existe_confirma_arquivo_publicado(tmp_path: Path) -> None:
    armazenamento = ArmazenamentoImagensDiretorio(tmp_path)
    url = armazenamento.publicar("produtos/SKU1/foto-1.jpg", b"conteudo-jpeg")

    assert armazenamento.existe(url) is True


def test_existe_e_falso_para_url_nunca_publicada(tmp_path: Path) -> None:
    armazenamento = ArmazenamentoImagensDiretorio(tmp_path)
    url_inexistente = (tmp_path / "produtos" / "SKU1" / "nunca.jpg").resolve().as_uri()

    assert armazenamento.existe(url_inexistente) is False


def test_publicar_a_mesma_chave_sobrescreve(tmp_path: Path) -> None:
    armazenamento = ArmazenamentoImagensDiretorio(tmp_path)
    armazenamento.publicar("produtos/SKU1/foto-1.jpg", b"versao-1")

    armazenamento.publicar("produtos/SKU1/foto-1.jpg", b"versao-2")

    destino = tmp_path / "produtos" / "SKU1" / "foto-1.jpg"
    assert destino.read_bytes() == b"versao-2"
