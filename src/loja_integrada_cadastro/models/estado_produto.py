from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal

from loja_integrada_cadastro.models.exceptions.erro_transicao_estado_invalida import (
    ErroTransicaoEstadoInvalida,
)
from loja_integrada_cadastro.models.foto_produto import FotoProduto
from loja_integrada_cadastro.models.produto_entrada import ProdutoEntrada
from loja_integrada_cadastro.models.resultado_validacao import ResultadoValidacao
from loja_integrada_cadastro.models.status_produto import StatusProduto

# Statuses de origem em que cada método de intenção pode ser chamado.
_ORIGENS_ETAPA_FOTOS = frozenset({StatusProduto.VALIDADO, StatusProduto.ERRO_FOTOS})
_ORIGENS_ETAPA_TEXTOS = frozenset({StatusProduto.FOTOS_PUBLICADAS, StatusProduto.ERRO_LLM})


@dataclass
class EstadoProduto:
    """Progresso de um produto do lote pelas etapas do pipeline (`docs/ARQUITETURA.md` §8).

    Único agregado mutável do sistema: os campos não devem ser reatribuídos diretamente por fora
    desta classe, só através dos métodos de intenção (`registrar_fotos`, `registrar_textos`…),
    que também validam a transição de status. Não existe construtor "vazio": um `EstadoProduto`
    só nasce já validado ou reprovado na validação, pela fábrica `registrar_validacao`.
    """

    sku_pai: str
    status: StatusProduto
    entrada: ProdutoEntrada
    hash_entrada: str
    validacao: ResultadoValidacao
    fotos: tuple[FotoProduto, ...] = ()
    imagens_pai: tuple[str, ...] = ()
    textos: Mapping[str, str] | None = None
    tentativas: tuple[Mapping[str, object], ...] = ()
    custo_usd_estimado: Decimal = Decimal("0")
    verificacao: Mapping[str, object] | None = None
    atualizado_em: datetime = field(default_factory=lambda: datetime.now(UTC))

    @classmethod
    def registrar_validacao(
        cls,
        sku_pai: str,
        entrada: ProdutoEntrada,
        hash_entrada: str,
        resultado: ResultadoValidacao,
    ) -> EstadoProduto:
        """Cria o `EstadoProduto` de um produto a partir do resultado da etapa 1 (validar)."""
        status = StatusProduto.VALIDADO if resultado.aprovado else StatusProduto.REPROVADO_VALIDACAO
        return cls(
            sku_pai=sku_pai,
            status=status,
            entrada=entrada,
            hash_entrada=hash_entrada,
            validacao=resultado,
        )

    def registrar_fotos(self, fotos: tuple[FotoProduto, ...], imagens_pai: tuple[str, ...]) -> None:
        """Registra o sucesso da etapa 2 (fotos comprimidas e publicadas no R2)."""
        self._exigir_origem("registrar_fotos", _ORIGENS_ETAPA_FOTOS)
        self.fotos = fotos
        self.imagens_pai = imagens_pai
        self._concluir(StatusProduto.FOTOS_PUBLICADAS)

    def registrar_erro_fotos(self) -> None:
        """Registra falha na etapa 2, retomável numa próxima execução."""
        self._exigir_origem("registrar_erro_fotos", _ORIGENS_ETAPA_FOTOS)
        self._concluir(StatusProduto.ERRO_FOTOS)

    def registrar_tentativa(
        self, tentativa: Mapping[str, object], custo_usd: Decimal = Decimal("0")
    ) -> None:
        """Acrescenta uma tentativa de geração de texto (Copywriter/SEO/QA); não muda o status."""
        self._exigir_origem("registrar_tentativa", _ORIGENS_ETAPA_TEXTOS)
        self.tentativas = (*self.tentativas, tentativa)
        self.custo_usd_estimado += custo_usd
        self._tocar()

    def registrar_textos(self, textos: Mapping[str, str]) -> None:
        """Registra o sucesso da etapa 3 (textos aprovados pelo QA)."""
        self._exigir_origem("registrar_textos", _ORIGENS_ETAPA_TEXTOS)
        self.textos = textos
        self._concluir(StatusProduto.TEXTOS_GERADOS)

    def registrar_erro_llm(self) -> None:
        """Registra falha de infraestrutura (API Anthropic) durante a etapa 3."""
        self._exigir_origem("registrar_erro_llm", _ORIGENS_ETAPA_TEXTOS)
        self._concluir(StatusProduto.ERRO_LLM)

    def reprovar_qa(self) -> None:
        """Registra o esgotamento das tentativas de QA (produto fica fora do `.xlsx`).

        O último texto tentado e os motivos da reprovação já estão em `tentativas`
        (`registrar_tentativa` é chamado a cada rodada, antes desta).
        """
        self._exigir_origem("reprovar_qa", _ORIGENS_ETAPA_TEXTOS)
        self._concluir(StatusProduto.REPROVADO_QA)

    def marcar_pronto(self) -> None:
        """Registra que o produto foi montado na planilha de saída (etapa 4)."""
        self._exigir_origem("marcar_pronto", frozenset({StatusProduto.TEXTOS_GERADOS}))
        self._concluir(StatusProduto.PRONTO)

    def registrar_verificacao(self, verificacao: Mapping[str, object]) -> None:
        """Registra o resultado da verificação pós-importação (`verificar`, etapa 9)."""
        self._exigir_origem("registrar_verificacao", frozenset({StatusProduto.PRONTO}))
        self.verificacao = verificacao
        self._tocar()

    def _concluir(self, status: StatusProduto) -> None:
        self.status = status
        self._tocar()

    def _tocar(self) -> None:
        self.atualizado_em = datetime.now(UTC)

    def _exigir_origem(self, metodo: str, origens: frozenset[StatusProduto]) -> None:
        if self.status not in origens:
            raise ErroTransicaoEstadoInvalida(self.sku_pai, self.status, metodo)
