from __future__ import annotations

from decimal import Decimal
from pathlib import Path

from loja_integrada_cadastro.models.estado_produto import EstadoProduto
from loja_integrada_cadastro.models.exceptions.erro_publicacao_imagem import ErroPublicacaoImagem
from loja_integrada_cadastro.models.foto_produto import FotoProduto
from loja_integrada_cadastro.models.padroes_fisicos import PadroesFisicos
from loja_integrada_cadastro.models.produto_entrada import ProdutoEntrada
from loja_integrada_cadastro.models.relatorio_lote import Relatorio
from loja_integrada_cadastro.models.resultado_validacao import (
    ProblemaValidacao,
    ResultadoValidacao,
)
from loja_integrada_cadastro.models.status_produto import StatusProduto
from loja_integrada_cadastro.models.textos_produto import TextosProduto
from loja_integrada_cadastro.models.variacao_entrada import VariacaoEntrada
from loja_integrada_cadastro.services.gerador_relatorio import GeradorRelatorio
from loja_integrada_cadastro.services.montador_planilha import MontadorPlanilha
from loja_integrada_cadastro.services.politica_reexecucao import PoliticaReexecucao
from loja_integrada_cadastro.services.processador_lote import (
    OpcoesProcessamento,
    ProcessarLote,
    _hash_entrada,
)

_APROVADO = ResultadoValidacao(problemas=(), avisos=())
_PADROES_FISICOS = PadroesFisicos(
    peso_kg=Decimal("0.1"),
    altura_cm=Decimal("4"),
    largura_cm=Decimal("22"),
    comprimento_cm=Decimal("22"),
)


def _produto(sku_pai: str = "3254002", *, composicao: str = "100% algodão") -> ProdutoEntrada:
    return ProdutoEntrada(
        sku_pai=sku_pai,
        marca="Kiki",
        nome_fornecedor="Conjunto Baby Malha e Moletom",
        tipo_peca="Conjunto",
        categoria=("Linha Baby (P ao XG)", "Menino", "Conjunto"),
        composicao=composicao,
        detalhes="Botões na gola",
        colecao=None,
        faixa_tamanho="P ao G",
        variacoes=(
            VariacaoEntrada(
                cor="Beige",
                tamanho="P",
                gtin="7891234567895",
                preco=Decimal("119.90"),
                estoque=10,
            ),
        ),
    )


class _LeitorFake:
    def __init__(self, produtos: list[ProdutoEntrada]) -> None:
        self._produtos = produtos

    def ler(self, caminho: Path) -> list[ProdutoEntrada]:
        return self._produtos


class _ValidadorFake:
    """Fake do serviço de validação: devolve os produtos como vieram, com o resultado dado."""

    def __init__(self, resultado: ResultadoValidacao | None = None) -> None:
        self._resultado = resultado or _APROVADO

    def validar(
        self, produtos: list[ProdutoEntrada]
    ) -> tuple[list[ProdutoEntrada], ResultadoValidacao]:
        return produtos, self._resultado


class _PipelineFotosFake:
    """Fake do serviço `PipelineFotos`: registra chamadas, pode falhar por SKU."""

    def __init__(self, falhar_em: frozenset[str] = frozenset()) -> None:
        self._falhar_em = falhar_em
        self.chamadas: list[str] = []

    def processar(self, produto: ProdutoEntrada, estado: EstadoProduto) -> list[FotoProduto]:
        self.chamadas.append(produto.sku_pai)
        if produto.sku_pai in self._falhar_em:
            estado.registrar_erro_fotos()
            raise ErroPublicacaoImagem(produto.sku_pai, "falha fake")
        estado.registrar_fotos((), ())
        return []


class _PipelineFotosInterrompeFake:
    """Fake que simula `Ctrl+C` no meio do processamento de fotos."""

    def processar(self, produto: ProdutoEntrada, estado: EstadoProduto) -> list[FotoProduto]:
        raise KeyboardInterrupt


class _GeradorTextosFake:
    def __init__(self) -> None:
        self.chamadas: list[str] = []

    def gerar(self, produto: ProdutoEntrada, estado: EstadoProduto) -> TextosProduto:
        self.chamadas.append(produto.sku_pai)
        return TextosProduto(
            titulo=f"Título {produto.sku_pai}",
            descricao_html="<h2>x</h2>",
            seo_tag_title="tag",
            seo_tag_description="meta",
        )


class _EscritorFake:
    def __init__(self) -> None:
        self.chamadas: list[tuple[list[object], Path]] = []

    def escrever(self, linhas: object, destino: Path) -> None:
        self.chamadas.append((list(linhas), destino))  # type: ignore[call-overload]


class _RepositorioEstadoLoteFake:
    """Fake em memória do port `RepositorioEstadoLote` (sem tocar disco)."""

    def __init__(self, raiz: Path) -> None:
        self._raiz = raiz
        self._estados: dict[str, EstadoProduto] = {}
        self.planilhas_copiadas: list[Path] = []
        self.relatorio_salvo: Relatorio | None = None

    def carregar(self, sku_pai: str) -> EstadoProduto | None:
        return self._estados.get(sku_pai)

    def salvar(self, estado: EstadoProduto) -> None:
        self._estados[estado.sku_pai] = estado

    def listar(self) -> list[EstadoProduto]:
        return list(self._estados.values())

    def copiar_planilha_entrada(self, planilha: Path) -> None:
        self.planilhas_copiadas.append(planilha)

    def salvar_relatorio(self, relatorio: Relatorio) -> None:
        self.relatorio_salvo = relatorio

    def diretorio_lote(self) -> Path:
        return self._raiz


def _processador(
    tmp_path: Path,
    produtos: list[ProdutoEntrada],
    *,
    resultado: ResultadoValidacao | None = None,
    pipeline_fotos: object | None = None,
    repositorio: _RepositorioEstadoLoteFake | None = None,
) -> tuple[ProcessarLote, object, _GeradorTextosFake, _EscritorFake, _RepositorioEstadoLoteFake]:
    pipeline_fotos = pipeline_fotos or _PipelineFotosFake()
    gerador_textos = _GeradorTextosFake()
    escritor = _EscritorFake()
    repositorio = repositorio or _RepositorioEstadoLoteFake(tmp_path)
    processador = ProcessarLote(
        leitor_planilha_entrada=_LeitorFake(produtos),  # type: ignore[arg-type]
        validador=_ValidadorFake(resultado),  # type: ignore[arg-type]
        pipeline_fotos=pipeline_fotos,  # type: ignore[arg-type]
        gerador_textos=gerador_textos,  # type: ignore[arg-type]
        montador=MontadorPlanilha(_PADROES_FISICOS, "S"),
        escritor=escritor,  # type: ignore[arg-type]
        repositorio_estado=repositorio,  # type: ignore[arg-type]
        gerador_relatorio=GeradorRelatorio(),
        politica_reexecucao=PoliticaReexecucao(),
    )
    return processador, pipeline_fotos, gerador_textos, escritor, repositorio


def test_lote_feliz_processa_todos_ate_pronto(tmp_path: Path) -> None:
    produtos = [_produto("3254002"), _produto("3254010")]
    processador, pipeline_fotos, gerador_textos, escritor, repositorio = _processador(
        tmp_path, produtos
    )

    resumo = processador.executar(Path("p.xlsx"), Path("fotos"), "lote-1", OpcoesProcessamento())

    assert resumo.todos_prontos
    assert resumo.contagem_por_status[StatusProduto.PRONTO] == 2
    assert sorted(pipeline_fotos.chamadas) == ["3254002", "3254010"]  # type: ignore[attr-defined]
    assert sorted(gerador_textos.chamadas) == ["3254002", "3254010"]
    assert len(escritor.chamadas) == 1
    linhas, destino = escritor.chamadas[0]
    assert destino == tmp_path / "saida" / "lote-1.xlsx"
    assert len(linhas) == 4
    assert repositorio.relatorio_salvo is not None
    assert repositorio.planilhas_copiadas == [Path("p.xlsx")]


def test_erro_de_fotos_nao_impede_outros_produtos(tmp_path: Path) -> None:
    produtos = [_produto("3254002"), _produto("3254010")]
    pipeline_fotos = _PipelineFotosFake(falhar_em=frozenset({"3254002"}))
    processador, _, gerador_textos, _, _ = _processador(
        tmp_path, produtos, pipeline_fotos=pipeline_fotos
    )

    resumo = processador.executar(Path("p.xlsx"), Path("fotos"), "lote-1", OpcoesProcessamento())

    assert resumo.contagem_por_status[StatusProduto.ERRO_FOTOS] == 1
    assert resumo.contagem_por_status[StatusProduto.PRONTO] == 1
    assert gerador_textos.chamadas == ["3254010"]


def test_reexecucao_pula_produto_pronto(tmp_path: Path) -> None:
    produtos = [_produto("3254002")]
    repositorio = _RepositorioEstadoLoteFake(tmp_path)
    processador, *_ = _processador(tmp_path, produtos, repositorio=repositorio)
    processador.executar(Path("p.xlsx"), Path("fotos"), "lote-1", OpcoesProcessamento())

    processador2, pipeline_fotos2, gerador_textos2, _, _ = _processador(
        tmp_path, produtos, repositorio=repositorio
    )
    resumo = processador2.executar(Path("p.xlsx"), Path("fotos"), "lote-1", OpcoesProcessamento())

    assert resumo.contagem_por_status[StatusProduto.PRONTO] == 1
    assert pipeline_fotos2.chamadas == []  # type: ignore[attr-defined]
    assert gerador_textos2.chamadas == []


def test_refazer_textos_regenera_so_os_textos(tmp_path: Path) -> None:
    produtos = [_produto("3254002")]
    repositorio = _RepositorioEstadoLoteFake(tmp_path)
    processador, *_ = _processador(tmp_path, produtos, repositorio=repositorio)
    processador.executar(Path("p.xlsx"), Path("fotos"), "lote-1", OpcoesProcessamento())

    processador2, pipeline_fotos2, gerador_textos2, _, _ = _processador(
        tmp_path, produtos, repositorio=repositorio
    )
    opcoes = OpcoesProcessamento(refazer_textos=frozenset({"3254002"}))
    resumo = processador2.executar(Path("p.xlsx"), Path("fotos"), "lote-1", opcoes)

    assert resumo.contagem_por_status[StatusProduto.PRONTO] == 1
    assert pipeline_fotos2.chamadas == []  # type: ignore[attr-defined]
    assert gerador_textos2.chamadas == ["3254002"]


def test_refazer_fotos_reprocessa_fotos_e_textos(tmp_path: Path) -> None:
    produtos = [_produto("3254002")]
    repositorio = _RepositorioEstadoLoteFake(tmp_path)
    processador, *_ = _processador(tmp_path, produtos, repositorio=repositorio)
    processador.executar(Path("p.xlsx"), Path("fotos"), "lote-1", OpcoesProcessamento())

    processador2, pipeline_fotos2, gerador_textos2, _, _ = _processador(
        tmp_path, produtos, repositorio=repositorio
    )
    opcoes = OpcoesProcessamento(refazer_fotos=frozenset({"3254002"}))
    resumo = processador2.executar(Path("p.xlsx"), Path("fotos"), "lote-1", opcoes)

    assert resumo.contagem_por_status[StatusProduto.PRONTO] == 1
    assert pipeline_fotos2.chamadas == ["3254002"]  # type: ignore[attr-defined]
    assert gerador_textos2.chamadas == ["3254002"]


def test_produto_reprovado_na_validacao_fica_fora_do_pipeline_mas_aparece_no_relatorio(
    tmp_path: Path,
) -> None:
    produtos = [_produto("3254002")]
    resultado = ResultadoValidacao(
        problemas=(ProblemaValidacao("3254002", "cor", "cor inválida"),), avisos=()
    )
    processador, pipeline_fotos, gerador_textos, _, repositorio = _processador(
        tmp_path, produtos, resultado=resultado
    )

    resumo = processador.executar(Path("p.xlsx"), Path("fotos"), "lote-1", OpcoesProcessamento())

    assert resumo.contagem_por_status[StatusProduto.REPROVADO_VALIDACAO] == 1
    assert pipeline_fotos.chamadas == []  # type: ignore[attr-defined]
    assert gerador_textos.chamadas == []
    assert repositorio.relatorio_salvo is not None
    assert "3254002" in repositorio.relatorio_salvo.markdown


def test_keyboard_interrupt_gera_planilha_e_relatorio_parciais(tmp_path: Path) -> None:
    produtos = [_produto("3254002")]
    processador, _, _, escritor, repositorio = _processador(
        tmp_path, produtos, pipeline_fotos=_PipelineFotosInterrompeFake()
    )

    resumo = processador.executar(Path("p.xlsx"), Path("fotos"), "lote-1", OpcoesProcessamento())

    assert not resumo.todos_prontos
    assert len(escritor.chamadas) == 1
    assert repositorio.relatorio_salvo is not None


def test_hash_diferente_recomeca_mesmo_ja_pronto(tmp_path: Path) -> None:
    repositorio = _RepositorioEstadoLoteFake(tmp_path)
    processador, *_ = _processador(tmp_path, [_produto("3254002")], repositorio=repositorio)
    processador.executar(Path("p.xlsx"), Path("fotos"), "lote-1", OpcoesProcessamento())

    produto_alterado = _produto("3254002", composicao="70% algodão, 30% poliéster")
    processador2, pipeline_fotos2, gerador_textos2, _, _ = _processador(
        tmp_path, [produto_alterado], repositorio=repositorio
    )
    resumo = processador2.executar(Path("p.xlsx"), Path("fotos"), "lote-1", OpcoesProcessamento())

    assert resumo.contagem_por_status[StatusProduto.PRONTO] == 1
    assert pipeline_fotos2.chamadas == ["3254002"]  # type: ignore[attr-defined]
    assert gerador_textos2.chamadas == ["3254002"]


def test_hash_entrada_e_estavel_para_a_mesma_entrada() -> None:
    assert _hash_entrada(_produto("3254002")) == _hash_entrada(_produto("3254002"))


def test_hash_entrada_muda_quando_um_campo_muda() -> None:
    original = _produto("3254002")
    alterado = _produto("3254002", composicao="outra composição")
    assert _hash_entrada(original) != _hash_entrada(alterado)
