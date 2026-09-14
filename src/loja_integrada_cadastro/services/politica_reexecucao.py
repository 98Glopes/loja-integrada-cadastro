from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from loja_integrada_cadastro.models.estado_produto import EstadoProduto
from loja_integrada_cadastro.models.status_produto import StatusProduto


class EtapaLote(Enum):
    """Etapa do pipeline por onde uma reexecução deve retomar (`docs/ARQUITETURA.md` §3)."""

    VALIDAR = "validar"
    FOTOS = "fotos"
    TEXTOS = "textos"
    MONTAR = "montar"


class DecisaoReexecucao(Enum):
    """O que fazer com um produto ao reexecutar o lote."""

    PULAR = "pular"
    RETOMAR = "retomar"
    RECOMECAR = "recomecar"


@dataclass(frozen=True)
class ResultadoPoliticaReexecucao:
    """Decisão da `PoliticaReexecucao` para um produto."""

    decisao: DecisaoReexecucao
    a_partir_de: EtapaLote | None

    @classmethod
    def pular(cls) -> ResultadoPoliticaReexecucao:
        return cls(DecisaoReexecucao.PULAR, None)

    @classmethod
    def recomecar(cls) -> ResultadoPoliticaReexecucao:
        return cls(DecisaoReexecucao.RECOMECAR, None)

    @classmethod
    def retomar(cls, a_partir_de: EtapaLote) -> ResultadoPoliticaReexecucao:
        return cls(DecisaoReexecucao.RETOMAR, a_partir_de)


# Etapa por onde retomar quando o status indica que a etapa seguinte é a que falta/falhou.
_ETAPA_SEGUINTE: dict[StatusProduto, EtapaLote] = {
    StatusProduto.REPROVADO_VALIDACAO: EtapaLote.VALIDAR,
    StatusProduto.VALIDADO: EtapaLote.FOTOS,
    StatusProduto.ERRO_FOTOS: EtapaLote.FOTOS,
    StatusProduto.FOTOS_PUBLICADAS: EtapaLote.TEXTOS,
    StatusProduto.ERRO_LLM: EtapaLote.TEXTOS,
    StatusProduto.REPROVADO_QA: EtapaLote.TEXTOS,
    StatusProduto.TEXTOS_GERADOS: EtapaLote.MONTAR,
}

# Statuses a partir dos quais já passou pela etapa de fotos (fazem sentido para --refazer-fotos).
_JA_TEM_FOTOS = frozenset(
    {
        StatusProduto.FOTOS_PUBLICADAS,
        StatusProduto.TEXTOS_GERADOS,
        StatusProduto.REPROVADO_QA,
        StatusProduto.ERRO_LLM,
        StatusProduto.PRONTO,
    }
)

# Statuses a partir dos quais já passou pela etapa de textos (fazem sentido para --refazer-textos).
_JA_TEM_TEXTOS = frozenset({StatusProduto.TEXTOS_GERADOS, StatusProduto.PRONTO})


class PoliticaReexecucao:
    """Decide, produto a produto, se uma reexecução do lote pula, retoma ou recomeça.

    Ver `docs/ARQUITETURA.md` §8 ("Reexecução"): entrada alterada (hash diferente) sempre
    recomeça do zero; `pronto` é pulado por padrão; os demais status retomam da etapa que ainda
    falta ou que falhou; `--refazer-textos`/`--refazer-fotos` forçam retomar de uma etapa
    anterior à que o status indicaria.
    """

    def decidir(
        self,
        estado_anterior: EstadoProduto | None,
        hash_entrada_atual: str,
        *,
        refazer_textos: bool = False,
        refazer_fotos: bool = False,
    ) -> ResultadoPoliticaReexecucao:
        if estado_anterior is None:
            return ResultadoPoliticaReexecucao.recomecar()
        if estado_anterior.hash_entrada != hash_entrada_atual:
            return ResultadoPoliticaReexecucao.recomecar()

        if refazer_fotos and estado_anterior.status in _JA_TEM_FOTOS:
            return ResultadoPoliticaReexecucao.retomar(EtapaLote.FOTOS)
        if refazer_textos and estado_anterior.status in _JA_TEM_TEXTOS:
            return ResultadoPoliticaReexecucao.retomar(EtapaLote.TEXTOS)

        if estado_anterior.status is StatusProduto.PRONTO:
            return ResultadoPoliticaReexecucao.pular()

        return ResultadoPoliticaReexecucao.retomar(_ETAPA_SEGUINTE[estado_anterior.status])
