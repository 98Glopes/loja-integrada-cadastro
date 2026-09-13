# Task 03 — Spike: a importação cria valor novo de grade (cor)?

- **Depende de:** nenhuma (usa `poc/gerar_planilha_poc.py`)
- **Modelo recomendado:** sonnet
- **Leia antes:** `docs/ARQUITETURA.md` §14 risco 1; `docs/regras-planilha-loja-integrada.md`
  §2 (col. 41) e §4; `poc/REGISTRO_ITERACOES.md`

## Objetivo

Descobrir experimentalmente se a importação massiva **cria** um valor inexistente em
`grade-produto-com-uma-cor` (a exportação tem 413 cores, sugerindo que sim) ou se a linha
falha. A resposta define se a validação de cor permanece estrita (reprova) ou vira
"normaliza e avisa".

## Escopo

1. Adicionar ao `poc/gerar_planilha_poc.py` um produto `POC-COR-006` com uma cor que
   certamente não existe (ex.: `Teste Cor Inexistente Kmilaa`) e outro `POC-COR-007` com
   uma cor existente em caixa diferente (`beige`).
2. Gerar a planilha (`--skus POC-COR-006 POC-COR-007 --sufixo spike-grade`) e **parar**: a
   importação no painel é feita manualmente pelo desenvolvedor.
3. Após a importação, registrar em `poc/REGISTRO_ITERACOES.md` (nova rodada) o resultado
   linha a linha: criou o valor? ligou `beige` a `Beige` ou criou duplicado? mensagem de erro?
4. Atualizar `docs/regras-planilha-loja-integrada.md` §2/§4 com o fato observado (marcar ✅)
   e `docs/ARQUITETURA.md` §14 risco 1 com a decisão resultante:
   - cria valor → validação de cor fica **estrita mesmo assim** (evitar poluir a grade), e a
     mensagem de erro passa a orientar: "cor não cadastrada — cadastre a grade no painel e
     rode `scripts/extrair_dados_mestre.py` com uma exportação nova, ou corrija a grafia".
   - não cria → validação estrita confirmada, sem mudança.
   - liga ignorando caixa → o validador pode normalizar caixa/acento com aviso (ajustar a
     task 05 antes de executá-la).

## Critério de aceite

- Registro da rodada em `poc/REGISTRO_ITERACOES.md` com evidência (mensagem do painel, página
  do produto ou exportação nova).
- Regras e arquitetura atualizadas com a decisão; produtos `POC-COR-*` apagados da loja ou
  listados para exclusão manual.
