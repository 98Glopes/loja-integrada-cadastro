class ErroConfiguracao(Exception):
    """Variável de ambiente obrigatória ausente ou com valor inválido."""

    def __init__(self, variavel: str, valor_invalido: str | None = None) -> None:
        self.variavel = variavel
        self.valor_invalido = valor_invalido
        super().__init__(self._montar_mensagem())

    def _montar_mensagem(self) -> str:
        if self.valor_invalido is None:
            return f"Variável de ambiente obrigatória não definida: {self.variavel}"
        return f"Valor inválido para {self.variavel}: '{self.valor_invalido}'"
