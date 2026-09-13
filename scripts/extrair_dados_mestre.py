#!/usr/bin/env python
"""Regenera as seções `cores`, `tamanhos` e `categorias_referencia` de
`recursos/dados_mestre.yaml` a partir de uma exportação real de produtos da Loja Integrada.

A seção `marcas` é editada à mão (decisão humana documentada em
`docs/brutos/dados_mestre.md` §2) e nunca é tocada por este script — ela precisa já existir
no YAML de destino antes de rodar.

Uso:
    python scripts/extrair_dados_mestre.py docs/brutos/produtos-*.xlsx

Rodar duas vezes sobre o mesmo arquivo de entrada produz um YAML idêntico byte-a-byte
(critério de aceite da task 02) — a ordenação de cada seção é determinística.
"""

from __future__ import annotations

import sys
from collections import Counter
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any

import openpyxl
import yaml

CAMINHO_YAML = (
    Path(__file__).resolve().parent.parent
    / "src"
    / "loja_integrada_cadastro"
    / "recursos"
    / "dados_mestre.yaml"
)

COLUNA_TIPO = "tipo"
COLUNA_COR = "grade-produto-com-uma-cor"
COLUNA_TAMANHO = "grade-tamanho-infantil"
COLUNAS_CATEGORIA = [f"categoria-nome-nivel-{nivel}" for nivel in range(1, 6)]
SEPARADOR_CATEGORIA = " > "

ORDEM_TAMANHOS_LETRA = ["P", "M", "G", "GG", "XG"]


class TipoLinha(StrEnum):
    """Valores observados na coluna `tipo` da exportação (linha-pai, linha-filha ou residual)."""

    PAI = "com-variacao"
    FILHA = "variacao"
    SEM_VARIACAO = "sem-variacao"  # 1 linha residual na exportação real; não usada pela Kmilaa


class PlanilhaSemCabecalho(Exception):
    """Uma das colunas esperadas não foi encontrada no cabeçalho da planilha."""


@dataclass
class ExtracaoPlanilha:
    """Acumula as três grandezas extraídas de um `.xlsx`, para mesclar entre vários arquivos."""

    cores: Counter[str] = field(default_factory=Counter)
    tamanhos: set[str] = field(default_factory=set)
    categorias: set[str] = field(default_factory=set)

    def mesclar(self, outra: ExtracaoPlanilha) -> None:
        self.cores.update(outra.cores)
        self.tamanhos |= outra.tamanhos
        self.categorias |= outra.categorias


def _indice_colunas(cabecalho: Sequence[object]) -> dict[str, int]:
    indices: dict[str, int] = {}
    for indice, nome in enumerate(cabecalho):
        if isinstance(nome, str):
            indices[nome] = indice
    obrigatorias = [COLUNA_TIPO, COLUNA_COR, COLUNA_TAMANHO, *COLUNAS_CATEGORIA]
    faltantes = [nome for nome in obrigatorias if nome not in indices]
    if faltantes:
        raise PlanilhaSemCabecalho(f"colunas obrigatórias ausentes no cabeçalho: {faltantes}")
    return indices


def _texto_ou_none(valor: object) -> str | None:
    if valor is None:
        return None
    texto = str(valor).strip()
    return texto or None


def _registrar_linha_filha(
    linha: Sequence[object], indices: dict[str, int], acumulado: ExtracaoPlanilha
) -> None:
    cor = _texto_ou_none(linha[indices[COLUNA_COR]])
    if cor is not None:
        acumulado.cores[cor] += 1
    tamanho = _texto_ou_none(linha[indices[COLUNA_TAMANHO]])
    if tamanho is not None:
        acumulado.tamanhos.add(tamanho)


def _registrar_linha_pai(
    linha: Sequence[object], indices: dict[str, int], acumulado: ExtracaoPlanilha
) -> None:
    niveis = [_texto_ou_none(linha[indices[coluna]]) for coluna in COLUNAS_CATEGORIA]
    niveis_preenchidos = list(_niveis_ate_o_primeiro_vazio(niveis))
    if niveis_preenchidos:
        acumulado.categorias.add(SEPARADOR_CATEGORIA.join(niveis_preenchidos))


def _niveis_ate_o_primeiro_vazio(niveis: Iterable[str | None]) -> Iterable[str]:
    for nivel in niveis:
        if nivel is None:
            return
        yield nivel


def extrair(caminho_xlsx: Path) -> ExtracaoPlanilha:
    """Lê um `.xlsx` de exportação e devolve cores/tamanhos/categorias observados."""
    livro = openpyxl.load_workbook(caminho_xlsx, read_only=True, data_only=True)
    try:
        planilha = livro.active
        if planilha is None:
            raise PlanilhaSemCabecalho(f"{caminho_xlsx} não tem planilha ativa")

        linhas = planilha.iter_rows(values_only=True)
        indices = _indice_colunas(next(linhas))

        acumulado = ExtracaoPlanilha()
        for linha in linhas:
            tipo = _texto_ou_none(linha[indices[COLUNA_TIPO]])
            if tipo == TipoLinha.FILHA:
                _registrar_linha_filha(linha, indices, acumulado)
            elif tipo == TipoLinha.PAI:
                _registrar_linha_pai(linha, indices, acumulado)
            # TipoLinha.SEM_VARIACAO (ou tipo desconhecido) não contribui para a extração.
        return acumulado
    finally:
        livro.close()


def montar_cores(contagem: Counter[str]) -> list[dict[str, Any]]:
    """Ordena por frequência decrescente; empate resolvido alfabeticamente (determinismo)."""
    itens = sorted(contagem.items(), key=lambda item: (-item[1], item[0]))
    return [{"nome": nome, "uso": uso} for nome, uso in itens]


def _chave_ordenacao_tamanho(tamanho: str) -> tuple[int, int, str]:
    if tamanho in ORDEM_TAMANHOS_LETRA:
        return (0, ORDEM_TAMANHOS_LETRA.index(tamanho), tamanho)
    if tamanho.isdigit():
        return (1, int(tamanho), tamanho)
    return (2, 0, tamanho)


def montar_tamanhos(vistos: set[str]) -> list[str]:
    """Letras (`P M G GG XG`) antes de números, ambos em ordem crescente — determinístico."""
    return sorted(vistos, key=_chave_ordenacao_tamanho)


def montar_categorias(vistas: set[str]) -> list[str]:
    """Ordem alfabética — é só referência/aviso, a ordem não é semântica, só precisa ser estável."""
    return sorted(vistas)


def carregar_marcas_existentes(caminho_yaml: Path) -> dict[str, Any]:
    if not caminho_yaml.exists():
        raise SystemExit(
            f"{caminho_yaml} não existe. A seção 'marcas' é editada à mão "
            "(docs/brutos/dados_mestre.md §2) — crie o arquivo com essa seção antes de rodar "
            "este script."
        )
    bruto = yaml.safe_load(caminho_yaml.read_text(encoding="utf-8")) or {}
    marcas = bruto.get("marcas")
    if not marcas:
        raise SystemExit(
            f"{caminho_yaml} não tem a seção 'marcas'. Ela é editada à mão — adicione-a antes "
            "de rodar este script."
        )
    return dict(marcas)


def escrever_yaml(caminho: Path, documento: dict[str, Any]) -> None:
    texto = yaml.dump(
        documento,
        sort_keys=False,
        allow_unicode=True,
        default_flow_style=False,
    )
    caminho.write_text(texto, encoding="utf-8")


def main(argv: list[str]) -> int:
    if not argv:
        print("uso: python scripts/extrair_dados_mestre.py <planilha.xlsx> [...]", file=sys.stderr)
        return 2

    caminhos = sorted(Path(p) for p in argv)
    acumulado = ExtracaoPlanilha()
    for caminho in caminhos:
        acumulado.mesclar(extrair(caminho))

    documento = {
        "marcas": carregar_marcas_existentes(CAMINHO_YAML),
        "cores": montar_cores(acumulado.cores),
        "tamanhos": montar_tamanhos(acumulado.tamanhos),
        "categorias_referencia": montar_categorias(acumulado.categorias),
    }
    escrever_yaml(CAMINHO_YAML, documento)

    print(
        f"{CAMINHO_YAML}: {len(documento['cores'])} cores, {len(documento['tamanhos'])} tamanhos, "
        f"{len(documento['categorias_referencia'])} categorias de referência."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
