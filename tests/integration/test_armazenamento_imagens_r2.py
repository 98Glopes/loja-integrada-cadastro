from __future__ import annotations

import io
import uuid
from collections.abc import Iterator

import boto3
import pytest
from PIL import Image

from loja_integrada_cadastro.config.configuracao import Configuracao
from loja_integrada_cadastro.infra.armazenamento_imagens_r2 import ArmazenamentoImagensR2
from loja_integrada_cadastro.models.exceptions.erro_configuracao import ErroConfiguracao


def _configuracao() -> Configuracao:
    configuracao = Configuracao.do_ambiente()
    try:
        configuracao.exigir_r2()
    except ErroConfiguracao as erro:
        pytest.skip(f"R2 não configurado neste ambiente ({erro})")
    return configuracao


def _jpeg_pequeno() -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (8, 8), color="red").save(buffer, format="JPEG")
    return buffer.getvalue()


@pytest.fixture
def chave_de_teste() -> Iterator[str]:
    """Sobe em `testes/<uuid>.jpg`; apaga o objeto direto no bucket ao final do teste."""
    chave = f"testes/{uuid.uuid4()}.jpg"
    yield chave
    configuracao = Configuracao.do_ambiente()
    if configuracao.r2_bucket is None or configuracao.r2_account_id is None:
        return
    cliente = boto3.client(
        "s3",
        endpoint_url=f"https://{configuracao.r2_account_id}.r2.cloudflarestorage.com",
        aws_access_key_id=configuracao.r2_access_key_id,
        aws_secret_access_key=configuracao.r2_secret_access_key,
        region_name="auto",
    )
    cliente.delete_object(Bucket=configuracao.r2_bucket, Key=chave)


@pytest.mark.integration
def test_publica_e_confirma_acessibilidade_no_bucket_real(chave_de_teste: str) -> None:
    configuracao = _configuracao()
    assert configuracao.r2_bucket is not None
    assert configuracao.r2_account_id is not None
    assert configuracao.r2_access_key_id is not None
    assert configuracao.r2_secret_access_key is not None
    assert configuracao.r2_url_publica is not None

    armazenamento = ArmazenamentoImagensR2(
        bucket=configuracao.r2_bucket,
        account_id=configuracao.r2_account_id,
        access_key_id=configuracao.r2_access_key_id,
        secret_access_key=configuracao.r2_secret_access_key,
        url_publica=configuracao.r2_url_publica,
    )

    url = armazenamento.publicar(chave_de_teste, _jpeg_pequeno())

    assert url == f"{configuracao.r2_url_publica.rstrip('/')}/{chave_de_teste}"
    assert armazenamento.existe(url) is True
