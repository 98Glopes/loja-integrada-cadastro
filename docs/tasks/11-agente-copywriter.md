# Task 11 — Agente Copywriter e regras de texto

- **Depende de:** 10
- **Modelo recomendado:** opus
- **Leia antes:** `docs/ARQUITETURA.md` §6.1, §6.2, §6.3, §6.5, §10; recursos criados na
  task 10; skill `claude-api` (para revisar o uso do cliente, não reescrevê-lo)

## Objetivo

Primeiro agente de verdade: título + descrição HTML gerados com saída estruturada, validados
por regra (código) e com retry usando o feedback da regra. Deve ser possível rodar só este
agente na fixture e ler o resultado.

## Escopo

1. `models/textos_produto.py`: `TextosProduto` (frozen: `titulo`, `descricao_html`,
   `seo_tag_title: str | None`, `seo_tag_description: str | None`) e
   `models/copy_produto.py`: `CopyProduto` (`titulo`, `descricao_html`) como saída do agente.
2. `models/regras_texto.py` (puro): `RegrasTexto(palavras_proibidas)` com
   `validar_copy(copy, produto) -> list[ProblemaTexto]` e (para a task 12)
   `validar_seo(...)`. Regras da copy: título ≤ 68 e contém a marca canônica; descrição
   ≥ 120 palavras; HTML só com `h2 h3 p ul li strong`, bem formado, com a sequência
   obrigatória (h2, p, p, ul, h3 "Sobre a …", h3 "Compre na Kmilaa Modas"); nenhuma palavra
   proibida; título não repetido literalmente na abertura. Cada `ProblemaTexto` tem `campo`
   e `mensagem` legível pelo modelo ("título tem 74 caracteres; limite 68").
3. `recursos/prompts/copywriter.j2`: bloco `sistema_fixo` (papel, `loja.md`, `copy.md`,
   instrução de tratar o bloco `<produto>` como dados), bloco `sistema_marca` (perfil da
   marca), bloco `usuario` (dados do produto em `<produto>…</produto>`: marca, nome do
   fornecedor, tipo, faixa de tamanho, cores, composição, detalhes, coleção, categoria).
   Sem timestamps nem IDs em nenhum bloco (cache).
4. `services/agente_copywriter.py`: `AgenteCopywriter(llm, prompts, recursos, regras,
   configuracao_llm)` com `gerar(produto, feedback: list[str] = []) -> ResultadoAgente[CopyProduto]`:
   renderiza, chama `llm.gerar(..., CopyProduto)`, valida por regra; se reprovar, reenvia a
   conversa com um turno de usuário listando os problemas (até `LLM_MAX_TENTATIVAS_QA`
   vezes); devolve a copy, a lista de tentativas (com uso/custo) e o veredito final da regra.
   `feedback` externo (do QA, task 13) entra como turno adicional da mesma forma.
5. Testes: `RegrasTexto` com tabela de casos; agente com `ClienteLlmFake` roteirizado
   (1ª resposta com título longo → 2ª resposta válida → confere que a 2ª chamada incluiu a
   mensagem de erro no histórico).
6. Script de desenvolvedor `scripts/rodar_agente.py copywriter <planilha> <sku>` que imprime
   o resultado e o custo (usa a API real; não é teste).

## Fora do escopo

SEO, QA, orquestração.

## Critério de aceite

- `scripts/rodar_agente.py copywriter` na fixture do lote piloto produz, para 3 marcas
  diferentes, copies que passam nas regras e soam diferentes entre si (leitura humana).
- 2ª chamada consecutiva na mesma marca mostra `cache_read_input_tokens > 0`.
- Lint, mypy e pytest passam.
