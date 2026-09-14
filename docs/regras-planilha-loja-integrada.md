# Regras da planilha de importação — Loja Integrada (Kmilaa Modas)

Fonte de verdade do formato de saída do projeto. Consolidado a partir de:

- prova de conceito validada na loja real em 13/09/2026 (`poc/`, 2 rodadas, 23 linhas, 0 erros);
- exportação real do catálogo (`docs/brutos/produtos-2026-09-10-03-25-78670adce0a94f6.xlsx`, 9.183 linhas);
- artigos oficiais de cadastro massivo (links em `CLAUDE.md`) e respostas do suporte.

Onde um fato foi **observado na POC** ele está marcado com ✅; o resto vem da documentação
oficial ou da exportação.

---

## 1. Arquivo

| Regra | Detalhe |
|---|---|
| Formato | `.xlsx`, uma única aba, cabeçalho na linha 1. ✅ Gerado com `openpyxl`, aba `Sheet1`. |
| Layout de colunas | **54 colunas, na ordem exata da exportação real da loja** (seção 2). Não incluir, remover ou reordenar colunas. |
| Origem do layout | A exportação (`Visão de Negócios > Relatórios > Exportar produtos`), **não** o `planilha-modelo.xlsx` genérico da central de ajuda (49 colunas, sem as grades da loja). O modelo baixado no painel em `Produtos > Importar` também traz as grades da loja e serve igualmente. |
| Limites | ≤ 9.997 linhas por arquivo; ≤ 50 variações por produto; ≤ 32.767 caracteres por célula. |
| Produto novo | `id` em branco. ✅ |
| Resultado | Painel/e-mail informa `N linhas de N ... processadas com sucesso em X seg`. ✅ Páginas públicas podem responder 404 por alguns minutos após a importação. ✅ |

---

## 2. As 54 colunas

Legenda de "Pai/Filha": **P** preenchido só no pai, **F** só na filha, **PF** nos dois,
**—** nunca preenchido pela Kmilaa.

| # | Coluna | Pai/Filha | Obrigatória | Valores / observação |
|---|---|---|---|---|
| 1 | `id` | — | não | Em branco para criar. Preenchido só na exportação. |
| 2 | `tipo` | PF | sim | `com-variacao` (pai), `variacao` (filha), `sem-variacao` (produto sem grade — não usado pela Kmilaa). ✅ |
| 3 | `sku-pai` | F | sim na filha | SKU do pai, idêntico ao `sku` da linha pai. ✅ |
| 4 | `sku` | PF | sim | Único. Convenção Kmilaa: pai = código do fornecedor; filha = `<sku-pai>-<cor>-<tamanho>` em minúsculas (ex.: `3254002-beige-1`). ✅ |
| 5 | `ativo` | PF | sim | `S` / `N`. ✅ |
| 6 | `usado` | PF | — | `N` (100% do catálogo). ✅ |
| 7 | `destaque` | PF | — | `N` (ou `S` para destacar na home). ✅ |
| 8 | `ncm` | — | não | Em branco por decisão (`dados_mestre.md`). ✅ |
| 9 | `gtin` | F | sim na filha | Código de barras da variação, informado na planilha de entrada (decisão de 13/09/2026, `ARQUITETURA.md` §2). Na POC ficou em branco ✅; preenchido ainda não testado em importação real. |
| 10 | `mpn` | — | não | Em branco por decisão. ✅ |
| 11 | `nome` | P | sim no pai | Título do produto. **Gera a URL** (slug: minúsculas, sem acento, hífens). ✅ |
| 12 | `seo-tag-title` | P | não | Vai para o `<title>`; a loja **anexa** ` - Roupas para Bebê, Infantil e Juvenil \| Kmilaa Modas`. **Não** terminar com `\| Kmilaa Modas`. ✅ |
| 13 | `seo-tag-description` | P | não | Vai íntegra para `<meta name="description">`. ✅ |
| 14 | `descricao-completa` | P | não | HTML renderizado na página (`h2`, `p`, `ul`, `h3` funcionam). ✅ |
| 15 | `url-video-youtube` | P | não | Em branco. |
| 16 | `estoque-gerenciado` | F | sim na filha | `S` (filhas). Pai em branco. ✅ |
| 17 | `estoque-quantidade` | F | se gerenciado | Inteiro. ✅ |
| 18 | `estoque-situacao-em-estoque` | F | — | `imediata` (ou `1 dia` … `90 dias`). ✅ |
| 19 | `estoque-situacao-sem-estoque` | F | — | `indisponivel` (padrão Kmilaa) ou `manter disponibilidade`. ✅ |
| 20 | `preco-sob-consulta` | PF | — | `N`. ✅ |
| 21 | `preco-custo` | F | não | `0` quando não informado. ✅ |
| 22 | `preco-cheio` | F | sim na filha | Decimal com ponto (`119.9`), célula numérica. Pai em branco. ✅ |
| 23 | `preco-promocional` | F | não | `0` = sem promoção. Para remover promoção existente numa atualização, enviar `0`. ✅ |
| 24 | `marca` | P | não | Grafia canônica de `dados_mestre.md` (`somnii`, `kiki`, `Onda Marinha`…). Vincula à marca existente sem duplicar. ✅ |
| 25 | `peso-em-kg` | F | sim na filha | Decimal (`0.1`). ✅ |
| 26 | `altura-em-cm` | F | sim na filha | Inteiro (`4`). ✅ |
| 27 | `largura-em-cm` | F | sim na filha | Inteiro (`22`). ✅ |
| 28 | `comprimento-em-cm` | F | sim na filha | Inteiro (`22`). ✅ |
| 29–33 | `categoria-nome-nivel-1` … `-5` | P | não | Caminho da categoria, um nível por coluna. **A categoria precisa existir no painel com grafia idêntica** — a importação não cria. Não testado na POC (ficou em branco, como 85% do catálogo). |
| 34–38 | `imagem-1` … `-5` | P | não | URL pública `https://` de JPEG. A loja baixa e re-hospeda no CDN (`cdn.awsli.com.br`). Só no pai; não há imagem por variação. ✅ |
| 39 | `grade-genero` | — | | Nunca usada. |
| 40 | `grade-produto-com-duas-cores` | — | | Nunca usada. |
| 41 | `grade-produto-com-uma-cor` | F | ≥1 grade por filha | Nome da cor com a **grafia exata da grade da loja** (`Beige`, `Rosa`, `Preto`, `Branco`, `Vermelho`, `Buff`, `Cinza Claro`…). Cor fora da lista — inclusive com caixa diferente, ex. `beige` — é **rejeitada** pela importação (task 03: `Cor não permitida em 'grade-produto-com-uma-cor'`). ✅ |
| 42–46 | `grade-tamanho-de-anelalianca`, `-calca`, `-camisacamiseta`, `-capacete`, `-tenis` | — | | Grades padrão da plataforma, nunca usadas. |
| 47 | `grade-tamanho-juvenil-infantil` | — | | **Não usar** (3 linhas legadas). |
| 48 | `grade-voltagem` | — | | Nunca usada. |
| 49 | `grade-colecao` | — | | Grade da loja, nunca usada. |
| 50 | `grade-estampa-infanti` | — | | Grade da loja, nunca usada. |
| 51 | `grade-generos` | — | | Grade da loja, nunca usada. |
| 52 | `grade-gorro` | — | | 1 linha legada. |
| 53 | `grade-modelo-body-frases` | — | | Nunca usada. |
| 54 | `grade-tamanho-infantil` | F | ≥1 grade por filha | Tamanho: `P M G GG XG` ou `1 2 3 4 6 8 10 12 14 16 18 20`. ✅ |

---

## 3. Estrutura pai/filha

```
com-variacao  sku=3254002        nome, marca, seo, descrição, imagens      (1 linha)
variacao      sku-pai=3254002    sku=3254002-beige-1  Beige  1  preço/estoque/peso
variacao      sku-pai=3254002    sku=3254002-beige-2  Beige  2  ...
variacao      sku-pai=3254002    sku=3254002-rosa-1   Rosa   1  ...
```

- Uma linha filha por combinação **cor × tamanho**; cada filha com as duas grades
  preenchidas (`grade-produto-com-uma-cor` + `grade-tamanho-infantil`). ✅
- As filhas vêm logo após o pai (ordem observada na exportação e usada na POC). ✅
- O pai não carrega preço nem estoque; a página exibe o preço das filhas. ✅
- Produto de cor única: uma cor × N tamanhos. Produto de tamanho único: N cores × um tamanho.
  Ambos os casos importam normalmente. ✅
- Nova grade só pode ser adicionada a um produto que **ainda não tem variações** — na
  prática, defina cor+tamanho já na criação (suporte).

---

## 4. O que a importação NÃO faz (implicações para o pipeline)

| Limitação | Consequência |
|---|---|
| Não há coluna de URL; o slug é derivado de `nome`. ✅ | O campo "URL da página" do `SKILL.md` deixa de ser gerado: a URL é consequência do título. Se quiser controlar a URL, controle o título. |
| `<title>` recebe sufixo automático da loja. ✅ | `seo-tag-title` deve ter até ~60 caracteres **sem** `\| Kmilaa Modas`; corrigir a fórmula do Campo 3 do `SKILL.md`. |
| Imagem só no pai; nenhuma por variação. ✅ | A foto de cada cor entra como `imagem-1..5` do pai (até 5 no total). |
| Uma das 4 imagens da rodada 1 falhou silenciosamente e não reproduziu na rodada 2. ✅ | O pipeline deve comprimir imagens (< 500 KB) e **verificar após importar** se cada pai ficou com imagem; reimportação **não** altera imagens de produto existente (doc oficial) — a correção é manual ou com produto novo. |
| Não cria valor novo de grade de cor — cor fora da lista mestre (mesmo com caixa diferente, ex. `beige` vs `Beige`) é **rejeitada** linha a linha com o erro "Cor não permitida em 'grade-produto-com-uma-cor'. Verifique as cores permitidas em: http://cdn.awsli.com.br/download/cores.html" (confirmado na task 03: spike `POC-COR-006`/`POC-COR-007`, ver `poc/REGISTRO_ITERACOES.md` rodada 3). Criação de categoria segue não testada. ✅ | Validador estrito (`DadosMestre.cor_valida`, comparação exata, sem normalizar caixa) está correto e fica como está: uma cor reprovada localmente nunca seria aceita pela loja mesmo assim. |
| Após importar não é possível alterar `tipo`, `sku`, `sku-pai`, categorias e imagens. | Erros nesses campos exigem excluir o produto no painel e reimportar. |
| Páginas 404 por alguns minutos após a importação. ✅ | Verificação pós-importação deve aguardar/retentar. |

---

## 5. Convenções da Kmilaa (decididas)

- Layout de cabeçalhos: copiar da exportação real mais recente da loja (não do modelo genérico).
- SKU filha: `<sku-pai>-<cor-slug>-<tamanho-slug>` em minúsculas.
- Grades: `grade-produto-com-uma-cor` + `grade-tamanho-infantil`; nunca `grade-tamanho-juvenil-infantil`.
- Filhas: `estoque-gerenciado=S`, `estoque-situacao-em-estoque=imediata`,
  `estoque-situacao-sem-estoque=indisponivel`, `preco-custo=0`, `preco-promocional=0`.
- Pai e filhas: `usado=N`, `destaque=N`, `preco-sob-consulta=N`; NCM/MPN em branco; `gtin` só nas filhas.
- `seo-tag-title` sem sufixo de loja; `seo-tag-description` 140–155 caracteres.
- Marca com grafia canônica (`dados_mestre.md`).

---

## 6. Reprodução

```bash
.venv/Scripts/python poc/gerar_planilha_poc.py                       # 3 produtos da rodada 1
.venv/Scripts/python poc/gerar_planilha_poc.py --skus POC-VEST-004   # filtro por SKU
```

Histórico detalhado das rodadas e das páginas geradas: `poc/REGISTRO_ITERACOES.md`.
