from __future__ import annotations

from itertools import islice, zip_longest

from loja_integrada_cadastro.models.foto_produto import FotoProduto
from loja_integrada_cadastro.models.produto_entrada import ProdutoEntrada
from loja_integrada_cadastro.models.slug import slugificar

_TAMANHO_MAX_NOME = 60
# Duplica services.validador_entrada.MAX_FOTOS_POR_PRODUTO: `models` não pode importar de
# `services` (regra de dependência de `docs/ARQUITETURA.md` §10).
MAX_IMAGENS_PAI = 5


class NomeadorFotos:
    """Nome de arquivo determinístico e estável entre reexecuções (`docs/ARQUITETURA.md` §5.2)."""

    @staticmethod
    def nomear(produto: ProdutoEntrada, cor: str, ordem: int) -> str:
        marca = slugificar(produto.marca)
        tipo = slugificar(produto.tipo_peca)
        nome_fornecedor = _sem_prefixo_duplicado(slugificar(produto.nome_fornecedor), tipo)
        cor_slug = slugificar(cor)

        base = "-".join(parte for parte in (marca, tipo, nome_fornecedor) if parte)
        base = base[:_TAMANHO_MAX_NOME].rstrip("-")
        return f"{base}-{cor_slug}-{ordem}.jpg"


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
    """Escolhe até `MAX_IMAGENS_PAI` fotos para a imagem do pai, round-robin por cor (§5.3)."""

    @staticmethod
    def selecionar(fotos: list[FotoProduto]) -> list[FotoProduto]:
        por_cor: dict[str, list[FotoProduto]] = {}
        for foto in fotos:
            por_cor.setdefault(foto.cor, []).append(foto)
        for lista in por_cor.values():
            lista.sort(key=lambda foto: foto.ordem)

        # zip_longest intercala uma lista por cor: primeiro a `-1` de cada cor, depois a `-2`...
        intercaladas = (
            foto for rodada in zip_longest(*por_cor.values()) for foto in rodada if foto is not None
        )
        return list(islice(intercaladas, MAX_IMAGENS_PAI))
