from decimal import Decimal
from pathlib import Path

from loja_integrada_cadastro.models.dados_mestre import DadosMestre
from loja_integrada_cadastro.models.produto_entrada import ProdutoEntrada
from loja_integrada_cadastro.models.variacao_entrada import VariacaoEntrada
from loja_integrada_cadastro.services.validador_entrada import ValidadorEntrada


class CatalogoFotosFake:
    """Fake do port `CatalogoFotos`: dict em memória, sem tocar o disco."""

    def __init__(self, dados: dict[str, dict[str, list[Path]]] | None = None) -> None:
        self._dados = dados or {}

    def listar(self, sku_pai: str) -> dict[str, list[Path]]:
        return self._dados.get(sku_pai, {})

    def cores_disponiveis(self, sku_pai: str) -> list[str]:
        return list(self._dados.get(sku_pai, {}).keys())


def _gtin(corpo: str) -> str:
    """Monta um GTIN válido a partir do corpo, calculando o dígito verificador (GS1)."""
    digitos = [int(caractere) for caractere in corpo]
    soma = sum(
        digito * (3 if indice % 2 == 0 else 1) for indice, digito in enumerate(reversed(digitos))
    )
    return corpo + str((10 - soma % 10) % 10)


GTIN_1 = _gtin("789123456780")
GTIN_2 = _gtin("789123456781")
GTIN_INVALIDO = GTIN_1[:-1] + str((int(GTIN_1[-1]) + 1) % 10)

FOTO_PADRAO = {"Beige": [Path("beige-1.jpg")]}


def _dados_mestre() -> DadosMestre:
    return DadosMestre(
        marcas_canonicas={"kiki": ("Kiki", "KIKI"), "somnii": ()},
        marcas_proibidas={"Açucena": "não é uma marca própria"},
        cores=frozenset({"Beige", "Rosa", "Preto"}),
        tamanhos=frozenset({"P", "M", "G"}),
        categorias_referencia=frozenset({"Linha Baby > Menina > Vestido"}),
    )


def _variacao(
    cor: str = "Beige",
    tamanho: str = "P",
    gtin: str = GTIN_1,
    preco: Decimal = Decimal("119.90"),
    estoque: int = 10,
) -> VariacaoEntrada:
    return VariacaoEntrada(cor=cor, tamanho=tamanho, gtin=gtin, preco=preco, estoque=estoque)


def _produto(
    sku_pai: str = "3254002",
    marca: str = "kiki",
    nome_fornecedor: str = "Conjunto Baby",
    tipo_peca: str = "Conjunto",
    categoria: tuple[str, ...] = ("Linha Baby", "Menina", "Vestido"),
    composicao: str = "100% algodão",
    detalhes: str = "Botões na gola",
    colecao: str | None = None,
    faixa_tamanho: str = "P ao G",
    variacoes: tuple[VariacaoEntrada, ...] = (),
) -> ProdutoEntrada:
    return ProdutoEntrada(
        sku_pai=sku_pai,
        marca=marca,
        nome_fornecedor=nome_fornecedor,
        tipo_peca=tipo_peca,
        categoria=categoria,
        composicao=composicao,
        detalhes=detalhes,
        colecao=colecao,
        faixa_tamanho=faixa_tamanho,
        variacoes=variacoes or (_variacao(),),
    )


def _validador(
    catalogo: CatalogoFotosFake | None = None, marcas_com_perfil: frozenset[str] = frozenset()
) -> ValidadorEntrada:
    return ValidadorEntrada(_dados_mestre(), catalogo or CatalogoFotosFake(), marcas_com_perfil)


# --- marca -------------------------------------------------------------------------------


def test_marca_alias_normaliza_para_canonica() -> None:
    catalogo = CatalogoFotosFake({"3254002": FOTO_PADRAO})
    produtos, resultado = _validador(catalogo).validar([_produto(marca="Kiki")])

    assert produtos[0].marca == "kiki"
    assert resultado.aprovado is True


def test_marca_sem_perfil_gera_aviso() -> None:
    _, resultado = _validador().validar([_produto(marca="kiki")])

    assert any(aviso.campo == "marca" for aviso in resultado.avisos)


def test_marca_com_perfil_nao_gera_aviso() -> None:
    _, resultado = _validador(marcas_com_perfil=frozenset({"kiki"})).validar([_produto()])

    assert not any(aviso.campo == "marca" for aviso in resultado.avisos)


def test_marca_proibida_gera_problema_com_motivo() -> None:
    _, resultado = _validador().validar([_produto(marca="Açucena")])

    assert resultado.aprovado is False
    problema = resultado.problemas[0]
    assert problema.campo == "marca"
    assert "não é uma marca própria" in problema.mensagem


def test_marca_desconhecida_gera_problema() -> None:
    _, resultado = _validador().validar([_produto(marca="MarcaInexistente")])

    assert resultado.aprovado is False
    assert "desconhecida" in resultado.problemas[0].mensagem


# --- cor / tamanho -------------------------------------------------------------------------


def test_cor_invalida_gera_problema() -> None:
    catalogo = CatalogoFotosFake({"3254002": {"Amarelo": [Path("a.jpg")]}})
    _, resultado = _validador(catalogo).validar([_produto(variacoes=(_variacao(cor="Amarelo"),))])

    assert resultado.aprovado is False
    assert resultado.problemas[0].campo == "cor"


def test_tamanho_invalido_gera_problema() -> None:
    catalogo = CatalogoFotosFake({"3254002": FOTO_PADRAO})
    _, resultado = _validador(catalogo).validar([_produto(variacoes=(_variacao(tamanho="XG"),))])

    assert resultado.aprovado is False
    assert resultado.problemas[0].campo == "tamanho"


# --- gtin ----------------------------------------------------------------------------------


def test_gtin_nao_numerico_gera_problema() -> None:
    catalogo = CatalogoFotosFake({"3254002": FOTO_PADRAO})
    _, resultado = _validador(catalogo).validar([_produto(variacoes=(_variacao(gtin="ABC"),))])

    assert resultado.aprovado is False
    assert resultado.problemas[0].campo == "gtin"


def test_gtin_tamanho_invalido_gera_problema() -> None:
    catalogo = CatalogoFotosFake({"3254002": FOTO_PADRAO})
    _, resultado = _validador(catalogo).validar([_produto(variacoes=(_variacao(gtin="123"),))])

    assert resultado.aprovado is False
    assert resultado.problemas[0].campo == "gtin"


def test_gtin_digito_verificador_invalido_gera_problema() -> None:
    catalogo = CatalogoFotosFake({"3254002": FOTO_PADRAO})
    produto = _produto(variacoes=(_variacao(gtin=GTIN_INVALIDO),))

    _, resultado = _validador(catalogo).validar([produto])

    assert resultado.aprovado is False
    assert "dígito verificador" in resultado.problemas[0].mensagem


def test_gtin_duplicado_no_lote_gera_problema_nos_dois_produtos() -> None:
    catalogo = CatalogoFotosFake({"A": FOTO_PADRAO, "B": FOTO_PADRAO})
    produto_a = _produto(sku_pai="A", variacoes=(_variacao(gtin=GTIN_1),))
    produto_b = _produto(sku_pai="B", variacoes=(_variacao(gtin=GTIN_1),))

    _, resultado = _validador(catalogo).validar([produto_a, produto_b])

    skus_com_problema = {
        problema.sku_pai for problema in resultado.problemas if problema.campo == "gtin"
    }
    assert skus_com_problema == {"A", "B"}


# --- preço / estoque -----------------------------------------------------------------------


def test_preco_zero_ou_negativo_gera_problema() -> None:
    catalogo = CatalogoFotosFake({"3254002": FOTO_PADRAO})
    _, resultado = _validador(catalogo).validar(
        [_produto(variacoes=(_variacao(preco=Decimal("0")),))]
    )

    assert resultado.aprovado is False
    assert resultado.problemas[0].campo == "preco"


def test_estoque_negativo_gera_problema() -> None:
    catalogo = CatalogoFotosFake({"3254002": FOTO_PADRAO})
    _, resultado = _validador(catalogo).validar([_produto(variacoes=(_variacao(estoque=-1),))])

    assert resultado.aprovado is False
    assert resultado.problemas[0].campo == "estoque"


# --- combinações / limites -------------------------------------------------------------------


def test_combinacao_cor_tamanho_duplicada_gera_problema() -> None:
    catalogo = CatalogoFotosFake({"3254002": FOTO_PADRAO})
    variacoes = (_variacao(gtin=GTIN_1), _variacao(gtin=GTIN_2))

    _, resultado = _validador(catalogo).validar([_produto(variacoes=variacoes)])

    assert any(problema.campo == "cor-tamanho" for problema in resultado.problemas)


def test_mais_de_50_variacoes_gera_problema() -> None:
    catalogo = CatalogoFotosFake({"3254002": {"Beige": [Path("a.jpg")], "Rosa": [Path("b.jpg")]}})
    variacoes = tuple(
        _variacao(
            cor="Beige" if i % 2 == 0 else "Rosa", tamanho="P", gtin=_gtin(f"78912345{i:04d}")
        )
        for i in range(51)
    )

    _, resultado = _validador(catalogo).validar([_produto(variacoes=variacoes)])

    assert any(problema.campo == "variacoes" for problema in resultado.problemas)


def test_sku_pai_duplicado_no_lote_gera_problema() -> None:
    catalogo = CatalogoFotosFake({"3254002": FOTO_PADRAO})
    produtos = [_produto(), _produto(variacoes=(_variacao(gtin=GTIN_2),))]

    _, resultado = _validador(catalogo).validar(produtos)

    assert any(problema.campo == "sku-pai" for problema in resultado.problemas)


# --- categoria -------------------------------------------------------------------------------


def test_categoria_com_mais_de_5_niveis_gera_problema() -> None:
    catalogo = CatalogoFotosFake({"3254002": FOTO_PADRAO})
    categoria = ("a", "b", "c", "d", "e", "f")

    _, resultado = _validador(catalogo).validar([_produto(categoria=categoria)])

    assert any(problema.campo == "categoria" for problema in resultado.problemas)


def test_categoria_com_espaco_extra_gera_problema() -> None:
    catalogo = CatalogoFotosFake({"3254002": FOTO_PADRAO})

    _, resultado = _validador(catalogo).validar([_produto(categoria=("Linha Baby ", "Menina"))])

    assert any(problema.campo == "categoria" for problema in resultado.problemas)


def test_categoria_fora_da_referencia_gera_aviso() -> None:
    catalogo = CatalogoFotosFake({"3254002": FOTO_PADRAO})

    _, resultado = _validador(catalogo).validar([_produto(categoria=("Outra", "Categoria"))])

    assert resultado.aprovado is True
    assert any(aviso.campo == "categoria" for aviso in resultado.avisos)


# --- campos obrigatórios -----------------------------------------------------------------------


def test_campo_obrigatorio_vazio_gera_problema() -> None:
    catalogo = CatalogoFotosFake({"3254002": FOTO_PADRAO})

    _, resultado = _validador(catalogo).validar([_produto(detalhes="  ")])

    assert any(problema.campo == "detalhes" for problema in resultado.problemas)


# --- fotos ---------------------------------------------------------------------------------


def test_cor_sem_pasta_de_fotos_gera_problema() -> None:
    catalogo = CatalogoFotosFake({})

    _, resultado = _validador(catalogo).validar([_produto()])

    assert resultado.aprovado is False
    assert resultado.problemas[0].campo == "fotos"


def test_pasta_de_fotos_sem_arquivo_gera_problema() -> None:
    catalogo = CatalogoFotosFake({"3254002": {"Beige": []}})

    _, resultado = _validador(catalogo).validar([_produto()])

    assert resultado.aprovado is False
    assert resultado.problemas[0].campo == "fotos"


def test_subpasta_sem_cor_correspondente_gera_aviso() -> None:
    catalogo = CatalogoFotosFake({"3254002": {"Beige": [Path("a.jpg")], "Preto": [Path("b.jpg")]}})

    _, resultado = _validador(catalogo).validar([_produto()])

    assert resultado.aprovado is True
    assert any(aviso.campo == "fotos" and "Preto" in aviso.mensagem for aviso in resultado.avisos)


def test_mais_de_5_fotos_gera_aviso() -> None:
    catalogo = CatalogoFotosFake({"3254002": {"Beige": [Path(f"{i}.jpg") for i in range(6)]}})

    _, resultado = _validador(catalogo).validar([_produto()])

    assert resultado.aprovado is True
    assert any("6 fotos" in aviso.mensagem for aviso in resultado.avisos)


def test_casamento_de_fotos_ignora_caixa_e_acento() -> None:
    catalogo = CatalogoFotosFake({"3254002": {"beige": [Path("a.jpg")]}})

    _, resultado = _validador(catalogo).validar([_produto(variacoes=(_variacao(cor="Beige"),))])

    assert resultado.aprovado is True
    assert not any(aviso.campo == "fotos" for aviso in resultado.avisos)


# --- lote feliz ------------------------------------------------------------------------------


def test_lote_feliz_aprova_sem_problemas() -> None:
    catalogo = CatalogoFotosFake(
        {
            "3254002": {"Beige": [Path("a.jpg")], "Rosa": [Path("b.jpg")]},
            "3254010": {"Preto": [Path("c.jpg")]},
        }
    )
    produtos = [
        _produto(
            sku_pai="3254002",
            variacoes=(
                _variacao(cor="Beige", tamanho="P", gtin=GTIN_1),
                _variacao(cor="Rosa", tamanho="M", gtin=GTIN_2),
            ),
        ),
        _produto(
            sku_pai="3254010",
            marca="somnii",
            variacoes=(_variacao(cor="Preto", tamanho="G", gtin=_gtin("789123456790")),),
        ),
    ]

    produtos_normalizados, resultado = _validador(catalogo).validar(produtos)

    assert resultado.problemas == ()
    assert len(produtos_normalizados) == 2
