# Task 06 — Workspace e estado do lote

- **Depende de:** 05
- **Modelo recomendado:** sonnet
- **Leia antes:** `docs/ARQUITETURA.md` §8 (workspace, estado, reexecução), §10

## Objetivo

Persistir o progresso de cada produto para que reexecuções pulem o que está pronto e
retomem do ponto de falha — é o que evita pagar LLM e upload duas vezes.

## Escopo

1. `models/status_produto.py`: `StatusProduto` (Enum): `validado`, `reprovado-validacao`,
   `erro-fotos`, `fotos-publicadas`, `textos-gerados`, `reprovado-qa`, `erro-llm`, `pronto`.
2. `models/estado_produto.py`: `EstadoProduto` (o único agregado mutável): `sku_pai`,
   `status`, `entrada` (ProdutoEntrada normalizado), `hash_entrada`, `validacao`,
   `fotos`, `imagens_pai`, `textos`, `tentativas`, `custo_usd_estimado`, `verificacao`,
   `atualizado_em`. Mutação só por métodos de intenção (`registrar_validacao`,
   `registrar_fotos`, `registrar_tentativa`, `registrar_textos`, `reprovar_qa`,
   `marcar_pronto`, `registrar_verificacao`) que também validam transições de status.
   Os campos ainda sem tipo definido (fotos, textos, tentativas) entram como
   `tuple`/`dict` tipados de forma mínima e são refinados pelas tasks 07/11/13 — não
   antecipar modelos que não existem ainda.
3. `services/ports/repositorio_estado_lote.py`: `RepositorioEstadoLote` (Protocol):
   `carregar(sku_pai) -> EstadoProduto | None`, `salvar(estado)`, `listar() -> list[EstadoProduto]`.
4. `infra/repositorio_estado_lote_json.py`: um JSON por SKU em `lotes/<lote>/estado/`,
   escrita atômica (arquivo temporário + `replace`), `Decimal` e `datetime` serializados
   explicitamente. Cria a árvore do workspace (`entrada/`, `estado/`, `fotos-processadas/`,
   `saida/`) e copia a planilha de entrada para `entrada/`.
5. Regra de reexecução (em `services/`, função ou classe pequena `PoliticaReexecucao`):
   dado o estado anterior e a entrada atual, decide `pular` / `retomar de <etapa>` /
   `recomeçar` (hash diferente) e aplica `--refazer-textos`/`--refazer-fotos`.
6. Testes: transições válidas e inválidas do `EstadoProduto`; repositório em `tmp_path`
   (round-trip, escrita atômica); política de reexecução com tabela de casos.

## Fora do escopo

Orquestração do lote (task 15).

## Critério de aceite

- Round-trip `salvar` → `carregar` preserva todos os campos, inclusive `Decimal`.
- Tabela de casos da política de reexecução coberta por teste parametrizado.
- Lint, mypy e pytest passam.
