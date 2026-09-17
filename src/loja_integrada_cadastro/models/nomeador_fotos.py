from __future__ import annotations

from loja_integrada_cadastro.models.foto_produto import FotoProduto
from loja_integrada_cadastro.models.produto_entrada import ProdutoEntrada
from loja_integrada_cadastro.models.slug import slugificar

_TAMANHO_MAX_NOME = 60
# Duplica services.validador_entrada.MAX_FOTOS_POR_PRODUTO: `models` não pode importar de
# `services` (regra de dependência de `docs/ARQUITETURA.md` §10).
MAX_IMAGENS_PAI = 5


class NomeadorFotos:
    """Nome de arquivo determinístico e estável entre reexecuções (`docs/ARQUITETURA.md` §5.2).

    Fotos não têm cor (valem para o produto inteiro), então o nome não carrega esse segmento.
    """

    @staticmethod
    def nomear(produto: ProdutoEntrada, ordem: int) -> str:
        marca = slugificar(produto.marca)
        tipo = slugificar(produto.tipo_peca)
        nome_fornecedor = _sem_prefixo_duplicado(slugificar(produto.nome_fornecedor), tipo)

        base = "-".join(parte for parte in (marca, tipo, nome_fornecedor) if parte)
        base = base[:_TAMANHO_MAX_NOME].rstrip("-")
        return f"{base}-{ordem}.jpg"


def _sem_prefixo_duplicado(nome_fornecedor_slug: str, tipo_slug: str) -> str:
    """Remove de `nome_fornecedor` os tokens que repetem, no início, os tokens de `tipo_peca`."""
    tokens_tipo = tipo_slug.split("-") if tipo_slug else []
    tokens_nome = nome_fornecedor_slug.split("-") if nome_fornecedor_slug else []
    indice = 0
    while (
        indice < len(tokens_tipo)
        and indice < len(tokens_nome)
        and tokens_nome[indice] == tokens_tipo[indice]
    ):
        indice += 1
    return "-".join(tokens_nome[indice:])


class SeletorImagensPai:
    """Escolhe até `MAX_IMAGENS_PAI` fotos para a imagem do pai (§5.3): as primeiras, em ordem."""

    @staticmethod
    def selecionar(fotos: list[FotoProduto]) -> list[FotoProduto]:
        return sorted(fotos, key=lambda foto: foto.ordem)[:MAX_IMAGENS_PAI]
