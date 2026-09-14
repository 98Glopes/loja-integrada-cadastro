from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ProblemaValidacao:
    """Um problema ou aviso encontrado ao validar um produto de entrada."""

    sku_pai: str
    campo: str
    mensagem: str


@dataclass(frozen=True)
class ResultadoValidacao:
    """Resultado da validação de um lote inteiro de produtos.

    `problemas` bloqueiam o produto correspondente (não deve seguir para as etapas seguintes);
    `avisos` só chamam atenção, sem impedir o processamento.
    """

    problemas: tuple[ProblemaValidacao, ...]
    avisos: tuple[ProblemaValidacao, ...]

    @property
    def aprovado(self) -> bool:
        """`True` quando não há nenhum problema bloqueante no lote (avisos não contam)."""
        return not self.problemas
