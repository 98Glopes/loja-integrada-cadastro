"""Gera a fixture `tests/fixtures/lote-piloto/` usada pelos testes da task 05.

Cria `planilha.xlsx` (6 produtos, com marcas/cores/tamanhos reais de `recursos/dados_mestre.yaml`)
e `fotos/<sku-pai>/<cor>/*.jpg` com arquivos mínimos (cabeçalho JPEG válido — SOI/APP0/EOI —, mas
sem dados de imagem reais; suficiente para o catálogo de fotos, que só confere extensão e
existência, não decodifica o conteúdo). Dois produtos têm um defeito proposital (cor inválida e
GTIN inválido) para exercitar o comando `validar` ponta a ponta.

Reexecução: apaga e regera a pasta inteira, para o resultado ser determinístico.

Uso:
    .venv/Scripts/python scripts/gerar_fixture_lote_piloto.py
"""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path

from openpyxl import Workbook

from loja_integrada_cadastro.models.layout_planilha_entrada import COLUNAS_PLANILHA_ENTRADA

RAIZ = Path(__file__).resolve().parent.parent / "tests" / "fixtures" / "lote-piloto"

# Cabeçalho JPEG mínimo (SOI + APP0/JFIF + EOI), sem dados de imagem — o catálogo de fotos só
# confere extensão e existência do arquivo, não decodifica o conteúdo (decodificação real de
# imagem é escopo da task 07, com Pillow).
JPEG_MINIMO = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00\xff\xd9"

CATEGORIA_REFERENCIA = "Inverno>1 - Linha Baby (P ao XG)>Menina>Vestido"
CATEGORIA_FORA_DA_REFERENCIA = "Categoria Manual>Sub Categoria"


@dataclass(frozen=True)
class _Variacao:
    cor: str
    tamanho: str
    gtin: str
    preco: str = "119,90"
    estoque: int = 10


@dataclass(frozen=True)
class _Produto:
    sku_pai: str
    marca: str
    nome_fornecedor: str
    tipo_peca: str
    categoria: str
    composicao: str
    detalhes: str
    faixa_tamanho: str
    variacoes: tuple[_Variacao, ...]
    pastas_de_fotos: tuple[str, ...]
    """Cores para as quais gerar pasta de fotos — normalmente as mesmas das variações; um
    produto pode ter uma pasta com o nome literal de uma cor inválida, para isolar o defeito."""


def _gtin(corpo: str) -> str:
    digitos = [int(caractere) for caractere in corpo]
    soma = sum(
        digito * (3 if indice % 2 == 0 else 1) for indice, digito in enumerate(reversed(digitos))
    )
    return corpo + str((10 - soma % 10) % 10)


_GTIN_BASE_VALIDO = _gtin("789100000999")
GTIN_INVALIDO = _GTIN_BASE_VALIDO[:-1] + str((int(_GTIN_BASE_VALIDO[-1]) + 1) % 10)
"""GTIN com dígito verificador propositalmente errado (o correto seria `_GTIN_BASE_VALIDO`)."""


PRODUTOS = (
    _Produto(
        sku_pai="3254002",
        marca="kiki",
        nome_fornecedor="Conjunto Baby Malha e Moletom",
        tipo_peca="Conjunto",
        categoria=CATEGORIA_REFERENCIA,
        composicao="100% algodão",
        detalhes="Botões na gola, acabamento em ribana",
        faixa_tamanho="P ao G",
        variacoes=(
            _Variacao("Beige", "P", _gtin("789100000010")),
            _Variacao("Beige", "M", _gtin("789100000020")),
            _Variacao("Beige", "G", _gtin("789100000030")),
        ),
        pastas_de_fotos=("Beige",),
    ),
    _Produto(
        sku_pai="3254010",
        marca="somnii",
        nome_fornecedor="Vestido Florzinha Babados",
        tipo_peca="Vestido",
        categoria=CATEGORIA_REFERENCIA,
        composicao="100% viscose",
        detalhes="Babados na barra, laço na cintura",
        faixa_tamanho="1 ao 2",
        variacoes=(
            _Variacao("Beige", "1", _gtin("789100000040")),
            _Variacao("Beige", "2", _gtin("789100000050")),
            _Variacao("Rosa", "1", _gtin("789100000060")),
            _Variacao("Rosa", "2", _gtin("789100000070")),
        ),
        pastas_de_fotos=("Beige", "Rosa"),
    ),
    _Produto(
        sku_pai="3254020",
        marca="Onda Marinha",
        nome_fornecedor="Blusinha Canelada Manga Longa",
        tipo_peca="Blusinha",
        categoria=CATEGORIA_REFERENCIA,
        composicao="98% algodão, 2% elastano",
        detalhes="Gola careca, tecido canelado",
        faixa_tamanho="Único (M)",
        variacoes=(
            _Variacao("Preto", "M", _gtin("789100000080")),
            _Variacao("Branco", "M", _gtin("789100000090")),
        ),
        pastas_de_fotos=("Preto", "Branco"),
    ),
    _Produto(
        sku_pai="3254030",
        marca="kiki",
        nome_fornecedor="Macacão Plush Ursinho",
        tipo_peca="Macacão",
        categoria=CATEGORIA_REFERENCIA,
        composicao="100% poliéster (plush)",
        detalhes="Capuz com orelhinhas, zíper frontal",
        faixa_tamanho="P",
        # Defeito proposital: cor fora da lista mestre — único problema deste produto.
        variacoes=(_Variacao("Arco-Iris", "P", _gtin("789100000100")),),
        pastas_de_fotos=("Arco-Iris",),
    ),
    _Produto(
        sku_pai="3254040",
        marca="Lemon",
        nome_fornecedor="Casaco Moletom com Capuz",
        tipo_peca="Casaco",
        categoria=CATEGORIA_REFERENCIA,
        composicao="100% moletom",
        detalhes="Bolso canguru, punho e barra em ribana",
        faixa_tamanho="P",
        # Defeito proposital: dígito verificador de GTIN inválido — único problema deste produto.
        variacoes=(_Variacao("Preto", "P", GTIN_INVALIDO),),
        pastas_de_fotos=("Preto",),
    ),
    _Produto(
        sku_pai="3254050",
        marca="Kyly",
        nome_fornecedor="Body Manga Curta Estampado",
        tipo_peca="Body",
        categoria=CATEGORIA_FORA_DA_REFERENCIA,
        composicao="100% algodão",
        detalhes="Estampa localizada, abertura de fralda",
        faixa_tamanho="G",
        variacoes=(_Variacao("Branco", "G", _gtin("789100000110")),),
        pastas_de_fotos=("Branco",),
    ),
)


def _gerar_planilha(destino: Path) -> None:
    workbook = Workbook()
    aba = workbook.active
    assert aba is not None
    aba.append(list(COLUNAS_PLANILHA_ENTRADA))
    for produto in PRODUTOS:
        for variacao in produto.variacoes:
            aba.append(
                [
                    produto.sku_pai,
                    produto.marca,
                    produto.nome_fornecedor,
                    produto.tipo_peca,
                    produto.categoria,
                    produto.composicao,
                    produto.detalhes,
                    "",  # colecao (opcional)
                    produto.faixa_tamanho,
                    variacao.cor,
                    variacao.tamanho,
                    variacao.gtin,
                    variacao.preco,
                    variacao.estoque,
                ]
            )
    workbook.save(destino)


def _gerar_fotos(raiz_fotos: Path) -> None:
    for produto in PRODUTOS:
        for cor in produto.pastas_de_fotos:
            pasta = raiz_fotos / produto.sku_pai / cor
            pasta.mkdir(parents=True, exist_ok=True)
            (pasta / f"{produto.sku_pai}-{cor.lower()}-1.jpg").write_bytes(JPEG_MINIMO)


def main() -> None:
    if RAIZ.exists():
        shutil.rmtree(RAIZ)
    RAIZ.mkdir(parents=True)

    _gerar_planilha(RAIZ / "planilha.xlsx")
    _gerar_fotos(RAIZ / "fotos")

    total_variacoes = sum(len(produto.variacoes) for produto in PRODUTOS)
    print(f"Fixture gerada em {RAIZ}: {len(PRODUTOS)} produtos, {total_variacoes} variações.")


if __name__ == "__main__":
    main()
