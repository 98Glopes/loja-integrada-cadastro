from __future__ import annotations

import logging
import sys
from argparse import ArgumentParser, Namespace
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import TYPE_CHECKING

from loja_integrada_cadastro.config.composicao import (
    montar_gerador_modelo_entrada,
    montar_leitor_planilha_entrada,
    montar_processador_lote,
    montar_validador_entrada,
)
from loja_integrada_cadastro.config.configuracao import Configuracao
from loja_integrada_cadastro.models.exceptions.erro_configuracao import ErroConfiguracao
from loja_integrada_cadastro.models.exceptions.erro_planilha_entrada import ErroPlanilhaEntrada
from loja_integrada_cadastro.models.exceptions.erro_planilha_saida import ErroPlanilhaSaida
from loja_integrada_cadastro.models.exceptions.erro_recursos import ErroRecursos
from loja_integrada_cadastro.models.resultado_validacao import ResultadoValidacao
from loja_integrada_cadastro.models.resumo_lote import ResumoLote
from loja_integrada_cadastro.services.processador_lote import OpcoesProcessamento

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
        parser.add_argument("--verboso", action="store_true", help="log em nível debug")

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
        try:
            produtos = montar_leitor_planilha_entrada().ler(opcoes.planilha)
        except ErroPlanilhaEntrada as erro:
            print(f"validar: {erro}", file=sys.stderr)
            return CODIGO_ERRO_NEGOCIO

        try:
            _, resultado = montar_validador_entrada(opcoes.fotos).validar(produtos)
        except ErroRecursos as erro:
            print(f"validar: {erro}", file=sys.stderr)
            return CODIGO_ERRO_NEGOCIO

        self._imprimir_resultado_validacao(resultado)
        return 0 if resultado.aprovado else CODIGO_ERRO_NEGOCIO

    @staticmethod
    def _imprimir_resultado_validacao(resultado: ResultadoValidacao) -> None:
        skus = dict.fromkeys(item.sku_pai for item in (*resultado.problemas, *resultado.avisos))
        for sku_pai in skus:
            print(f"SKU {sku_pai}:")
            for problema in resultado.problemas:
                if problema.sku_pai == sku_pai:
                    print(f"  [problema] {problema.campo}: {problema.mensagem}")
            for aviso in resultado.avisos:
                if aviso.sku_pai == sku_pai:
                    print(f"  [aviso] {aviso.campo}: {aviso.mensagem}")

        if resultado.aprovado:
            print(f"validar: aprovado ({len(resultado.avisos)} aviso(s))")
        else:
            print(
                f"validar: reprovado ({len(resultado.problemas)} problema(s), "
                f"{len(resultado.avisos)} aviso(s))"
            )

    def _processar(self, opcoes: Namespace) -> int:
        logging.basicConfig(
            level=logging.DEBUG if opcoes.verboso else logging.INFO, format="%(message)s"
        )
        try:
            configuracao = Configuracao.do_ambiente()
            processador = montar_processador_lote(configuracao, opcoes.fotos, opcoes.lote)
        except ErroConfiguracao as erro:
            print(f"processar: {erro}", file=sys.stderr)
            return CODIGO_ERRO_NEGOCIO

        opcoes_processamento = OpcoesProcessamento(
            incluir_reprovados=opcoes.incluir_reprovados,
            refazer_textos=frozenset(opcoes.refazer_textos),
            refazer_fotos=frozenset(opcoes.refazer_fotos),
        )
        try:
            resumo = processador.executar(
                opcoes.planilha, opcoes.fotos, opcoes.lote, opcoes_processamento
            )
        except (ErroPlanilhaEntrada, ErroRecursos, ErroPlanilhaSaida) as erro:
            print(f"processar: {erro}", file=sys.stderr)
            return CODIGO_ERRO_NEGOCIO

        self._imprimir_resumo_lote(resumo)
        return 0 if resumo.todos_prontos else CODIGO_ERRO_NEGOCIO

    @staticmethod
    def _imprimir_resumo_lote(resumo: ResumoLote) -> None:
        for status, quantidade in resumo.contagem_por_status.items():
            if quantidade:
                print(f"  {status.value}: {quantidade}")
        print(f"processar: planilha em {resumo.caminho_planilha}")
        print(f"processar: relatório em {resumo.caminho_relatorio_md}")
        print(
            f"processar: custo estimado US$ {resumo.custo_usd_total} "
            f"({resumo.duracao_segundos:.1f}s)"
        )

    def _verificar(self, opcoes: Namespace) -> int:
        return self._nao_implementado("verificar")

    @staticmethod
    def _nao_implementado(comando: str) -> int:
        print(f"{comando}: não implementado", file=sys.stderr)
        return CODIGO_NAO_IMPLEMENTADO
