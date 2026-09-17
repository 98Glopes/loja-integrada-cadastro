from __future__ import annotations

import unicodedata
from collections import Counter
from collections.abc import Sequence
from dataclasses import replace

from loja_integrada_cadastro.models.dados_mestre import DadosMestre
from loja_integrada_cadastro.models.produto_entrada import ProdutoEntrada
from loja_integrada_cadastro.models.resultado_validacao import (
    ProblemaValidacao,
    ResultadoValidacao,
)
from loja_integrada_cadastro.services.ports.catalogo_fotos import CatalogoFotos

MAX_VARIACOES_POR_PRODUTO = 50
MAX_NIVEIS_CATEGORIA = 5
MAX_FOTOS_POR_PRODUTO = 5
TAMANHOS_GTIN_VALIDOS = frozenset({8, 12, 13, 14})


class ValidadorEntrada:
    """Reprova cedo o que faria a importação real falhar; avisa sobre o que merece atenção.

    Ver `docs/ARQUITETURA.md` §3 (etapa 1) e `docs/regras-planilha-loja-integrada.md`. Marca
    reconhecida (canônica ou alias) é normalizada para a grafia canônica nos produtos devolvidos;
    os demais campos voltam como vieram.
    """

    def __init__(
        self,
        dados_mestre: DadosMestre,
        catalogo_fotos: CatalogoFotos,
        marcas_com_perfil: frozenset[str] = frozenset(),
    ) -> None:
        self._dados_mestre = dados_mestre
        self._catalogo_fotos = catalogo_fotos
        self._marcas_com_perfil = marcas_com_perfil

    def validar(
        self, produtos: Sequence[ProdutoEntrada]
    ) -> tuple[list[ProdutoEntrada], ResultadoValidacao]:
        contagem_sku_pai = Counter(produto.sku_pai for produto in produtos)
        contagem_gtin = Counter(
            variacao.gtin for produto in produtos for variacao in produto.variacoes
        )

        normalizados: list[ProdutoEntrada] = []
        problemas: list[ProblemaValidacao] = []
        avisos: list[ProblemaValidacao] = []
        for produto in produtos:
            produto_normalizado, problemas_produto, avisos_produto = self._validar_produto(
                produto, contagem_sku_pai, contagem_gtin
            )
            normalizados.append(produto_normalizado)
            problemas.extend(problemas_produto)
            avisos.extend(avisos_produto)

        return normalizados, ResultadoValidacao(tuple(problemas), tuple(avisos))

    def _validar_produto(
        self,
        produto: ProdutoEntrada,
        contagem_sku_pai: Counter[str],
        contagem_gtin: Counter[str],
    ) -> tuple[ProdutoEntrada, list[ProblemaValidacao], list[ProblemaValidacao]]:
        problemas: list[ProblemaValidacao] = []
        avisos: list[ProblemaValidacao] = []

        produto = self._validar_e_normalizar_marca(produto, problemas, avisos)
        self._validar_campos_obrigatorios(produto, problemas)
        self._validar_categoria(produto, problemas, avisos)
        if contagem_sku_pai[produto.sku_pai] > 1:
            problemas.append(
                ProblemaValidacao(produto.sku_pai, "sku-pai", "sku-pai duplicado no lote")
            )
        self._validar_variacoes(produto, contagem_gtin, problemas)
        self._validar_fotos(produto, problemas, avisos)

        return produto, problemas, avisos

    def _validar_e_normalizar_marca(
        self,
        produto: ProdutoEntrada,
        problemas: list[ProblemaValidacao],
        avisos: list[ProblemaValidacao],
    ) -> ProdutoEntrada:
        canonica = self._dados_mestre.marca_canonica(produto.marca)
        if canonica is None:
            motivo = self._dados_mestre.motivo_marca_proibida(produto.marca)
            mensagem = (
                f"marca proibida '{produto.marca}': {motivo}"
                if motivo is not None
                else f"marca desconhecida: '{produto.marca}'"
            )
            problemas.append(ProblemaValidacao(produto.sku_pai, "marca", mensagem))
            return produto

        if canonica not in self._marcas_com_perfil:
            avisos.append(
                ProblemaValidacao(
                    produto.sku_pai,
                    "marca",
                    f"'{canonica}' sem perfil de marca próprio; usará conteúdo genérico",
                )
            )
        return replace(produto, marca=canonica)

    @staticmethod
    def _validar_campos_obrigatorios(
        produto: ProdutoEntrada, problemas: list[ProblemaValidacao]
    ) -> None:
        campos = (
            ("nome-fornecedor", produto.nome_fornecedor),
            ("tipo-peca", produto.tipo_peca),
            ("composicao", produto.composicao),
            ("detalhes", produto.detalhes),
            ("faixa-tamanho", produto.faixa_tamanho),
        )
        for coluna, valor in campos:
            if not valor.strip():
                problemas.append(
                    ProblemaValidacao(produto.sku_pai, coluna, "campo obrigatório vazio")
                )

    def _validar_categoria(
        self,
        produto: ProdutoEntrada,
        problemas: list[ProblemaValidacao],
        avisos: list[ProblemaValidacao],
    ) -> None:
        niveis = produto.categoria
        if not niveis or len(niveis) > MAX_NIVEIS_CATEGORIA:
            problemas.append(
                ProblemaValidacao(
                    produto.sku_pai,
                    "categoria",
                    f"categoria precisa ter de 1 a {MAX_NIVEIS_CATEGORIA} níveis, "
                    f"tem {len(niveis)}",
                )
            )
            return

        for nivel in niveis:
            if nivel != nivel.strip() or "  " in nivel or _tem_caractere_controle(nivel):
                problemas.append(
                    ProblemaValidacao(
                        produto.sku_pai, "categoria", f"nível de categoria mal formatado: '{nivel}'"
                    )
                )

        caminho = " > ".join(niveis)
        if not self._dados_mestre.categoria_conhecida(caminho):
            avisos.append(
                ProblemaValidacao(
                    produto.sku_pai,
                    "categoria",
                    f"categoria fora da lista de referência: '{caminho}'",
                )
            )

    def _validar_variacoes(
        self,
        produto: ProdutoEntrada,
        contagem_gtin: Counter[str],
        problemas: list[ProblemaValidacao],
    ) -> None:
        if len(produto.variacoes) > MAX_VARIACOES_POR_PRODUTO:
            problemas.append(
                ProblemaValidacao(
                    produto.sku_pai,
                    "variacoes",
                    f"{len(produto.variacoes)} variações no produto, "
                    f"máximo é {MAX_VARIACOES_POR_PRODUTO}",
                )
            )

        for cor in produto.cores:
            if not self._dados_mestre.cor_valida(cor):
                problemas.append(
                    ProblemaValidacao(produto.sku_pai, "cor", f"cor fora da lista mestre: '{cor}'")
                )
        for tamanho in produto.tamanhos:
            if not self._dados_mestre.tamanho_valido(tamanho):
                problemas.append(
                    ProblemaValidacao(
                        produto.sku_pai,
                        "tamanho",
                        f"tamanho fora da lista mestre: '{tamanho}'",
                    )
                )

        combinacoes_vistas: set[tuple[str, str]] = set()
        for variacao in produto.variacoes:
            combinacao = (variacao.cor, variacao.tamanho)
            if combinacao in combinacoes_vistas:
                problemas.append(
                    ProblemaValidacao(
                        produto.sku_pai,
                        "cor-tamanho",
                        f"combinação repetida: cor '{variacao.cor}', tamanho '{variacao.tamanho}'",
                    )
                )
            combinacoes_vistas.add(combinacao)

            self._validar_gtin(produto.sku_pai, variacao.gtin, contagem_gtin, problemas)
            if variacao.preco <= 0:
                problemas.append(
                    ProblemaValidacao(
                        produto.sku_pai,
                        "preco",
                        f"preço precisa ser maior que zero: {variacao.preco}",
                    )
                )
            if variacao.estoque < 0:
                problemas.append(
                    ProblemaValidacao(
                        produto.sku_pai,
                        "estoque",
                        f"estoque não pode ser negativo: {variacao.estoque}",
                    )
                )

    @staticmethod
    def _validar_gtin(
        sku_pai: str, gtin: str, contagem_gtin: Counter[str], problemas: list[ProblemaValidacao]
    ) -> None:
        if not gtin.isdigit() or len(gtin) not in TAMANHOS_GTIN_VALIDOS:
            problemas.append(
                ProblemaValidacao(
                    sku_pai, "gtin", f"GTIN precisa ter 8, 12, 13 ou 14 dígitos numéricos: '{gtin}'"
                )
            )
            return
        if not _digito_verificador_valido(gtin):
            problemas.append(
                ProblemaValidacao(sku_pai, "gtin", f"dígito verificador inválido: '{gtin}'")
            )
            return
        if contagem_gtin[gtin] > 1:
            problemas.append(
                ProblemaValidacao(sku_pai, "gtin", f"GTIN duplicado no lote: '{gtin}'")
            )

    def _validar_fotos(
        self,
        produto: ProdutoEntrada,
        problemas: list[ProblemaValidacao],
        avisos: list[ProblemaValidacao],
    ) -> None:
        """Fotos não têm cor (valem para o produto inteiro): só confere se existe alguma."""
        arquivos = self._catalogo_fotos.listar(produto.sku_pai)
        if not arquivos:
            problemas.append(
                ProblemaValidacao(
                    produto.sku_pai, "fotos", "nenhuma foto encontrada para o produto"
                )
            )
            return

        if len(arquivos) > MAX_FOTOS_POR_PRODUTO:
            avisos.append(
                ProblemaValidacao(
                    produto.sku_pai,
                    "fotos",
                    f"{len(arquivos)} fotos encontradas; só as {MAX_FOTOS_POR_PRODUTO} "
                    "primeiras serão usadas",
                )
            )


def _digito_verificador_valido(gtin: str) -> bool:
    """Confere o dígito verificador GTIN (GS1): mod10, pesos alternados 3/1 da direita."""
    digitos = [int(caractere) for caractere in gtin]
    corpo, digito_informado = digitos[:-1], digitos[-1]
    soma = sum(
        digito * (3 if indice % 2 == 0 else 1) for indice, digito in enumerate(reversed(corpo))
    )
    digito_calculado = (10 - soma % 10) % 10
    return digito_calculado == digito_informado


def _tem_caractere_controle(texto: str) -> bool:
    return any(unicodedata.category(caractere) == "Cc" for caractere in texto)
