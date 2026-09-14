from __future__ import annotations

import io
from pathlib import Path

from PIL import Image, ImageOps

try:
    import pillow_heif

    pillow_heif.register_heif_opener()  # type: ignore[attr-defined]
except ImportError:
    pass

from loja_integrada_cadastro.models.exceptions.erro_processamento_imagem import (
    ErroProcessamentoImagem,
)

_QUALIDADE_INICIAL = 85
_QUALIDADE_MINIMA = 60
_PASSO_QUALIDADE = 5
_LADO_REDUZIDO_PX = 1200


class ProcessadorImagemPillow:
    """Pillow (+ `pillow-heif` p/ HEIC): orientação, RGB, redimensionar, comprimir (§5.3).

    Se `pillow-heif` não estiver disponível no ambiente, arquivos `.heic` falham com
    `ErroProcessamentoImagem` ao serem abertos (mitigação documentada em `docs/ARQUITETURA.md`
    §14, risco #6: exigir JPG/PNG/WEBP nesse caso).
    """

    def __init__(self, lado_max_px: int, tamanho_max_kb: int) -> None:
        self._lado_max_px = lado_max_px
        self._tamanho_max_kb = tamanho_max_kb

    def preparar(self, origem: Path) -> bytes:
        try:
            with Image.open(origem) as bruta:
                corrigida = ImageOps.exif_transpose(bruta) or bruta
                imagem = corrigida.convert("RGB")

            imagem = self._redimensionar(imagem, self._lado_max_px)
            dados = self._comprimir(imagem, _QUALIDADE_INICIAL)
            if len(dados) >= self._tamanho_max_kb * 1024:
                reduzida = self._redimensionar(imagem, _LADO_REDUZIDO_PX)
                dados = self._comprimir(reduzida, _QUALIDADE_INICIAL)
        except (OSError, ValueError) as erro:  # boundary infra → domínio (docs/ARQUITETURA.md §10)
            raise ErroProcessamentoImagem(origem, str(erro)) from erro
        return dados

    @staticmethod
    def _redimensionar(imagem: Image.Image, lado_max_px: int) -> Image.Image:
        largura, altura = imagem.size
        maior = max(largura, altura)
        if maior <= lado_max_px:
            return imagem
        fator = lado_max_px / maior
        nova_largura = round(largura * fator)
        nova_altura = round(altura * fator)
        return imagem.resize((nova_largura, nova_altura), Image.Resampling.LANCZOS)

    def _comprimir(self, imagem: Image.Image, qualidade_inicial: int) -> bytes:
        qualidade = qualidade_inicial
        dados = self._salvar_jpeg(imagem, qualidade)
        while len(dados) >= self._tamanho_max_kb * 1024 and qualidade > _QUALIDADE_MINIMA:
            qualidade -= _PASSO_QUALIDADE
            dados = self._salvar_jpeg(imagem, qualidade)
        return dados

    @staticmethod
    def _salvar_jpeg(imagem: Image.Image, qualidade: int) -> bytes:
        buffer = io.BytesIO()
        imagem.save(buffer, format="JPEG", quality=qualidade, progressive=True, exif=b"")
        return buffer.getvalue()
