# Spec as-built — Task 02: Dados mestre e carregador de recursos

- **Data:** 2026-09-13 · **Task:** `docs/tasks/02-dados-mestre-recursos.md` · **Módulos:** `dados-mestre-recursos`

## Entregue

- `recursos/dados_mestre.yaml` versionado no pacote, com `marcas` (9 canônicas + aliases +
  2 proibidas, editada à mão), `cores` (413 grafias observadas, ordenadas por uso decrescente),
  `tamanhos` (17 tokens: `P M G GG XG` + `1 2 3 4 6 8 10 12 14 16 18 20`) e
  `categorias_referencia` (45 caminhos observados).
- `scripts/extrair_dados_mestre.py` regenera `cores`/`tamanhos`/`categorias_referencia` a partir
  de um `.xlsx` de exportação real, preservando `marcas` intacta; rodar duas vezes sobre o mesmo
  arquivo de entrada produz o YAML idêntico byte-a-byte (verificado por hash).
- `CarregadorRecursos().dados_mestre()` lê e valida o YAML do pacote via `importlib.resources` e
  monta `DadosMestre`; `.texto(nome)` lê qualquer recurso como texto puro.
- `DadosMestre` responde `marca_canonica`, `motivo_marca_proibida` (ignorando caixa/acento),
  `cor_valida`, `tamanho_valido`, `categoria_conhecida` (comparação exata nos três últimos).

## Arquivos

| Camada | Criados | Alterados |
|---|---|---|
| models | `models/dados_mestre.py`, `models/exceptions/erro_recursos.py` | — |
| infra | `infra/carregador_recursos.py` | — |
| recursos | `recursos/__init__.py`, `recursos/dados_mestre.yaml` | — |
| scripts | `scripts/extrair_dados_mestre.py` | — |
| raiz | — | `pyproject.toml` (`pyyaml`, `types-PyYAML`, `package-data` inclui `recursos/**`, `ruff.src` inclui `scripts`) |
| tests | `tests/unit/models/test_dados_mestre.py`, `tests/unit/infra/__init__.py`, `tests/unit/infra/test_carregador_recursos.py` | — |

## Contratos

```python
# models/exceptions/erro_recursos.py
class ErroRecursos(Exception):
    recurso: str        # nome do arquivo, ex.: "dados_mestre.yaml"
    motivo: str          # texto livre e específico, ex.: "seção obrigatória ausente: 'cores'"

# models/dados_mestre.py
@dataclass(frozen=True)
class DadosMestre:
    marcas_canonicas: Mapping[str, tuple[str, ...]]   # canônica -> aliases
    marcas_proibidas: Mapping[str, str]               # nome -> motivo
    cores: frozenset[str]
    tamanhos: frozenset[str]
    categorias_referencia: frozenset[str]

    def marca_canonica(self, texto: str) -> str | None       # ignora caixa/acento (NFKD + casefold)
    def motivo_marca_proibida(self, texto: str) -> str | None # idem
    def cor_valida(self, texto: str) -> bool                  # comparação exata
    def tamanho_valido(self, texto: str) -> bool               # comparação exata
    def categoria_conhecida(self, caminho: str) -> bool         # comparação exata

# infra/carregador_recursos.py
class CarregadorRecursos:
    def texto(self, nome: str) -> str                 # importlib.resources; ErroRecursos se ausente
    def dados_mestre(self) -> DadosMestre              # yaml.safe_load + montar_dados_mestre

def montar_dados_mestre(bruto: object) -> DadosMestre  # validação isolada de I/O, testável com dict puro
```

Esquema de `recursos/dados_mestre.yaml`:

```yaml
marcas:
  canonicas: {<nome>: {aliases: [<alias>, ...]}, ...}
  proibidas: {<nome>: "<motivo>", ...}
cores: [{nome: "<grafia>", uso: <int>}, ...]        # ordenado por uso decrescente
tamanhos: ["P", "M", "G", "GG", "XG", "1", "2", ...] # números como string YAML
categorias_referencia: ["<nivel1> > <nivel2> > ...", ...]
```

`scripts/extrair_dados_mestre.py`:

```python
def extrair(caminho_xlsx: Path) -> ExtracaoPlanilha    # lê tipo=variacao/com-variacao por header
def montar_cores(contagem: Counter[str]) -> list[dict[str, Any]]
def montar_tamanhos(vistos: set[str]) -> list[str]
def montar_categorias(vistas: set[str]) -> list[str]
def carregar_marcas_existentes(caminho_yaml: Path) -> dict[str, Any]  # falha se 'marcas' não existir
def main(argv: list[str]) -> int
```

## Regras de negócio implementadas

- Marca é resolvida por grafia canônica ou qualquer alias, ignorando caixa e acentuação.
- Marca proibida (`Açucena`, `Abrange`) devolve o motivo documentado; case-insensitive.
- Cor e tamanho são validados por comparação **exata** (decisão estrita da task).
- Categoria de referência é comparação exata sobre o caminho completo (`nivel1 > nivel2 > ...`);
  usada só como referência/aviso, nunca bloqueia (regra de negócio de `dados_mestre.md` §3, fora
  do escopo desta task implementar o bloqueio).
- Coluna `tipo = sem-variacao` (1 linha residual na exportação real) não contribui para nenhuma
  das três extrações.
- `scripts/extrair_dados_mestre.py` nunca modifica a seção `marcas`; falha explicitamente se ela
  não existir no YAML de destino, em vez de inferir marcas da coluna `marca` da planilha.

## Desvios e decisões

| Pedido (task/arquitetura) | Feito | Motivo |
|---|---|---|
| Seção `padroes_fisicos` no YAML + campo/método em `DadosMestre` | Removido do escopo | `Configuracao` (task 01) já expõe os mesmos defaults via `.env`; `MontadorPlanilha` (task 14) consome `Configuracao`, não `DadosMestre` — manter os dois seria duas fontes de verdade sem religação. Decisão tomada com o usuário nesta sessão. Ver ADR-004 em `ARQUITETURA.md` §16. |
| "46 caminhos observados" (nota informal em `dados_mestre.md` §3) | Extração real produz 45 caminhos | A contagem informal do doc bruto parece ter sido feita à mão; a extração automatizada (determinística, a partir do `.xlsx` real) é a fonte de verdade a partir de agora — a diferença não afeta nada, pois a lista é só referência/aviso, não validação. |
| Esquema do YAML não especificado em detalhe pela task | `marcas.canonicas`/`marcas.proibidas` aninhados; `cores` como lista de `{nome, uso}`; `tamanhos`/`categorias_referencia` como listas de strings | Estrutura mais simples de validar e testar; seguida a decisão registrada em `docs/specs/README.md` de descrever o que existe. |
| `DadosMestre` (campos internos) | Campos públicos que espelham as seções do YAML (`marcas_canonicas`, `marcas_proibidas`, ...), sem índice pré-computado | ~9 marcas no catálogo: iterar a cada chamada é trivial e mantém a classe fácil de construir com dados fake nos testes, sem precisar de "alias de si mesma" hardcoded. |
| Erro de YAML malformado | `yaml.YAMLError` traduzido para `ErroRecursos` em `CarregadorRecursos.dados_mestre()` | Regra da arquitetura: infra traduz erros de biblioteca externa para exceção de domínio; nunca deixa `yaml.YAMLError` vazar para quem chama. |

Mudança de decisão de arquitetura → ADR-004 em `ARQUITETURA.md` §16 (ver acima).

## Verificação executada

- `ruff check . && ruff format --check . && mypy src && pytest` → tudo passando (52 testes).
- `/python-clean-architecture:check-quality` → 6 ajustes aplicados: fechamento explícito do
  workbook `openpyxl` (context/`finally`), `TipoLinha(StrEnum)` no lugar de strings soltas,
  extração de `_registrar_linha_filha`/`_registrar_linha_pai` para reduzir aninhamento,
  `ExtracaoPlanilha` (dataclass com `.mesclar()`) no lugar de tupla de 3 coleções paralelas,
  tradução de `yaml.YAMLError` para `ErroRecursos`, renomeação de parâmetros/variáveis vagas
  (`dados` → `entrada_marca`/`entrada`/`documento`).
- Manual: `python scripts/extrair_dados_mestre.py docs/brutos/produtos-2026-09-10-03-25-78670adce0a94f6.xlsx`
  rodado duas vezes → mesmo hash SHA-256 do YAML gerado; saída reporta 413 cores, 17 tamanhos,
  45 categorias.
- Critério de aceite da task: `CarregadorRecursos().dados_mestre().cor_valida("Cinza Claro")` →
  `True`; `.cor_valida("cinza claro")` → `False`; `.marca_canonica("Kiki Xodó") == "kiki"`;
  `.motivo_marca_proibida("Açucena")` retorna texto — todos cobertos por
  `tests/unit/infra/test_carregador_recursos.py::test_dados_mestre_carrega_do_pacote_real`.

## Pendências para tasks futuras

- Perfis de marca em Markdown (`recursos/marcas/*.md`) e prompts Jinja2 — task 10.
- Uso de `categoria_conhecida()` pelo validador para emitir aviso (não bloqueio) — task 05.
- Se algum caso de uso real precisar ler `padroes_fisicos` de um recurso versionado (hoje não
  há), reavaliar a decisão do ADR-004 nessa task.
