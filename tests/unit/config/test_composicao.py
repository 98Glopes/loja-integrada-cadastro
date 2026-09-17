from pathlib import Path

import pytest

from loja_integrada_cadastro.config.composicao import (
    montar_cliente_llm,
    montar_gerador_modelo_entrada,
    montar_gerador_textos,
    montar_leitor_planilha_entrada,
    montar_montador_planilha,
    montar_pipeline_fotos,
    montar_processador_lote,
    montar_repositorio_prompts,
    montar_validador_entrada,
)
from loja_integrada_cadastro.config.configuracao import Configuracao
from loja_integrada_cadastro.infra.cliente_llm_anthropic import ClienteLlmAnthropic
from loja_integrada_cadastro.infra.gerador_modelo_entrada_openpyxl import GeradorModeloEntrada
from loja_integrada_cadastro.infra.gerador_textos_dummy import GeradorTextosDummy
from loja_integrada_cadastro.infra.leitor_planilha_entrada_openpyxl import (
    LeitorPlanilhaEntradaOpenpyxl,
)
from loja_integrada_cadastro.infra.repositorio_prompts_jinja import RepositorioPromptsJinja
from loja_integrada_cadastro.models.exceptions.erro_configuracao import ErroConfiguracao
from loja_integrada_cadastro.services.montador_planilha import MontadorPlanilha
from loja_integrada_cadastro.services.pipeline_fotos import PipelineFotos
from loja_integrada_cadastro.services.processador_lote import ProcessarLote
from loja_integrada_cadastro.services.validador_entrada import ValidadorEntrada

_CONFIGURACAO_COM_R2 = Configuracao(
    r2_account_id="conta",
    r2_access_key_id="chave",
    r2_secret_access_key="segredo",
    r2_bucket="bucket",
    r2_url_publica="https://exemplo.com",
)


def test_montar_gerador_modelo_entrada_devolve_gerador_funcional(tmp_path: Path) -> None:
    gerador = montar_gerador_modelo_entrada()

    assert isinstance(gerador, GeradorModeloEntrada)

    destino = tmp_path / "modelo-entrada.xlsx"
    gerador.gerar(destino)

    assert destino.exists()


def test_montar_leitor_planilha_entrada_devolve_leitor_openpyxl() -> None:
    assert isinstance(montar_leitor_planilha_entrada(), LeitorPlanilhaEntradaOpenpyxl)


def test_montar_validador_entrada_devolve_validador_funcional(tmp_path: Path) -> None:
    validador = montar_validador_entrada(tmp_path)

    assert isinstance(validador, ValidadorEntrada)


def test_montar_gerador_textos_devolve_gerador_dummy() -> None:
    gerador = montar_gerador_textos(Configuracao())

    assert isinstance(gerador, GeradorTextosDummy)


def test_montar_cliente_llm_sem_chave_levanta_erro_configuracao() -> None:
    with pytest.raises(ErroConfiguracao, match="ANTHROPIC_API_KEY"):
        montar_cliente_llm(Configuracao())


def test_montar_cliente_llm_devolve_conector_anthropic_sem_tocar_a_rede() -> None:
    cliente = montar_cliente_llm(Configuracao(anthropic_api_key="sk-ant-teste"))

    assert isinstance(cliente, ClienteLlmAnthropic)


def test_montar_repositorio_prompts_devolve_repositorio_jinja() -> None:
    assert isinstance(montar_repositorio_prompts(), RepositorioPromptsJinja)


def test_montar_montador_planilha_devolve_montador_funcional() -> None:
    montador = montar_montador_planilha(Configuracao())

    assert isinstance(montador, MontadorPlanilha)


def test_montar_pipeline_fotos_sem_r2_levanta_erro_configuracao(tmp_path: Path) -> None:
    with pytest.raises(ErroConfiguracao) as excecao:
        montar_pipeline_fotos(Configuracao(), tmp_path)

    assert excecao.value.variavel == "R2_ACCOUNT_ID"


def test_montar_pipeline_fotos_devolve_pipeline_funcional(tmp_path: Path) -> None:
    pipeline = montar_pipeline_fotos(_CONFIGURACAO_COM_R2, tmp_path)

    assert isinstance(pipeline, PipelineFotos)


def test_montar_processador_lote_devolve_processador_funcional(tmp_path: Path) -> None:
    configuracao = Configuracao(
        r2_account_id="conta",
        r2_access_key_id="chave",
        r2_secret_access_key="segredo",
        r2_bucket="bucket",
        r2_url_publica="https://exemplo.com",
        lotes_dir=tmp_path,
    )

    processador = montar_processador_lote(configuracao, tmp_path, "lote-1")

    assert isinstance(processador, ProcessarLote)
    assert (tmp_path / "lote-1" / "estado").is_dir()
