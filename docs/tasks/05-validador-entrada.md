# Task 05 — Validador de entrada, catálogo de fotos e comando `validar`

- **Depende de:** 03 (decisão sobre cores), 04
- **Modelo recomendado:** sonnet
- **Leia antes:** `docs/ARQUITETURA.md` §3 etapa 1, §4, §5.1, §10; resultado da task 03 em
  `docs/regras-planilha-loja-integrada.md`

## Objetivo

Reprovar cedo — antes de gastar LLM e upload — tudo que faria a importação falhar ou poluir
o catálogo, e avisar sobre o que merece atenção sem bloquear.

## Escopo

1. `models/resultado_validacao.py`: `ResultadoValidacao` (frozen) com `problemas` e `avisos`
   (`tuple[ProblemaValidacao, ...]`, cada um com `sku_pai`, `campo`, `mensagem`) e propriedade
   `aprovado`.
2. `services/ports/catalogo_fotos.py`: `CatalogoFotos` (Protocol) com
   `listar(sku_pai) -> dict[str, list[Path]]` (cor → arquivos em ordem alfabética,
   case-insensitive) e `cores_disponiveis(sku_pai) -> list[str]`.
   `infra/catalogo_fotos_diretorio.py`: implementação sobre `fotos/<sku-pai>/<cor>/`,
   aceitando `.jpg .jpeg .png .webp .heic` (qualquer caixa) e casando o nome da subpasta com
   a cor da planilha ignorando caixa e acento.
3. `services/validador_entrada.py`: `ValidadorEntrada(dados_mestre, catalogo_fotos)` com
   `validar(produtos) -> ResultadoValidacao`. Regras (problema = bloqueia o produto):
   - marca: canônica ou alias → **normaliza** para canônica (o validador devolve os produtos
     normalizados, ex.: método `validar` retorna `(produtos_normalizados, resultado)` ou um
     objeto que carrega ambos); marca proibida ou desconhecida → problema.
   - cor: conforme decisão da task 03 (padrão estrito: exata na lista mestre).
   - tamanho: na lista mestre.
   - GTIN: obrigatório, 8/12/13/14 dígitos, dígito verificador válido, único no lote.
   - preço > 0; estoque ≥ 0; cor × tamanho única por SKU; ≤ 50 variações por produto;
     `sku-pai` único no lote; categoria com 1–5 níveis sem espaços extras/caracteres de
     controle; campos obrigatórios não vazios.
   - fotos: cada cor do produto precisa de subpasta com ≥ 1 arquivo.
   - Avisos (não bloqueiam): categoria fora da lista de referência; subpasta de cor sem linha
     na planilha; marca sem perfil próprio (lista de perfis vem de um parâmetro simples por
     enquanto — a task 10 conecta ao carregador de recursos); produto com mais de 5 fotos no
     total (só 5 serão usadas).
4. Subcomando `validar --planilha --fotos`: imprime problemas e avisos agrupados por SKU e
   retorna 1 se houver problema. Wiring em `config/composicao.py`.
5. Testes com `CatalogoFotosFake` (dict em memória) e `DadosMestre` construído no teste:
   um caso por regra, mais um lote "feliz".

## Fora do escopo

Estado, workspace, qualquer coisa de IA.

## Critério de aceite

- Fixture `tests/fixtures/lote-piloto/` criada (planilha com 6–8 produtos conforme
  `ARQUITETURA.md` §12 e pastas de fotos com JPEGs minúsculos gerados por script) e
  `validar` reporta exatamente os erros propositais (cor inválida, GTIN inválido) e aprova o
  resto.
- Lint, mypy e pytest passam.
