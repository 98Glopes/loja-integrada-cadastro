# Spec as-built — Task 03: spike de grade na importação

- **Data:** 2026-09-13 · **Task:** `docs/tasks/03-spike-grade-importacao.md` · **Módulos:** nenhum
  em `src/` (spike experimental sobre `poc/`).

## Entregue

Confirmação experimental de que a importação em massa da Loja Integrada **não cria** valor
novo em `grade-produto-com-uma-cor`: uma cor fora da lista cadastrada na loja é rejeitada
linha a linha, com o erro "Cor não permitida em 'grade-produto-com-uma-cor'. Verifique as
cores permitidas em: http://cdn.awsli.com.br/download/cores.html". A importação também
**não normaliza caixa** — `beige` (minúsculo) não foi ligado ao valor `Beige` já cadastrado;
foi tratado como cor inexistente e rejeitado com o mesmo erro. Os produtos pai (`POC-COR-006`,
`POC-COR-007`) foram criados normalmente; ficam sem nenhuma variação, pois a única filha de
cada um falhou.

Comando usado para gerar a evidência:
```bash
.venv/Scripts/python poc/gerar_planilha_poc.py --skus POC-COR-006 POC-COR-007 --sufixo spike-grade
```

## Arquivos

| Camada | Criados | Alterados |
|---|---|---|
| poc | `poc/saida/poc-loja-integrada-2026-09-13-spike-grade.xlsx` | `poc/gerar_planilha_poc.py` (2 `ProdutoDummy` novos: `POC-COR-006`, `POC-COR-007`), `poc/REGISTRO_ITERACOES.md` (rodada 3) |
| docs | `docs/specs/tasks/03-spike-grade-importacao.md` | `docs/regras-planilha-loja-integrada.md` (§2, §4), `docs/ARQUITETURA.md` (§13, §14), `docs/tasks/README.md` |

Nenhum arquivo de `src/` foi criado ou alterado — a task não implementa código, apenas
confirma um fato experimental que orienta a task 05.

## Contratos

Não aplicável — spike não introduz ports, classes ou subcomandos. O contrato relevante já
existente e agora confirmado como correto é `DadosMestre.cor_valida(texto: str) -> bool`
(`src/loja_integrada_cadastro/models/dados_mestre.py`, task 02): comparação exata,
case-sensitive, sem normalização.

## Regras de negócio implementadas

- A importação da Loja Integrada nunca cria valor novo em `grade-produto-com-uma-cor`; rejeita
  a linha com erro explícito.
- A importação não ignora diferença de caixa na cor (`beige` ≠ `Beige`).
- Consequência para o pipeline: a validação estrita e sem normalização de `cor_valida`
  (decidida na task 02) é a correta e não precisa mudar — reprovar localmente evita gastar uma
  tentativa de importação que a loja rejeitaria de qualquer forma. Task 05 não precisa prever
  "normaliza e avisa" para cor.

## Desvios e decisões

| Pedido (task/arquitetura) | Feito | Motivo |
|---|---|---|
| Task pedia um produto com cor "certamente inexistente" e outro com cor existente em caixa diferente (`beige`), sem especificar marca/tamanho/preço dos dummies. | Reaproveitada a marca `somnii` (já validada nas rodadas 1/2) e tamanho único `"1"`, para isolar a variável "cor" sem introduzir ruído de marca/tamanho novos. | Reduzir variáveis do experimento; marca e tamanho não são o que o spike testa. |
| Task previa 3 desfechos possíveis (cria valor / não cria / liga ignorando caixa). | Resultado real cobriu dois desfechos ao mesmo tempo: "não cria" **e** "não ignora caixa" — ambos confirmados na mesma rodada, sem ambiguidade. | A plataforma respondeu com o mesmo erro para as duas cores testadas, tornando o resultado conclusivo sem precisar de rodada extra. |

## Verificação executada

- `ruff check . && ruff format --check . && mypy src && pytest` → todos passaram (58 arquivos
  formatados, `mypy`: sem problemas em 16 arquivos, `pytest`: 52 passed) — nenhuma mudança em
  `src/`, então nenhum teste novo era esperado.
- `/python-clean-architecture:check-quality` não foi executado: a mudança é documentação e
  script de POC (fora de `src/`), sem código de arquitetura em camadas para revisar.
- Evidência da importação real: mensagem da plataforma e coluna `Erro` da planilha retornada,
  registradas literalmente em `poc/REGISTRO_ITERACOES.md` (rodada 3), reportadas pelo
  desenvolvedor após importação manual em `Produtos > Importar`.

## Pendências para tasks futuras

- Apagar manualmente `POC-COR-006` e `POC-COR-007` da loja (produtos pai sem variação) — ação
  do desenvolvedor no painel, fora do escopo automatizável.
- Risco 2 de `ARQUITETURA.md` §14 (criação de categoria) segue não testado — fora do escopo
  desta task.
- `http://cdn.awsli.com.br/download/cores.html` é uma lista pública de cores permitidas pela
  loja; pode ser uma fonte alternativa/complementar a `scripts/extrair_dados_mestre.py` para
  detectar cores novas cadastradas no painel sem precisar de uma exportação completa — avaliar
  se vale a pena numa task futura de manutenção de `dados_mestre.yaml`.
