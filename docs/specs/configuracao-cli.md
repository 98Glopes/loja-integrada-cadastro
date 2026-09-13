# Módulo: configuracao-cli

**Responsabilidade:** ler a configuração do ambiente e expor a CLI com seus subcomandos, delegando aos casos de uso.
**Estado:** implementado pela task 01 · última atualização 2026-09-13 (task 01)

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
  `processar --planilha --fotos --lote [--incluir-reprovados] [--refazer-textos SKU…] [--refazer-fotos SKU…]`,
  `verificar --lote [--esperar]`.
- `python -m loja_integrada_cadastro …` e o script `loja-integrada-cadastro` chamam
  `__main__.main()`, que faz `SystemExit(AplicacaoCli().executar())`.

## Comportamento

- `do_ambiente()` sem argumento: `load_dotenv(".env")` (cwd; não sobrescreve env existente) e lê
  `os.environ`. Com `Mapping`: usa só o mapping (testes).
- Ausente ou vazio → padrão. `int`/`Decimal` inválidos e `PRODUTO_ATIVO` ∉ {S, N} →
  `ErroConfiguracao` com nome da variável e valor.
- Obrigatórias só são cobradas por `exigir_*` — cada comando chama o que usa.
- Todo subcomando hoje retorna `CODIGO_NAO_IMPLEMENTADO = 2` e escreve `<comando>: não
  implementado` em stderr. Argumento obrigatório ausente → argparse encerra com 2.
- `executar` despacha por `dict[str, Callable[[Namespace], int]]`; nenhuma lógica de negócio
  na CLI.

## Limites

- Não instancia `Configuracao` nem casos de uso ainda — isso entra com `config/composicao.py`
  (tasks 04, 05, 15, 17).
- Não interpreta `--esperar` (task 17) nem valida `LLM_EFFORT_*` (task 09).
- Não expõe `--sem-upload`/`--verboso` (task 15).

## Testes

- `tests/unit/config/test_configuracao.py`: padrões, conversão, string vazia, `exigir_*`,
  valores inválidos (parametrizado), imutabilidade.
- `tests/unit/test_cli.py`: `--help` com 4 subcomandos, retorno 2 + mensagem por subcomando,
  parsing completo de `processar`, defaults, `--destino`, `--esperar`, erros de uso.
- Para outros módulos: construir `Configuracao.do_ambiente({...})` ou `Configuracao(campo=...)`
  diretamente — não há fake necessário.

## Histórico

- Task 01 (2026-09-13): criação do módulo — `Configuracao`, `LeitorAmbiente`, `ErroConfiguracao`,
  `AplicacaoCli` com 4 subcomandos, `.env.exemplo`.
