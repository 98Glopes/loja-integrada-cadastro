from pathlib import Path

import pytest

from loja_integrada_cadastro.cli import AplicacaoCli

SUBCOMANDOS = ("modelo-entrada", "validar", "processar", "verificar")


def test_help_lista_os_quatro_subcomandos(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as saida:
        AplicacaoCli().executar(["--help"])

    assert saida.value.code == 0
    ajuda = capsys.readouterr().out
    for subcomando in SUBCOMANDOS:
        assert subcomando in ajuda


@pytest.mark.parametrize(
    "argumentos",
    [
        ["modelo-entrada"],
        ["validar", "--planilha", "p.xlsx", "--fotos", "fotos"],
        ["processar", "--planilha", "p.xlsx", "--fotos", "fotos", "--lote", "lote-1"],
        ["verificar", "--lote", "lote-1"],
    ],
    ids=SUBCOMANDOS,
)
def test_subcomando_retorna_2_e_avisa_nao_implementado(
    argumentos: list[str], capsys: pytest.CaptureFixture[str]
) -> None:
    codigo = AplicacaoCli().executar(argumentos)

    assert codigo == 2
    assert f"{argumentos[0]}: não implementado" in capsys.readouterr().err


def test_processar_parseia_todos_os_argumentos() -> None:
    opcoes = (
        AplicacaoCli()
        .criar_parser()
        .parse_args(
            [
                "processar",
                "--planilha",
                "produtos.xlsx",
                "--fotos",
                "fotos",
                "--lote",
                "2026-09-w38",
                "--incluir-reprovados",
                "--refazer-textos",
                "A1",
                "B2",
                "--refazer-fotos",
                "C3",
            ]
        )
    )

    assert opcoes.comando == "processar"
    assert opcoes.planilha == Path("produtos.xlsx")
    assert opcoes.fotos == Path("fotos")
    assert opcoes.lote == "2026-09-w38"
    assert opcoes.incluir_reprovados is True
    assert opcoes.refazer_textos == ["A1", "B2"]
    assert opcoes.refazer_fotos == ["C3"]


def test_processar_tem_flags_desligadas_por_padrao() -> None:
    opcoes = (
        AplicacaoCli()
        .criar_parser()
        .parse_args(["processar", "--planilha", "p.xlsx", "--fotos", "f", "--lote", "l"])
    )

    assert opcoes.incluir_reprovados is False
    assert opcoes.refazer_textos == []
    assert opcoes.refazer_fotos == []


def test_modelo_entrada_tem_destino_padrao() -> None:
    opcoes = AplicacaoCli().criar_parser().parse_args(["modelo-entrada"])

    assert opcoes.destino == Path("modelo-entrada.xlsx")


def test_verificar_aceita_esperar() -> None:
    opcoes = (
        AplicacaoCli().criar_parser().parse_args(["verificar", "--lote", "l", "--esperar", "5m"])
    )

    assert opcoes.esperar == "5m"


@pytest.mark.parametrize(
    "argumentos",
    [
        [],
        ["processar", "--planilha", "p.xlsx", "--fotos", "f"],
        ["validar", "--planilha", "p.xlsx"],
        ["verificar"],
    ],
    ids=["sem-subcomando", "processar-sem-lote", "validar-sem-fotos", "verificar-sem-lote"],
)
def test_argumento_obrigatorio_ausente_e_erro_de_uso(
    argumentos: list[str], capsys: pytest.CaptureFixture[str]
) -> None:
    with pytest.raises(SystemExit) as saida:
        AplicacaoCli().executar(argumentos)

    assert saida.value.code == 2
    assert "usage" in capsys.readouterr().err
