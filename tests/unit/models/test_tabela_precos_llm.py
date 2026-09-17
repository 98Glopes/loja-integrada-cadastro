from datetime import date
from decimal import Decimal

import pytest

from loja_integrada_cadastro.models.exceptions.erro_recursos import ErroRecursos
from loja_integrada_cadastro.models.preco_modelo_llm import PrecoModeloLlm
from loja_integrada_cadastro.models.tabela_precos_llm import TabelaPrecosLlm

_OPUS = PrecoModeloLlm(
    entrada=Decimal("5"),
    saida=Decimal("25"),
    cache_leitura=Decimal("0.5"),
    cache_escrita=Decimal("6.25"),
)
_TABELA = TabelaPrecosLlm(precos={"claude-opus-5": _OPUS}, data_referencia=date(2026, 9, 16))


def test_custo_soma_os_quatro_componentes_por_milhao_de_tokens() -> None:
    custo = _OPUS.custo(
        tokens_entrada=1_000_000,
        tokens_saida=1_000_000,
        tokens_cache_leitura=1_000_000,
        tokens_cache_escrita=1_000_000,
    )

    assert custo == Decimal("36.75")


def test_custo_de_uma_chamada_tipica_em_decimal_exato() -> None:
    custo = _OPUS.custo(
        tokens_entrada=1_500, tokens_saida=1_000, tokens_cache_leitura=4_000, tokens_cache_escrita=0
    )

    assert custo == Decimal("0.0345")


def test_exigir_devolve_o_preco_do_modelo_cadastrado() -> None:
    assert _TABELA.exigir("claude-opus-5") is _OPUS


def test_exigir_levanta_erro_recursos_nomeando_os_modelos_conhecidos() -> None:
    with pytest.raises(ErroRecursos, match="claude-sonnet-9.*claude-opus-5"):
        _TABELA.exigir("claude-sonnet-9")
