from __future__ import annotations

from decimal import Decimal
from pathlib import Path

from loja_integrada_cadastro.models.foto_produto import FotoProduto
from loja_integrada_cadastro.models.nomeador_fotos import NomeadorFotos, SeletorImagensPai
from loja_integrada_cadastro.models.produto_entrada import ProdutoEntrada
from loja_integrada_cadastro.models.variacao_entrada import VariacaoEntrada


def _produto(
    marca: str = "Marca",
    tipo_peca: str = "Tipo",
    nome_fornecedor: str = "Nome",
    cores: tuple[str, ...] = ("Cor",),
) -> ProdutoEntrada:
    return ProdutoEntrada(
        sku_pai="SKU1",
        marca=marca,
        nome_fornecedor=nome_fornecedor,
        tipo_peca=tipo_peca,
        categoria=("Categoria",),
        composicao="100% algodão",
        detalhes="detalhes",
        colecao=None,
        faixa_tamanho="P ao G",
        variacoes=tuple(
            VariacaoEntrada(
                cor=cor, tamanho="P", gtin="7891234567895", preco=Decimal("10"), estoque=1
            )
            for cor in cores
        ),
    )


class TestNomear:
    def test_exemplo_literal_arquitetura(self) -> None:
        produto = _produto(
            marca="Onda Marinha",
            tipo_peca="Conjunto",
            nome_fornecedor="Conjunto Baby Malha e Moletom",
        )
        nome = NomeadorFotos.nomear(produto, "Azul aco", 1)
        assert nome == "onda-marinha-conjunto-baby-malha-e-moletom-azul-aco-1.jpg"

    def test_sem_dedupe_quando_tipo_nao_e_prefixo(self) -> None:
        produto = _produto(marca="Kiki", tipo_peca="Vestido", nome_fornecedor="Florzinha")
        nome = NomeadorFotos.nomear(produto, "Rosa", 2)
        assert nome == "kiki-vestido-florzinha-rosa-2.jpg"

    def test_dedupe_zera_nome_fornecedor_quando_igual_ao_tipo(self) -> None:
        produto = _produto(marca="Somnii", tipo_peca="Vestido", nome_fornecedor="Vestido")
        nome = NomeadorFotos.nomear(produto, "Beige", 1)
        assert nome == "somnii-vestido-beige-1.jpg"

    def test_truncamento_em_60_caracteres(self) -> None:
        produto = _produto(
            marca="Marca",
            tipo_peca="Tipo",
            nome_fornecedor=(
                "Nome Fornecedor Extremamente Longo Que Ultrapassa O Limite De Caracteres"
            ),
        )
        nome = NomeadorFotos.nomear(produto, "Preto", 3)
        base, sufixo = nome.rsplit("-preto-3.jpg", 1)
        assert sufixo == ""
        assert len(base) <= 60
        assert not base.endswith("-")

    def test_cor_com_acento_e_espaco(self) -> None:
        produto = _produto(marca="Marca", tipo_peca="Tipo", nome_fornecedor="Nome")
        nome = NomeadorFotos.nomear(produto, "Verde Água", 1)
        assert nome == "marca-tipo-nome-verde-agua-1.jpg"


class TestSelecionar:
    @staticmethod
    def _foto(cor: str, ordem: int) -> FotoProduto:
        return FotoProduto(
            sku_pai="SKU1",
            cor=cor,
            ordem=ordem,
            arquivo_origem=Path(f"{cor}-{ordem}.jpg"),
            nome=f"{cor.lower()}-{ordem}.jpg",
            chave=f"produtos/SKU1/{cor.lower()}-{ordem}.jpg",
        )

    def test_round_robin_duas_cores_quatro_fotos_cada(self) -> None:
        fotos = [
            self._foto("Beige", 1),
            self._foto("Beige", 2),
            self._foto("Beige", 3),
            self._foto("Beige", 4),
            self._foto("Rosa", 1),
            self._foto("Rosa", 2),
            self._foto("Rosa", 3),
            self._foto("Rosa", 4),
        ]
        selecionadas = SeletorImagensPai.selecionar(fotos)
        assert [(foto.cor, foto.ordem) for foto in selecionadas] == [
            ("Beige", 1),
            ("Rosa", 1),
            ("Beige", 2),
            ("Rosa", 2),
            ("Beige", 3),
        ]

    def test_uma_cor_com_seis_fotos_limita_em_cinco(self) -> None:
        fotos = [self._foto("Preto", ordem) for ordem in range(1, 7)]
        selecionadas = SeletorImagensPai.selecionar(fotos)
        assert [foto.ordem for foto in selecionadas] == [1, 2, 3, 4, 5]

    def test_total_menor_que_cinco_devolve_todas(self) -> None:
        fotos = [self._foto("Azul", 1), self._foto("Azul", 2)]
        selecionadas = SeletorImagensPai.selecionar(fotos)
        assert selecionadas == fotos

    def test_lista_vazia(self) -> None:
        assert SeletorImagensPai.selecionar([]) == []
