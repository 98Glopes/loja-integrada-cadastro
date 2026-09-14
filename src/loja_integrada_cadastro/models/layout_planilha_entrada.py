from __future__ import annotations

COLUNAS_PLANILHA_ENTRADA: tuple[str, ...] = (
    "sku-pai",
    "marca",
    "nome-fornecedor",
    "tipo-peca",
    "categoria",
    "composicao",
    "detalhes",
    "colecao",
    "faixa-tamanho",
    "cor",
    "tamanho",
    "gtin",
    "preco",
    "estoque",
)
"""As 14 colunas da planilha de entrada (`docs/ARQUITETURA.md` §4), na ordem sugerida.

O leitor valida por nome, aceitando qualquer ordem de colunas na planilha real.
"""

CAMPOS_PRODUTO_OBRIGATORIOS: tuple[str, ...] = (
    "marca",
    "nome-fornecedor",
    "tipo-peca",
    "categoria",
    "composicao",
    "detalhes",
    "faixa-tamanho",
)
"""Campos de escopo produto, exigidos na primeira linha de cada `sku-pai`."""

CAMPO_PRODUTO_OPCIONAL = "colecao"
"""Único campo de produto que pode ficar vazio."""

CAMPOS_VARIACAO_OBRIGATORIOS: tuple[str, ...] = ("cor", "tamanho", "gtin", "preco", "estoque")
"""Campos de escopo variação, exigidos em toda linha não vazia."""
