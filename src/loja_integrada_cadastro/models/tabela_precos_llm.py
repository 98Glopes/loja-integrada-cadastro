from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date

from loja_integrada_cadastro.models.exceptions.erro_recursos import ErroRecursos
from loja_integrada_cadastro.models.preco_modelo_llm import PrecoModeloLlm

ARQUIVO_PRECOS_LLM = "precos_llm.yaml"


@dataclass(frozen=True)
class TabelaPrecosLlm:
    """Preços por modelo, com a data em que foram copiados da documentação oficial."""

    precos: Mapping[str, PrecoModeloLlm]
    data_referencia: date

    def exigir(self, modelo: str) -> PrecoModeloLlm:
        """Preço de `modelo`; `ErroRecursos` se ele não estiver na tabela.

        O conector chama isto **antes** da requisição: gastar sem conseguir calcular o custo
        deixaria o relatório do lote inconsistente.
        """
        preco = self.precos.get(modelo)
        if preco is None:
            conhecidos = ", ".join(sorted(self.precos))
            raise ErroRecursos(
                ARQUIVO_PRECOS_LLM,
                f"modelo '{modelo}' sem preço cadastrado (conhecidos: {conhecidos})",
            )
        return preco
