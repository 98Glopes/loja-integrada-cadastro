from __future__ import annotations


class ErroPrompt(Exception):
    """Template de prompt ausente, malformado, sem bloco obrigatório ou com variável faltante.

    É sempre erro de programação/recursos, nunca de dados do lote — o template e o contexto
    que o agente passa são do próprio pacote.
    """

    def __init__(self, nome: str, motivo: str) -> None:
        self.nome = nome
        self.motivo = motivo
        super().__init__(f"Prompt '{nome}': {motivo}")
