# Módulo: validacao

**Responsabilidade:** reprovar cedo (antes de gastar LLM/upload) tudo que faria a importação
real da Loja Integrada falhar, e avisar sobre o que merece atenção sem bloquear.
**Estado:** implementado pela task 05 · última atualização 2026-09-17 (fix ad-hoc, ADR-009)

## Arquivos

- `models/resultado_validacao.py` — `ProblemaValidacao`, `ResultadoValidacao`
- `services/ports/catalogo_fotos.py` — `CatalogoFotos` (Protocol)
- `infra/catalogo_fotos_diretorio.py` — `CatalogoFotosDiretorio`
- `services/validador_entrada.py` — `ValidadorEntrada`
- `config/composicao.py` — `montar_leitor_planilha_entrada()`, `montar_validador_entrada(fotos)`
- `cli.py` — subcomando `validar --planilha --fotos`
- `scripts/gerar_fixture_lote_piloto.py` — gera `tests/fixtures/lote-piloto/`

## Contratos

```python
# models/resultado_validacao.py
@dataclass(frozen=True)
class ProblemaValidacao:
    sku_pai: str
    campo: str
    mensagem: str

@dataclass(frozen=True)
class ResultadoValidacao:
    problemas: tuple[ProblemaValidacao, ...]
    avisos: tuple[ProblemaValidacao, ...]

    @property
    def aprovado(self) -> bool          # True quando não há nenhum problema (avisos não contam)

# services/ports/catalogo_fotos.py
class CatalogoFotos(Protocol):
    def listar(self, sku_pai: str) -> list[Path]: ...

# infra/catalogo_fotos_diretorio.py
class CatalogoFotosDiretorio:
    def __init__(self, raiz: Path) -> None: ...
    def listar(self, sku_pai: str) -> list[Path]: ...

EXTENSOES_ACEITAS: frozenset[str]   # {".jpg", ".jpeg", ".png", ".webp", ".heic"}

# services/validador_entrada.py
class ValidadorEntrada:
    def __init__(
        self,
        dados_mestre: DadosMestre,
        catalogo_fotos: CatalogoFotos,
        marcas_com_perfil: frozenset[str] = frozenset(),
    ) -> None: ...

    def validar(
        self, produtos: Sequence[ProdutoEntrada]
    ) -> tuple[list[ProdutoEntrada], ResultadoValidacao]: ...

MAX_VARIACOES_POR_PRODUTO = 50
MAX_NIVEIS_CATEGORIA = 5
MAX_FOTOS_POR_PRODUTO = 5
TAMANHOS_GTIN_VALIDOS = frozenset({8, 12, 13, 14})

# config/composicao.py
def montar_leitor_planilha_entrada() -> LeitorPlanilhaEntrada: ...
def montar_validador_entrada(fotos: Path) -> ValidadorEntrada: ...
```

Subcomando: `validar --planilha <arquivo.xlsx> --fotos <pasta>` — imprime problemas e avisos
agrupados por `sku_pai`, depois um resumo (`validar: aprovado (N aviso(s))` ou `validar:
reprovado (N problema(s), M aviso(s))`); código de saída `0` se aprovado, `1`
(`CODIGO_ERRO_NEGOCIO`) se houver problema, ou se a planilha/os recursos forem inválidos
(`ErroPlanilhaEntrada`/`ErroRecursos`).

## Comportamento

`ValidadorEntrada.validar(produtos)` roda, para cada `ProdutoEntrada` do lote:

1. **Marca**: `DadosMestre.marca_canonica` resolve canônica ou alias e o produto devolvido já
   vem com `marca` normalizada para a grafia canônica; marca proibida (`motivo_marca_proibida`)
   ou desconhecida vira problema. Marca canônica fora do parâmetro `marcas_com_perfil` vira
   aviso (lista vazia por padrão em `montar_validador_entrada` — a task 13 liga ao carregador de
   recursos).
2. **Campos obrigatórios**: `nome_fornecedor`, `tipo_peca`, `composicao`, `detalhes`,
   `faixa_tamanho` e `categoria` vazios viram problema (defesa extra; o leitor de planilha já
   garante isso hoje).
3. **Categoria**: 0 ou mais de 5 níveis vira problema; nível com espaço nas pontas, espaço
   duplo ou caractere de controle (`unicodedata.category == "Cc"`) vira problema; caminho
   (`" > ".join(niveis)`) fora de `DadosMestre.categorias_referencia` vira aviso.
4. **`sku_pai` único no lote**: contagem sobre a lista recebida; duplicado vira problema em cada
   produto com aquele `sku_pai`.
5. **Cor/tamanho**: cada cor/tamanho distinto do produto (`ProdutoEntrada.cores`/`.tamanhos`)
   fora da lista mestre vira problema — comparação exata, sem normalizar caixa/acento (decisão
   da task 03).
6. **Combinação cor × tamanho** repetida dentro do mesmo produto vira problema.
7. **GTIN**: não numérico ou tamanho fora de `{8, 12, 13, 14}` vira problema; dígito verificador
   inválido (algoritmo GS1 padrão, `_digito_verificador_valido`) vira problema; duplicado entre
   variações do lote inteiro (contagem sobre todas as variações de todos os produtos) vira
   problema em cada ocorrência.
8. **Preço/estoque**: preço ≤ 0 ou estoque < 0 vira problema.
9. **Mais de 50 variações** no produto vira problema.
10. **Fotos** (sem cor desde o ADR-009 — foto vale para o produto inteiro):
    `CatalogoFotos.listar(sku_pai)` vazio vira problema ("nenhuma foto encontrada para o
    produto"); mais de 5 fotos no total (`MAX_FOTOS_POR_PRODUTO`) vira aviso.

`CatalogoFotosDiretorio` só lê o disco (`raiz/<sku_pai>/*`, sem subpasta), filtrando por
`EXTENSOES_ACEITAS` (case-insensitive) e ordenando por nome (case-insensitive). `sku_pai` sem
pasta, ou pasta sem nenhum arquivo aceito, devolve `[]`, sem lançar exceção.

## Limites

- Não decodifica imagem nenhuma (HEIC incluído) — só extensão e existência de arquivo; abrir e
  processar a imagem é escopo da task 07 (Pillow/`pillow-heif`).
- `marcas_com_perfil` é um parâmetro simples (`frozenset[str]`); `montar_validador_entrada`
  passa vazio — toda marca aparece com aviso "sem perfil" até a task 13 ligar ao carregador de
  recursos.
- Não persiste nada (workspace/estado é a task 06); cada chamada a `validar` é sem estado.
- Cabeçalho duplicado ou planilha malformada continuam sendo erro do leitor
  (`ErroPlanilhaEntrada`, task 04), não deste módulo.

## Testes

- `tests/unit/models/test_resultado_validacao.py` — `aprovado` com/sem problema.
- `tests/unit/infra/test_catalogo_fotos_diretorio.py` — extensões variadas/case, ordenação,
  `sku_pai` sem pasta, pasta sem arquivo aceito, subpastas antigas ignoradas.
- `tests/unit/services/test_validador_entrada.py` — `CatalogoFotosFake` (dict `sku_pai` →
  lista de arquivos) + `DadosMestre` de teste; um teste por regra (marca alias/proibida/
  desconhecida/sem perfil, cor, tamanho, GTIN formato/dígito/duplicado, preço, estoque,
  combinação repetida, > 50 variações, `sku_pai` duplicado, categoria níveis/formatação/
  referência, campo obrigatório vazio, fotos faltando/vazias/sobrando) e um lote feliz.
- `tests/unit/test_fixture_lote_piloto.py` — roda o pipeline real (leitor openpyxl + catálogo de
  diretório + `CarregadorRecursos().dados_mestre()` do pacote) sobre
  `tests/fixtures/lote-piloto/` e confere que só os dois defeitos propositais (cor inválida do
  `3254030`, GTIN inválido do `3254040`) reprovam.
- `tests/unit/test_cli.py` — `validar` aprovando, reprovando (imprime `SKU <sku>:` e a linha de
  problema) e propagando `ErroPlanilhaEntrada` como código de erro de negócio.
- `tests/unit/config/test_composicao.py` — as duas fábricas novas funcionais.
- Fake disponível para outros módulos: `CatalogoFotosFake` (definido em
  `tests/unit/services/test_validador_entrada.py`, não extraído para um módulo compartilhado
  ainda — sem um segundo consumidor até aqui).

## Histórico

- Task 05 (2026-09-14): criação do módulo — `ResultadoValidacao`/`ProblemaValidacao`,
  `CatalogoFotos`/`CatalogoFotosDiretorio`, `ValidadorEntrada`, subcomando `validar`, fixture
  `tests/fixtures/lote-piloto/`.
- 2026-09-17 (fix ad-hoc, branch `fix/fix-validation`, sem task numerada — ADR-009 em
  `ARQUITETURA.md`): foto deixa de ter cor. `CatalogoFotos.listar` devolve `list[Path]` (era
  `dict[cor, list[Path]]`); `cores_disponiveis` removido; `_validar_fotos` simplificado para só
  "o SKU tem alguma foto" — perde a checagem por cor e o aviso de subpasta sem cor
  correspondente.
