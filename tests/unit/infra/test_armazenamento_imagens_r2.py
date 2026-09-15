from __future__ import annotations

from unittest.mock import MagicMock

import httpx
import pytest
from botocore.exceptions import ClientError

from loja_integrada_cadastro.infra.armazenamento_imagens_r2 import ArmazenamentoImagensR2
from loja_integrada_cadastro.models.exceptions.erro_publicacao_imagem import (
    ErroPublicacaoImagem,
)


def _armazenamento(
    cliente: MagicMock | None = None,
) -> tuple[ArmazenamentoImagensR2, MagicMock]:
    cliente = cliente if cliente is not None else MagicMock()
    armazenamento = ArmazenamentoImagensR2(
        bucket="fotos",
        account_id="conta-123",
        access_key_id="chave",
        secret_access_key="segredo",
        url_publica="https://bucket.exemplo.com",
        cliente=cliente,
    )
    return armazenamento, cliente


class TestPublicar:
    def test_grava_com_content_type_e_cache_control_e_devolve_url(self) -> None:
        armazenamento, cliente = _armazenamento()

        url = armazenamento.publicar("produtos/SKU1/foto-1.jpg", b"conteudo-jpeg")

        assert url == "https://bucket.exemplo.com/produtos/SKU1/foto-1.jpg"
        cliente.put_object.assert_called_once_with(
            Bucket="fotos",
            Key="produtos/SKU1/foto-1.jpg",
            Body=b"conteudo-jpeg",
            ContentType="image/jpeg",
            CacheControl="public, max-age=31536000",
        )

    def test_url_publica_sem_barra_final_nao_duplica_barra(self) -> None:
        cliente = MagicMock()
        armazenamento = ArmazenamentoImagensR2(
            bucket="fotos",
            account_id="conta-123",
            access_key_id="chave",
            secret_access_key="segredo",
            url_publica="https://bucket.exemplo.com/",
            cliente=cliente,
        )

        url = armazenamento.publicar("produtos/SKU1/foto-1.jpg", b"conteudo-jpeg")

        assert url == "https://bucket.exemplo.com/produtos/SKU1/foto-1.jpg"

    def test_erro_do_boto_vira_erro_publicacao_imagem_com_a_chave(self) -> None:
        cliente = MagicMock()
        cliente.put_object.side_effect = ClientError(
            {"Error": {"Code": "500", "Message": "falhou"}}, "PutObject"
        )
        armazenamento, _ = _armazenamento(cliente)

        with pytest.raises(ErroPublicacaoImagem) as excinfo:
            armazenamento.publicar("produtos/SKU1/foto-1.jpg", b"conteudo-jpeg")

        assert excinfo.value.chave_ou_url == "produtos/SKU1/foto-1.jpg"


class TestExiste:
    def test_200_e_image_jpeg_e_verdadeiro(self, monkeypatch: pytest.MonkeyPatch) -> None:
        armazenamento, _ = _armazenamento()
        resposta = httpx.Response(200, headers={"content-type": "image/jpeg"})
        monkeypatch.setattr(httpx, "head", lambda url, timeout: resposta)

        assert armazenamento.existe("https://bucket.exemplo.com/produtos/SKU1/foto-1.jpg") is True

    def test_404_e_falso(self, monkeypatch: pytest.MonkeyPatch) -> None:
        armazenamento, _ = _armazenamento()
        resposta = httpx.Response(404)
        monkeypatch.setattr(httpx, "head", lambda url, timeout: resposta)

        assert armazenamento.existe("https://bucket.exemplo.com/produtos/SKU1/foto-1.jpg") is False

    def test_200_com_content_type_errado_e_falso(self, monkeypatch: pytest.MonkeyPatch) -> None:
        armazenamento, _ = _armazenamento()
        resposta = httpx.Response(200, headers={"content-type": "text/html"})
        monkeypatch.setattr(httpx, "head", lambda url, timeout: resposta)

        assert armazenamento.existe("https://bucket.exemplo.com/produtos/SKU1/foto-1.jpg") is False

    def test_falha_de_transporte_vira_erro_publicacao_imagem(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        armazenamento, _ = _armazenamento()

        def _falhar(url: str, timeout: float) -> httpx.Response:
            raise httpx.ConnectTimeout("timeout")

        monkeypatch.setattr(httpx, "head", _falhar)

        with pytest.raises(ErroPublicacaoImagem) as excinfo:
            armazenamento.existe("https://bucket.exemplo.com/produtos/SKU1/foto-1.jpg")

        assert excinfo.value.chave_ou_url == "https://bucket.exemplo.com/produtos/SKU1/foto-1.jpg"
