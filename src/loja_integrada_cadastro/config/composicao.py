from __future__ import annotations

from pathlib import Path

import anthropic

from loja_integrada_cadastro.config.configuracao import Configuracao
from loja_integrada_cadastro.infra.armazenamento_imagens_r2 import ArmazenamentoImagensR2
from loja_integrada_cadastro.infra.carregador_recursos import CarregadorRecursos
from loja_integrada_cadastro.infra.catalogo_fotos_diretorio import CatalogoFotosDiretorio
from loja_integrada_cadastro.infra.cliente_llm_anthropic import ClienteLlmAnthropic
from loja_integrada_cadastro.infra.escritor_planilha_saida_openpyxl import (
    EscritorPlanilhaSaidaOpenpyxl,
)
from loja_integrada_cadastro.infra.gerador_modelo_entrada_openpyxl import GeradorModeloEntrada
from loja_integrada_cadastro.infra.gerador_textos_dummy import GeradorTextosDummy
from loja_integrada_cadastro.infra.leitor_planilha_entrada_openpyxl import (
    LeitorPlanilhaEntradaOpenpyxl,
)
from loja_integrada_cadastro.infra.processador_imagem_pillow import ProcessadorImagemPillow
from loja_integrada_cadastro.infra.repositorio_estado_lote_json import RepositorioEstadoLoteJson
from loja_integrada_cadastro.infra.repositorio_prompts_jinja import RepositorioPromptsJinja
from loja_integrada_cadastro.models.padroes_fisicos import PadroesFisicos
from loja_integrada_cadastro.services.gerador_relatorio import GeradorRelatorio
from loja_integrada_cadastro.services.montador_planilha import MontadorPlanilha
from loja_integrada_cadastro.services.pipeline_fotos import PipelineFotos
from loja_integrada_cadastro.services.politica_reexecucao import PoliticaReexecucao
from loja_integrada_cadastro.services.ports.cliente_llm import ClienteLlm
from loja_integrada_cadastro.services.ports.gerador_textos import GeradorTextos
from loja_integrada_cadastro.services.ports.leitor_planilha_entrada import LeitorPlanilhaEntrada
from loja_integrada_cadastro.services.ports.repositorio_prompts import RepositorioPrompts
from loja_integrada_cadastro.services.processador_lote import ProcessarLote
from loja_integrada_cadastro.services.validador_entrada import ValidadorEntrada

_LLM_MAX_RETRIES = 3
_LLM_TIMEOUT_SEGUNDOS = 120.0


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


def montar_cliente_llm(configuracao: Configuracao) -> ClienteLlm:
    """Composition root do conector Anthropic: uma instância do SDK por execução (§6.3).

    Retries de 429/5xx/rede ficam no SDK (`max_retries=3`); o timeout é generoso porque as
    chamadas usam adaptive thinking. Ainda não é chamado por `montar_processador_lote` — a
    task 16 liga os agentes ao pipeline.
    """
    cliente = anthropic.Anthropic(
        api_key=configuracao.exigir_anthropic(),
        max_retries=_LLM_MAX_RETRIES,
        timeout=_LLM_TIMEOUT_SEGUNDOS,
    )
    return ClienteLlmAnthropic(cliente, CarregadorRecursos().precos_llm())


def montar_repositorio_prompts() -> RepositorioPrompts:
    """Composition root do repositório de prompts (templates de `recursos/prompts/`)."""
    return RepositorioPromptsJinja()


def montar_montador_planilha(configuracao: Configuracao) -> MontadorPlanilha:
    """Composition root do montador da planilha de saída, usado por `processar`."""
    padroes_fisicos = PadroesFisicos(
        peso_kg=configuracao.peso_kg,
        altura_cm=configuracao.altura_cm,
        largura_cm=configuracao.largura_cm,
        comprimento_cm=configuracao.comprimento_cm,
    )
    return MontadorPlanilha(padroes_fisicos, configuracao.produto_ativo)


def montar_pipeline_fotos(configuracao: Configuracao, fotos: Path) -> PipelineFotos:
    """Composition root do pipeline de fotos, usado por `processar`.

    Sempre publica no Cloudflare R2 real — sem opção de armazenamento local (decisão
    confirmada com o usuário na task 11: nada de flag `--sem-upload`).
    """
    configuracao.exigir_r2()
    assert configuracao.r2_bucket is not None
    assert configuracao.r2_account_id is not None
    assert configuracao.r2_access_key_id is not None
    assert configuracao.r2_secret_access_key is not None
    assert configuracao.r2_url_publica is not None

    catalogo = CatalogoFotosDiretorio(fotos)
    processador = ProcessadorImagemPillow(
        configuracao.imagem_lado_max_px, configuracao.imagem_tamanho_max_kb
    )
    armazenamento = ArmazenamentoImagensR2(
        bucket=configuracao.r2_bucket,
        account_id=configuracao.r2_account_id,
        access_key_id=configuracao.r2_access_key_id,
        secret_access_key=configuracao.r2_secret_access_key,
        url_publica=configuracao.r2_url_publica,
    )
    return PipelineFotos(catalogo, processador, armazenamento)


def montar_processador_lote(configuracao: Configuracao, fotos: Path, lote: str) -> ProcessarLote:
    """Composition root do caso de uso principal, usado pelo subcomando `processar`."""
    lote_dir = configuracao.lotes_dir / lote
    return ProcessarLote(
        leitor_planilha_entrada=montar_leitor_planilha_entrada(),
        validador=montar_validador_entrada(fotos),
        pipeline_fotos=montar_pipeline_fotos(configuracao, fotos),
        gerador_textos=montar_gerador_textos(configuracao),
        montador=montar_montador_planilha(configuracao),
        escritor=EscritorPlanilhaSaidaOpenpyxl(),
        repositorio_estado=RepositorioEstadoLoteJson(lote_dir),
        gerador_relatorio=GeradorRelatorio(),
        politica_reexecucao=PoliticaReexecucao(),
    )
