from __future__ import annotations

from typing import TYPE_CHECKING

import boto3
import httpx
from botocore.exceptions import BotoCoreError, ClientError

from loja_integrada_cadastro.models.exceptions.erro_publicacao_imagem import (
    ErroPublicacaoImagem,
)

if TYPE_CHECKING:
    from mypy_boto3_s3 import S3Client

_CONTENT_TYPE_JPEG = "image/jpeg"
_CACHE_CONTROL = "public, max-age=31536000"
_TIMEOUT_HEAD_SEGUNDOS = 10.0


class ArmazenamentoImagensR2:
    """Publica o JPEG final no Cloudflare R2 e confere disponibilidade via HEAD.

    Implementa o port `ArmazenamentoImagens` (`docs/ARQUITETURA.md` §5.3/§10, task 08). O bucket
    é sempre R2 (S3-compatível): `endpoint_url = https://<account_id>.r2.cloudflarestorage.com`,
    região `auto`.
    """

    def __init__(
        self,
        bucket: str,
        account_id: str,
        access_key_id: str,
        secret_access_key: str,
        url_publica: str,
        cliente: S3Client | None = None,
    ) -> None:
        self._bucket = bucket
        self._url_publica = url_publica.rstrip("/")
        self._cliente = cliente or boto3.client(
            "s3",
            endpoint_url=f"https://{account_id}.r2.cloudflarestorage.com",
            aws_access_key_id=access_key_id,
            aws_secret_access_key=secret_access_key,
            region_name="auto",
        )

    def publicar(self, chave: str, dados: bytes) -> str:
        """Grava/sobrescreve `dados` em `chave` no bucket; devolve a URL pública resultante."""
        try:
            self._cliente.put_object(
                Bucket=self._bucket,
                Key=chave,
                Body=dados,
                ContentType=_CONTENT_TYPE_JPEG,
                CacheControl=_CACHE_CONTROL,
            )
        except (BotoCoreError, ClientError) as erro:
            raise ErroPublicacaoImagem(chave, str(erro)) from erro
        return f"{self._url_publica}/{chave}"

    def existe(self, url: str) -> bool:
        """Confirma com um HEAD real que `url` responde 200 com `image/jpeg`.

        Uma resposta HTTP obtida normalmente (mesmo que não seja 200) só resulta em `False` —
        significa que a foto ainda não está pronta. Uma falha de transporte (timeout, conexão
        recusada etc.) é um problema de infraestrutura e vira `ErroPublicacaoImagem`.
        """
        try:
            resposta = httpx.head(url, timeout=_TIMEOUT_HEAD_SEGUNDOS)
        except httpx.HTTPError as erro:
            raise ErroPublicacaoImagem(url, str(erro)) from erro
        content_type = resposta.headers.get("content-type", "")
        return resposta.status_code == 200 and content_type.startswith(_CONTENT_TYPE_JPEG)
