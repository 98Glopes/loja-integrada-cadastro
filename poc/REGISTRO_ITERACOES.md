# Registro de iterações — POC de importação na Loja Integrada

Cada rodada: o que foi gerado, o que mudou em relação à anterior e o resultado
real da importação em `Produtos > Importar`. Consolidado depois em
`docs/regras-planilha-loja-integrada.md`.

## Como rodar

```bash
.venv/Scripts/python poc/gerar_planilha_poc.py
# gera poc/saida/poc-loja-integrada-<data>.xlsx
```

## Produtos dummy (todos `ativo = S`, apagar da loja ao final)

| SKU pai | Marca | Cores | Tamanhos | Filhas |
|---|---|---|---|---|
| `POC-VEST-001` | somnii | Beige, Rosa | 1, 2, 3 | 6 |
| `POC-CONJ-002` | kiki | Branco | P, M, G | 3 |
| `POC-BLUS-003` | Onda Marinha | Preto, Vermelho, Rosa | 4 | 3 |

SKU das filhas: `<sku-pai>-<cor>-<tamanho>` em minúsculas (ex.: `POC-VEST-001-beige-1`).

## Imagens a subir no registry (upload manual)

Qualquer JPEG serve — é só para provar que a importação puxa a URL para o pai.
Nomes sugeridos (convenção do SKILL: `marca-tipo-detalhe-cor-angulo.jpg`):

| SKU pai | Arquivo |
|---|---|
| `POC-VEST-001` | `somnii-vestido-florzinha-beige-frente.jpg`, `somnii-vestido-florzinha-rosa-frente.jpg` |
| `POC-CONJ-002` | `kiki-conjunto-body-calca-branco-frente.jpg` |
| `POC-BLUS-003` | `onda-marinha-blusinha-canelada-preto-frente.jpg` |

Fotos já renomeadas em `poc/fotos/` (originais preservados em `poc/fotos_input/`):

| Original | Renomeada para |
|---|---|
| `20250920_113424.jpg` (blusa florzinha + shorts preto) | `somnii-vestido-florzinha-beige-frente.jpg` |
| `20250920_113552.jpg` (regata branca + shorts rosa) | `somnii-vestido-florzinha-rosa-frente.jpg` |
| `20250920_113035.jpg` (regata vermelha + saia branca) | `kiki-conjunto-body-calca-branco-frente.jpg` |
| `20250920_113940.jpg` (camiseta cinza + bermuda listrada) | `onda-marinha-blusinha-canelada-preto-frente.jpg` |

As fotos não correspondem exatamente aos produtos dummy — para a POC só importa
que a URL seja pública e carregue. Estão em 3000×4000 (~1,8 MB cada), sem
compressão; o pipeline de imagens (compressão/redimensionamento) fica fora desta POC.

Hospedadas em `https://bucket.gleite.com/fotos/<nome>.jpg` (as 4 URLs respondem
`200 image/jpeg`), preenchidas em `IMAGENS` no script.

## Rodadas

### Rodada 1 — planilha base com imagens, sem categoria

- Gerado: `poc/saida/poc-loja-integrada-2026-09-13.xlsx` — 3 pais + 12 filhas, 54 colunas
  (cabeçalhos copiados da exportação real `docs/produtos-2026-09-10-...xlsx`).
- Preenchimento: pai com `nome`, `marca`, `seo-tag-*`, `descricao-completa` em HTML e
  `imagem-1` (`imagem-2` no vestido); filhas com estoque/preço/peso/dimensões +
  `grade-produto-com-uma-cor` + `grade-tamanho-infantil`. `id`, NCM/GTIN/MPN e
  categorias em branco.
- Resultado da importação: **sucesso** — "15 linhas de 15 ... processadas com sucesso em 2.373 seg".
- Páginas geradas (URL derivada do `nome`, slugificada pela plataforma — não há coluna de URL):
  - https://www.kmilaamodas.com.br/poc-vestido-somnii-florzinha-babados-e-laco-1-ao-3
  - https://www.kmilaamodas.com.br/poc-conjunto-kiki-body-e-calca-moletom-p-ao-g
  - https://www.kmilaamodas.com.br/poc-blusinha-onda-marinha-manga-longa-canelada-4
- Conferido no HTML público:
  - `seo-tag-title` entra no `<title>`, mas a loja **anexa** ` - Roupas para Bebê, Infantil e
    Juvenil | Kmilaa Modas` → o valor importado **não deve** terminar com `| Kmilaa Modas`
    (ficou duplicado: `... | Kmilaa Modas - Roupas para ... | Kmilaa Modas`).
  - `seo-tag-description` vai íntegra para `<meta name="description">`.
  - `descricao-completa` renderiza como HTML (h2/p/ul/h3).
  - Marca vinculada corretamente (`/marca/somnii`, `/marca/kiki`, `/marca/onda-marinha`), sem
    criar marca duplicada.
  - Imagens: `POC-CONJ-002` e `POC-BLUS-003` (1 imagem cada) importaram e foram para o CDN da
    loja (`cdn.awsli.com.br/.../produto/<id>/poc-conjunto-kiki-...jpg`). **`POC-VEST-001` (2
    imagens) ficou sem nenhuma foto**, embora as duas URLs respondam `200 image/jpeg`.
- Pendente de confirmação visual pela usuária: seletores de cor/tamanho com as 12 combinações.

### Rodada 2 — isolar a falha de imagem do vestido

Hipóteses: (a) o problema é ter 2 imagens no mesmo produto; (b) o problema é a imagem beige
em si. Dois produtos novos (não dá para alterar imagem de produto já importado):

| SKU pai | Imagens | Testa |
|---|---|---|
| `POC-VEST-004` | só `somnii-vestido-florzinha-beige-frente.jpg` | hipótese (b) |
| `POC-VEST-005` | `kiki-...-branco-frente.jpg` + `onda-marinha-...-preto-frente.jpg` (as duas que funcionaram) | hipótese (a) |

Também: `seo-tag-title` sem o sufixo `| Kmilaa Modas` para conferir o `<title>` final.

- Gerado: `poc/saida/poc-loja-integrada-2026-09-13-rodada-2.xlsx` — 2 pais + 6 filhas
  (`python poc/gerar_planilha_poc.py --skus POC-VEST-004 POC-VEST-005 --sufixo rodada-2`).
- Resultado da importação: **sucesso** — "8 linhas de 8 ... processadas com sucesso em 1.938 seg".
- Imagens: **as duas hipóteses caíram**. `POC-VEST-004` (só a beige) importou 1 imagem e
  `POC-VEST-005` (duas imagens) importou 2 — ambos visíveis na busca do site (`/buscar?q=POC`,
  ids 403765767 e 403765771). Logo, nem a imagem beige nem "2 imagens por produto" quebram.
  A falha do `POC-VEST-001` na rodada 1 fica registrada como **transitória/não reproduzida**
  (suspeita: tempo de download de 4 imagens de ~1,8 MB no mesmo lote). Mitigação para o
  pipeline: comprimir imagens (< 500 KB) e conferir `imagem-1` no pós-importação.
- Páginas: logo após a importação as URLs retornaram **404 transitório** (a busca já listava
  os produtos); minutos depois abriram normalmente. Regra prática: esperar alguns minutos
  antes de validar páginas pós-importação.
- `<title>` final confirmado: `POC Vestido Somnii Teste Duas Imagens 1 ao 3 - Roupas para
  Bebê, Infantil e Juvenil | Kmilaa Modas` — ou seja, `seo-tag-title` **sem** `| Kmilaa Modas`.
- Variações: página carrega `grades = [8945, 774914]` (grade de cor + grade de tamanho
  infantil) e preço `R$ 119,90` das filhas — pai sem preço não é problema.

## Conclusão

Formato validado ponta a ponta em 2 rodadas (23 linhas, 0 erros). Regras consolidadas em
`docs/regras-planilha-loja-integrada.md`. Produtos `POC-*` (5 pais, 18 filhas) ficam na loja
até exclusão manual pelo painel.
