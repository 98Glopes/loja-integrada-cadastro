from __future__ import annotations

from collections.abc import Mapping

from jinja2 import (
    BaseLoader,
    Environment,
    PackageLoader,
    StrictUndefined,
    Template,
    TemplateError,
    TemplateNotFound,
)

from loja_integrada_cadastro.models.exceptions.erro_prompt import ErroPrompt
from loja_integrada_cadastro.models.prompt_renderizado import PromptRenderizado

_PACOTE = "loja_integrada_cadastro"
_PASTA_PROMPTS = "recursos/prompts"
_EXTENSAO = ".j2"
_BLOCOS_SISTEMA = ("sistema_fixo", "sistema_marca")
_BLOCO_USUARIO = "usuario"


class RepositorioPromptsJinja:
    """Renderiza `recursos/prompts/<nome>.j2` em blocos separados (`docs/ARQUITETURA.md` §6.4).

    Cada template declara `{% block sistema_fixo %}`, `{% block sistema_marca %}` (opcional) e
    `{% block usuario %}`. Os blocos de system são renderizados um a um e devolvidos separados,
    na ordem, para o conector marcar o breakpoint de cache no último. `autoescape` fica
    desligado (os prompts contêm tags como `<produto>` de propósito) e `StrictUndefined` faz
    variável faltante virar `ErroPrompt` em vez de texto vazio silencioso.
    """

    def __init__(self, loader: BaseLoader | None = None) -> None:
        self._ambiente = Environment(
            loader=loader or PackageLoader(_PACOTE, _PASTA_PROMPTS),
            autoescape=False,
            undefined=StrictUndefined,
            trim_blocks=True,
            lstrip_blocks=True,
            keep_trailing_newline=False,
        )

    def renderizar(self, nome: str, contexto: Mapping[str, object]) -> PromptRenderizado:
        template = self._carregar(nome)
        blocos_sistema = tuple(
            texto
            for bloco in _BLOCOS_SISTEMA
            if (texto := self._renderizar_bloco(template, nome, bloco, contexto))
        )
        if _BLOCO_USUARIO not in template.blocks:
            raise ErroPrompt(nome, f"bloco obrigatório '{_BLOCO_USUARIO}' ausente")
        usuario = self._renderizar_bloco(template, nome, _BLOCO_USUARIO, contexto)
        return PromptRenderizado(blocos_sistema=blocos_sistema, usuario=usuario)

    def _carregar(self, nome: str) -> Template:
        try:
            return self._ambiente.get_template(f"{nome}{_EXTENSAO}")
        except TemplateNotFound as erro:
            raise ErroPrompt(nome, f"template '{nome}{_EXTENSAO}' não encontrado") from erro
        except TemplateError as erro:
            raise ErroPrompt(nome, f"template malformado: {erro}") from erro

    def _renderizar_bloco(
        self, template: Template, nome: str, bloco: str, contexto: Mapping[str, object]
    ) -> str:
        renderizador = template.blocks.get(bloco)
        if renderizador is None:
            return ""
        try:
            return "".join(renderizador(template.new_context(dict(contexto)))).strip()
        except TemplateError as erro:
            raise ErroPrompt(nome, f"erro ao renderizar bloco '{bloco}': {erro}") from erro
