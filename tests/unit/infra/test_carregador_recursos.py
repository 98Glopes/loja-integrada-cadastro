from datetime import date
from decimal import Decimal
from typing import Any

import pytest

from loja_integrada_cadastro.infra.carregador_recursos import (
    CarregadorRecursos,
    extrair_palavras_proibidas,
    montar_dados_mestre,
    montar_tabela_precos_llm,
)
from loja_integrada_cadastro.models.exceptions.erro_recursos import ErroRecursos

MARCAS_CANONICAS = frozenset(
    {
        "kiki",
        "Onda Marinha",
        "Colorittá",
        "somnii",
        "Menina Anjo",
        "Luc.boo",
        "Nina Go",
        "Kyly",
        "Lemon",
    }
)
RECURSOS_DE_TEXTO = (
    "loja.md",
    "copy.md",
    "seo.md",
    "qa.md",
    "marcas/_generico.md",
    "marcas/kiki.md",
    "marcas/onda-marinha.md",
    "marcas/coloritta.md",
    "marcas/somnii.md",
    "marcas/menina-anjo.md",
    "marcas/luc-boo.md",
    "marcas/nina-go.md",
    "marcas/kyly.md",
    "marcas/lemon.md",
)


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


# --- recursos de conteúdo (task 13) --------------------------------------------------------


@pytest.mark.parametrize("nome", RECURSOS_DE_TEXTO)
def test_recursos_de_conteudo_carregam_do_pacote_real(nome: str) -> None:
    conteudo = CarregadorRecursos().texto(nome)

    assert conteudo.startswith("# ")
    assert len(conteudo.split()) > 50


@pytest.mark.parametrize("nome", RECURSOS_DE_TEXTO)
def test_recursos_de_conteudo_nao_pedem_url_foto_nem_sufixo_da_loja(nome: str) -> None:
    conteudo = CarregadorRecursos().texto(nome)

    assert "| Kmilaa Modas" not in conteudo
    assert ".jpg" not in conteudo
    assert "Foto 1" not in conteudo


@pytest.mark.parametrize("marca", ["Menina Anjo", "Kyly"])
def test_perfil_marca_devolve_perfil_proprio(marca: str) -> None:
    perfil = CarregadorRecursos().perfil_marca(marca)

    assert perfil.marca == marca
    assert perfil.generico is False
    assert perfil.texto.startswith(f"# {marca}")
    assert "Big Idea" in perfil.texto


def test_perfil_marca_inexistente_cai_no_generico_e_sinaliza() -> None:
    carregador = CarregadorRecursos()

    perfil = carregador.perfil_marca("Marca Nova")

    assert perfil.marca == "Marca Nova"
    assert perfil.generico is True
    assert perfil.texto == carregador.texto("marcas/_generico.md")


def test_toda_marca_canonica_do_dados_mestre_tem_perfil_proprio() -> None:
    carregador = CarregadorRecursos()

    for marca in carregador.dados_mestre().marcas_canonicas:
        assert carregador.perfil_marca(marca).generico is False, marca


def test_marcas_com_perfil_lista_as_nove_marcas_canonicas() -> None:
    assert CarregadorRecursos().marcas_com_perfil() == MARCAS_CANONICAS


def test_palavras_proibidas_do_seo_real() -> None:
    palavras = CarregadorRecursos().palavras_proibidas()

    assert {"lindo", "incrível", "qualidade incomparável"} <= palavras
    assert "especial" not in palavras


def test_extrair_palavras_proibidas_le_so_a_secao_e_normaliza_caixa() -> None:
    markdown = (
        "# SEO\n\n## Outra seção\n\n- não conta\n\n## Palavras proibidas\n\nTexto.\n\n"
        "- Lindo\n- Qualidade Incomparável \n\n## Depois\n\n- também não conta\n"
    )

    assert extrair_palavras_proibidas(markdown) == frozenset({"lindo", "qualidade incomparável"})


def test_extrair_palavras_proibidas_falha_sem_secao() -> None:
    with pytest.raises(ErroRecursos, match="Palavras proibidas"):
        extrair_palavras_proibidas("# SEO\n\n- lindo\n")


def test_extrair_palavras_proibidas_falha_com_secao_vazia() -> None:
    with pytest.raises(ErroRecursos, match="sem itens"):
        extrair_palavras_proibidas("## Palavras proibidas\n\nNada.\n\n## Fim\n")


# --- preços LLM (task 12) ------------------------------------------------------------------


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
