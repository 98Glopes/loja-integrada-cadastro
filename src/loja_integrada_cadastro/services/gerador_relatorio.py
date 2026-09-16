from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from loja_integrada_cadastro.models.estado_produto import EstadoProduto
from loja_integrada_cadastro.models.relatorio_lote import Relatorio
from loja_integrada_cadastro.models.resumo_lote import ResumoLote
from loja_integrada_cadastro.models.status_produto import StatusProduto

_STATUS_REPROVADOS = frozenset({StatusProduto.REPROVADO_VALIDACAO, StatusProduto.REPROVADO_QA})
_CHAVES_USAGE = ("input_tokens", "output_tokens", "cache_read_tokens", "cache_write_tokens")


class GeradorRelatorio:
    """Monta o relatório do lote (`docs/ARQUITETURA.md` §8) a partir dos estados finais.

    Sem dependências externas: só lê o que já está em `EstadoProduto`/`ResumoLote` e devolve as
    duas formas (`markdown`/`dados`) — quem grava em disco é `RepositorioEstadoLote`
    (`salvar_relatorio`, task 11).
    """

    def gerar(self, estados: Sequence[EstadoProduto], resumo: ResumoLote) -> Relatorio:
        dados: dict[str, Any] = {
            "resumo": self._resumo(estados, resumo),
            "produtos": self._tabela_produtos(estados),
            "reprovados": self._reprovados(estados),
            "avisos": self._avisos(estados),
            "custo_por_agente": self._custo_por_agente(estados),
            "categorias_usadas": self._categorias_usadas(estados),
            "fotos": self._fotos(estados),
        }
        markdown = self._markdown(dados)
        return Relatorio(markdown=markdown, dados=dados)

    def _resumo(self, estados: Sequence[EstadoProduto], resumo: ResumoLote) -> dict[str, Any]:
        linhas_planilha = sum(
            1 + len(estado.entrada.variacoes)
            for estado in estados
            if estado.status is StatusProduto.PRONTO
        )
        return {
            "total_produtos": len(estados),
            "contagem_por_status": {
                status.value: quantidade
                for status, quantidade in resumo.contagem_por_status.items()
            },
            "linhas_planilha": linhas_planilha,
            "custo_usd_total": str(resumo.custo_usd_total),
            "duracao_segundos": round(resumo.duracao_segundos, 1),
            "caminho_planilha": str(resumo.caminho_planilha),
        }

    @staticmethod
    def _tabela_produtos(estados: Sequence[EstadoProduto]) -> list[dict[str, Any]]:
        linhas = []
        for estado in sorted(estados, key=lambda item: item.sku_pai):
            titulo = (estado.textos or {}).get("titulo", "")
            linhas.append(
                {
                    "sku_pai": estado.sku_pai,
                    "marca": estado.entrada.marca,
                    "status": estado.status.value,
                    "titulo": titulo,
                    "fotos": len(estado.fotos),
                    "tentativas": len(estado.tentativas),
                    "custo_usd": str(estado.custo_usd_estimado),
                }
            )
        return linhas

    @staticmethod
    def _reprovados(estados: Sequence[EstadoProduto]) -> list[dict[str, Any]]:
        reprovados = []
        for estado in estados:
            if estado.status not in _STATUS_REPROVADOS:
                continue
            if estado.status is StatusProduto.REPROVADO_VALIDACAO:
                motivos = [
                    f"{problema.campo}: {problema.mensagem}"
                    for problema in estado.validacao.problemas
                ]
            else:
                motivos = [str(tentativa.get("veredito_qa")) for tentativa in estado.tentativas]
            reprovados.append(
                {
                    "sku_pai": estado.sku_pai,
                    "status": estado.status.value,
                    "motivos": motivos,
                    "ultimo_texto": estado.textos,
                }
            )
        return reprovados

    @staticmethod
    def _avisos(estados: Sequence[EstadoProduto]) -> list[dict[str, str]]:
        avisos = []
        for estado in estados:
            for aviso in estado.validacao.avisos:
                avisos.append(
                    {"sku_pai": aviso.sku_pai, "campo": aviso.campo, "mensagem": aviso.mensagem}
                )
        return avisos

    @staticmethod
    def _custo_por_agente(estados: Sequence[EstadoProduto]) -> dict[str, dict[str, Any]]:
        por_agente: dict[str, dict[str, Any]] = {}
        for estado in estados:
            for tentativa in estado.tentativas:
                agente = str(tentativa.get("agente", "desconhecido"))
                resumo_agente = por_agente.setdefault(
                    agente, {"tentativas": 0, "custo_usd": "0", **dict.fromkeys(_CHAVES_USAGE, 0)}
                )
                resumo_agente["tentativas"] += 1
                usage = tentativa.get("usage")
                if isinstance(usage, dict):
                    for chave in _CHAVES_USAGE:
                        resumo_agente[chave] += int(usage.get(chave, 0) or 0)
        return por_agente

    @staticmethod
    def _categorias_usadas(estados: Sequence[EstadoProduto]) -> list[str]:
        categorias = dict.fromkeys(
            " > ".join(estado.entrada.categoria) for estado in estados if estado.entrada.categoria
        )
        return sorted(categorias)

    @staticmethod
    def _fotos(estados: Sequence[EstadoProduto]) -> dict[str, Any]:
        nao_usadas = []
        total_publicadas = 0
        for estado in estados:
            total_publicadas += len(estado.fotos)
            for foto in estado.fotos:
                if foto.url not in estado.imagens_pai:
                    nao_usadas.append({"sku_pai": estado.sku_pai, "nome": foto.nome})
        return {"publicadas": total_publicadas, "nao_usadas": nao_usadas}

    def _markdown(self, dados: dict[str, Any]) -> str:
        linhas = ["# Relatório do lote", "", "## Resumo"]
        resumo = dados["resumo"]
        linhas.append(f"- Produtos no lote: {resumo['total_produtos']}")
        for status, quantidade in resumo["contagem_por_status"].items():
            linhas.append(f"  - `{status}`: {quantidade}")
        linhas.append(f"- Linhas na planilha de saída: {resumo['linhas_planilha']}")
        linhas.append(f"- Custo estimado: US$ {resumo['custo_usd_total']}")
        linhas.append(f"- Duração: {resumo['duracao_segundos']}s")
        linhas.append(f"- Planilha: `{resumo['caminho_planilha']}`")

        linhas += ["", "## Reprovados"]
        if dados["reprovados"]:
            for item in dados["reprovados"]:
                linhas.append(f"- **{item['sku_pai']}** ({item['status']}):")
                for motivo in item["motivos"]:
                    linhas.append(f"  - {motivo}")
        else:
            linhas.append("- nenhum")

        linhas += [
            "",
            "## Produtos",
            "",
            "| SKU | Marca | Status | Título | Fotos | Tentativas | Custo |",
            "|---|---|---|---|---|---|---|",
        ]
        for item in dados["produtos"]:
            linhas.append(
                f"| {item['sku_pai']} | {item['marca']} | {item['status']} | {item['titulo']} "
                f"| {item['fotos']} | {item['tentativas']} | US$ {item['custo_usd']} |"
            )

        linhas += ["", "## Avisos"]
        if dados["avisos"]:
            for aviso in dados["avisos"]:
                linhas.append(f"- {aviso['sku_pai']} [{aviso['campo']}]: {aviso['mensagem']}")
        else:
            linhas.append("- nenhum")

        linhas += ["", "## Custo/tokens por agente"]
        if dados["custo_por_agente"]:
            for agente, valores in dados["custo_por_agente"].items():
                linhas.append(
                    f"- {agente}: {valores['tentativas']} tentativa(s), "
                    f"US$ {valores['custo_usd']}, tokens "
                    f"entrada={valores['input_tokens']} saída={valores['output_tokens']}"
                )
        else:
            linhas.append("- nenhuma tentativa registrada")

        linhas += ["", "## Categorias usadas"]
        linhas += [f"- {categoria}" for categoria in dados["categorias_usadas"]] or ["- nenhuma"]

        linhas += ["", "## Fotos"]
        linhas.append(f"- Publicadas: {dados['fotos']['publicadas']}")
        if dados["fotos"]["nao_usadas"]:
            linhas.append("- Não usadas no pai:")
            for foto in dados["fotos"]["nao_usadas"]:
                linhas.append(f"  - {foto['sku_pai']}/{foto['nome']}")
        else:
            linhas.append("- Não usadas no pai: nenhuma")

        return "\n".join(linhas) + "\n"
