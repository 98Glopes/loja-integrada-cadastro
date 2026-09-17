from __future__ import annotations

import pytest
from jinja2 import DictLoader

from loja_integrada_cadastro.infra.repositorio_prompts_jinja import RepositorioPromptsJinja
from loja_integrada_cadastro.models.exceptions.erro_prompt import ErroPrompt

_COMPLETO = """
{% block sistema_fixo %}
Regras da loja {{ loja }}.
{% endblock %}
{% block sistema_marca %}
Perfil da marca {{ marca }}.
{% endblock %}
{% block usuario %}
<produto>{{ produto.titulo }}</produto>
{% endblock %}
"""

_SEM_MARCA = """
{% block sistema_fixo %}Regras.{% endblock %}
{% block usuario %}Dados: {{ dados }}{% endblock %}
"""

_MARCA_VAZIA = """
{% block sistema_fixo %}Regras.{% endblock %}
{% block sistema_marca %}{% if perfil %}{{ perfil }}{% endif %}{% endblock %}
{% block usuario %}Dados.{% endblock %}
"""

_SEM_USUARIO = "{% block sistema_fixo %}Regras.{% endblock %}"

_MALFORMADO = "{% block sistema_fixo %}Regras."


def _repositorio(**templates: str) -> RepositorioPromptsJinja:
    return RepositorioPromptsJinja(DictLoader({f"{n}.j2": t for n, t in templates.items()}))


def test_renderiza_os_tres_blocos_separados_e_na_ordem() -> None:
    repositorio = _repositorio(copywriter=_COMPLETO)

    prompt = repositorio.renderizar(
        "copywriter", {"loja": "Kmilaa", "marca": "Kiki", "produto": {"titulo": "Vestido"}}
    )

    assert prompt.blocos_sistema == ("Regras da loja Kmilaa.", "Perfil da marca Kiki.")
    assert prompt.usuario == "<produto>Vestido</produto>"


def test_template_sem_bloco_de_marca_devolve_um_bloco_de_sistema() -> None:
    prompt = _repositorio(seo=_SEM_MARCA).renderizar("seo", {"dados": "x"})

    assert prompt.blocos_sistema == ("Regras.",)
    assert prompt.usuario == "Dados: x"


def test_bloco_de_marca_que_renderiza_vazio_e_omitido() -> None:
    prompt = _repositorio(qa=_MARCA_VAZIA).renderizar("qa", {"perfil": ""})

    assert prompt.blocos_sistema == ("Regras.",)


def test_autoescape_desligado_preserva_tags_e_aspas() -> None:
    prompt = _repositorio(x="{% block usuario %}{{ v }}{% endblock %}").renderizar(
        "x", {"v": '<b>"a" & b</b>'}
    )

    assert prompt.usuario == '<b>"a" & b</b>'


def test_variavel_faltante_e_erro_prompt_nao_texto_vazio() -> None:
    with pytest.raises(ErroPrompt, match="copywriter.*bloco 'sistema_fixo'.*'loja'"):
        _repositorio(copywriter=_COMPLETO).renderizar("copywriter", {"marca": "Kiki"})


def test_template_inexistente_e_erro_prompt() -> None:
    with pytest.raises(ErroPrompt, match="template 'nada.j2' não encontrado"):
        _repositorio().renderizar("nada", {})


def test_template_sem_bloco_usuario_e_erro_prompt() -> None:
    with pytest.raises(ErroPrompt, match="bloco obrigatório 'usuario' ausente"):
        _repositorio(x=_SEM_USUARIO).renderizar("x", {})


def test_template_malformado_e_erro_prompt() -> None:
    with pytest.raises(ErroPrompt, match="malformado"):
        _repositorio(x=_MALFORMADO).renderizar("x", {})


def test_loader_padrao_aponta_para_recursos_prompts_do_pacote() -> None:
    repositorio = RepositorioPromptsJinja()

    with pytest.raises(ErroPrompt, match="não encontrado"):
        repositorio.renderizar("inexistente", {})
