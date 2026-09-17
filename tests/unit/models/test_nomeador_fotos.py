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
    def test_exemplo_literal_arquitetura_sem_cor(self) -> None:
        produto = _produto(
            marca="Onda Marinha",
            tipo_peca="Conjunto",
            nome_fornecedor="Conjunto Baby Malha e Moletom",
        )
        nome = NomeadorFotos.nomear(produto, 1)
        assert nome == "onda-marinha-conjunto-baby-malha-e-moletom-1.jpg"

    def test_sem_dedupe_quando_tipo_nao_e_prefixo(self) -> None:
        produto = _produto(marca="Kiki", tipo_peca="Vestido", nome_fornecedor="Florzinha")
        nome = NomeadorFotos.nomear(produto, 2)
        assert nome == "kiki-vestido-florzinha-2.jpg"

    def test_dedupe_zera_nome_fornecedor_quando_igual_ao_tipo(self) -> None:
        produto = _produto(marca="Somnii", tipo_peca="Vestido", nome_fornecedor="Vestido")
        nome = NomeadorFotos.nomear(produto, 1)
        assert nome == "somnii-vestido-1.jpg"

    def test_truncamento_em_60_caracteres(self) -> None:
        produto = _produto(
            marca="Marca",
            tipo_peca="Tipo",
            nome_fornecedor=(
                "Nome Fornecedor Extremamente Longo Que Ultrapassa O Limite De Caracteres"
            ),
        )
        nome = NomeadorFotos.nomear(produto, 3)
        base, sufixo = nome.rsplit("-3.jpg", 1)
        assert sufixo == ""
        assert len(base) <= 60
        assert not base.endswith("-")


class TestSelecionar:
    @staticmethod
    def _foto(ordem: int) -> FotoProduto:
        return FotoProduto(
            sku_pai="SKU1",
            ordem=ordem,
            arquivo_origem=Path(f"{ordem}.jpg"),
            nome=f"foto-{ordem}.jpg",
            chave=f"produtos/SKU1/foto-{ordem}.jpg",
        )

    def test_devolve_as_5_primeiras_em_ordem(self) -> None:
        fotos = [self._foto(ordem) for ordem in (3, 1, 5, 2, 4, 6, 7)]
        selecionadas = SeletorImagensPai.selecionar(fotos)
        assert [foto.ordem for foto in selecionadas] == [1, 2, 3, 4, 5]

    def test_total_menor_que_cinco_devolve_todas_em_ordem(self) -> None:
        fotos = [self._foto(2), self._foto(1)]
        selecionadas = SeletorImagensPai.selecionar(fotos)
        assert [foto.ordem for foto in selecionadas] == [1, 2]

    def test_lista_vazia(self) -> None:
        assert SeletorImagensPai.selecionar([]) == []
