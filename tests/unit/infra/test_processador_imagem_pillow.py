from __future__ import annotations

import io
import random
from pathlib import Path

import pytest
from PIL import Image

from loja_integrada_cadastro.infra.processador_imagem_pillow import ProcessadorImagemPillow
from loja_integrada_cadastro.models.exceptions.erro_processamento_imagem import (
    ErroProcessamentoImagem,
)

try:
    import pillow_heif

    _HEIC_DISPONIVEL = True
except ImportError:
    _HEIC_DISPONIVEL = False

LADO_MAX_PX = 1600
TAMANHO_MAX_KB = 500


def _imagem_ruidosa(largura: int, altura: int) -> Image.Image:
    """Imagem com ruído aleatório: cor sólida comprimiria demais e não testaria o loop real."""
    aleatorio = random.Random(42)
    dados = bytes(aleatorio.randrange(256) for _ in range(largura * altura * 3))
    return Image.frombytes("RGB", (largura, altura), dados)


def _salvar_jpeg_com_orientacao(imagem: Image.Image, destino: Path, orientacao: int) -> None:
    exif = imagem.getexif()
    exif[0x0112] = orientacao  # tag Orientation
    imagem.save(destino, format="JPEG", exif=exif)


@pytest.fixture
def processador() -> ProcessadorImagemPillow:
    return ProcessadorImagemPillow(LADO_MAX_PX, TAMANHO_MAX_KB)


class TestPreparar:
    def test_jpeg_grande_fica_dentro_dos_limites_e_sem_exif(
        self, processador: ProcessadorImagemPillow, tmp_path: Path
    ) -> None:
        origem = tmp_path / "bruta.jpg"
        _salvar_jpeg_com_orientacao(_imagem_ruidosa(3000, 4000), origem, orientacao=6)

        dados = processador.preparar(origem)

        assert len(dados) < TAMANHO_MAX_KB * 1024
        resultado = Image.open(io.BytesIO(dados))
        assert max(resultado.size) <= LADO_MAX_PX
        assert resultado.format == "JPEG"
        assert not resultado.getexif()

    def test_png_com_canal_alfa_converte_para_rgb(
        self, processador: ProcessadorImagemPillow, tmp_path: Path
    ) -> None:
        origem = tmp_path / "bruta.png"
        imagem = _imagem_ruidosa(800, 600).convert("RGBA")
        imagem.save(origem, format="PNG")

        dados = processador.preparar(origem)

        resultado = Image.open(io.BytesIO(dados))
        assert resultado.mode == "RGB"
        assert resultado.format == "JPEG"

    @pytest.mark.skipif(not _HEIC_DISPONIVEL, reason="pillow-heif não disponível neste ambiente")
    def test_heic_e_decodificado(
        self, processador: ProcessadorImagemPillow, tmp_path: Path
    ) -> None:
        origem = tmp_path / "bruta.heic"
        heif = pillow_heif.from_pillow(_imagem_ruidosa(1000, 800))
        heif.save(origem, quality=80)

        dados = processador.preparar(origem)

        resultado = Image.open(io.BytesIO(dados))
        assert resultado.format == "JPEG"

    def test_arquivo_corrompido_levanta_erro_processamento_imagem(
        self, processador: ProcessadorImagemPillow, tmp_path: Path
    ) -> None:
        origem = tmp_path / "quebrado.jpg"
        origem.write_bytes(b"nao-e-uma-imagem-de-verdade")

        with pytest.raises(ErroProcessamentoImagem) as excecao:
            processador.preparar(origem)

        assert excecao.value.origem == origem
