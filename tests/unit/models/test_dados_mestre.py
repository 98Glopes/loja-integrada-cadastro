import pytest

from loja_integrada_cadastro.models.dados_mestre import DadosMestre


def _dados_mestre_exemplo() -> DadosMestre:
    return DadosMestre(
        marcas_canonicas={
            "kiki": ("Kiki", "Kiki Xodó", "KIKI"),
            "Colorittá": ("Coloritta", "colorittá"),
        },
        marcas_proibidas={
            "Açucena": (
                "É o nome do grupo fornecedor (dono de Onda Marinha, Nina Go e Somnii), "
                "não uma marca — existe em 26 produtos legados que ficam como estão por decisão."
            ),
        },
        cores=frozenset({"Cinza Claro", "Preto", "Branco"}),
        tamanhos=frozenset({"P", "M", "G", "GG", "XG", "14"}),
        categorias_referencia=frozenset({"Linha Baby (P ao XG) > Menino > Conjunto"}),
    )


@pytest.mark.parametrize(
    "texto",
    ["Kiki Xodó", "KIKI XODÓ", "kiki xodo", "kiki", "KIKI"],
)
def test_marca_canonica_resolve_alias_e_canonica_ignorando_caixa_e_acento(texto: str) -> None:
    assert _dados_mestre_exemplo().marca_canonica(texto) == "kiki"


@pytest.mark.parametrize("texto", ["Coloritta", "colorittá", "COLORITTA", "Colorittá"])
def test_marca_canonica_resolve_alias_com_diferenca_de_acento(texto: str) -> None:
    assert _dados_mestre_exemplo().marca_canonica(texto) == "Colorittá"


def test_marca_canonica_retorna_none_para_marca_desconhecida() -> None:
    assert _dados_mestre_exemplo().marca_canonica("MarcaInexistente") is None


@pytest.mark.parametrize("texto", ["Açucena", "AÇUCENA", "açucena"])
def test_motivo_marca_proibida_retorna_texto_ignorando_caixa_e_acento(texto: str) -> None:
    motivo = _dados_mestre_exemplo().motivo_marca_proibida(texto)
    assert motivo is not None
    assert "grupo fornecedor" in motivo


def test_motivo_marca_proibida_retorna_none_para_marca_valida() -> None:
    assert _dados_mestre_exemplo().motivo_marca_proibida("kiki") is None


def test_cor_valida_e_comparacao_exata() -> None:
    dados = _dados_mestre_exemplo()
    assert dados.cor_valida("Cinza Claro") is True
    assert dados.cor_valida("cinza claro") is False


def test_cor_valida_falso_para_cor_desconhecida() -> None:
    assert _dados_mestre_exemplo().cor_valida("Amarelo Fluorescente") is False


def test_tamanho_valido_e_comparacao_exata() -> None:
    dados = _dados_mestre_exemplo()
    assert dados.tamanho_valido("GG") is True
    assert dados.tamanho_valido("gg") is False
    assert dados.tamanho_valido("14") is True
    assert dados.tamanho_valido("15") is False


def test_categoria_conhecida_true_para_caminho_observado() -> None:
    dados = _dados_mestre_exemplo()
    assert dados.categoria_conhecida("Linha Baby (P ao XG) > Menino > Conjunto") is True


def test_categoria_conhecida_false_para_caminho_desconhecido() -> None:
    dados = _dados_mestre_exemplo()
    assert dados.categoria_conhecida("Linha Teen (12 ao 18) > Menina > Vestido") is False
