from datetime import date
from decimal import Decimal
from typing import Any

import pytest

from loja_integrada_cadastro.infra.carregador_recursos import (
    CarregadorRecursos,
    montar_dados_mestre,
    montar_tabela_precos_llm,
)
from loja_integrada_cadastro.models.exceptions.erro_recursos import ErroRecursos


def _dict_dados_mestre_completo() -> dict[str, Any]:
    return {
        "marcas": {
            "canonicas": {
                "kiki": {"aliases": ["Kiki", "Kiki Xodó", "KIKI"]},
                "Colorittá": {"aliases": ["Coloritta"]},
            },
            "proibidas": {"Açucena": "É o nome do grupo fornecedor, não uma marca."},
        },
        "cores": [{"nome": "Cinza Claro", "uso": 10}, {"nome": "Preto", "uso": 5}],
        "tamanhos": ["P", "M", "14"],
        "categorias_referencia": ["Linha Baby (P ao XG) > Menino > Conjunto"],
    }


def test_dados_mestre_carrega_do_pacote_real() -> None:
    dados = CarregadorRecursos().dados_mestre()

    assert dados.cor_valida("Cinza Claro") is True
    assert dados.cor_valida("cinza claro") is False
    assert dados.marca_canonica("Kiki Xodó") == "kiki"
    motivo = dados.motivo_marca_proibida("Açucena")
    assert motivo is not None and "grupo fornecedor" in motivo


def test_texto_le_recurso_existente() -> None:
    conteudo = CarregadorRecursos().texto("dados_mestre.yaml")

    assert conteudo.strip() != ""
    assert "marcas:" in conteudo


def test_texto_levanta_erro_recursos_para_arquivo_inexistente() -> None:
    with pytest.raises(ErroRecursos, match="nao_existe.md"):
        CarregadorRecursos().texto("nao_existe.md")


def test_montar_dados_mestre_com_dict_completo_funciona() -> None:
    dados = montar_dados_mestre(_dict_dados_mestre_completo())

    assert dados.marca_canonica("Kiki Xodó") == "kiki"
    assert dados.marca_canonica("Coloritta") == "Colorittá"
    assert dados.motivo_marca_proibida("AÇUCENA") is not None
    assert dados.cor_valida("Cinza Claro") is True
    assert dados.tamanho_valido("14") is True
    assert dados.categoria_conhecida("Linha Baby (P ao XG) > Menino > Conjunto") is True


def test_montar_dados_mestre_falha_sem_secao_obrigatoria() -> None:
    bruto = _dict_dados_mestre_completo()
    del bruto["cores"]

    with pytest.raises(ErroRecursos, match="cores"):
        montar_dados_mestre(bruto)


def test_montar_dados_mestre_falha_com_tamanho_nao_string() -> None:
    bruto = _dict_dados_mestre_completo()
    bruto["tamanhos"] = [1, 2]

    with pytest.raises(ErroRecursos, match="tamanhos"):
        montar_dados_mestre(bruto)


def test_montar_dados_mestre_falha_com_conteudo_nao_mapeamento() -> None:
    with pytest.raises(ErroRecursos):
        montar_dados_mestre(["não é um dict"])


def _dict_precos_completo() -> dict[str, Any]:
    return {
        "data_referencia": date(2026, 9, 16),
        "modelos": {
            "claude-opus-5": {
                "entrada": 5.0,
                "saida": 25,
                "cache_leitura": 0.5,
                "cache_escrita": 6.25,
            }
        },
    }


def test_precos_llm_carrega_do_pacote_real_com_os_modelos_da_arquitetura() -> None:
    tabela = CarregadorRecursos().precos_llm()

    assert set(tabela.precos) >= {
        "claude-opus-5",
        "claude-opus-4-8",
        "claude-sonnet-5",
        "claude-haiku-4-5",
    }
    assert tabela.exigir("claude-opus-5").saida == Decimal("25")
    assert tabela.data_referencia == date(2026, 9, 16)


def test_montar_tabela_precos_llm_converte_numeros_em_decimal_exato() -> None:
    tabela = montar_tabela_precos_llm(_dict_precos_completo())

    preco = tabela.exigir("claude-opus-5")
    assert preco.entrada == Decimal("5.0")
    assert preco.saida == Decimal("25")
    assert preco.cache_escrita == Decimal("6.25")


@pytest.mark.parametrize("chave", ["data_referencia", "modelos"])
def test_montar_tabela_precos_llm_falha_sem_campo_obrigatorio(chave: str) -> None:
    bruto = _dict_precos_completo()
    del bruto[chave]

    with pytest.raises(ErroRecursos, match=chave):
        montar_tabela_precos_llm(bruto)


def test_montar_tabela_precos_llm_falha_com_preco_nao_numerico() -> None:
    bruto = _dict_precos_completo()
    bruto["modelos"]["claude-opus-5"]["saida"] = "25"

    with pytest.raises(ErroRecursos, match="'saida' do modelo 'claude-opus-5'"):
        montar_tabela_precos_llm(bruto)


def test_montar_tabela_precos_llm_falha_com_preco_ausente() -> None:
    bruto = _dict_precos_completo()
    del bruto["modelos"]["claude-opus-5"]["cache_leitura"]

    with pytest.raises(ErroRecursos, match="cache_leitura"):
        montar_tabela_precos_llm(bruto)
