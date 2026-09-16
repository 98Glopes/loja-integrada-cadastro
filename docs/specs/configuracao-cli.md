# Módulo: configuracao-cli

**Responsabilidade:** ler a configuração do ambiente e expor a CLI com seus subcomandos, delegando aos casos de uso.
**Estado:** implementado pelas tasks 01, 11 · última atualização 2026-09-16 (task 11)

## Arquivos

- models: `src/loja_integrada_cadastro/models/exceptions/erro_configuracao.py`
- config: `src/loja_integrada_cadastro/config/configuracao.py`, `config/leitor_ambiente.py`
- cli: `src/loja_integrada_cadastro/cli.py`, `__main__.py`
- raiz: `.env.exemplo`
- tests: `tests/unit/config/test_configuracao.py`, `tests/unit/test_cli.py`

## Contratos

- `Configuracao` (frozen dataclass) — campos, tipos e padrões em
  `docs/specs/tasks/01-fundacao-configuracao-cli.md` §Contratos; espelham `ARQUITETURA.md` §11.
  - `Configuracao.do_ambiente(ambiente: Mapping[str, str] | None = None) -> Configuracao`
  - `exigir_anthropic() -> str` · `exigir_r2() -> None` — lançam `ErroConfiguracao(variavel)`.
- `ErroConfiguracao(variavel: str, valor_invalido: str | None = None)` — atributos `variavel`,
  `valor_invalido`.
- `AplicacaoCli.executar(argumentos: Sequence[str] | None = None) -> int` ·
  `AplicacaoCli.criar_parser() -> ArgumentParser`.
- Subcomandos: `modelo-entrada [--destino]`, `validar --planilha --fotos`,
  `processar --planilha --fotos --lote [--incluir-reprovados] [--refazer-textos SKU…] [--refazer-fotos SKU…] [--verboso]`
  (task 11), `verificar --lote [--esperar]`.
- `python -m loja_integrada_cadastro …` e o script `loja-integrada-cadastro` chamam
  `__main__.main()`, que faz `SystemExit(AplicacaoCli().executar())`.

## Comportamento

- `do_ambiente()` sem argumento: `load_dotenv(".env")` (cwd; não sobrescreve env existente) e lê
  `os.environ`. Com `Mapping`: usa só o mapping (testes).
- Ausente ou vazio → padrão. `int`/`Decimal` inválidos e `PRODUTO_ATIVO` ∉ {S, N} →
  `ErroConfiguracao` com nome da variável e valor.
- Obrigatórias só são cobradas por `exigir_*` — cada comando chama o que usa.
- `verificar` retorna `CODIGO_NAO_IMPLEMENTADO = 2` e escreve `<comando>: não implementado` em
  stderr; `modelo-entrada`/`validar`/`processar` já são reais (tasks 04, 05, 11). Argumento
  obrigatório ausente → argparse encerra com 2.
- `executar` despacha por `dict[str, Callable[[Namespace], int]]`; nenhuma lógica de negócio
  na CLI.

## Limites

- Não instancia `Configuracao` nem casos de uso ainda para `verificar` — isso entra na task 18.
  `processar` já instancia (`Configuracao.do_ambiente()`) e chama `exigir_r2()` desde a task 11
  (primeiro comando a exigir configuração de verdade; `ErroConfiguracao` vira código de erro de
  negócio, igual aos outros comandos).
- Não interpreta `--esperar` (task 18) nem valida `LLM_EFFORT_*` (task 12).
- `--sem-upload` não existe — decisão confirmada com o usuário (ADR-008): `processar` sempre
  publica no R2 real. `--verboso` existe desde a task 11 (nível de log, não passado a
  `Configuracao`).

## Testes

- `tests/unit/config/test_configuracao.py`: padrões, conversão, string vazia, `exigir_*`,
  valores inválidos (parametrizado), imutabilidade.
- `tests/unit/test_cli.py`: `--help` com 4 subcomandos; `verificar` retorna 2 + mensagem "não
  implementado"; parsing completo de `processar` (incluindo `--verboso`), defaults, `--destino`,
  `--esperar`, erros de uso; `processar` sem R2 configurado (`monkeypatch.chdir`/`delenv` para
  isolar do `.env` real do desenvolvedor) devolve código de erro de negócio com a mensagem de
  `ErroConfiguracao`.
- Para outros módulos: construir `Configuracao.do_ambiente({...})` ou `Configuracao(campo=...)`
  diretamente — não há fake necessário.

## Histórico

- Task 01 (2026-09-13): criação do módulo — `Configuracao`, `LeitorAmbiente`, `ErroConfiguracao`,
  `AplicacaoCli` com 4 subcomandos, `.env.exemplo`.
- Task 11 (2026-09-16): `processar` deixa de ser stub — chama `Configuracao.do_ambiente()` e
  `exigir_r2()` (primeiro comando a exigir configuração de verdade), ganha `--verboso`
  (nível de log). `--sem-upload` não foi implementada (ADR-008).
