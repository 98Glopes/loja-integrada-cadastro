from collections.abc import Mapping, Sequence
from decimal import Decimal
from pathlib import Path

import pytest
from openpyxl import Workbook

from loja_integrada_cadastro.infra.leitor_planilha_entrada_openpyxl import (
    LeitorPlanilhaEntradaOpenpyxl,
)
from loja_integrada_cadastro.models.exceptions.erro_planilha_entrada import ErroPlanilhaEntrada
from loja_integrada_cadastro.models.layout_planilha_entrada import COLUNAS_PLANILHA_ENTRADA


def _planilha(
    tmp_path: Path,
    linhas: Sequence[Mapping[str, object]],
    cabecalho: Sequence[str] = COLUNAS_PLANILHA_ENTRADA,
    nome: str = "planilha.xlsx",
) -> Path:
    workbook = Workbook()
    aba = workbook.active
    assert aba is not None
    aba.append(list(cabecalho))
    for linha in linhas:
        aba.append([linha.get(coluna, "") for coluna in cabecalho])
    caminho = tmp_path / nome
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
        "colecao": "Outono/Inverno 2026",
        "faixa-tamanho": "P ao G",
        "cor": "Beige",
        "tamanho": "P",
        "gtin": "7891234567895",
        "preco": "119,90",
        "estoque": 10,
    }
    base.update(sobrescritas)
    return base


def _linha_variacao(**sobrescritas: object) -> dict[str, object]:
    """Linha só com sku-pai + campos de variação (produto já lido na 1ª linha do grupo)."""
    base: dict[str, object] = {
        "sku-pai": "3254002",
        "cor": "Beige",
        "tamanho": "P",
        "gtin": "7891234567895",
        "preco": "119,90",
        "estoque": 10,
    }
    base.update(sobrescritas)
    return base


def test_um_produto_com_duas_cores_e_tres_tamanhos(tmp_path: Path) -> None:
    combinacoes = [(cor, tamanho) for cor in ("Beige", "Rosa") for tamanho in ("P", "M", "G")]
    linhas = [
        _linha_produto(cor=cor, tamanho=tamanho, gtin=f"78912345678{indice:02d}")
        for indice, (cor, tamanho) in enumerate(combinacoes)
    ]
    caminho = _planilha(tmp_path, linhas)

    produtos = LeitorPlanilhaEntradaOpenpyxl().ler(caminho)

    assert len(produtos) == 1
    produto = produtos[0]
    assert produto.sku_pai == "3254002"
    assert len(produto.variacoes) == 6
    assert produto.cores == ("Beige", "Rosa")
    assert produto.tamanhos == ("P", "M", "G")


def test_campos_de_produto_lidos_so_na_primeira_linha(tmp_path: Path) -> None:
    linhas = [_linha_produto(), _linha_variacao(tamanho="G")]
    caminho = _planilha(tmp_path, linhas)

    produtos = LeitorPlanilhaEntradaOpenpyxl().ler(caminho)

    assert len(produtos) == 1
    assert produtos[0].marca == "kiki"
    assert produtos[0].faixa_tamanho == "P ao G"
    assert len(produtos[0].variacoes) == 2


def test_preco_aceita_virgula_e_ponto(tmp_path: Path) -> None:
    linhas = [_linha_produto(preco="119,90"), _linha_variacao(tamanho="G", preco="129.90")]
    caminho = _planilha(tmp_path, linhas)

    produtos = LeitorPlanilhaEntradaOpenpyxl().ler(caminho)

    precos = {variacao.preco for variacao in produtos[0].variacoes}
    assert precos == {Decimal("119.90"), Decimal("129.90")}


def test_linha_totalmente_vazia_no_meio_do_grupo_e_ignorada(tmp_path: Path) -> None:
    linhas = [_linha_produto(), {}, _linha_variacao(tamanho="G")]
    caminho = _planilha(tmp_path, linhas)

    produtos = LeitorPlanilhaEntradaOpenpyxl().ler(caminho)

    assert len(produtos) == 1
    assert len(produtos[0].variacoes) == 2


def test_categoria_e_dividida_por_maior_que(tmp_path: Path) -> None:
    caminho = _planilha(tmp_path, [_linha_produto(categoria="Linha Kids > Menina > Vestido")])

    produtos = LeitorPlanilhaEntradaOpenpyxl().ler(caminho)

    assert produtos[0].categoria == ("Linha Kids", "Menina", "Vestido")


def test_ordem_de_colunas_diferente_da_sugerida_ainda_funciona(tmp_path: Path) -> None:
    cabecalho_embaralhado = tuple(reversed(COLUNAS_PLANILHA_ENTRADA))
    caminho = _planilha(tmp_path, [_linha_produto()], cabecalho=cabecalho_embaralhado)

    produtos = LeitorPlanilhaEntradaOpenpyxl().ler(caminho)

    assert produtos[0].sku_pai == "3254002"


def test_gtin_digitado_como_numero_nao_fica_com_sufixo_ponto_zero(tmp_path: Path) -> None:
    caminho = _planilha(tmp_path, [_linha_produto(gtin=7891234567895.0)])

    produtos = LeitorPlanilhaEntradaOpenpyxl().ler(caminho)

    assert produtos[0].variacoes[0].gtin == "7891234567895"


def test_multiplos_produtos_preservam_ordem_de_aparicao(tmp_path: Path) -> None:
    linhas = [_linha_produto(**{"sku-pai": "B"}), _linha_produto(**{"sku-pai": "A"})]
    caminho = _planilha(tmp_path, linhas)

    produtos = LeitorPlanilhaEntradaOpenpyxl().ler(caminho)

    assert [produto.sku_pai for produto in produtos] == ["B", "A"]


def test_colecao_vazia_nao_gera_erro_e_fica_none(tmp_path: Path) -> None:
    caminho = _planilha(tmp_path, [_linha_produto(colecao="")])

    produtos = LeitorPlanilhaEntradaOpenpyxl().ler(caminho)

    assert produtos[0].colecao is None


def test_linha_mais_curta_que_o_cabecalho_trata_colunas_finais_como_vazias(
    tmp_path: Path,
) -> None:
    """Reproduz o comportamento real do Excel/Sheets: quando as últimas colunas de uma linha
    nunca foram digitadas, o arquivo não guarda célula nenhuma ali e `openpyxl` (modo
    `read_only`) devolve uma tupla mais curta que a do cabeçalho para aquela linha — não deve
    estourar `IndexError`, só tratar a coluna faltando como célula vazia.
    """
    cabecalho = (*[c for c in COLUNAS_PLANILHA_ENTRADA if c != "colecao"], "colecao")
    workbook = Workbook()
    aba = workbook.active
    assert aba is not None
    aba.append(list(cabecalho))
    linha_completa = _linha_produto()
    valores_sem_colecao = [linha_completa[coluna] for coluna in cabecalho if coluna != "colecao"]
    aba.append(valores_sem_colecao)  # linha fisicamente sem a última célula (colecao)
    caminho = tmp_path / "planilha.xlsx"
    workbook.save(caminho)

    produtos = LeitorPlanilhaEntradaOpenpyxl().ler(caminho)

    assert produtos[0].colecao is None


def test_coluna_obrigatoria_faltando_leva_erro_antes_de_processar_linhas(tmp_path: Path) -> None:
    cabecalho_sem_gtin = tuple(coluna for coluna in COLUNAS_PLANILHA_ENTRADA if coluna != "gtin")
    caminho = _planilha(tmp_path, [_linha_produto()], cabecalho=cabecalho_sem_gtin)

    with pytest.raises(ErroPlanilhaEntrada) as excinfo:
        LeitorPlanilhaEntradaOpenpyxl().ler(caminho)

    assert any(problema.coluna == "gtin" for problema in excinfo.value.problemas)


def test_coluna_desconhecida_no_cabecalho_gera_erro(tmp_path: Path) -> None:
    cabecalho_com_extra = (*COLUNAS_PLANILHA_ENTRADA, "peso")
    caminho = _planilha(tmp_path, [_linha_produto()], cabecalho=cabecalho_com_extra)

    with pytest.raises(ErroPlanilhaEntrada) as excinfo:
        LeitorPlanilhaEntradaOpenpyxl().ler(caminho)

    assert any(problema.coluna == "peso" for problema in excinfo.value.problemas)


def test_conflito_de_campo_de_produto_entre_linhas_gera_erro(tmp_path: Path) -> None:
    linhas = [_linha_produto(), _linha_variacao(tamanho="G", marca="outra-marca")]
    caminho = _planilha(tmp_path, linhas)

    with pytest.raises(ErroPlanilhaEntrada) as excinfo:
        LeitorPlanilhaEntradaOpenpyxl().ler(caminho)

    problema = next(p for p in excinfo.value.problemas if p.coluna == "marca")
    assert "kiki" in problema.motivo
    assert "outra-marca" in problema.motivo


def test_sku_pai_vazio_gera_erro(tmp_path: Path) -> None:
    caminho = _planilha(tmp_path, [_linha_produto(**{"sku-pai": ""})])

    with pytest.raises(ErroPlanilhaEntrada) as excinfo:
        LeitorPlanilhaEntradaOpenpyxl().ler(caminho)

    assert any(problema.coluna == "sku-pai" for problema in excinfo.value.problemas)


def test_estoque_nao_numerico_gera_erro(tmp_path: Path) -> None:
    caminho = _planilha(tmp_path, [_linha_produto(estoque="dez")])

    with pytest.raises(ErroPlanilhaEntrada) as excinfo:
        LeitorPlanilhaEntradaOpenpyxl().ler(caminho)

    assert any(problema.coluna == "estoque" for problema in excinfo.value.problemas)


def test_preco_invalido_gera_erro(tmp_path: Path) -> None:
    caminho = _planilha(tmp_path, [_linha_produto(preco="abc")])

    with pytest.raises(ErroPlanilhaEntrada) as excinfo:
        LeitorPlanilhaEntradaOpenpyxl().ler(caminho)

    assert any(problema.coluna == "preco" for problema in excinfo.value.problemas)


def test_celula_obrigatoria_de_produto_vazia_gera_erro(tmp_path: Path) -> None:
    caminho = _planilha(tmp_path, [_linha_produto(marca="")])

    with pytest.raises(ErroPlanilhaEntrada) as excinfo:
        LeitorPlanilhaEntradaOpenpyxl().ler(caminho)

    assert any(problema.coluna == "marca" for problema in excinfo.value.problemas)


def test_multiplos_problemas_de_linhas_diferentes_sao_acumulados(tmp_path: Path) -> None:
    linhas = [
        _linha_produto(**{"sku-pai": "A"}, estoque="dez"),
        _linha_produto(**{"sku-pai": "B"}, preco="abc"),
    ]
    caminho = _planilha(tmp_path, linhas)

    with pytest.raises(ErroPlanilhaEntrada) as excinfo:
        LeitorPlanilhaEntradaOpenpyxl().ler(caminho)

    colunas_com_problema = {problema.coluna for problema in excinfo.value.problemas}
    assert colunas_com_problema == {"estoque", "preco"}


def test_arquivo_inexistente_gera_erro(tmp_path: Path) -> None:
    with pytest.raises(ErroPlanilhaEntrada):
        LeitorPlanilhaEntradaOpenpyxl().ler(tmp_path / "nao-existe.xlsx")


def test_arquivo_corrompido_gera_erro(tmp_path: Path) -> None:
    caminho = tmp_path / "corrompido.xlsx"
    caminho.write_text("isso não é um .xlsx")

    with pytest.raises(ErroPlanilhaEntrada):
        LeitorPlanilhaEntradaOpenpyxl().ler(caminho)
