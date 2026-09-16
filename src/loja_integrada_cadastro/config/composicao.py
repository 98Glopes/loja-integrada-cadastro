from __future__ import annotations

from pathlib import Path

from loja_integrada_cadastro.config.configuracao import Configuracao
from loja_integrada_cadastro.infra.carregador_recursos import CarregadorRecursos
from loja_integrada_cadastro.infra.catalogo_fotos_diretorio import CatalogoFotosDiretorio
from loja_integrada_cadastro.infra.gerador_modelo_entrada_openpyxl import GeradorModeloEntrada
from loja_integrada_cadastro.infra.gerador_textos_dummy import GeradorTextosDummy
from loja_integrada_cadastro.infra.leitor_planilha_entrada_openpyxl import (
    LeitorPlanilhaEntradaOpenpyxl,
)
from loja_integrada_cadastro.models.padroes_fisicos import PadroesFisicos
from loja_integrada_cadastro.services.montador_planilha import MontadorPlanilha
from loja_integrada_cadastro.services.ports.gerador_textos import GeradorTextos
from loja_integrada_cadastro.services.ports.leitor_planilha_entrada import LeitorPlanilhaEntrada
from loja_integrada_cadastro.services.validador_entrada import ValidadorEntrada


def montar_gerador_modelo_entrada() -> GeradorModeloEntrada:
    """Composition root do comando `modelo-entrada`."""
    dados_mestre = CarregadorRecursos().dados_mestre()
    return GeradorModeloEntrada(dados_mestre)


def montar_leitor_planilha_entrada() -> LeitorPlanilhaEntrada:
    """Composition root do leitor de planilha, usado por `validar` e `processar`."""
    return LeitorPlanilhaEntradaOpenpyxl()


def montar_validador_entrada(fotos: Path) -> ValidadorEntrada:
    """Composition root do comando `validar`.

    `marcas_com_perfil` fica vazio por enquanto (parâmetro simples, ver
    `docs/tasks/05-validador-entrada.md`); a task 10 liga ao carregador de recursos.
    """
    dados_mestre = CarregadorRecursos().dados_mestre()
    catalogo_fotos = CatalogoFotosDiretorio(fotos)
    return ValidadorEntrada(dados_mestre, catalogo_fotos)


def montar_gerador_textos(configuracao: Configuracao) -> GeradorTextos:
    """Composition root do gerador de textos usado por `processar`.

    Devolve `GeradorTextosDummy` — única implementação até a task 16 trocar para
    `GeradorTextosIa` (ADR-007). `configuracao` não é usado pelo dummy; o parâmetro existe
    para a assinatura já ficar estável quando a troca acontecer (a implementação de IA
    precisa da configuração de modelos/effort/chave da API).
    """
    dados_mestre = CarregadorRecursos().dados_mestre()
    return GeradorTextosDummy(dados_mestre)


def montar_montador_planilha(configuracao: Configuracao) -> MontadorPlanilha:
    """Composition root do montador da planilha de saída, usado por `processar`."""
    padroes_fisicos = PadroesFisicos(
        peso_kg=configuracao.peso_kg,
        altura_cm=configuracao.altura_cm,
        largura_cm=configuracao.largura_cm,
        comprimento_cm=configuracao.comprimento_cm,
    )
    return MontadorPlanilha(padroes_fisicos, configuracao.produto_ativo)
