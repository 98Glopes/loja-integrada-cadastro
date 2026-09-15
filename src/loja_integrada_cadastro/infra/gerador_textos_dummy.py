from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from loja_integrada_cadastro.models.dados_mestre import DadosMestre
from loja_integrada_cadastro.models.estado_produto import EstadoProduto
from loja_integrada_cadastro.models.produto_entrada import ProdutoEntrada
from loja_integrada_cadastro.models.textos_produto import TextosProduto

_PREFIXO_DUMMY = "[DUMMY] "
_LIMITE_TITULO = 68
_LIMITE_TAG_TITLE = 60
_MINIMO_META = 140
_LIMITE_META = 155
_MINIMO_PALAVRAS_DESCRICAO = 120

_DIFERENCIAIS_LOJA = "3x sem juros e frete grátis para São Paulo capital"


class GeradorTextosDummy:
    """Implementação determinística e sem rede do port `GeradorTextos` (ADR-007).

    Deriva os 4 campos dos dados do produto (tipo, marca canônica, detalhe principal,
    faixa de tamanho, composição), respeitando os limites de `docs/ARQUITETURA.md` §6.1 por
    construção — não valida, garante pela forma como monta o texto. Provisório: existe para
    provar o pipeline antes da geração por IA (task 16); nunca deve ir ao ar, por isso todo
    texto visível ao operador carrega o placeholder `[DUMMY]`.
    """

    def __init__(self, dados_mestre: DadosMestre) -> None:
        self._dados_mestre = dados_mestre

    def gerar(self, produto: ProdutoEntrada, estado: EstadoProduto) -> TextosProduto:
        marca = self._dados_mestre.marca_canonica(produto.marca) or produto.marca
        detalhe = _detalhe_principal(produto.detalhes)

        textos = TextosProduto(
            titulo=_montar_titulo(produto, marca, detalhe),
            descricao_html=_montar_descricao(produto, marca),
            seo_tag_title=_montar_tag_title(produto, marca, detalhe),
            seo_tag_description=_montar_meta_description(produto, marca),
        )

        estado.registrar_tentativa(
            {
                "agente": "dummy",
                "tentativa": 1,
                "modelo": "dummy",
                "usage": {
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "cache_read_tokens": 0,
                    "cache_write_tokens": 0,
                },
                "veredito_regra": None,
                "veredito_qa": None,
                "request_id": None,
                "em": datetime.now(UTC).isoformat(),
            },
            custo_usd=Decimal("0"),
        )

        return textos


def _detalhe_principal(detalhes: str) -> str:
    """Primeiro segmento de `detalhes`, antes da primeira vírgula."""
    return detalhes.split(",", 1)[0].strip()


def _truncar_em_palavra(texto: str, limite: int) -> str:
    """Trunca `texto` para caber em `limite` caracteres, sem cortar no meio de uma palavra.

    Se a primeira palavra sozinha já estourar `limite`, corta o caractere necessário como
    último recurso (garante que o resultado nunca ultrapasse `limite`).
    """
    if limite <= 0:
        return ""
    if len(texto) <= limite:
        return texto

    cortado = texto[:limite]
    ultimo_espaco = cortado.rfind(" ")
    if ultimo_espaco <= 0:
        return cortado
    return cortado[:ultimo_espaco].rstrip()


def _montar_titulo(produto: ProdutoEntrada, marca: str, detalhe: str) -> str:
    partes_fixas = f"{_PREFIXO_DUMMY}{produto.tipo_peca}  {marca} {produto.faixa_tamanho}"
    orcamento_detalhe = _LIMITE_TITULO - len(partes_fixas)
    detalhe_truncado = _truncar_em_palavra(detalhe, orcamento_detalhe)

    titulo = (
        f"{_PREFIXO_DUMMY}{produto.tipo_peca} {marca} {detalhe_truncado} {produto.faixa_tamanho}"
    ).strip()
    titulo = " ".join(titulo.split())
    if len(titulo) > _LIMITE_TITULO:
        # Salvaguarda: se o detalhe truncado ficou vazio e ainda assim sobrar espaço extra por
        # causa dos separadores colapsados, o título já cabe; este ramo só existe para nunca
        # devolver um título acima do limite mesmo em casos-limite não previstos.
        titulo = titulo[:_LIMITE_TITULO].rstrip()
    return titulo


def _montar_tag_title(produto: ProdutoEntrada, marca: str, detalhe: str) -> str:
    partes_fixas = f"{produto.tipo_peca}  {marca}"
    orcamento_detalhe = _LIMITE_TAG_TITLE - len(partes_fixas)
    detalhe_truncado = _truncar_em_palavra(detalhe, orcamento_detalhe)

    tag_title = f"{produto.tipo_peca} {marca} {detalhe_truncado}".strip()
    tag_title = " ".join(tag_title.split())
    if len(tag_title) > _LIMITE_TAG_TITLE:
        tag_title = tag_title[:_LIMITE_TAG_TITLE].rstrip()
    return tag_title


def _montar_meta_description(produto: ProdutoEntrada, marca: str) -> str:
    base = (
        f"{_PREFIXO_DUMMY}{produto.tipo_peca} {marca}, {produto.composicao.lower()}. "
        f"Conforto e qualidade para o seu bebê, com {_DIFERENCIAIS_LOJA}."
    )
    base = " ".join(base.split())

    if len(base) > _LIMITE_META:
        cortado = _truncar_em_palavra(base, _LIMITE_META)
        base = cortado

    while len(base) < _MINIMO_META:
        complemento = " Compre na Kmilaa Modas."
        if len(base) + len(complemento) > _LIMITE_META:
            faltam = _MINIMO_META - len(base)
            base = base + complemento[: max(faltam, 0)]
            break
        base += complemento

    return base


def _montar_descricao(produto: ProdutoEntrada, marca: str) -> str:
    cores = ", ".join(produto.cores) if produto.cores else "diversas cores"
    tamanhos = ", ".join(produto.tamanhos) if produto.tamanhos else produto.faixa_tamanho

    h2 = (
        f"<h2>{_PREFIXO_DUMMY}{produto.tipo_peca} {marca} para a faixa {produto.faixa_tamanho}</h2>"
    )

    paragrafo_1 = (
        f"<p>Texto dummy de prova de conceito: este {produto.tipo_peca.lower()} da {marca} "
        f"traz {produto.detalhes.lower()}, pensado para o dia a dia do bebê.</p>"
    )
    paragrafo_2 = (
        f"<p>Feito em {produto.composicao.lower()}, garante conforto e durabilidade lavagem "
        f"após lavagem, com acabamento que acompanha a faixa de tamanho {produto.faixa_tamanho} "
        "sem perder o caimento.</p>"
    )

    itens = [
        f"<li>Composição: {produto.composicao}</li>",
        f"<li>Detalhes: {produto.detalhes}</li>",
        f"<li>Faixa de tamanho: {produto.faixa_tamanho} (tamanhos: {tamanhos})</li>",
        f"<li>Cores disponíveis: {cores}</li>",
    ]
    lista = "<ul>" + "".join(itens) + "</ul>"

    h3_marca = f"<h3>Sobre a {marca}</h3>"
    paragrafo_marca = (
        f"<p>Texto dummy de prova de conceito sobre a marca {marca}: peças pensadas para "
        "acompanhar o crescimento e o conforto dos pequenos, com atenção a cada detalhe de "
        "acabamento.</p>"
    )

    h3_loja = "<h3>Compre na Kmilaa Modas</h3>"
    paragrafo_loja = (
        "<p>Na Kmilaa Modas você encontra uma seleção de moda infantil com atendimento "
        f"dedicado, {_DIFERENCIAIS_LOJA}. Fale com a gente e garanta o seu.</p>"
    )

    blocos = [
        h2,
        paragrafo_1,
        paragrafo_2,
        lista,
        h3_marca,
        paragrafo_marca,
        h3_loja,
        paragrafo_loja,
    ]

    descricao = "\n".join(blocos)
    return _garantir_minimo_de_palavras(descricao, paragrafo_2)


def _contar_palavras(html: str) -> int:
    sem_tags = html
    for aberto, fechado in (
        ("<h2>", "</h2>"),
        ("<h3>", "</h3>"),
        ("<p>", "</p>"),
        ("<li>", "</li>"),
    ):
        sem_tags = sem_tags.replace(aberto, " ").replace(fechado, " ")
    sem_tags = sem_tags.replace("<ul>", " ").replace("</ul>", " ")
    return len(sem_tags.split())


_FRASES_PREENCHIMENTO = (
    "Uma peça pensada para o dia a dia, do jeito que a família precisa.",
    "Qualidade de tecido revisada a cada lote, para chegar sempre perfeita até você.",
    "Fácil de combinar com o resto do guarda-roupa, para qualquer ocasião.",
    "Feita para durar mesmo com o uso intenso da rotina dos pequenos.",
)


def _garantir_minimo_de_palavras(descricao: str, paragrafo_2: str) -> str:
    """Acrescenta frases fixas e determinísticas ao 2º parágrafo até bater o mínimo de palavras."""
    indice = 0
    while _contar_palavras(descricao) < _MINIMO_PALAVRAS_DESCRICAO:
        frase = _FRASES_PREENCHIMENTO[indice % len(_FRASES_PREENCHIMENTO)]
        novo_paragrafo_2 = paragrafo_2.replace("</p>", f" {frase}</p>")
        descricao = descricao.replace(paragrafo_2, novo_paragrafo_2)
        paragrafo_2 = novo_paragrafo_2
        indice += 1
    return descricao
