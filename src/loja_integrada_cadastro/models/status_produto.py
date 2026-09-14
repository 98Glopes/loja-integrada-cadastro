from __future__ import annotations

from enum import Enum


class StatusProduto(Enum):
    """Situação de um produto no pipeline do lote (`docs/ARQUITETURA.md` §3, §8)."""

    VALIDADO = "validado"
    REPROVADO_VALIDACAO = "reprovado-validacao"
    ERRO_FOTOS = "erro-fotos"
    FOTOS_PUBLICADAS = "fotos-publicadas"
    TEXTOS_GERADOS = "textos-gerados"
    REPROVADO_QA = "reprovado-qa"
    ERRO_LLM = "erro-llm"
    PRONTO = "pronto"
