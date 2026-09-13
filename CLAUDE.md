# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Projeto

CLI em Python para cadastro de produtos em massa na plataforma **Loja Integrada**. Recebe uma planilha de produtos de e-commerce, gera descrições e realiza os cadastros na plataforma. O código deve ser estruturado para evoluir, sem reescrita, de CLI para serviço web.

Estado atual: esqueleto de pastas e toolchain criados, sem casos de uso implementados. Este arquivo registra os **requisitos não funcionais** e as decisões de arquitetura que toda contribuição deve respeitar.

## Comandos

Toolchain (Python 3.12+, definido em `pyproject.toml`):

```bash
python -m venv .venv && .venv/Scripts/activate   # Windows (bash: source .venv/Scripts/activate)
pip install -e ".[dev]"                          # instala o pacote + dev deps (pytest, ruff, mypy)

ruff check . && ruff format .                    # lint + formatação
mypy src                                         # type check (strict)
pytest                                           # todos os testes
pytest tests/unit/models/test_produto.py         # um arquivo
pytest tests/unit/models/test_produto.py::test_nome -v   # um teste
pytest -k "descricao"                            # por palavra-chave

python -m loja_integrada_cadastro <planilha.xlsx>   # executa a CLI
```

## Arquitetura: Hexagonal (Ports & Adapters) em layout simplificado

Layout em `src/loja_integrada_cadastro/`:

```
models/          Entidades, value objects e regras de negócio puras. ZERO imports de infra.
  exceptions/    Exceções de domínio.
services/        Lógica de negócio: casos de uso que orquestram models + ports.
  ports/         Interfaces (typing.Protocol) que os services exigem do mundo externo.
                 Ex.: LeitorPlanilha, ClienteLojaIntegrada, GeradorDescricao
infra/           Conectores de infraestrutura: implementações concretas dos ports.
                 Ex.: leitor_openpyxl.py, cliente_http_loja_integrada.py, gerador_llm.py
config/          Configurações e composition root (wiring/injeção de dependências).
cli.py           Entrada CLI: só faz parsing de argumentos e chama services.
```

Regra de dependência (inviolável): `cli / infra → services → models`. `models` nunca importa de `services` ou `infra`; `services` nunca importa de `infra` — enxerga infraestrutura apenas pelos `Protocol`s em `services/ports/`, injetados via construtor em `config/`.

Por que isso importa aqui: a evolução para serviço web deve consistir apenas em adicionar um `web.py`/`web/` (ex.: FastAPI) ao lado de `cli.py`, reutilizando os mesmos services — se um service precisar mudar para suportar web, o design está errado.

## Convenções de código (não negociáveis)

- **Arquitetura evolutiva, não especulativa:** crie pastas, ports e abstrações somente quando uma funcionalidade concreta precisar delas. Não antecipe camadas, interfaces ou módulos "para o futuro"; o layout acima é a direção, não um esqueleto a preencher.
- **Uma classe por arquivo.** Nome do arquivo em `snake_case` espelhando a classe (`produto.py` → `class Produto`).
- **Type hints em tudo** (parâmetros, retornos, atributos). `mypy --strict` deve passar.
- **Clean Code / legibilidade humana:** nomes que revelam intenção, funções pequenas, sem comentários que expliquem código ruim — refatore em vez de comentar.
- **SOLID com ênfase em Single Responsibility:** uma classe tem um motivo para mudar. Se uma classe lê planilha *e* valida *e* chama API, divida.
- **Negócio separado de infraestrutura:** classes que tocam rede, disco, processos ou bibliotecas de terceiros pesadas vivem em `infra/`. `models` e `services` são puros e testáveis sem mocks de I/O.
- **Ports como `typing.Protocol`** (structural typing) em vez de herança de ABC, salvo quando comportamento compartilhado justifique.
- Entidades e value objects do domínio como `@dataclass(frozen=True)` quando imutáveis.
- Erros de domínio são exceções próprias em `models/exceptions/`; `infra` traduz erros de infraestrutura (HTTP, IO) para elas — o service nunca captura `requests.HTTPError`.

## Testes

- `tests/unit/` espelha `src/` — `models` e `services` testados com **stubs/fakes dos ports** (sem mock de bibliotecas externas).
- `tests/integration/` para conectores de `infra` reais (API da Loja Integrada, leitura de arquivo), isolados por marker `@pytest.mark.integration` e desligados por padrão.
- Framework: `pytest`. Sem `unittest.TestCase`.

## Plugin habilitado

`python-clean-architecture` (`.claude/settings.local.json`) — use `/python-clean-architecture:review-architecture` e `/python-clean-architecture:check-quality` antes de concluir mudanças estruturais.

## Documentação de negócio

Referências oficiais da Loja Integrada sobre cadastro massivo (fonte de verdade para o formato da planilha e regras de importação):

- [Central de ajuda da Loja Integrada](https://ajuda.lojaintegrada.com.br/pt-BR/)
- [Como cadastrar produtos simples de forma massiva](https://ajuda.lojaintegrada.com.br/pt-BR/articles/5360633-como-cadastrar-produtos-simples-de-forma-massiva)
- [Como cadastrar produtos com variações de forma massiva](https://ajuda.lojaintegrada.com.br/pt-BR/articles/5360649-como-cadastrar-produtos-com-variacoes-de-forma-massiva)

Material de apoio local em `docs/` (planilha modelo, exportação real de produtos, perfis de marca, dados mestre).
