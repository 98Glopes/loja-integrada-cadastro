from __future__ import annotations

import hashlib
import logging
import time
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path

from loja_integrada_cadastro.models.estado_produto import EstadoProduto
from loja_integrada_cadastro.models.exceptions.erro_planilha_saida import ErroPlanilhaSaida
from loja_integrada_cadastro.models.exceptions.erro_processamento_imagem import (
    ErroProcessamentoImagem,
)
from loja_integrada_cadastro.models.exceptions.erro_publicacao_imagem import (
    ErroPublicacaoImagem,
)
from loja_integrada_cadastro.models.produto_entrada import ProdutoEntrada
from loja_integrada_cadastro.models.resultado_validacao import (
    ProblemaValidacao,
    ResultadoValidacao,
)
from loja_integrada_cadastro.models.resumo_lote import ResumoLote
from loja_integrada_cadastro.models.status_produto import StatusProduto
from loja_integrada_cadastro.services.gerador_relatorio import GeradorRelatorio
from loja_integrada_cadastro.services.montador_planilha import MontadorPlanilha
from loja_integrada_cadastro.services.pipeline_fotos import PipelineFotos
from loja_integrada_cadastro.services.politica_reexecucao import (
    DecisaoReexecucao,
    EtapaLote,
    PoliticaReexecucao,
)
from loja_integrada_cadastro.services.ports.escritor_planilha_saida import EscritorPlanilhaSaida
from loja_integrada_cadastro.services.ports.gerador_textos import GeradorTextos
from loja_integrada_cadastro.services.ports.leitor_planilha_entrada import LeitorPlanilhaEntrada
from loja_integrada_cadastro.services.ports.repositorio_estado_lote import RepositorioEstadoLote
from loja_integrada_cadastro.services.validador_entrada import ValidadorEntrada

_logger = logging.getLogger(__name__)

_ERROS_ETAPA = (ErroProcessamentoImagem, ErroPublicacaoImagem, ErroPlanilhaSaida)


@dataclass(frozen=True)
class OpcoesProcessamento:
    """Flags de `processar` que afetam a política de reexecução e o conteúdo da planilha."""

    incluir_reprovados: bool = False
    refazer_textos: frozenset[str] = field(default_factory=frozenset)
    refazer_fotos: frozenset[str] = field(default_factory=frozenset)


class ProcessarLote:
    """Caso de uso principal: valida, processa fotos/textos, monta e relata um lote inteiro,
    um produto por vez, com estado persistido a cada etapa (`docs/ARQUITETURA.md` §3, §8).

    `Ctrl+C` durante o laço de produtos é capturado: a planilha e o relatório são gerados com o
    que já estiver `pronto` até então, sem propagar a interrupção.
    """

    def __init__(
        self,
        leitor_planilha_entrada: LeitorPlanilhaEntrada,
        validador: ValidadorEntrada,
        pipeline_fotos: PipelineFotos,
        gerador_textos: GeradorTextos,
        montador: MontadorPlanilha,
        escritor: EscritorPlanilhaSaida,
        repositorio_estado: RepositorioEstadoLote,
        gerador_relatorio: GeradorRelatorio,
        politica_reexecucao: PoliticaReexecucao,
    ) -> None:
        self._leitor = leitor_planilha_entrada
        self._validador = validador
        self._pipeline_fotos = pipeline_fotos
        self._gerador_textos = gerador_textos
        self._montador = montador
        self._escritor = escritor
        self._repositorio = repositorio_estado
        self._gerador_relatorio = gerador_relatorio
        self._politica = politica_reexecucao

    def executar(
        self, planilha: Path, fotos: Path, lote: str, opcoes: OpcoesProcessamento
    ) -> ResumoLote:
        inicio = time.monotonic()
        _logger.info("lote %s: planilha=%s fotos=%s", lote, planilha, fotos)

        self._repositorio.copiar_planilha_entrada(planilha)
        produtos = self._leitor.ler(planilha)
        normalizados, resultado_global = self._validador.validar(produtos)

        aprovados = self._preparar_aprovados(normalizados, resultado_global, opcoes)

        try:
            for estado, etapa_inicial in aprovados:
                self._processar_produto(estado, etapa_inicial)
        except KeyboardInterrupt:
            _logger.warning(
                "interrompido pelo usuário — gerando planilha/relatório com o que estiver pronto"
            )

        return self._finalizar(lote, opcoes, inicio)

    def _preparar_aprovados(
        self,
        produtos: list[ProdutoEntrada],
        resultado_global: ResultadoValidacao,
        opcoes: OpcoesProcessamento,
    ) -> list[tuple[EstadoProduto, EtapaLote | None]]:
        aprovados: list[tuple[EstadoProduto, EtapaLote | None]] = []
        for produto in produtos:
            hash_atual = _hash_entrada(produto)
            anterior = self._repositorio.carregar(produto.sku_pai)
            decisao = self._politica.decidir(
                anterior,
                hash_atual,
                refazer_textos=produto.sku_pai in opcoes.refazer_textos,
                refazer_fotos=produto.sku_pai in opcoes.refazer_fotos,
            )

            if decisao.decisao is DecisaoReexecucao.RECOMECAR:
                estado = EstadoProduto.registrar_validacao(
                    produto.sku_pai,
                    produto,
                    hash_atual,
                    _resultado_do_produto(resultado_global, produto.sku_pai),
                )
                self._repositorio.salvar(estado)
                _logger.info("%s: validar -> %s", produto.sku_pai, estado.status.value)
                if estado.status is StatusProduto.REPROVADO_VALIDACAO:
                    continue
                aprovados.append((estado, EtapaLote.FOTOS))
                continue

            assert anterior is not None
            if decisao.decisao is DecisaoReexecucao.PULAR:
                aprovados.append((anterior, None))
                continue

            if anterior.status is StatusProduto.REPROVADO_VALIDACAO:
                continue
            assert decisao.a_partir_de is not None
            aprovados.append((anterior, decisao.a_partir_de))

        aprovados.sort(key=lambda item: item[0].entrada.marca)
        return aprovados

    def _processar_produto(self, estado: EstadoProduto, etapa_inicial: EtapaLote | None) -> None:
        if etapa_inicial is None:
            _logger.info("%s: pulado (já pronto)", estado.sku_pai)
            return

        etapa = etapa_inicial
        try:
            if etapa is EtapaLote.FOTOS:
                self._pipeline_fotos.processar(estado.entrada, estado)
                self._repositorio.salvar(estado)
                _logger.info("%s: fotos -> %s", estado.sku_pai, estado.status.value)
                etapa = EtapaLote.TEXTOS

            if etapa is EtapaLote.TEXTOS:
                textos = self._gerador_textos.gerar(estado.entrada, estado)
                estado.registrar_textos(textos.como_mapa())
                self._repositorio.salvar(estado)
                _logger.info("%s: textos -> %s", estado.sku_pai, estado.status.value)
                etapa = EtapaLote.MONTAR

            if etapa is EtapaLote.MONTAR:
                self._montador.montar(estado)
                estado.marcar_pronto()
                self._repositorio.salvar(estado)
                _logger.info("%s: montar -> %s", estado.sku_pai, estado.status.value)
        except _ERROS_ETAPA as erro:
            self._repositorio.salvar(estado)
            _logger.error("%s: %s", estado.sku_pai, erro)

    def _finalizar(self, lote: str, opcoes: OpcoesProcessamento, inicio: float) -> ResumoLote:
        estados_finais = self._repositorio.listar()
        linhas = self._montador.montar_lote(estados_finais, opcoes.incluir_reprovados)

        lote_dir = self._repositorio.diretorio_lote()
        caminho_planilha = lote_dir / "saida" / f"{lote}.xlsx"
        caminho_relatorio_md = lote_dir / "relatorio.md"
        caminho_relatorio_json = lote_dir / "relatorio.json"
        self._escritor.escrever(linhas, caminho_planilha)

        contagens = dict.fromkeys(StatusProduto, 0)
        custo_total = Decimal("0")
        for estado in estados_finais:
            contagens[estado.status] += 1
            custo_total += estado.custo_usd_estimado

        resumo = ResumoLote(
            contagem_por_status=contagens,
            custo_usd_total=custo_total,
            duracao_segundos=time.monotonic() - inicio,
            caminho_planilha=caminho_planilha,
            caminho_relatorio_md=caminho_relatorio_md,
            caminho_relatorio_json=caminho_relatorio_json,
        )
        relatorio = self._gerador_relatorio.gerar(estados_finais, resumo)
        self._repositorio.salvar_relatorio(relatorio)
        _logger.info(
            "lote %s: %d produto(s), custo estimado US$ %s, %.1fs",
            lote,
            len(estados_finais),
            custo_total,
            resumo.duracao_segundos,
        )
        return resumo


def _hash_entrada(produto: ProdutoEntrada) -> str:
    """Hash estável e determinístico da entrada normalizada (`docs/ARQUITETURA.md` §8).

    Não usa `hash()` nativo do Python: ele é aleatorizado por processo (`PYTHONHASHSEED`) e
    daria valores diferentes entre a execução que salvou o hash e a que o recalcula para
    comparar.
    """
    variacoes = "|".join(
        f"{variacao.cor}:{variacao.tamanho}:{variacao.gtin}:{variacao.preco}:{variacao.estoque}"
        for variacao in produto.variacoes
    )
    partes = (
        produto.sku_pai,
        produto.marca,
        produto.nome_fornecedor,
        produto.tipo_peca,
        "|".join(produto.categoria),
        produto.composicao,
        produto.detalhes,
        produto.colecao or "",
        produto.faixa_tamanho,
        variacoes,
    )
    canonico = "\x1f".join(partes)
    return hashlib.sha256(canonico.encode("utf-8")).hexdigest()


def _resultado_do_produto(resultado: ResultadoValidacao, sku_pai: str) -> ResultadoValidacao:
    """Recorta o `ResultadoValidacao` do lote inteiro para os problemas/avisos de um SKU."""

    def _do_sku(itens: tuple[ProblemaValidacao, ...]) -> tuple[ProblemaValidacao, ...]:
        return tuple(item for item in itens if item.sku_pai == sku_pai)

    return ResultadoValidacao(
        problemas=_do_sku(resultado.problemas), avisos=_do_sku(resultado.avisos)
    )
