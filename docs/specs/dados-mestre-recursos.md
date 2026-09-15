# Módulo: dados-mestre-recursos

**Responsabilidade:** versionar e servir a lista mestre de marcas, cores, tamanhos e categorias
de referência do catálogo, extraída da exportação real da loja, para o validador e os prompts.
**Estado:** implementado pela task 02 · última atualização 2026-09-13 (task 02)

## Arquivos

| Camada | Arquivo |
|---|---|
| models | `models/dados_mestre.py` (`DadosMestre`), `models/exceptions/erro_recursos.py` (`ErroRecursos`) |
| infra | `infra/carregador_recursos.py` (`CarregadorRecursos`, `montar_dados_mestre`) |
| recursos | `recursos/__init__.py`, `recursos/dados_mestre.yaml` |
| scripts | `scripts/extrair_dados_mestre.py` (ferramenta de dev, fora do pacote) |

## Contratos

```python
class ErroRecursos(Exception):
    def __init__(self, recurso: str, motivo: str) -> None: ...


@dataclass(frozen=True)
class DadosMestre:
    marcas_canonicas: Mapping[str, tuple[str, ...]]
    marcas_proibidas: Mapping[str, str]
    cores: frozenset[str]
    tamanhos: frozenset[str]
    categorias_referencia: frozenset[str]

    def marca_canonica(self, texto: str) -> str | None: ...
    def motivo_marca_proibida(self, texto: str) -> str | None: ...
    def cor_valida(self, texto: str) -> bool: ...
    def tamanho_valido(self, texto: str) -> bool: ...
    def categoria_conhecida(self, caminho: str) -> bool: ...


class CarregadorRecursos:
    def texto(self, nome: str) -> str: ...
    def dados_mestre(self) -> DadosMestre: ...


def montar_dados_mestre(bruto: object) -> DadosMestre: ...
```

Variáveis de ambiente: nenhuma (recurso é lido do pacote instalado, não configurável).

## Comportamento

- `CarregadorRecursos.texto(nome)` lê qualquer arquivo de `recursos/` via `importlib.resources`
  (funciona a partir do repositório ou do pacote instalado); levanta `ErroRecursos` se o arquivo
  não existir.
- `CarregadorRecursos.dados_mestre()` lê `dados_mestre.yaml`, traduz `yaml.YAMLError` em
  `ErroRecursos` e delega a validação/montagem a `montar_dados_mestre` (função isolada de I/O,
  testável com um `dict` puro).
- `montar_dados_mestre` exige as seções `marcas.canonicas`, `marcas.proibidas`, `cores`,
  `tamanhos`, `categorias_referencia`; qualquer uma ausente ou com tipo errado (ex.: item de
  `tamanhos` que não é string) levanta `ErroRecursos` com mensagem citando a seção — nunca deixa
  `KeyError`/`TypeError` vazar.
- `DadosMestre.marca_canonica`/`motivo_marca_proibida` normalizam (`unicodedata.normalize`
  `"NFKD"` + `casefold()`) antes de comparar — aceitam a própria grafia canônica ou qualquer
  alias, ignorando caixa e acentuação.
- `cor_valida`, `tamanho_valido`, `categoria_conhecida` são comparação **exata** (decisão
  estrita); não normalizam nada.
- `scripts/extrair_dados_mestre.py` lê um ou mais `.xlsx` de exportação real, classifica linhas
  por `tipo` (`com-variacao` = pai, `variacao` = filha, `sem-variacao` = ignorada), acumula
  cores/tamanhos das linhas-filha e caminhos de categoria das linhas-pai, e regrava
  `cores`/`tamanhos`/`categorias_referencia` no YAML preservando `marcas` intacta. Determinístico
  (ordenação fixa) — rodar duas vezes sobre o mesmo arquivo produz saída idêntica.

## Limites

- Não valida categoria contra lista fechada — `categoria_conhecida` é só referência/aviso
  (decisão de negócio em `docs/brutos/dados_mestre.md` §3); quem decide usar isso para emitir
  aviso é o validador (task 05), ainda não implementado.
- Não cobre padrões físicos (peso/altura/largura/comprimento) — isso é `Configuracao` (módulo
  `configuracao-cli`, task 01); ver ADR-004 em `ARQUITETURA.md` §16.
- `scripts/extrair_dados_mestre.py` nunca cria ou edita a seção `marcas` — é decisão humana
  documentada em `docs/brutos/dados_mestre.md` §2; o script falha (`SystemExit`) se ela não
  existir no YAML de destino.
- Não versiona perfis de marca em Markdown nem prompts Jinja2 — isso é o módulo
  `agentes-textos` (task 13).

## Testes

- `tests/unit/models/test_dados_mestre.py` — `DadosMestre` construído com dados fake pequenos
  (sem tocar `CarregadorRecursos`): resolução de alias/canônica ignorando caixa/acento, marca
  proibida com motivo, cor/tamanho/categoria com comparação exata.
- `tests/unit/infra/test_carregador_recursos.py` — carregamento do YAML real do pacote
  (`CarregadorRecursos().dados_mestre()`, espelha o critério de aceite da task 02), `.texto()`
  para arquivo existente/inexistente, e `montar_dados_mestre()` chamado direto com dicts
  Python (completo, seção ausente, tipo inválido) sem precisar de arquivo real.
- Nenhum teste automatizado para `scripts/extrair_dados_mestre.py` (fora de `tests/`, que
  espelha só `src/`) — verificado manualmente rodando duas vezes e comparando hash do YAML.

## Histórico

- Task 02 (2026-09-13): criação do módulo — `DadosMestre`, `ErroRecursos`,
  `CarregadorRecursos`, `recursos/dados_mestre.yaml` e `scripts/extrair_dados_mestre.py`.
