from __future__ import annotations

from datetime import date
from decimal import Decimal
from importlib import resources
from typing import Any

import yaml

from loja_integrada_cadastro.models.dados_mestre import DadosMestre
from loja_integrada_cadastro.models.exceptions.erro_recursos import ErroRecursos
from loja_integrada_cadastro.models.preco_modelo_llm import PrecoModeloLlm
from loja_integrada_cadastro.models.tabela_precos_llm import ARQUIVO_PRECOS_LLM, TabelaPrecosLlm

_PACOTE_RECURSOS = "loja_integrada_cadastro.recursos"
_ARQUIVO_DADOS_MESTRE = "dados_mestre.yaml"


class CarregadorRecursos:
    """Lê arquivos versionados em `recursos/` via `importlib.resources`.

    Funciona tanto a partir do repositório quanto do pacote instalado, sem depender do
    diretório de trabalho atual.
    """

    def texto(self, nome: str) -> str:
        """Lê `nome` como texto puro (usado para prompts/perfis de marca em Markdown)."""
        recurso = resources.files(_PACOTE_RECURSOS) / nome
        if not recurso.is_file():
            raise ErroRecursos(nome, "arquivo não encontrado no pacote 'recursos/'")
        return recurso.read_text(encoding="utf-8")

    def dados_mestre(self) -> DadosMestre:
        """Lê e valida `recursos/dados_mestre.yaml`, montando o dataclass `DadosMestre`."""
        return montar_dados_mestre(self._yaml(_ARQUIVO_DADOS_MESTRE))

    def precos_llm(self) -> TabelaPrecosLlm:
        """Lê e valida `recursos/precos_llm.yaml`, montando `TabelaPrecosLlm`."""
        return montar_tabela_precos_llm(self._yaml(ARQUIVO_PRECOS_LLM))

    def _yaml(self, nome: str) -> object:
        try:
            return yaml.safe_load(self.texto(nome))
        except yaml.YAMLError as erro:
            raise ErroRecursos(nome, f"YAML malformado: {erro}") from erro


def montar_dados_mestre(bruto: object) -> DadosMestre:
    """Valida a estrutura de um dict já carregado do YAML e monta `DadosMestre`.

    Isolada de I/O de propósito: permite testar a validação diretamente com um dict Python,
    sem precisar de um arquivo real. Qualquer seção ausente ou com tipo inesperado vira
    `ErroRecursos` com uma mensagem específica — nunca deixa `KeyError`/`TypeError` vazar.
    """
    if not isinstance(bruto, dict):
        raise ErroRecursos(_ARQUIVO_DADOS_MESTRE, "conteúdo não é um mapeamento YAML válido")

    marcas = _exigir_secao(bruto, "marcas", dict)
    canonicas_bruto = _exigir_subsecao(marcas, "marcas", "canonicas", dict)
    proibidas_bruto = _exigir_subsecao(marcas, "marcas", "proibidas", dict)
    cores_bruto = _exigir_secao(bruto, "cores", list)
    tamanhos_bruto = _exigir_secao(bruto, "tamanhos", list)
    categorias_bruto = _exigir_secao(bruto, "categorias_referencia", list)

    marcas_canonicas = {
        nome: _aliases_de(nome, entrada) for nome, entrada in canonicas_bruto.items()
    }
    marcas_proibidas = {
        nome: _texto_de(nome, "marcas.proibidas", motivo)
        for nome, motivo in proibidas_bruto.items()
    }
    cores = frozenset(_nome_cor_de(item) for item in cores_bruto)
    tamanhos = frozenset(_string_de("tamanhos", item) for item in tamanhos_bruto)
    categorias_referencia = frozenset(
        _string_de("categorias_referencia", item) for item in categorias_bruto
    )

    return DadosMestre(
        marcas_canonicas=marcas_canonicas,
        marcas_proibidas=marcas_proibidas,
        cores=cores,
        tamanhos=tamanhos,
        categorias_referencia=categorias_referencia,
    )


def montar_tabela_precos_llm(bruto: object) -> TabelaPrecosLlm:
    """Valida o dict de `precos_llm.yaml` e monta `TabelaPrecosLlm` (isolada de I/O)."""
    if not isinstance(bruto, dict):
        raise ErroRecursos(ARQUIVO_PRECOS_LLM, "conteúdo não é um mapeamento YAML válido")
    data_referencia = bruto.get("data_referencia")
    if not isinstance(data_referencia, date):
        raise ErroRecursos(
            ARQUIVO_PRECOS_LLM, "campo obrigatório 'data_referencia' ausente ou inválido"
        )
    modelos = bruto.get("modelos")
    if not isinstance(modelos, dict) or not modelos:
        raise ErroRecursos(ARQUIVO_PRECOS_LLM, "seção obrigatória ausente ou vazia: 'modelos'")
    precos = {
        str(modelo): _preco_modelo_de(str(modelo), precos_brutos)
        for modelo, precos_brutos in modelos.items()
    }
    return TabelaPrecosLlm(precos=precos, data_referencia=data_referencia)


def _preco_modelo_de(modelo: str, precos_brutos: object) -> PrecoModeloLlm:
    if not isinstance(precos_brutos, dict):
        raise ErroRecursos(ARQUIVO_PRECOS_LLM, f"modelo '{modelo}' sem mapeamento de preços")
    return PrecoModeloLlm(
        entrada=_preco_de(modelo, precos_brutos, "entrada"),
        saida=_preco_de(modelo, precos_brutos, "saida"),
        cache_leitura=_preco_de(modelo, precos_brutos, "cache_leitura"),
        cache_escrita=_preco_de(modelo, precos_brutos, "cache_escrita"),
    )


def _preco_de(modelo: str, precos_brutos: dict[str, Any], chave: str) -> Decimal:
    valor = precos_brutos.get(chave)
    if isinstance(valor, bool) or not isinstance(valor, int | float):
        raise ErroRecursos(
            ARQUIVO_PRECOS_LLM, f"preço '{chave}' do modelo '{modelo}' ausente ou não numérico"
        )
    return Decimal(str(valor))


def _exigir_secao[T](bruto: dict[str, Any], chave: str, tipo: type[T]) -> T:
    valor = bruto.get(chave)
    if not isinstance(valor, tipo):
        raise ErroRecursos(
            _ARQUIVO_DADOS_MESTRE, f"seção obrigatória ausente ou inválida: '{chave}'"
        )
    return valor


def _exigir_subsecao[T](secao: dict[str, Any], secao_pai: str, chave: str, tipo: type[T]) -> T:
    valor = secao.get(chave)
    if not isinstance(valor, tipo):
        raise ErroRecursos(
            _ARQUIVO_DADOS_MESTRE, f"seção obrigatória ausente ou inválida: '{secao_pai}.{chave}'"
        )
    return valor


def _aliases_de(nome_marca: str, entrada_marca: object) -> tuple[str, ...]:
    if not isinstance(entrada_marca, dict) or not isinstance(entrada_marca.get("aliases"), list):
        raise ErroRecursos(
            _ARQUIVO_DADOS_MESTRE, f"marca '{nome_marca}' sem lista 'aliases' em marcas.canonicas"
        )
    aliases = entrada_marca["aliases"]
    for alias in aliases:
        if not isinstance(alias, str):
            raise ErroRecursos(
                _ARQUIVO_DADOS_MESTRE, f"alias não textual em marcas.canonicas.{nome_marca}"
            )
    return tuple(aliases)


def _texto_de(chave: str, secao: str, valor: object) -> str:
    if not isinstance(valor, str):
        raise ErroRecursos(_ARQUIVO_DADOS_MESTRE, f"valor não textual em {secao} para '{chave}'")
    return valor


def _nome_cor_de(item: object) -> str:
    if not isinstance(item, dict) or not isinstance(item.get("nome"), str):
        raise ErroRecursos(
            _ARQUIVO_DADOS_MESTRE, f"item de 'cores' sem campo 'nome' textual: {item!r}"
        )
    nome: str = item["nome"]
    return nome


def _string_de(secao: str, valor: object) -> str:
    if not isinstance(valor, str):
        raise ErroRecursos(_ARQUIVO_DADOS_MESTRE, f"item não textual em '{secao}': {valor!r}")
    return valor
