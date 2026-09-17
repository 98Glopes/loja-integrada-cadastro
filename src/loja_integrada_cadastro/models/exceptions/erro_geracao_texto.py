from __future__ import annotations


class ErroGeracaoTexto(Exception):
    """Falha ao obter uma resposta válida do modelo de linguagem.

    `retentavel=True` indica problema transitório (rate limit, erro 5xx, rede, JSON fora do
    esquema): vale tentar de novo mais tarde. `False` indica que repetir a mesma chamada não
    resolve (chave inválida, parâmetros rejeitados, refusal, resposta truncada duas vezes).
    """

    def __init__(self, motivo: str, retentavel: bool = False) -> None:
        self.motivo = motivo
        self.retentavel = retentavel
        super().__init__(f"Falha na geração de texto: {motivo}")
