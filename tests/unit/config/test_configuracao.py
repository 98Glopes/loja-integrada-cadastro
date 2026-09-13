from decimal import Decimal
from pathlib import Path

import pytest

from loja_integrada_cadastro.config.configuracao import Configuracao
from loja_integrada_cadastro.models.exceptions.erro_configuracao import ErroConfiguracao

AMBIENTE_R2_COMPLETO = {
    "R2_ACCOUNT_ID": "conta",
    "R2_ACCESS_KEY_ID": "chave",
    "R2_SECRET_ACCESS_KEY": "segredo",
    "R2_BUCKET": "bucket",
    "R2_URL_PUBLICA": "https://bucket.exemplo.com",
}


def test_ambiente_vazio_produz_padroes_da_arquitetura() -> None:
    config = Configuracao.do_ambiente({})

    assert config.anthropic_api_key is None
    assert config.llm_modelo_copywriter == "claude-opus-5"
    assert config.llm_modelo_seo == "claude-opus-5"
    assert config.llm_modelo_qa == "claude-opus-5"
    assert config.llm_effort_copywriter == "high"
    assert config.llm_effort_seo == "medium"
    assert config.llm_effort_qa == "medium"
    assert config.llm_max_tentativas_qa == 2
    assert config.r2_account_id is None
    assert config.r2_url_publica is None
    assert config.imagem_lado_max_px == 1600
    assert config.imagem_tamanho_max_kb == 500
    assert config.produto_ativo == "S"
    assert config.peso_kg == Decimal("0.1")
    assert config.altura_cm == Decimal("4")
    assert config.largura_cm == Decimal("22")
    assert config.comprimento_cm == Decimal("22")
    assert config.loja_url == "https://www.kmilaamodas.com.br"
    assert config.lotes_dir == Path("lotes")


def test_le_e_converte_valores_do_ambiente() -> None:
    config = Configuracao.do_ambiente(
        {
            "ANTHROPIC_API_KEY": "sk-teste",
            "LLM_MODELO_QA": "claude-sonnet-5",
            "LLM_MAX_TENTATIVAS_QA": "3",
            "IMAGEM_LADO_MAX_PX": "1200",
            "PRODUTO_ATIVO": "n",
            "PESO_KG": "0.25",
            "LOTES_DIR": "C:/lotes",
            **AMBIENTE_R2_COMPLETO,
        }
    )

    assert config.anthropic_api_key == "sk-teste"
    assert config.llm_modelo_qa == "claude-sonnet-5"
    assert config.llm_max_tentativas_qa == 3
    assert config.imagem_lado_max_px == 1200
    assert config.produto_ativo == "N"
    assert config.peso_kg == Decimal("0.25")
    assert config.lotes_dir == Path("C:/lotes")
    assert config.r2_bucket == "bucket"


def test_string_vazia_conta_como_ausente() -> None:
    config = Configuracao.do_ambiente({"LLM_MAX_TENTATIVAS_QA": "", "ANTHROPIC_API_KEY": "  "})

    assert config.llm_max_tentativas_qa == 2
    assert config.anthropic_api_key is None


def test_exigir_anthropic_devolve_chave() -> None:
    config = Configuracao.do_ambiente({"ANTHROPIC_API_KEY": "sk-teste"})

    assert config.exigir_anthropic() == "sk-teste"


def test_exigir_anthropic_sem_chave_nomeia_variavel() -> None:
    config = Configuracao.do_ambiente({})

    with pytest.raises(ErroConfiguracao, match="ANTHROPIC_API_KEY") as erro:
        config.exigir_anthropic()
    assert erro.value.variavel == "ANTHROPIC_API_KEY"


def test_exigir_r2_completo_nao_falha() -> None:
    Configuracao.do_ambiente(AMBIENTE_R2_COMPLETO).exigir_r2()


def test_exigir_r2_nomeia_primeira_variavel_faltante() -> None:
    ambiente = {k: v for k, v in AMBIENTE_R2_COMPLETO.items() if k != "R2_BUCKET"}
    config = Configuracao.do_ambiente(ambiente)

    with pytest.raises(ErroConfiguracao, match="R2_BUCKET"):
        config.exigir_r2()


@pytest.mark.parametrize(
    ("variavel", "valor"),
    [
        ("LLM_MAX_TENTATIVAS_QA", "abc"),
        ("IMAGEM_TAMANHO_MAX_KB", "1.5"),
        ("PESO_KG", "cem gramas"),
        ("PRODUTO_ATIVO", "X"),
    ],
)
def test_valor_invalido_nomeia_variavel_e_valor(variavel: str, valor: str) -> None:
    with pytest.raises(ErroConfiguracao, match=variavel) as erro:
        Configuracao.do_ambiente({variavel: valor})
    assert erro.value.valor_invalido == valor.upper() if variavel == "PRODUTO_ATIVO" else valor


def test_configuracao_e_imutavel() -> None:
    config = Configuracao.do_ambiente({})

    with pytest.raises(AttributeError):
        config.produto_ativo = "N"  # type: ignore[misc]
