# Spec as-built — Task 01: Fundação: configuração e CLI com subcomandos

- **Data:** 2026-09-13 · **Task:** `docs/tasks/01-fundacao-configuracao-cli.md` · **Módulos:** `configuracao-cli`

## Entregue

- `python -m loja_integrada_cadastro --help` lista os subcomandos `modelo-entrada`, `validar`,
  `processar`, `verificar`, cada um com seus argumentos definitivos (§3/§8/§9 + `--destino`).
- Qualquer subcomando com argumentos válidos escreve `<comando>: não implementado` em stderr e
  retorna código de saída 2; argumento obrigatório ausente → erro de uso do argparse (código 2).
- `Configuracao.do_ambiente()` carrega `.env` do diretório corrente (se existir) e monta um
  dataclass imutável com todos os padrões de §11; `exigir_anthropic()`/`exigir_r2()` falham com
  `ErroConfiguracao` nomeando a variável ausente. Valor não conversível também falha nomeando a
  variável e o valor.
- `.env.exemplo` documenta todas as variáveis de §11.

## Arquivos

| Camada | Criados | Alterados |
|---|---|---|
| models | `models/exceptions/erro_configuracao.py` | — |
| config | `config/configuracao.py`, `config/leitor_ambiente.py` | — |
| cli | — | `cli.py`, `__main__.py` |
| raiz | `.env.exemplo` | `pyproject.toml` (`python-dotenv>=1.0`; `ignore = ["N818"]`) |
| tests | `tests/unit/config/__init__.py`, `tests/unit/config/test_configuracao.py`, `tests/unit/test_cli.py` | — |

## Contratos

```python
# models/exceptions/erro_configuracao.py
class ErroConfiguracao(Exception):
    variavel: str
    valor_invalido: str | None      # None → "Variável de ambiente obrigatória não definida: <VAR>"
                                    # str  → "Valor inválido para <VAR>: '<valor>'"

# config/configuracao.py
@dataclass(frozen=True)
class Configuracao:
    anthropic_api_key: str | None = None
    llm_modelo_copywriter: str = "claude-opus-5"; llm_modelo_seo: str = ...; llm_modelo_qa: str = ...
    llm_effort_copywriter: str = "high"; llm_effort_seo: str = "medium"; llm_effort_qa: str = "medium"
    llm_max_tentativas_qa: int = 2
    r2_account_id, r2_access_key_id, r2_secret_access_key, r2_bucket, r2_url_publica: str | None = None
    imagem_lado_max_px: int = 1600; imagem_tamanho_max_kb: int = 500
    produto_ativo: str = "S"                       # só "S" ou "N" (normalizado para maiúscula)
    peso_kg: Decimal = Decimal("0.1"); altura_cm = Decimal("4"); largura_cm = Decimal("22"); comprimento_cm = Decimal("22")
    loja_url: str = "https://www.kmilaamodas.com.br"
    lotes_dir: Path = Path("lotes")

    @classmethod
    def do_ambiente(cls, ambiente: Mapping[str, str] | None = None) -> Configuracao
    def exigir_anthropic(self) -> str            # devolve a chave ou ErroConfiguracao("ANTHROPIC_API_KEY")
    def exigir_r2(self) -> None                  # ErroConfiguracao na 1ª R2_* ausente, ordem de §11

# config/leitor_ambiente.py (colaborador interno de Configuracao)
class LeitorAmbiente:
    def __init__(self, ambiente: Mapping[str, str]) -> None
    def opcional(self, variavel) -> str | None   # "" e espaços contam como ausente
    def texto(self, variavel, padrao) -> str
    def inteiro(self, variavel, padrao) -> int
    def decimal(self, variavel, padrao) -> Decimal
    def sim_ou_nao(self, variavel, padrao) -> str

# cli.py
class AplicacaoCli:
    def executar(self, argumentos: Sequence[str] | None = None) -> int
    def criar_parser(self) -> ArgumentParser
CODIGO_NAO_IMPLEMENTADO = 2
```

Subcomandos e argumentos:

| Subcomando | Argumentos |
|---|---|
| `modelo-entrada` | `--destino PATH` (padrão `modelo-entrada.xlsx`) |
| `validar` | `--planilha PATH` (obrig.), `--fotos PATH` (obrig.) |
| `processar` | `--planilha PATH`, `--fotos PATH`, `--lote STR` (obrig.); `--incluir-reprovados` (flag); `--refazer-textos SKU [SKU…]`; `--refazer-fotos SKU [SKU…]` (padrão `[]`) |
| `verificar` | `--lote STR` (obrig.); `--esperar STR` (ex.: `5m`; não interpretado ainda) |

Variáveis de ambiente: exatamente as de `ARQUITETURA.md` §11 (ver `.env.exemplo`).

## Regras de negócio implementadas

- Padrões de §11 valem quando a variável está ausente ou vazia.
- Variável obrigatória só é exigida pelo método `exigir_*` correspondente, não na construção.
- `PRODUTO_ATIVO` aceita apenas `S`/`N` (caixa indiferente); outro valor → `ErroConfiguracao`.
- Inteiros (`LLM_MAX_TENTATIVAS_QA`, `IMAGEM_*`) e decimais (`PESO_KG`, `*_CM`) inválidos →
  `ErroConfiguracao` com nome da variável e valor recebido.

## Desvios e decisões

| Pedido (task/arquitetura) | Feito | Motivo |
|---|---|---|
| `modelo-entrada` sem argumentos listados na task 01 | `--destino` incluído (padrão `modelo-entrada.xlsx`) | Task 04 já define esse argumento; evita mexer na CLI duas vezes. |
| Tipos dos padrões físicos não especificados | `Decimal` para `PESO_KG`/`*_CM`; `Path` para `LOTES_DIR` | `Decimal` preserva `0.1` exato ao escrever a planilha; `Path` é o tipo natural para diretório. |
| `exigir_r2()` "lança ErroConfiguracao" | Retorna `None`; não agrupa credenciais em classe | Arquitetura evolutiva: a task 08 decide se precisa de um VO de credenciais. |
| `LLM_EFFORT_*` | `str` livre, sem validação | Valores válidos dependem do SDK; a task 12 valida. |
| "python-dotenv carregar `.env` se existir" | `load_dotenv(".env")` relativo ao cwd, sem sobrescrever variáveis já definidas; só quando `do_ambiente()` é chamado sem `ambiente` | Previsível para CLI instalada; testes injetam `dict` e não tocam o disco. |
| Mensagem "não implementado" | Escrita em **stderr** | Diagnóstico não é saída de dados. |
| Uma classe por arquivo | `LeitorAmbiente` em `config/leitor_ambiente.py` | Conversão de env separada do dataclass; ambos em `config/`. |
| ruff `N` completo | `ignore = ["N818"]` em `pyproject.toml` | A arquitetura nomeia exceções `Erro<Nome>`; N818 exigiria sufixo `Error`. |

Nenhuma decisão de arquitetura mudou → sem ADR.

## Verificação executada

- `ruff check . && ruff format --check . && mypy src && pytest` → tudo passando (26 testes).
- Manual: `python -m loja_integrada_cadastro --help` lista os 4 subcomandos;
  `processar --planilha x.xlsx --fotos f --lote t` → stderr `processar: não implementado`, código 2;
  `Configuracao.do_ambiente()` sem `.env` → padrões de §11.
- `/python-clean-architecture:check-quality` → 3 ajustes menores aplicados (nome `leitor`,
  `dict` em `exigir_r2`, um método por subparser).

## Pendências para tasks futuras

- Ligar cada subcomando ao seu caso de uso via `config/composicao.py`: 04 (`modelo-entrada`),
  05 (`validar`), 15 (`processar`, + `--sem-upload`, `--verboso`), 17 (`verificar`, parse de `--esperar`).
- Traduzir `ErroConfiguracao` em mensagem e código de saída na CLI quando o primeiro comando
  consumir `Configuracao` (task 04/05).
