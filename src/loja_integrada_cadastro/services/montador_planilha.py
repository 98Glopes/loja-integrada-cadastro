from __future__ import annotations

from collections.abc import Mapping, Sequence

from loja_integrada_cadastro.models.estado_produto import EstadoProduto
from loja_integrada_cadastro.models.linha_planilha import LinhaPlanilha
from loja_integrada_cadastro.models.padroes_fisicos import PadroesFisicos
from loja_integrada_cadastro.models.slug import slugificar
from loja_integrada_cadastro.models.status_produto import StatusProduto
from loja_integrada_cadastro.models.variacao_entrada import VariacaoEntrada

_STATUS_INCLUIDOS_SEMPRE = frozenset({StatusProduto.PRONTO})
_STATUS_INCLUIDOS_COM_REPROVADOS = frozenset({StatusProduto.PRONTO, StatusProduto.REPROVADO_QA})


class MontadorPlanilha:
    """Monta as linhas pai/filha de um produto no layout de 54 colunas (`docs/ARQUITETURA.md`
    §7), a partir de um `EstadoProduto` com textos e imagens já registrados.

    Só transforma dados já existentes no estado — não muda `estado.status` nem chama nenhum
    método de intenção; marcar o produto como `pronto` é responsabilidade de quem orquestra o
    lote (task 11).
    """

    def __init__(self, padroes_fisicos: PadroesFisicos, ativo: str) -> None:
        self._padroes_fisicos = padroes_fisicos
        self._ativo = ativo

    def montar(self, estado: EstadoProduto) -> list[LinhaPlanilha]:
        """Devolve 1 linha pai seguida de 1 linha filha por variação da entrada."""
        entrada = estado.entrada
        textos = estado.textos or {}
        linha_pai = self._montar_pai(estado, textos)
        linhas_filhas = [
            self._montar_filha(entrada.sku_pai, variacao) for variacao in entrada.variacoes
        ]
        return [linha_pai, *linhas_filhas]

    def montar_lote(
        self, estados: Sequence[EstadoProduto], incluir_reprovados: bool = False
    ) -> list[LinhaPlanilha]:
        """Concatena `montar` para os estados prontos para exportação.

        Sempre inclui `pronto`. Com `incluir_reprovados=True`, também inclui `reprovado-qa`
        cujo `estado.textos` não seja `None` — hoje isso nunca ocorre (`reprovar_qa` não
        guarda o último texto tentado; isso chega na task 16), então o parâmetro é aceito mas
        ainda não muda o resultado.
        """
        status_permitidos = (
            _STATUS_INCLUIDOS_COM_REPROVADOS if incluir_reprovados else _STATUS_INCLUIDOS_SEMPRE
        )
        linhas: list[LinhaPlanilha] = []
        for estado in estados:
            if estado.status not in status_permitidos:
                continue
            if estado.status is StatusProduto.REPROVADO_QA and estado.textos is None:
                continue
            linhas.extend(self.montar(estado))
        return linhas

    def _montar_pai(self, estado: EstadoProduto, textos: Mapping[str, str]) -> LinhaPlanilha:
        entrada = estado.entrada
        valores: dict[str, object] = {
            "tipo": "com-variacao",
            "sku": entrada.sku_pai,
            "ativo": self._ativo,
            "usado": "N",
            "destaque": "N",
            "nome": textos.get("titulo", ""),
            "seo-tag-title": textos.get("seo_tag_title", ""),
            "seo-tag-description": textos.get("seo_tag_description", ""),
            "descricao-completa": textos.get("descricao_html", ""),
            "preco-sob-consulta": "N",
            "marca": entrada.marca,
        }
        for nivel, nome_categoria in enumerate(entrada.categoria, start=1):
            valores[f"categoria-nome-nivel-{nivel}"] = nome_categoria
        for posicao, url in enumerate(estado.imagens_pai[:5], start=1):
            valores[f"imagem-{posicao}"] = url
        return LinhaPlanilha(tipo="com-variacao", valores=valores)

    def _montar_filha(self, sku_pai: str, variacao: VariacaoEntrada) -> LinhaPlanilha:
        padroes = self._padroes_fisicos
        sku = f"{sku_pai}-{slugificar(variacao.cor)}-{slugificar(variacao.tamanho)}"
        valores: dict[str, object] = {
            "tipo": "variacao",
            "sku-pai": sku_pai,
            "sku": sku,
            "ativo": self._ativo,
            "usado": "N",
            "destaque": "N",
            "gtin": variacao.gtin,
            "estoque-gerenciado": "S",
            "estoque-quantidade": variacao.estoque,
            "estoque-situacao-em-estoque": "imediata",
            "estoque-situacao-sem-estoque": "indisponivel",
            "preco-sob-consulta": "N",
            "preco-custo": 0.0,
            "preco-cheio": float(variacao.preco),
            "preco-promocional": 0.0,
            "peso-em-kg": float(padroes.peso_kg),
            "altura-em-cm": float(padroes.altura_cm),
            "largura-em-cm": float(padroes.largura_cm),
            "comprimento-em-cm": float(padroes.comprimento_cm),
            "grade-produto-com-uma-cor": variacao.cor,
            "grade-tamanho-infantil": variacao.tamanho,
        }
        return LinhaPlanilha(tipo="variacao", valores=valores)
