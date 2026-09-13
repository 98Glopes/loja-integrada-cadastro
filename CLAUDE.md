# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Projeto

CLI em Python para cadastro de produtos em massa na plataforma **Loja Integrada**. Recebe uma planilha de produtos de e-commerce, gera descrições e realiza os cadastros na plataforma. O código deve ser estruturado para evoluir, sem reescrita, de CLI para serviço web.

Estado atual: repositório recém-criado (apenas `.gitignore`). Este arquivo registra os **requisitos não funcionais** e as decisões de arquitetura que toda contribuição deve respeitar.

## Comandos

Toolchain alvo (Python 3.14 disponível na máquina). Criar `pyproject.toml` com estas ferramentas na primeira implementação:

```bash
python -m venv .venv && .venv/Scripts/activate   # Windows (bash: source .venv/Scripts/activate)
pip install -e ".[dev]"                          # instala o pacote + dev deps (pytest, ruff, mypy)

ruff check . && ruff format .                    # lint + formatação
mypy src                                         # type check (strict)
pytest                                           # todos os testes
pytest tests/unit/domain/test_product.py         # um arquivo
pytest tests/unit/domain/test_product.py::test_nome -v   # um teste
pytest -k "descricao"                            # por palavra-chave

python -m loja_integrada_cadastro <planilha.xlsx>   # executa a CLI
```

## Arquitetura: Hexagonal (Ports & Adapters)

Layout em `src/loja_integrada_cadastro/`:

```
domain/          Entidades, value objects e regras de negócio. ZERO imports externos ao domínio.
application/     Casos de uso (use cases) + definições de PORTS (Protocols/ABCs).
  ports/         Interfaces que o domínio/aplicação exigem do mundo externo.
    inbound/     Ex.: CadastrarProdutosPort (o que a CLI/web chama)
    outbound/    Ex.: LeitorPlanilhaPort, LojaIntegradaPort, GeradorDescricaoPort
  use_cases/     Um caso de uso por arquivo, orquestra domínio + ports outbound.
adapters/        Implementações concretas dos ports (infraestrutura).
  inbound/cli/   Entrada via CLI (Typer/argparse). Só faz parsing e chama use cases.
  outbound/      Ex.: leitor_openpyxl.py, cliente_loja_integrada.py, gerador_llm.py, escritor_disco.py
config/          Composition root: wiring/injeção de dependências. Único lugar que conhece todas as camadas.
```

Regra de dependência (inviolável): `adapters → application → domain`. Domínio nunca importa de `application` ou `adapters`; `application` nunca importa de `adapters`. Toda dependência em infraestrutura (HTTP, disco, LLM, planilha) entra por um **port** (`typing.Protocol`) e é injetada via construtor no composition root.

Por que isso importa aqui: a evolução para serviço web deve consistir apenas em adicionar `adapters/inbound/web/` (ex.: FastAPI) reutilizando os mesmos use cases — se um use case precisar mudar para suportar web, o design está errado.

## Convenções de código (não negociáveis)

- **Uma classe por arquivo.** Nome do arquivo em `snake_case` espelhando a classe (`produto.py` → `class Produto`).
- **Type hints em tudo** (parâmetros, retornos, atributos). `mypy --strict` deve passar.
- **Clean Code / legibilidade humana:** nomes que revelam intenção, funções pequenas, sem comentários que expliquem código ruim — refatore em vez de comentar.
- **SOLID com ênfase em Single Responsibility:** uma classe tem um motivo para mudar. Se uma classe lê planilha *e* valida *e* chama API, divida.
- **Negócio separado de infraestrutura:** classes que tocam rede, disco, processos ou bibliotecas de terceiros pesadas vivem em `adapters/`. Domínio e use cases são puros e testáveis sem mocks de I/O.
- **Ports como `typing.Protocol`** (structural typing) em vez de herança de ABC, salvo quando comportamento compartilhado justifique.
- Entidades e value objects do domínio como `@dataclass(frozen=True)` quando imutáveis.
- Erros de domínio são exceções próprias em `domain/exceptions/`; adapters traduzem erros de infraestrutura (HTTP, IO) para elas — o use case nunca captura `requests.HTTPError`.

## Testes

- `tests/unit/` espelha `src/` — domínio e use cases testados com **stubs/fakes dos ports** (sem mock de bibliotecas externas).
- `tests/integration/` para adapters reais (API da Loja Integrada, leitura de arquivo), isolados por marker `@pytest.mark.integration` e desligados por padrão.
- Framework: `pytest`. Sem `unittest.TestCase`.

## Plugin habilitado

`python-clean-architecture` (`.claude/settings.local.json`) — use `/python-clean-architecture:review-architecture` e `/python-clean-architecture:check-quality` antes de concluir mudanças estruturais.
