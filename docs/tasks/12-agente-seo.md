# Task 12 — Agente SEO

- **Depende de:** 11
- **Modelo recomendado:** opus
- **Leia antes:** `docs/ARQUITETURA.md` §6.1, §6.2; `recursos/seo.md`;
  `docs/regras-planilha-loja-integrada.md` §4 (sufixo do `<title>`)

## Objetivo

Segundo agente: tag title e meta description coerentes com a copy aprovada, dentro dos
limites da loja, com validação de regra e retry — mesmo desenho da task 11.

## Escopo

1. `models/seo_produto.py`: `SeoProduto` (frozen: `seo_tag_title`, `seo_tag_description`).
2. `RegrasTexto.validar_seo(seo, produto, copy)`: tag title ≤ 60, contém marca e tipo, não
   termina com `| Kmilaa Modas` nem contém `Kmilaa`; meta 140–155 caracteres, contém marca,
   contém um CTA/diferencial da loja (lista curta em `seo.md`); nenhuma palavra proibida;
   tag title diferente do título do produto (não copiar literalmente).
3. `recursos/prompts/seo.j2`: `sistema_fixo` (papel, `seo.md`, regra do sufixo automático),
   `sistema_marca`, `usuario` (`<produto>` + `<copy>` com título e descrição aprovados, com
   instrução de manter as palavras-chave da copy).
4. `services/agente_seo.py`: `AgenteSeo` com `gerar(produto, copy, feedback=[]) ->
   ResultadoAgente[SeoProduto]`, mesmo contrato de retry do Copywriter (extrair o loop de
   "chamar → validar por regra → reenviar com problemas" para uma classe reutilizável em
   `services/`, ex.: `ExecutorAgenteComRegras`, em vez de duplicar).
5. Testes: regras de SEO (tabela); agente com fake; `scripts/rodar_agente.py seo` reutilizando
   a copy gerada (aceita `--copy caminho.json` ou roda o copywriter antes).

## Critério de aceite

- Na fixture, os 4 campos de 3 produtos passam por todas as regras; `<title>` final previsto
  (`seo_tag_title + " - Roupas para Bebê, Infantil e Juvenil | Kmilaa Modas"`) fica ≤ ~110
  caracteres e legível.
- Lint, mypy e pytest passam.
