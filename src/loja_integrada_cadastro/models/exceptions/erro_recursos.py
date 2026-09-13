class ErroRecursos(Exception):
    """Recurso do pacote ausente ou com estrutura inválida (recursos/dados_mestre.yaml e afins)."""

    def __init__(self, recurso: str, motivo: str) -> None:
        self.recurso = recurso
        self.motivo = motivo
        super().__init__(self._montar_mensagem())

    def _montar_mensagem(self) -> str:
        return f"Recurso inválido '{self.recurso}': {self.motivo}"
