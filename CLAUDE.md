# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Projeto

CLI em Python para cadastro de produtos em massa na plataforma **Loja Integrada**. Recebe uma planilha de produtos de e-commerce, gera descrições e realiza os cadastros na plataforma. O código deve ser estruturado para evoluir, sem reescrita, de CLI para serviço web.

Estado atual: esqueleto de pastas e toolchain criados, sem casos de uso implementados.
Arquitetura definida e backlog planejado (13/09/2026). Este arquivo registra os **requisitos
não funcionais**; a arquitetura funcional está em `docs/ARQUITETURA.md` e as tasks em
`docs/tasks/` — leia ambos antes de implementar qualquer coisa.

Fluxo de trabalho: uma task de `docs/tasks/` por sessão, na ordem do `docs/tasks/README.md`,
seguindo o ciclo abaixo. Nenhuma task deve decidir regra de negócio nova sozinha — registre e
pergunte.

## Ciclo spec → código → spec (obrigatório em toda task)

Gatilho: qualquer pedido de "implementar a task NN" ou mudança funcional. Uma task só está
concluída quando os passos 4 e 5 foram feitos — código sem spec não conta como pronto.

1. **Ler**: `docs/ARQUITETURA.md` (seções citadas na task, §10 e §16), o arquivo da task,
   `docs/specs/README.md`, as specs vivas dos módulos que a task toca (`docs/specs/<modulo>.md`)
   e as specs das tasks de que ela depende (`docs/specs/tasks/`).
2. **Confrontar** task × arquitetura × specs vivas. Divergência, ambiguidade ou regra de
   negócio nova → parar e perguntar antes de codar.
3. **Implementar e verificar**: `ruff check . && ruff format . && mypy src && pytest`, depois
   `/python-clean-architecture:check-quality` sobre a mudança.
4. **Registrar** (todos, com os templates de `docs/specs/README.md`):
   - `docs/specs/tasks/NN-<nome>.md` — spec *as-built* da task: o que existe, com assinaturas,
     nomes de arquivo e comandos reais; seção "Desvios e decisões" obrigatória ("nenhum" se
     não houver).
   - `docs/specs/<modulo>.md` — criar ou atualizar a spec viva de cada módulo tocado.
   - `docs/ARQUITETURA.md` — reescrever as seções afetadas para refletir o implementado;
     marcar itens com 🔲 planejado / ✅ implementado (task NN); §10 com os arquivos reais; §14
     com riscos resolvidos; decisão que mudou → nova entrada em §16 (ADR: contexto, decisão,
     consequência, task). Nunca marcar ✅ o que não tem teste passando.
   - `docs/tasks/README.md` — status `concluída` e link para a spec da task.
5. **Commitar** automaticamente: um commit por task, título `Task NN: <resultado em uma
   linha>`, corpo com `Spec: docs/specs/tasks/NN-<nome>.md`, módulos atualizados e seções da
   arquitetura alteradas, mais as linhas de atribuição da sessão.
6. **Resumir** ao usuário: o que foi entregue, desvios, o que mudou na arquitetura, próxima
   task.

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

**Documentos canônicos (versionados em `docs/`):**

- `docs/ARQUITETURA.md` — fonte de verdade do sistema: decisões, fluxo, planilha de entrada,
  fotos/R2, agentes de IA, saída, estado, verificação, arquitetura de código, configuração.
- `docs/regras-planilha-loja-integrada.md` — formato de saída (54 colunas, pai/filha, grades),
  provado por importação real em 13/09/2026 (`poc/`). O layout vem da **exportação real** da
  loja, não do `planilha-modelo.xlsx` genérico (49 colunas, sem `grade-tamanho-infantil`).
- `docs/tasks/` — backlog de implementação (uma task por arquivo, índice em `README.md`).
- `docs/specs/` — o que **existe**: spec viva por módulo (`<modulo>.md`) e spec as-built por
  task (`tasks/NN-<nome>.md`); templates e mapa de módulos em `docs/specs/README.md`.

**Material bruto (não versionado, `docs/brutos/`):** skill original de copywriting (`SKILL.md`),
`brand_profiles.md`, `dados_mestre.md`, exportação real do catálogo (`produtos-*.xlsx`),
`planilha-modelo.xlsx`, notas do suporte. Servem de insumo para as tasks; quando divergirem de
`ARQUITETURA.md`, vale a arquitetura.
