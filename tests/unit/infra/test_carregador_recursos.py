from typing import Any

import pytest

from loja_integrada_cadastro.infra.carregador_recursos import (
    CarregadorRecursos,
    montar_dados_mestre,
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
