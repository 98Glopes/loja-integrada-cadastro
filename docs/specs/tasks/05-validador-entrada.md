# Spec as-built — Task 05: Validador de entrada, catálogo de fotos e comando `validar`

- **Data:** 2026-09-14 · **Task:** `docs/tasks/05-validador-entrada.md` · **Módulos:** `validacao`

## Entregue

- `ResultadoValidacao`/`ProblemaValidacao` (`models/resultado_validacao.py`): resultado de uma
  validação de lote, com `problemas` (bloqueiam) e `avisos` (não bloqueiam) e a propriedade
  `aprovado`.
- `CatalogoFotos` (port) e `CatalogoFotosDiretorio` (infra): leem `fotos/<sku-pai>/<cor>/*` do
  disco, aceitando `.jpg .jpeg .png .webp .heic` em qualquer caixa, ordenados alfabeticamente
  (case-insensitive).
- `ValidadorEntrada` (`services/validador_entrada.py`): normaliza marca (canônica/alias) e
  aplica todas as regras bloqueantes e de aviso do escopo da task (ver
  `docs/specs/validacao.md` §Comportamento) sobre uma lista de `ProdutoEntrada`.
- Subcomando `loja-integrada-cadastro validar --planilha --fotos`: lê a planilha, valida,
  imprime problemas/avisos agrupados por `sku_pai` e retorna `0` (aprovado) ou `1` (reprovado ou
  erro de planilha/recursos). Wiring em `config/composicao.py`
  (`montar_leitor_planilha_entrada`, `montar_validador_entrada`).
- Fixture `tests/fixtures/lote-piloto/` (planilha + fotos), gerada por
  `scripts/gerar_fixture_lote_piloto.py`: 6 produtos, 2 com defeito proposital (cor inválida,
  GTIN inválido); `validar` sobre ela reprova exatamente esses dois e aprova o resto (com
  avisos esperados de marca sem perfil e de categoria fora de referência).

## Arquivos

| Camada | Criados | Alterados |
|---|---|---|
| models | `models/resultado_validacao.py` | — |
| services/ports | `services/ports/catalogo_fotos.py` | — |
| services | `services/validador_entrada.py` | — |
| infra | `infra/catalogo_fotos_diretorio.py` | — |
| config | — | `config/composicao.py` (`montar_leitor_planilha_entrada`, `montar_validador_entrada`) |
| cli | — | `cli.py` (`_validar`, `_imprimir_resultado_validacao`) |
| scripts | `scripts/gerar_fixture_lote_piloto.py` | — |
| fixtures | `tests/fixtures/lote-piloto/planilha.xlsx`, `tests/fixtures/lote-piloto/fotos/**` | — |
| tests | `tests/unit/models/test_resultado_validacao.py`, `tests/unit/infra/test_catalogo_fotos_diretorio.py`, `tests/unit/services/test_validador_entrada.py`, `tests/unit/test_fixture_lote_piloto.py` | `tests/unit/config/test_composicao.py`, `tests/unit/test_cli.py` |

## Contratos

Ver `docs/specs/validacao.md` §Contratos (assinaturas completas de `ProblemaValidacao`,
`ResultadoValidacao`, `CatalogoFotos`, `CatalogoFotosDiretorio`, `ValidadorEntrada` e das duas
novas fábricas de `config/composicao.py`).

## Regras de negócio implementadas

Lista completa em `docs/specs/validacao.md` §Comportamento. Resumo: marca (normaliza
canônica/alias; problema se proibida/desconhecida; aviso se sem perfil), campos obrigatórios,
categoria (1–5 níveis, formatação, referência como aviso), `sku-pai` único no lote, cor/tamanho
na lista mestre (comparação exata), combinação cor×tamanho única por produto, GTIN (formato,
dígito verificador GS1, único no lote), preço > 0, estoque ≥ 0, ≤ 50 variações por produto,
fotos (cor sem pasta ou pasta vazia = problema; subpasta sem cor correspondente ou mais de 5
fotos = aviso, casamento ignorando caixa/acento).

## Desvios e decisões

| Pedido (task/arquitetura) | Feito | Motivo |
|---|---|---|
| Task: "infra/catalogo_fotos_diretorio.py: ... casando o nome da subpasta com a cor da planilha ignorando caixa e acento" | O casamento ignorando caixa/acento foi implementado em `ValidadorEntrada` (função privada `_normalizar`), não em `CatalogoFotosDiretorio`, que só devolve os nomes de pasta como estão no disco | `CatalogoFotos.listar(sku_pai)` só recebe o `sku_pai`, não a lista de cores esperadas da planilha — só o validador tem os dois lados da comparação (cor do produto e nome da subpasta) para normalizar e casar. Decisão de implementação, não muda nenhum comportamento observável descrito em `ARQUITETURA.md` §5.1, por isso não virou ADR. |
| Task: "validar(produtos) -> ResultadoValidacao" (com nota de que o retorno real pode ser `(produtos_normalizados, resultado)` ou um objeto que carrega ambos) | Escolhido `tuple[list[ProdutoEntrada], ResultadoValidacao]` | Opção mais simples oferecida pela própria task; evita criar uma classe wrapper sem um segundo motivo de existir (arquitetura evolutiva). |
| Task: "marca ... marca proibida ou desconhecida → problema" sem especificar onde vive o dígito verificador de GTIN | `_digito_verificador_valido` (algoritmo GS1 padrão) ficou como função privada em `services/validador_entrada.py`, não em `models/` | Não está no escopo explícito da task como um novo arquivo `models/`; é usada só ali. Se um segundo consumidor aparecer (ex.: geração/validação de GTIN em outro lugar), promover para `models/`. |
| Task: "campos obrigatórios não vazios" já garantidos pelo leitor de planilha (task 04) | Implementado mesmo assim, como checagem defensiva no validador | Protege contra `ProdutoEntrada` construído fora do `LeitorPlanilhaEntradaOpenpyxl` (testes, futura entrada web) — consistente com a evolução para serviço web prevista em `ARQUITETURA.md` §15. |
| Critério de aceite: fixture com "6–8 produtos" | 6 produtos | Cobre todas as combinações pedidas (cor única, várias cores × tamanhos, tamanho único, cor inválida, GTIN inválido, categoria fora de referência) sem repetição redundante. |

Nenhuma decisão de negócio nova foi tomada sem confirmação — todas as regras vieram
diretamente do escopo da task, de `ARQUITETURA.md` ou de `docs/regras-planilha-loja-integrada.md`.

## Verificação executada

- `ruff check . && ruff format --check . && mypy src && pytest` → tudo passando (120 testes, 38
  novos desta task; `mypy`: sem problemas em 29 arquivos fonte).
- `/python-clean-architecture:check-quality` sobre os arquivos novos/alterados: 1 ajuste
  aplicado (`_validar_marca` renomeado para `_validar_e_normalizar_marca` — regra 21, nome de
  método enganoso, já que o método também normaliza e devolve o produto, não só valida). Demais
  regras (nesting, nomes, flag parameters, exceção ampla, mutável como default) sem violação.
- Manual (critério de aceite): `python -m loja_integrada_cadastro validar --planilha
  tests/fixtures/lote-piloto/planilha.xlsx --fotos tests/fixtures/lote-piloto/fotos` reprova
  exatamente `3254030` (cor) e `3254040` (gtin), aprova os outros 4 com avisos esperados, código
  de saída 1 — confirmado tanto na execução manual quanto em
  `tests/unit/test_fixture_lote_piloto.py`.

## Pendências para tasks futuras

- `marcas_com_perfil` ligado ao carregador de recursos (hoje é `frozenset()` fixo em
  `montar_validador_entrada`) — task 10.
- Decodificação real de imagem (HEIC incluído) — task 07, com Pillow/`pillow-heif`.
- `CatalogoFotosFake` só existe local a `tests/unit/services/test_validador_entrada.py`; extrair
  para um módulo de teste compartilhado se um segundo consumidor precisar dele.
- Estado/workspace do lote (persistir `ResultadoValidacao`, retomar reexecução) — task 06.
