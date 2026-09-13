# Task 01 — Fundação: configuração e CLI com subcomandos

- **Depende de:** nenhuma
- **Modelo recomendado:** sonnet
- **Leia antes:** `CLAUDE.md`; `docs/ARQUITETURA.md` §3 (fluxo), §10 (código), §11 (configuração)

## Objetivo

Deixar a CLI com a estrutura de subcomandos definitiva e a configuração carregada de
variáveis de ambiente, sem nenhum caso de uso implementado ainda. Tudo que vier depois se
encaixa aqui.

## Escopo

1. `config/configuracao.py`: `@dataclass(frozen=True) Configuracao` com os campos de §11
   (valores padrão do documento). Método de classe `Configuracao.do_ambiente()` que lê
   `os.environ` (após `python-dotenv` carregar `.env` se existir). Variáveis obrigatórias
   só são exigidas pelo comando que as usa: expor `exigir_anthropic()` e `exigir_r2()` que
   lançam `ErroConfiguracao` (nova exceção em `models/exceptions/`) com mensagem dizendo o
   nome da variável faltante.
2. `cli.py`: `AplicacaoCli` com `argparse` e subcomandos `modelo-entrada`, `validar`,
   `processar`, `verificar`, cada um com os argumentos de §3/§8/§9 (`--planilha`, `--fotos`,
   `--lote`, `--incluir-reprovados`, `--refazer-textos`, `--refazer-fotos`, `--esperar`).
   Cada subcomando por enquanto imprime "não implementado" e retorna código de saída 2.
   A CLI só faz parsing e delega; nenhuma lógica de negócio aqui.
3. `.env.exemplo` na raiz com todas as variáveis de §11 comentadas.
4. `pyproject.toml`: adicionar `python-dotenv`.
5. Testes: `tests/unit/config/test_configuracao.py` (padrões, leitura de env, erro claro
   quando falta variável obrigatória) e `tests/unit/test_cli.py` (parsing dos subcomandos).

## Fora do escopo

Qualquer service, port ou conector. Não criar pastas vazias "para depois".

## Critério de aceite

- `python -m loja_integrada_cadastro --help` lista os 4 subcomandos.
- `python -m loja_integrada_cadastro processar --planilha x.xlsx --fotos f --lote t` retorna 2
  com mensagem "não implementado".
- `Configuracao.do_ambiente()` sem `.env` produz os padrões de §11.
- `ruff check . && ruff format --check . && mypy src && pytest` passam.

## Ao concluir

Atualizar status em `docs/tasks/README.md`.
