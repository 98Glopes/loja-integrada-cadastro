# Templates de prompt (`*.j2`)

Lidos por `infra/repositorio_prompts_jinja.py` (`RepositorioPromptsJinja.renderizar(nome, contexto)`
carrega `<nome>.j2`). Cada template declara três blocos Jinja2, renderizados separadamente:

```jinja
{% block sistema_fixo %}...regras estáveis da loja/formato...{% endblock %}
{% block sistema_marca %}...perfil da marca (opcional)...{% endblock %}
{% block usuario %}...dados variáveis do produto...{% endblock %}
```

`sistema_fixo` e `sistema_marca` viram `PromptRenderizado.blocos_sistema` (na ordem, blocos
vazios são omitidos) e recebem cache na API; `usuario` é obrigatório. `autoescape` está
desligado e variável faltante é erro (`ErroPrompt`). Os prompts reais dos agentes
(`copywriter.j2`, `seo.j2`, `qa.j2`) chegam na task 13.
