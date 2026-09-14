from __future__ import annotations

import sys
from argparse import ArgumentParser, Namespace
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import TYPE_CHECKING

from loja_integrada_cadastro.config.composicao import montar_gerador_modelo_entrada
from loja_integrada_cadastro.models.exceptions.erro_recursos import ErroRecursos

if TYPE_CHECKING:
    from argparse import _SubParsersAction

    Subcomandos = _SubParsersAction[ArgumentParser]

CODIGO_NAO_IMPLEMENTADO = 2
CODIGO_ERRO_NEGOCIO = 1


class AplicacaoCli:
    """Ponto de entrada da CLI. Faz parsing dos argumentos e delega aos casos de uso."""

    def executar(self, argumentos: Sequence[str] | None = None) -> int:
        opcoes = self.criar_parser().parse_args(argumentos)
        comandos: dict[str, Callable[[Namespace], int]] = {
            "modelo-entrada": self._modelo_entrada,
            "validar": self._validar,
            "processar": self._processar,
            "verificar": self._verificar,
        }
        return comandos[opcoes.comando](opcoes)

    def criar_parser(self) -> ArgumentParser:
        parser = ArgumentParser(
            prog="loja-integrada-cadastro",
            description="Cadastro em massa de produtos na Loja Integrada.",
        )
        subcomandos = parser.add_subparsers(dest="comando", required=True)
        self._definir_modelo_entrada(subcomandos)
        self._definir_validar(subcomandos)
        self._definir_processar(subcomandos)
        self._definir_verificar(subcomandos)
        return parser

    @staticmethod
    def _definir_modelo_entrada(subcomandos: Subcomandos) -> None:
        parser = subcomandos.add_parser(
            "modelo-entrada", help="gera a planilha modelo para preenchimento"
        )
        parser.add_argument(
            "--destino",
            type=Path,
            default=Path("modelo-entrada.xlsx"),
            help="arquivo .xlsx a gerar",
        )

    def _definir_validar(self, subcomandos: Subcomandos) -> None:
        parser = subcomandos.add_parser(
            "validar", help="valida a planilha e a pasta de fotos sem processar"
        )
        self._adicionar_entrada(parser)

    def _definir_processar(self, subcomandos: Subcomandos) -> None:
        parser = subcomandos.add_parser(
            "processar", help="processa o lote: fotos, textos por IA e planilha de importação"
        )
        self._adicionar_entrada(parser)
        parser.add_argument("--lote", required=True, help="nome do lote (workspace)")
        parser.add_argument(
            "--incluir-reprovados",
            action="store_true",
            help="inclui na planilha os produtos reprovados pelo QA",
        )
        parser.add_argument(
            "--refazer-textos", nargs="+", metavar="SKU", default=[], help="regera os textos"
        )
        parser.add_argument(
            "--refazer-fotos", nargs="+", metavar="SKU", default=[], help="reprocessa as fotos"
        )

    @staticmethod
    def _definir_verificar(subcomandos: Subcomandos) -> None:
        parser = subcomandos.add_parser(
            "verificar", help="confere no site público os produtos importados"
        )
        parser.add_argument("--lote", required=True, help="nome do lote (workspace)")
        parser.add_argument("--esperar", help="tempo máximo de espera pela página (ex.: 5m)")

    @staticmethod
    def _adicionar_entrada(parser: ArgumentParser) -> None:
        parser.add_argument(
            "--planilha", type=Path, required=True, help="planilha .xlsx de entrada"
        )
        parser.add_argument("--fotos", type=Path, required=True, help="pasta raiz das fotos")

    def _modelo_entrada(self, opcoes: Namespace) -> int:
        try:
            montar_gerador_modelo_entrada().gerar(opcoes.destino)
        except ErroRecursos as erro:
            print(f"modelo-entrada: {erro}", file=sys.stderr)
            return CODIGO_ERRO_NEGOCIO
        print(f"modelo-entrada: gerado em {opcoes.destino}")
        return 0

    def _validar(self, opcoes: Namespace) -> int:
        return self._nao_implementado("validar")

    def _processar(self, opcoes: Namespace) -> int:
        return self._nao_implementado("processar")

    def _verificar(self, opcoes: Namespace) -> int:
        return self._nao_implementado("verificar")

    @staticmethod
    def _nao_implementado(comando: str) -> int:
        print(f"{comando}: não implementado", file=sys.stderr)
        return CODIGO_NAO_IMPLEMENTADO
