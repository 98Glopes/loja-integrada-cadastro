from __future__ import annotations

import json
import shutil
import tempfile
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from loja_integrada_cadastro.models.estado_produto import EstadoProduto
from loja_integrada_cadastro.models.exceptions.erro_estado_lote import ErroEstadoLote
from loja_integrada_cadastro.models.foto_produto import FotoProduto
from loja_integrada_cadastro.models.produto_entrada import ProdutoEntrada
from loja_integrada_cadastro.models.relatorio_lote import Relatorio
from loja_integrada_cadastro.models.resultado_validacao import (
    ProblemaValidacao,
    ResultadoValidacao,
)
from loja_integrada_cadastro.models.status_produto import StatusProduto
from loja_integrada_cadastro.models.variacao_entrada import VariacaoEntrada

_SUBPASTAS_WORKSPACE = ("entrada", "estado", "fotos-processadas", "saida")


class RepositorioEstadoLoteJson:
    """Um JSON por SKU em `lotes/<lote>/estado/` (`docs/ARQUITETURA.md` §8).

    Cria a árvore do workspace do lote ao ser construído (idempotente).
    """

    def __init__(self, lote_dir: Path) -> None:
        self._lote_dir = lote_dir
        self._estado_dir = lote_dir / "estado"
        for subpasta in _SUBPASTAS_WORKSPACE:
            (lote_dir / subpasta).mkdir(parents=True, exist_ok=True)

    def copiar_planilha_entrada(self, planilha: Path) -> None:
        """Copia a planilha recebida para `entrada/`, para auditoria do lote."""
        destino = self._lote_dir / "entrada" / planilha.name
        shutil.copyfile(planilha, destino)

    def carregar(self, sku_pai: str) -> EstadoProduto | None:
        caminho = self._caminho(sku_pai)
        if not caminho.is_file():
            return None
        try:
            dados = json.loads(caminho.read_text(encoding="utf-8"))
            return _de_dict(dados)
        except (json.JSONDecodeError, KeyError, TypeError, ValueError) as erro:
            raise ErroEstadoLote(caminho, str(erro)) from erro

    def salvar(self, estado: EstadoProduto) -> None:
        caminho = self._caminho(estado.sku_pai)
        conteudo = json.dumps(_para_dict(estado), ensure_ascii=False, indent=2)
        descritor, temporario = tempfile.mkstemp(dir=self._estado_dir, suffix=".tmp")
        try:
            with open(descritor, "w", encoding="utf-8") as arquivo:
                arquivo.write(conteudo)
            Path(temporario).replace(caminho)
        finally:
            # Continua existindo só se a escrita ou a troca falharam antes de completar.
            Path(temporario).unlink(missing_ok=True)

    def listar(self) -> list[EstadoProduto]:
        estados = []
        for caminho in sorted(self._estado_dir.glob("*.json")):
            estado = self.carregar(caminho.stem)
            if estado is not None:
                estados.append(estado)
        return estados

    def diretorio_lote(self) -> Path:
        return self._lote_dir

    def salvar_relatorio(self, relatorio: Relatorio) -> None:
        (self._lote_dir / "relatorio.md").write_text(relatorio.markdown, encoding="utf-8")
        (self._lote_dir / "relatorio.json").write_text(
            json.dumps(relatorio.dados, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    def _caminho(self, sku_pai: str) -> Path:
        return self._estado_dir / f"{sku_pai}.json"


def _para_dict(estado: EstadoProduto) -> dict[str, Any]:
    return {
        "sku_pai": estado.sku_pai,
        "status": estado.status.value,
        "entrada": _produto_entrada_para_dict(estado.entrada),
        "hash_entrada": estado.hash_entrada,
        "validacao": _resultado_validacao_para_dict(estado.validacao),
        "fotos": [_foto_para_dict(foto) for foto in estado.fotos],
        "imagens_pai": list(estado.imagens_pai),
        "textos": dict(estado.textos) if estado.textos is not None else None,
        "tentativas": [dict(tentativa) for tentativa in estado.tentativas],
        "custo_usd_estimado": str(estado.custo_usd_estimado),
        "verificacao": dict(estado.verificacao) if estado.verificacao is not None else None,
        "atualizado_em": estado.atualizado_em.isoformat(),
    }


def _de_dict(dados: dict[str, Any]) -> EstadoProduto:
    return EstadoProduto(
        sku_pai=dados["sku_pai"],
        status=StatusProduto(dados["status"]),
        entrada=_produto_entrada_de_dict(dados["entrada"]),
        hash_entrada=dados["hash_entrada"],
        validacao=_resultado_validacao_de_dict(dados["validacao"]),
        fotos=tuple(_foto_de_dict(foto) for foto in dados["fotos"]),
        imagens_pai=tuple(dados["imagens_pai"]),
        textos=dados["textos"],
        tentativas=tuple(dados["tentativas"]),
        custo_usd_estimado=Decimal(dados["custo_usd_estimado"]),
        verificacao=dados["verificacao"],
        atualizado_em=datetime.fromisoformat(dados["atualizado_em"]),
    )


def _produto_entrada_para_dict(entrada: ProdutoEntrada) -> dict[str, Any]:
    return {
        "sku_pai": entrada.sku_pai,
        "marca": entrada.marca,
        "nome_fornecedor": entrada.nome_fornecedor,
        "tipo_peca": entrada.tipo_peca,
        "categoria": list(entrada.categoria),
        "composicao": entrada.composicao,
        "detalhes": entrada.detalhes,
        "colecao": entrada.colecao,
        "faixa_tamanho": entrada.faixa_tamanho,
        "variacoes": [
            {
                "cor": variacao.cor,
                "tamanho": variacao.tamanho,
                "gtin": variacao.gtin,
                "preco": str(variacao.preco),
                "estoque": variacao.estoque,
            }
            for variacao in entrada.variacoes
        ],
    }


def _produto_entrada_de_dict(dados: dict[str, Any]) -> ProdutoEntrada:
    return ProdutoEntrada(
        sku_pai=dados["sku_pai"],
        marca=dados["marca"],
        nome_fornecedor=dados["nome_fornecedor"],
        tipo_peca=dados["tipo_peca"],
        categoria=tuple(dados["categoria"]),
        composicao=dados["composicao"],
        detalhes=dados["detalhes"],
        colecao=dados["colecao"],
        faixa_tamanho=dados["faixa_tamanho"],
        variacoes=tuple(
            VariacaoEntrada(
                cor=variacao["cor"],
                tamanho=variacao["tamanho"],
                gtin=variacao["gtin"],
                preco=Decimal(variacao["preco"]),
                estoque=variacao["estoque"],
            )
            for variacao in dados["variacoes"]
        ),
    )


def _foto_para_dict(foto: FotoProduto) -> dict[str, Any]:
    return {
        "sku_pai": foto.sku_pai,
        "cor": foto.cor,
        "ordem": foto.ordem,
        "arquivo_origem": str(foto.arquivo_origem),
        "nome": foto.nome,
        "chave": foto.chave,
        "url": foto.url,
        "bytes": foto.bytes,
    }


def _foto_de_dict(dados: dict[str, Any]) -> FotoProduto:
    return FotoProduto(
        sku_pai=dados["sku_pai"],
        cor=dados["cor"],
        ordem=dados["ordem"],
        arquivo_origem=Path(dados["arquivo_origem"]),
        nome=dados["nome"],
        chave=dados["chave"],
        url=dados["url"],
        bytes=dados["bytes"],
    )


def _resultado_validacao_para_dict(resultado: ResultadoValidacao) -> dict[str, Any]:
    return {
        "problemas": [_problema_para_dict(problema) for problema in resultado.problemas],
        "avisos": [_problema_para_dict(aviso) for aviso in resultado.avisos],
    }


def _resultado_validacao_de_dict(dados: dict[str, Any]) -> ResultadoValidacao:
    return ResultadoValidacao(
        problemas=tuple(_problema_de_dict(problema) for problema in dados["problemas"]),
        avisos=tuple(_problema_de_dict(aviso) for aviso in dados["avisos"]),
    )


def _problema_para_dict(problema: ProblemaValidacao) -> dict[str, str]:
    return {"sku_pai": problema.sku_pai, "campo": problema.campo, "mensagem": problema.mensagem}


def _problema_de_dict(dados: dict[str, Any]) -> ProblemaValidacao:
    return ProblemaValidacao(
        sku_pai=dados["sku_pai"], campo=dados["campo"], mensagem=dados["mensagem"]
    )
