from collections.abc import Mapping, Sequence
from pathlib import Path

import pytest
from openpyxl import Workbook

from loja_integrada_cadastro.cli import AplicacaoCli
from loja_integrada_cadastro.models.layout_planilha_entrada import COLUNAS_PLANILHA_ENTRADA

SUBCOMANDOS = ("modelo-entrada", "validar", "processar", "verificar")


def _planilha(tmp_path: Path, linhas: Sequence[Mapping[str, object]]) -> Path:
    workbook = Workbook()
    aba = workbook.active
    assert aba is not None
    aba.append(list(COLUNAS_PLANILHA_ENTRADA))
    for linha in linhas:
        aba.append([linha.get(coluna, "") for coluna in COLUNAS_PLANILHA_ENTRADA])
    caminho = tmp_path / "planilha.xlsx"
    workbook.save(caminho)
    return caminho


def _linha_produto(**sobrescritas: object) -> dict[str, object]:
    base: dict[str, object] = {
        "sku-pai": "3254002",
        "marca": "kiki",
        "nome-fornecedor": "Conjunto Baby Malha e Moletom",
        "tipo-peca": "Conjunto",
        "categoria": "Linha Baby (P ao XG) > Menino > Conjunto",
        "composicao": "100% algodão",
        "detalhes": "Botões na gola",
        "colecao": "",
        "faixa-tamanho": "P ao G",
        "cor": "Beige",
        "tamanho": "P",
        "gtin": "7891234567895",
        "preco": "119,90",
        "estoque": 10,
    }
    base.update(sobrescritas)
    return base


def _pasta_de_fotos(tmp_path: Path, sku_pai: str = "3254002", cor: str = "Beige") -> Path:
    raiz = tmp_path / "fotos"
    pasta = raiz / sku_pai / cor
    pasta.mkdir(parents=True)
    (pasta / "foto-1.jpg").write_bytes(b"fake")
    return raiz


def test_help_lista_os_quatro_subcomandos(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as saida:
        AplicacaoCli().executar(["--help"])

    assert saida.value.code == 0
    ajuda = capsys.readouterr().out
    for subcomando in SUBCOMANDOS:
        assert subcomando in ajuda


def test_verificar_retorna_2_e_avisa_nao_implementado(
    capsys: pytest.CaptureFixture[str],
) -> None:
    codigo = AplicacaoCli().executar(["verificar", "--lote", "lote-1"])

    assert codigo == 2
    assert "verificar: não implementado" in capsys.readouterr().err


def test_processar_sem_configuracao_r2_retorna_erro_de_negocio(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    # cwd sem `.env` + variáveis de ambiente do R2 removidas: garante que `Configuracao.
    # do_ambiente()` (chamada sem argumento por `_processar`, igual à CLI real) não enxerga
    # nenhuma credencial de verdade, mesmo que o `.env` do desenvolvedor tenha uma.
    monkeypatch.chdir(tmp_path)
    for variavel in (
        "R2_ACCOUNT_ID",
        "R2_ACCESS_KEY_ID",
        "R2_SECRET_ACCESS_KEY",
        "R2_BUCKET",
        "R2_URL_PUBLICA",
    ):
        monkeypatch.delenv(variavel, raising=False)

    codigo = AplicacaoCli().executar(
        ["processar", "--planilha", "p.xlsx", "--fotos", "fotos", "--lote", "lote-1"]
    )

    assert codigo == 1
    assert "processar: Variável de ambiente obrigatória não definida: R2_ACCOUNT_ID" in (
        capsys.readouterr().err
    )


def test_validar_aprova_planilha_e_fotos_validas(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    planilha = _planilha(tmp_path, [_linha_produto()])
    fotos = _pasta_de_fotos(tmp_path)

    codigo = AplicacaoCli().executar(
        ["validar", "--planilha", str(planilha), "--fotos", str(fotos)]
    )

    assert codigo == 0
    assert "validar: aprovado" in capsys.readouterr().out


def test_validar_retorna_1_e_lista_problema_de_cor_invalida(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    planilha = _planilha(tmp_path, [_linha_produto(cor="Amarelo Fluorescente")])
    fotos = _pasta_de_fotos(tmp_path, cor="Amarelo Fluorescente")

    codigo = AplicacaoCli().executar(
        ["validar", "--planilha", str(planilha), "--fotos", str(fotos)]
    )

    saida = capsys.readouterr().out
    assert codigo == 1
    assert "SKU 3254002" in saida
    assert "cor" in saida
    assert "validar: reprovado" in saida


def test_validar_planilha_invalida_retorna_codigo_erro_negocio(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    planilha = _planilha(tmp_path, [_linha_produto(marca="")])
    fotos = _pasta_de_fotos(tmp_path)

    codigo = AplicacaoCli().executar(
        ["validar", "--planilha", str(planilha), "--fotos", str(fotos)]
    )

    assert codigo == 1
    assert "validar:" in capsys.readouterr().err


def test_modelo_entrada_gera_arquivo_no_destino(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    destino = tmp_path / "modelo-entrada.xlsx"

    codigo = AplicacaoCli().executar(["modelo-entrada", "--destino", str(destino)])

    assert codigo == 0
    assert destino.exists()
    assert f"modelo-entrada: gerado em {destino}" in capsys.readouterr().out


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
