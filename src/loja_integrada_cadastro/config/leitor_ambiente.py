from collections.abc import Callable, Mapping
from decimal import Decimal, InvalidOperation

from loja_integrada_cadastro.models.exceptions.erro_configuracao import ErroConfiguracao


class LeitorAmbiente:
    """Lê e converte variáveis de um mapping; string vazia conta como ausente."""

    def __init__(self, ambiente: Mapping[str, str]) -> None:
        self._ambiente = ambiente

    def opcional(self, variavel: str) -> str | None:
        valor = self._ambiente.get(variavel, "").strip()
        return valor or None

    def texto(self, variavel: str, padrao: str) -> str:
        return self.opcional(variavel) or padrao

    def inteiro(self, variavel: str, padrao: int) -> int:
        return self._converter(variavel, padrao, int)

    def decimal(self, variavel: str, padrao: Decimal) -> Decimal:
        return self._converter(variavel, padrao, Decimal)

    def sim_ou_nao(self, variavel: str, padrao: str) -> str:
        valor = self.texto(variavel, padrao).upper()
        if valor not in ("S", "N"):
            raise ErroConfiguracao(variavel, valor)
        return valor

    def _converter[T](self, variavel: str, padrao: T, conversor: Callable[[str], T]) -> T:
        bruto = self.opcional(variavel)
        if bruto is None:
            return padrao
        try:
            return conversor(bruto)
        except (ValueError, InvalidOperation) as erro:
            raise ErroConfiguracao(variavel, bruto) from erro
