# Task 18 — Lote piloto real, revisão de arquitetura e relatório final

- **Depende de:** 16, 17
- **Modelo recomendado:** opus
- **Leia antes:** `docs/ARQUITETURA.md` (inteiro), `docs/tasks/README.md` (status de tudo),
  `docs/regras-planilha-loja-integrada.md`

## Objetivo

Provar o critério de pronto do projeto com produtos reais e fechar a documentação: o que foi
construído, limitações conhecidas e o que depende de decisão da loja antes do uso rotineiro.

## Escopo

1. **Lote piloto real** (com a dona da loja): 5–10 produtos reais que ainda não estão no
   site, planilha preenchida por ela no `modelo-entrada.xlsx`, fotos na estrutura de pastas.
   Rodar `validar` → corrigir o que reprovar junto com ela (registrar as dúvidas que ela
   teve preenchendo: são melhorias do modelo/validador) → `processar` → importar no painel →
   `verificar`.
2. Registrar em `docs/PILOTO.md`: comandos usados, tempo, custo, problemas encontrados e
   como foram resolvidos, links das páginas publicadas, avaliação dos textos pela dona da
   loja (o que ela mudaria — vira caso de eval).
3. **Revisão de arquitetura**: rodar `/python-clean-architecture:review-architecture` e
   `/python-clean-architecture:check-quality` sobre `src/`; corrigir violações da regra de
   dependência, classes com mais de uma responsabilidade, ports não usados. Conferir que
   nenhum `services/` importa infra e que `mypy --strict` continua limpo.
4. **Sincronizar a documentação**: `docs/ARQUITETURA.md` passa a refletir o que existe
   (remover o que não foi construído, atualizar §10 com os arquivos reais, §14 com riscos
   resolvidos); `CLAUDE.md` atualizado (comandos reais, estado atual); `docs/tasks/README.md`
   com todos os status.
5. `docs/RELATORIO_FINAL.md`: o que foi construído, métricas do piloto (custo/produto,
   tempo/produto, taxa de aprovação de primeira), limitações conhecidas, decisões pendentes
   da loja (ex.: ativar `N` por padrão, modelo do QA, política de categorias) e próximos passos sugeridos (Batches, web, Langfuse).

## Critério de aceite

- Todos os produtos do piloto `pronto`, importados sem erro e confirmados pelo `verificar`
  (título, meta, imagens). Exceções documentadas com causa.
- Suíte completa verde: `ruff check . && ruff format --check . && mypy src && pytest`.
- `docs/RELATORIO_FINAL.md` e `docs/PILOTO.md` escritos; `docs/tasks/README.md` com 18 tasks
  `concluída`.
