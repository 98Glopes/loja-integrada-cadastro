# Arquitetura — Cadastro em massa de produtos (Kmilaa Modas × Loja Integrada)

Fonte de verdade do projeto a partir de 13/09/2026. Consolida as decisões da entrevista de
arquitetura, a POC de importação (`docs/regras-planilha-loja-integrada.md`) e o material bruto de
`docs/brutos/` (skill de copywriting, perfis de marca, dados mestre). Quando este documento e o
material bruto divergirem, vale este documento.

**Documento vivo.** Descreve o alvo e, à medida que as tasks são executadas, é reescrito para
refletir o que existe (ciclo spec → código → spec do `CLAUDE.md`). Legenda: 🔲 planejado ·
✅ implementado (task NN). O detalhe do que existe está em `docs/specs/` (spec viva por módulo
e spec as-built por task); decisões que mudaram ao longo do caminho estão em §16.

Índice:

1. [Objetivo e escopo](#1-objetivo-e-escopo)
2. [Decisões registradas](#2-decisões-registradas)
3. [Fluxo ponta a ponta](#3-fluxo-ponta-a-ponta)
4. [Planilha de entrada](#4-planilha-de-entrada)
5. [Fotos: estrutura de pastas, processamento e publicação no R2](#5-fotos)
6. [Geração de textos por IA](#6-geração-de-textos-por-ia)
7. [Montagem da planilha de saída](#7-montagem-da-planilha-de-saída)
8. [Workspace do lote, estado e relatório](#8-workspace-do-lote-estado-e-relatório)
9. [Verificação pós-importação](#9-verificação-pós-importação)
10. [Arquitetura de código](#10-arquitetura-de-código)
11. [Configuração e segredos](#11-configuração-e-segredos)
12. [Testes e evals](#12-testes-e-evals)
13. [Trade-offs avaliados](#13-trade-offs-avaliados)
14. [Riscos e questões em aberto](#14-riscos-e-questões-em-aberto)
15. [Evolução para serviço web](#15-evolução-para-serviço-web)
16. [Registro de decisões (ADR)](#16-registro-de-decisões-adr)

---

## 1. Objetivo e escopo

Substituir o processo manual atual (rodar a skill `kmilaa-produto` no Claude e copiar/colar no
painel) por um sistema autônomo que:

1. recebe uma **planilha simples** preenchida pela dona da loja e uma **pasta de fotos**;
2. valida os dados contra as regras da loja **antes** de gastar dinheiro (LLM/upload);
3. processa e publica as fotos no **Cloudflare R2**;
4. gera título, descrição HTML, tag title e meta description com **agentes especializados**
   (Copywriter → SEO → QA) usando a API da Anthropic;
5. monta a **planilha de importação em massa** da Loja Integrada (54 colunas, pai/filha);
6. produz um **relatório do lote** para conferência a posteriori;
7. depois da importação manual no painel, **verifica** no site público se cada produto ficou no
   ar com título, meta e imagens.

Fora do escopo desta versão: importar automaticamente no painel (a importação continua manual
em `Produtos > Importar`), edição de produtos já cadastrados, interface web (ver §15).

Operação: a dona da loja preenche planilha e fotos; o desenvolvedor roda a CLI. Fluxo
**autônomo** (sem etapa de aprovação humana dos textos), com QA de IA e relatório.

## 2. Decisões registradas

| Tema | Decisão |
|---|---|
| Quem opera | Dona da loja preenche a planilha/fotos; desenvolvedor roda a CLI (Windows). |
| Planilha de entrada | `.xlsx`, **uma linha por variação** (cor × tamanho), campos do produto repetidos ou preenchidos só na 1ª linha do SKU. Colunas em §4. |
| `sku-pai` | Código do fornecedor por família de produto (vem na etiqueta/nota). |
| GTIN | **Obrigatório por variação**; vai para a coluna `gtin` da linha filha. Revoga a regra "GTIN em branco" da POC. |
| Preço e estoque | Vêm da planilha, por variação. |
| Peso e dimensões | Padrão único configurável para todos os produtos (`0.1 kg`, `4×22×22 cm`, como na POC). |
| Fotos | `fotos/<sku-pai>/<cor>/*.jpg`; ordem alfabética dos arquivos define a numeração; **sem** classificação de ângulo; nomeadas por regra (não IA). |
| Processamento de imagem | JPEG, lado maior 1600 px, < 500 KB, EXIF removido, orientação corrigida. Entrada aceita jpg/png/webp/heic. |
| R2 | Bucket já existe com domínio público. Chave `produtos/<sku-pai>/<nome>.jpg`. **Sempre sobrescreve** na reexecução. |
| Agentes | **Por grupo**: Copywriter (título + descrição HTML) → SEO (tag title + meta description) → QA (veredito estruturado). Reprovação → retry do grupo culpado (máx. configurável, padrão 2). |
| Visão | **Não** — o modelo só recebe texto. |
| Modelos | Configuráveis por agente; padrão sugerido em §6.5. |
| Chamadas à API | Síncronas e **sequenciais, um produto por vez** (validar todos → para cada produto, ordenado por marca: fotos → textos). Sem paralelismo. Paralelismo por etapa e Message Batches ficam como evolução se o volume justificar. **Confirmado em 13/09/2026.** |
| Insumos dos prompts | Arquivos versionados no pacote (`recursos/`: Markdown para prosa, YAML para dados) + templates **Jinja2**; port `RepositorioPrompts` permite migrar para plataforma (Langfuse) depois. |
| Validação de grades | **Estrita**: cor e tamanho precisam existir na lista mestre versionada (extraída da exportação real). |
| Estado | Workspace por lote com estado por produto (JSON). Reexecução pula etapas concluídas. |
| `ativo` | Configurável, padrão `S`. |
| Revisão humana | Nenhuma antes do `.xlsx`. Produto `reprovado-qa` (esgotou `LLM_MAX_TENTATIVAS_QA=2` ciclos) fica **fora** da planilha, com o último texto e os motivos no relatório; a CLI retorna código ≠ 0; `--incluir-reprovados` inclui. Só problemas de gravidade `alta` reprovam. **Confirmado em 13/09/2026.** |
| Pós-importação | Comando separado que consulta o **site público** (busca + página do produto). |
| Documentação | `docs/*.md` canônicos versionados (`ARQUITETURA.md`, `regras-planilha-loja-integrada.md`, `tasks/`); `docs/brutos/` ignorado no git. |
| Tasks | Um arquivo por task em `docs/tasks/`, executadas manualmente e sequencialmente no Claude Code. |

## 3. Fluxo ponta a ponta

```
                 dona da loja                               desenvolvedor
        ┌──────────────────────────┐              ┌──────────────────────────────────┐
        │ produtos.xlsx            │              │ loja-integrada-cadastro processar │
        │ fotos/<sku>/<cor>/*.jpg  │ ───────────▶ │   --planilha produtos.xlsx        │
        └──────────────────────────┘              │   --fotos fotos/ --lote 2026-09-w38│
                                                  └──────────────┬───────────────────┘
                                                                 ▼
   ┌─────────────┐   ┌──────────────┐   ┌────────────────────┐   ┌──────────────┐   ┌───────────┐
   │ 1 Validar   │──▶│ 2 Fotos      │──▶│ 3 Textos (IA)      │──▶│ 4 Montar     │──▶│ 5 Relatar │
   │ (regras)    │   │ comprimir +  │   │ Copywriter→SEO→QA  │   │ 54 colunas   │   │ md + json │
   │             │   │ publicar R2  │   │ + validações regra │   │ pai/filhas   │   │           │
   └─────────────┘   └──────────────┘   └────────────────────┘   └──────────────┘   └───────────┘
        reprova ─▶ relatório         estado/<sku>.json atualizado a cada etapa
                                                                 ▼
                                             lotes/<lote>/saida/<lote>.xlsx  +  relatorio.md
                                                                 ▼
                              importação manual no painel (Produtos > Importar)
                                                                 ▼
                                  loja-integrada-cadastro verificar --lote 2026-09-w38
                                  (busca + página pública: título, meta, imagens, grades)
```

Etapas por produto (cada uma idempotente e registrada no estado):

| # | Etapa | Determinística? | Falha → |
|---|---|---|---|
| 1 | **Validar** entrada (campos, grafias, cores/tamanhos na lista mestre, GTIN, pasta de fotos existe) | sim | produto `reprovado-validacao`; não entra nas etapas seguintes |
| 2 | **Fotos**: descobrir, nomear, comprimir, publicar no R2, escolher até 5 URLs para o pai | sim | produto `erro-fotos`; retry na reexecução |
| 3 | **Textos**: Copywriter → validação de regra → SEO → validação de regra → QA (loop). Atrás do port `GeradorTextos`; até a task 16 a implementação é o `GeradorTextosDummy` (determinístico, custo 0 — ADR-007) | não (IA) | `reprovado-qa` após N tentativas, ou `erro-llm` |
| 4 | **Montar** linhas pai + filhas | sim | erro de programação (não deve ocorrer com entrada validada) |
| 5 | **Relatar** lote | sim | — |

Produtos são processados **um por vez**, na ordem por marca (para reaproveitar o cache do
system prompt); dentro de um produto as etapas são sequenciais. Etapas 2 e 3 são independentes
entre si, mas rodam nesta ordem para que a falha barata (fotos) apareça antes da cara (LLM). O
estado é salvo após cada etapa, então interromper (`Ctrl+C`) e reexecutar retoma do produto e
da etapa onde parou.

## 4. Planilha de entrada

Arquivo `.xlsx`, uma aba, cabeçalho na linha 1, **uma linha por variação**. Um modelo
preenchível (`modelo-entrada.xlsx`, com validação de dados nas colunas de cor/tamanho/marca) é
gerado pelo comando `loja-integrada-cadastro modelo-entrada`, para a dona da loja não digitar
cabeçalhos.

| Coluna | Escopo | Obrigatória | Regra |
|---|---|---|---|
| `sku-pai` | produto | sim | Código do fornecedor. Agrupa as linhas do mesmo produto. Único no lote. |
| `marca` | produto | sim | Grafia canônica (`kiki`, `Onda Marinha`, `somnii`, `Colorittá`, `Menina Anjo`, `Luc.boo`, `Nina Go`, `Kyly`, `Lemon`). Validador aceita variações de caixa/acento e **normaliza** para a canônica; `Açucena`/`Abrange` reprovam. |
| `nome-fornecedor` | produto | sim | Nome como veio do fornecedor (ex.: "Conjunto Baby Malha e Moletom"). |
| `tipo-peca` | produto | sim | Conjunto, Vestido, Macacão, Casaco, Blusinha… Texto livre; vira parte do título e do nome da foto. |
| `categoria` | produto | sim | Caminho com `>` (ex.: `Linha Kids (6 ao 10) > Menina > Vestido`). Até 5 níveis. Só formatação é validada (sem espaços extras/caracteres especiais); a categoria **precisa existir no painel**. |
| `composicao` | produto | sim | Ex.: `100% algodão`; `malha + moletom`. |
| `detalhes` | produto | sim | Diferenciais: botões na gola, bordado, babado, laço, estampa… |
| `colecao` | produto | não | Ex.: `Outono/Inverno 2026`. |
| `faixa-tamanho` | produto | sim | Texto livre com a faixa de tamanhos da família (ex.: `P ao G`, `1 ao 4`, `P ao 3`), escrita pela dona da loja — **não** é calculada a partir dos tamanhos das variações (ver ADR-005). Vai para título/descrição (§6). |
| `cor` | variação | sim | Grafia **exata** da grade da loja (`Beige`, `Rosa`, `Cinza Claro`…). Validador reprova cor fora da lista mestre. Precisa ter subpasta correspondente em `fotos/<sku-pai>/`. |
| `tamanho` | variação | sim | `P M G GG XG` ou `1 2 3 4 6 8 10 12 14 16 18 20` (lista mestre). |
| `gtin` | variação | sim | Código de barras da variação (8/12/13/14 dígitos, dígito verificador conferido). Único no lote. |
| `preco` | variação | sim | Decimal > 0 (`119,90` ou `119.9`). |
| `estoque` | variação | sim | Inteiro ≥ 0. |

Regras de agrupamento:

- Campos de escopo *produto* são lidos da **primeira linha** de cada `sku-pai`; nas demais
  linhas podem ficar em branco ou repetidos — se repetidos com valor diferente, o validador
  reprova o produto (ambiguidade).
- A ordem das cores na planilha define a ordem das fotos no pai (§5.3).
- Combinação cor × tamanho duplicada no mesmo SKU reprova.

O que **não** está na entrada porque é derivado ou configurado: peso/dimensões (config),
`ativo` (config), textos (IA), URLs de imagem (R2), SKU das filhas
(`<sku-pai>-<cor-slug>-<tamanho-slug>`), URL da página (a loja deriva do título).

## 5. Fotos

### 5.1 Estrutura de entrada

```
fotos/
  3254002/            ← sku-pai
    Beige/            ← nome da cor (case-insensitive, acento ignorado; precisa casar com a planilha)
      20250920_113424.jpg
      20250920_113552.jpg
    Rosa/
      IMG_0001.HEIC
```

O validador exige que cada cor da planilha tenha uma subpasta com ≥ 1 imagem; subpasta sem cor
correspondente na planilha gera aviso (não bloqueia).

### 5.2 Nomeação (regra determinística)

✅ Implementado (task 07, `models/slug.py` + `models/nomeador_fotos.py`).

`<marca>-<tipo-peca>-<nome-fornecedor>-<cor>-<n>.jpg`, tudo slugificado (minúsculas, sem
acento, hífens), `n` = posição do arquivo na ordem alfabética dentro da subpasta (1, 2, 3…).
Tokens do `tipo-peca` repetidos no início de `nome-fornecedor` são removidos; o nome é truncado
em 60 caracteres antes de `-<cor>-<n>`.

Exemplo: marca `Onda Marinha`, tipo `Conjunto`, nome `Conjunto Baby Malha e Moletom`, cor
`Azul aco`, 1ª foto → `onda-marinha-conjunto-baby-malha-e-moletom-azul-aco-1.jpg`.

Motivo para não usar a IA aqui: o nome fica estável entre reexecuções e a etapa de fotos não
depende da etapa de textos.

### 5.3 Processamento e publicação

✅ Implementado — passos 1–4 na task 07 (`PipelineFotos` + `ProcessadorImagemPillow`), passos
5–6 (R2 real) na task 08 (`ArmazenamentoImagensR2`).

1. Abrir com Pillow (`pillow-heif` registra HEIC), aplicar orientação EXIF, converter para RGB.
2. Redimensionar para lado maior ≤ 1600 px.
3. Salvar JPEG progressivo sem EXIF; começar em qualidade 85 e reduzir em passos de 5 até
   ficar < 500 KB (piso 60; se ainda passar, reduz o lado maior para 1200 px **e reinicia o
   loop de qualidade em 85** nesse novo tamanho). Caso extremo (mesmo em 1200 px/qualidade 60
   o arquivo ainda excede o limite): aceita o resultado sem erro (best-effort) — falhar a foto
   inteira por poucos KB acima do alvo é pior que publicar levemente acima do limite.
4. Guardar cópia em `lotes/<lote>/fotos-processadas/produtos/<sku-pai>/<nome>.jpg` — o mesmo
   caminho relativo (`produtos/<sku-pai>/<nome>.jpg`) é a `chave` usada depois para publicar no
   R2 (task 08), então o armazenamento local já espelha a estrutura de chaves do bucket.
5. Publicar no R2 com chave `produtos/<sku-pai>/<nome>.jpg`, `Content-Type: image/jpeg`,
   `Cache-Control: public, max-age=31536000`. Sempre sobrescreve. ✅ (task 08,
   `ArmazenamentoImagensR2.publicar`)
6. URL pública: `<R2_URL_PUBLICA>/produtos/<sku-pai>/<nome>.jpg`. Após o upload, um `HEAD`
   confirma `200 image/jpeg` (a POC teve uma falha silenciosa de imagem na importação; a URL
   precisa estar acessível antes de ir para a planilha). ✅ (task 08,
   `ArmazenamentoImagensR2.existe`, chamado por `PipelineFotos` logo após publicar)

Se uma foto falha ao processar (arquivo corrompido, formato não suportado) **ou falha ao
publicar/confirmar acessibilidade no R2**, o pipeline aborta o produto inteiro: nenhuma foto
parcial é publicada/contada, o produto vai para `erro-fotos` e a exceção
(`ErroProcessamentoImagem` ou `ErroPublicacaoImagem`) se propaga — decisão confirmada com o
usuário nas tasks 07/08, fail-fast em vez de best-effort por foto, para não repetir a falha
silenciosa de imagem da POC.

Seleção das até 5 imagens do pai (a Loja Integrada só aceita imagem no pai): primeiro a foto
`-1` de cada cor na ordem da planilha, depois as `-2` de cada cor, e assim por diante, até 5.
Assim toda cor aparece antes de qualquer cor ter duas fotos. As demais ficam publicadas no R2
sem uso (custo desprezível) e listadas no relatório. ✅ Implementado (task 07,
`SeletorImagensPai`).

Cloudflare R2 é compatível com S3: o conector usa `boto3` com `endpoint_url =
https://<ACCOUNT_ID>.r2.cloudflarestorage.com`, região `auto`. ✅ Implementado (task 08,
`ArmazenamentoImagensR2`). `ArmazenamentoImagensDiretorio` (task 07), que grava em
`fotos-processadas/` e devolve URL `file://` local, continua existindo para testes — ainda não
há wiring em `config/composicao.py`/`cli.py` escolhendo entre as duas (sem consumidor até a
task 11, que implementa o comando `processar`; ver ADR-006).

## 6. Geração de textos por IA

### 6.1 Campos gerados e limites (validados por regra antes do QA)

| Campo | Coluna da saída | Limite | Regras principais (da skill, ajustadas pela POC) |
|---|---|---|---|
| Título | `nome` | ≤ 68 caracteres | `[Tipo] [Marca] [detalhe principal] [faixa de tamanho]`; contém a marca com grafia canônica; sem adjetivos vazios (lista proibida em `recursos/seo.md`). **Gera a URL** da página — a IA não gera URL. |
| Descrição HTML | `descricao-completa` | ≥ 120 palavras | Estrutura obrigatória `h2 → p → p → ul → h3 Sobre a [Marca] → h3 Compre na Kmilaa Modas`; só tags `h2 h3 p ul li strong`; característica → benefício; escrita para a mãe; sem repetir o título na abertura. |
| Tag title | `seo-tag-title` | ≤ 60 caracteres | **Sem** sufixo `\| Kmilaa Modas` (a loja anexa ` - Roupas para Bebê, Infantil e Juvenil \| Kmilaa Modas`). Específico, com marca e tipo. |
| Meta description | `seo-tag-description` | 140–155 caracteres | Benefício + detalhe da marca + CTA com diferencial da loja (3x sem juros / frete grátis SP). |

Nome das fotos e URL **não** são mais gerados pela IA (ver §5.2 e `regras-planilha…` §4).

### 6.2 Topologia: Copywriter → SEO → QA

O pipeline enxerga a geração de textos só pelo port `GeradorTextos.gerar(produto, estado) ->
TextosProduto` (task 09). A topologia abaixo é a implementação de IA desse port
(`GeradorTextosIa`, task 16); até ela chegar, o `GeradorTextosDummy` ocupa o lugar para o
`processar` funcionar ponta a ponta (ADR-007).

```
 dados do produto ──▶ [Copywriter] ──▶ validação de regra ──▶ [SEO] ──▶ validação de regra ──▶ [QA]
        ▲                 │  título + descrição HTML            │ tag title + meta                │
        │                 └──────── reprovação de regra ◀───────┘                                │
        └─────────────────────────────── reprovação do QA (feedback por campo) ◀─────────────────┘
                                          máx. N tentativas por grupo (padrão 2)
```

- **Copywriter** recebe: dados do produto (planilha), perfil da marca, posicionamento da loja,
  regras de copy (Ogilvy, tabela característica→benefício). Devolve `titulo` e
  `descricao_html` (saída estruturada).
- **SEO** recebe: os mesmos dados **mais** o título e a descrição aprovados, e as regras de SEO
  (Google SEO Starter Guide + limites da loja). Devolve `seo_tag_title` e `seo_tag_description`.
  Recebe a copy para manter as mesmas palavras-chave — é o motivo de ser sequencial.
- **QA** (LLM como juiz) recebe: dados do produto, os 4 campos, o perfil da marca e um
  checklist objetivo. Devolve `VeredictoQa {aprovado: bool, problemas: [{campo, gravidade,
  motivo, sugestao}]}`. Só reprova por problema de gravidade `alta` (fato inventado que não
  está no input, tom fora da marca, promessa que a loja não faz, erro de português, campo
  genérico). Problemas `baixa` viram observação no relatório.
- **Validação de regra** (código, sem IA) roda antes do QA e é a primeira linha de defesa:
  limites de caracteres, estrutura HTML, presença da marca, sufixo proibido, adjetivos
  proibidos, número de palavras. Reprovação de regra devolve a mensagem exata ao agente
  ("título tem 74 caracteres, limite 68") numa nova tentativa — barato e determinístico.
- **Retry com feedback**: a nova tentativa reenvia a conversa anterior (prompt + resposta) e
  acrescenta um turno de usuário com os problemas apontados. Após N tentativas o produto fica
  `reprovado-qa`, com o último texto e os motivos no relatório.
- **Destino do `reprovado-qa`** (decisão confirmada): fica **fora** do `.xlsx`, aparece em
  destaque no topo do relatório e faz a CLI retornar código ≠ 0. Para resolver: corrigir os
  dados de entrada (`detalhes`, `composicao`…) e rodar `processar … --refazer-textos <sku>`,
  ou aceitar o último texto com `--incluir-reprovados`. Nada de qualidade duvidosa vai ao ar
  sem uma ação explícita do operador.

### 6.3 Boas práticas da API Anthropic aplicadas

Referência: skill `claude-api` (documentação oficial) — os pontos abaixo são os que o conector
`ClienteLlmAnthropic` implementa.

| Prática | Como entra no projeto |
|---|---|
| SDK oficial `anthropic` (Python), cliente síncrono, `max_retries=3`, timeout explícito | Uma instância por execução, injetada pelo composition root. |
| **Saída estruturada** com `client.messages.parse(output_format=<pydantic>)` | Cada agente tem um schema pydantic (em `infra/`), convertido para o dataclass de domínio. Elimina parsing de JSON em texto livre. Sem prefill (removido nos modelos atuais). |
| **Prompt caching** com `cache_control` no system prompt | System prompt = `[regras fixas da loja/formato] + [perfil da marca]`, ambos estáveis → breakpoint no último bloco de system. Dados do produto só no turno de usuário. Produtos do lote são **ordenados por marca** para maximizar cache hits dentro do TTL de 5 min. Sem timestamps/UUIDs no prefixo. |
| **Adaptive thinking + `effort`** | Copywriter `high`, SEO `medium`, QA `medium` (configuráveis). `temperature/top_p` não existem mais nos modelos atuais — não usar. |
| `max_tokens` com folga (4096 para geradores, 2048 para QA) | Textos são curtos; folga evita truncamento sem custo extra. |
| Dados da planilha como **dados, não instruções** | Conteúdo da dona da loja entra em blocos `<produto>…</produto>` no turno de usuário; system prompt instrui a tratar como dados (defesa contra injeção acidental). |
| Tratamento de erros por classe (`RateLimitError` → espera `retry-after`; `APIStatusError ≥ 500` → retry; `BadRequestError` → falha do produto) e tradução para `ErroGeracaoTexto` | O service nunca vê exceções do SDK. |
| `stop_reason` conferido (`max_tokens` → retry com limite maior; `refusal` → falha registrada) | — |
| `usage` (input, output, cache read/write) registrado por chamada | Vai para o estado do produto e para o custo estimado no relatório. `request_id` guardado para suporte. |
| Execução sequencial | Uma chamada por vez; rate limit tratado pelo backoff do SDK. Produtos ordenados por marca para maximizar cache hits. |
| Evolução: Message Batches (−50%) | Não usado agora: o loop de QA exigiria várias rodadas assíncronas. Se o volume por lote passar de centenas, a etapa Copywriter/SEO pode virar batch mantendo o QA síncrono. |

### 6.4 Insumos dos prompts (`recursos/`)

```
src/loja_integrada_cadastro/recursos/
  loja.md                 posicionamento da Kmilaa Modas, diferenciais, tom
  copy.md                 regras Ogilvy, tabela característica→benefício, estrutura HTML
  seo.md                  regras de tag title/meta/headings/conteúdo (Google SEO Starter Guide
                          + limites observados na POC) e lista de adjetivos/clichês proibidos
  qa.md                   checklist do revisor (critérios objetivos de reprovação)
  marcas/
    kiki.md  onda-marinha.md  somnii.md  coloritta.md  menina-anjo.md  luc-boo.md
    nina-go.md  kyly.md  lemon.md  _generico.md
  dados_mestre.yaml       marcas (canônica + aliases aceitos), cores da grade, tamanhos,
                          categorias conhecidas (só referência)
  prompts/
    copywriter.j2  seo.j2  qa.j2   (system e user separados por bloco)
```

Markdown é carregado como texto (prosa para o modelo); YAML é carregado e validado num
dataclass `DadosMestre` (usado pelo validador, não só pelos prompts). Templates Jinja2
recebem `produto`, `marca`, `loja`, `regras` e, no SEO/QA, os textos já gerados. Os arquivos
são recursos do pacote (`importlib.resources`), então o sistema funciona instalado, sem depender
do repositório.

Marca sem perfil próprio usa `_generico.md` (posicionamento da loja) e o relatório avisa.

### 6.5 Modelos e custo (padrão sugerido, tudo configurável)

| Agente | Modelo padrão | `effort` | Justificativa |
|---|---|---|---|
| Copywriter | `claude-opus-5` | `high` | Tom de marca e tradução característica→benefício são o coração do produto; julgamento fino de linguagem. |
| SEO | `claude-opus-5` | `medium` | Tarefa mais restrita (limites e fórmula), beneficia-se do mesmo cache de marca. |
| QA | `claude-opus-5` | `medium` | Juiz precisa ser pelo menos tão capaz quanto o gerador para pegar fato inventado e tom errado. Alavanca de custo: `claude-sonnet-5` aqui, se medido que a qualidade se mantém. |

Estimativa por produto (3 chamadas, sem retry): system ~4k tokens em cache (leitura ~$0,50/M),
~1,5k tokens de entrada variável, ~1k de saída por chamada → **≈ US$ 0,10 por produto**; um
lote de 50 produtos ≈ US$ 5, 500 produtos ≈ US$ 50 (Opus 5: $5/M entrada, $25/M saída). Retry
de QA adiciona ~50% naquele produto. O relatório mostra o custo real medido.

## 7. Montagem da planilha de saída

Segue integralmente `docs/regras-planilha-loja-integrada.md` (54 colunas na ordem da exportação
real, pai `com-variacao` + filhas `variacao`). A única mudança em relação à POC: coluna `gtin`
preenchida nas filhas.

O layout de cabeçalhos é versionado como constante (`models/layout_planilha_loja_integrada.py`,
54 nomes na ordem exata), com teste que confere contra a exportação real quando o arquivo bruto
estiver disponível localmente. Motivo: não depender de `docs/brutos/` em runtime.

Mapeamento resumido:

| Linha | Campos preenchidos |
|---|---|
| Pai | `tipo=com-variacao`, `sku`, `ativo` (config), `usado=N`, `destaque=N`, `nome` (título IA), `seo-tag-title`, `seo-tag-description`, `descricao-completa`, `preco-sob-consulta=N`, `marca` (canônica), `categoria-nome-nivel-1..5`, `imagem-1..5` (URLs R2) |
| Filha | `tipo=variacao`, `sku-pai`, `sku=<sku-pai>-<cor-slug>-<tamanho-slug>`, `ativo`, `usado=N`, `destaque=N`, `gtin`, `estoque-gerenciado=S`, `estoque-quantidade`, `estoque-situacao-em-estoque=imediata`, `estoque-situacao-sem-estoque=indisponivel`, `preco-sob-consulta=N`, `preco-custo=0`, `preco-cheio`, `preco-promocional=0`, `peso-em-kg`, `altura-em-cm`, `largura-em-cm`, `comprimento-em-cm` (config), `grade-produto-com-uma-cor`, `grade-tamanho-infantil` |

Produtos `reprovado-*`/`erro-*` ficam fora do arquivo por padrão (`--incluir-reprovados` inclui
os `reprovado-qa` com o último texto gerado). O arquivo respeita os limites da plataforma
(≤ 9.997 linhas; ≤ 50 variações por produto — validado na entrada).

## 8. Workspace do lote, estado e relatório

```
lotes/<nome-do-lote>/
  entrada/produtos.xlsx           cópia da planilha recebida (auditoria)
  estado/<sku-pai>.json           estado por produto (abaixo)
  fotos-processadas/<sku-pai>/    JPEGs finais enviados ao R2
  saida/<nome-do-lote>.xlsx       planilha de importação
  relatorio.md                    relatório humano
  relatorio.json                  mesmo conteúdo, estruturado (base do `verificar` e de evals)
```

Estado por produto (`EstadoProduto`, serializado em JSON) ✅ implementado (task 06):

```
sku_pai, status: validado | reprovado-validacao | erro-fotos | fotos-publicadas |
                 textos-gerados | reprovado-qa | erro-llm | pronto
entrada: ProdutoEntrada (normalizado)
hash_entrada
validacao: {problemas: [...], avisos: [...]}
fotos: tuple[FotoProduto, ...]   # {sku_pai, cor, ordem, arquivo_origem, nome, chave, url, bytes} — task 07
imagens_pai: [url × até 5]
textos: {titulo, descricao_html, seo_tag_title, seo_tag_description}   # tipo mínimo até a task 09 (TextosProduto) e 16 (tentativas)
tentativas: [{agente, tentativa, modelo, usage, veredito_regra, veredito_qa, request_id, em}]   # idem
custo_usd_estimado
verificacao: {em, url_pagina, title_ok, meta_ok, imagens_encontradas, grades_ok, problemas}   # tipo mínimo até a task 18
atualizado_em
```

`EstadoProduto` não tem construtor vazio: nasce pela fábrica `registrar_validacao`, já
`validado` ou `reprovado-validacao`, e evolui por métodos de intenção que validam a transição
(grafo completo em `docs/specs/estado-lote.md`). Persistência por
`RepositorioEstadoLoteJson` (`services/ports/repositorio_estado_lote.py` +
`infra/repositorio_estado_lote_json.py`): um JSON por SKU em `lotes/<lote>/estado/`, escrita
atômica, workspace (`entrada/`, `estado/`, `fotos-processadas/`, `saida/`) criado no construtor.

Reexecução (`PoliticaReexecucao`, `services/politica_reexecucao.py`, ✅ task 06 — o consumo pelo
comando `processar` é da task 11): produtos `pronto` são pulados; `erro-*` e `reprovado-*` são
reprocessados a partir da etapa que falhou; `--refazer-textos <sku>` e `--refazer-fotos <sku>`
forçam regeneração pontual (`--refazer-fotos` tem prioridade quando os dois aparecem juntos, já
que retomar de fotos cobre a etapa de textos na sequência). Planilha de entrada alterada →
produtos cujo conteúdo mudou (hash da entrada normalizada) voltam ao início (`recomeçar`).

Relatório (`relatorio.md`): resumo (produtos por status, linhas geradas, custo, tempo), tabela
por produto (SKU, marca, status, título, nº fotos, tentativas, custo), seção de reprovados com
motivos, seção de avisos (marca sem perfil, subpasta de foto sem cor, fotos não usadas),
seção de tokens/custo por agente. Não expõe segredos.

## 9. Verificação pós-importação

`loja-integrada-cadastro verificar --lote <nome> [--esperar 5m]`, executado depois da importação
manual. Para cada produto `pronto` no estado:

1. Busca pública do site (`/buscar?q=<título>`) para localizar a URL da página — a URL é
   derivada do título pela loja e pode divergir do slug previsto.
2. `GET` da página; espera até `--esperar` com retry exponencial pelo 404 transitório
   observado na POC.
3. Confere: `<title>` começa com `seo_tag_title`; `<meta name="description">` igual à gerada;
   nº de imagens do CDN (`cdn.awsli.com.br`) ≥ 1 e idealmente = nº enviado; script de grades
   presente com cor e tamanho; marca vinculada (`/marca/<slug>`).
4. Grava `verificacao` no estado e anexa seção ao `relatorio.md` (produtos sem imagem em
   destaque — a reimportação não corrige imagem; a ação é manual no painel).

Implementado com `httpx` + parser HTML (`selectolax`), atrás do port `ConsultaLoja`. Não usa a
API privada da Loja Integrada.

## 10. Arquitetura de código

Hexagonal em layout simplificado (`CLAUDE.md`): `cli / infra → services → models`. A lista
abaixo é a **direção**; cada task cria só o que a funcionalidade dela exige.

```
src/loja_integrada_cadastro/
  🔲 models/
    ✅ produto_entrada.py            ProdutoEntrada (frozen) + variacao_entrada.py: VariacaoEntrada (task 04)
    ✅ dados_mestre.py               DadosMestre: marcas (canônica+aliases), cores, tamanhos, categorias de referência (task 02)
    ✅ layout_planilha_entrada.py    as 14 colunas da planilha de entrada, na ordem sugerida (task 04)
    ✅ problema_linha_planilha.py    ProblemaLinhaPlanilha (linha, coluna, motivo) (task 04)
    ✅ resultado_validacao.py        ProblemaValidacao, ResultadoValidacao {problemas, avisos, aprovado} (task 05)
    ✅ foto_produto.py               FotoProduto (frozen: sku_pai, cor, ordem, arquivo_origem, nome, chave, url, bytes) (task 07)
    🔲 textos_produto.py             TextosProduto (4 campos) + como_mapa() (task 09)
    🔲 veredicto_qa.py               VeredictoQa + ProblemaQa
    ✅ estado_produto.py             EstadoProduto (fábrica registrar_validacao + 8 métodos de intenção; `fotos: tuple[FotoProduto, ...]` desde a task 07) e status_produto.py: StatusProduto (Enum) (task 06)
    🔲 linha_planilha.py             LinhaPlanilha (dict tipado coluna→valor) 
    🔲 layout_planilha_loja_integrada.py   as 54 colunas, na ordem
    🔲 regras_texto.py               limites e validações de regra dos 4 campos (puras)
    ✅ slug.py                       slugificar(texto) -> str (sem acento, minúsculas, hífens) (task 07)
    ✅ nomeador_fotos.py             NomeadorFotos.nomear(produto, cor, ordem) -> str; SeletorImagensPai.selecionar(fotos) -> list (task 07)
    exceptions/
      ✅ erro_configuracao.py        ErroConfiguracao(variavel, valor_invalido) (task 01)
      ✅ erro_recursos.py            ErroRecursos(recurso, motivo) (task 02)
      ✅ erro_planilha_entrada.py    ErroPlanilhaEntrada(caminho, problemas: tuple[ProblemaLinhaPlanilha, ...]) (task 04)
      ✅ erro_transicao_estado_invalida.py  ErroTransicaoEstadoInvalida(sku_pai, status_atual, metodo) (task 06)
      ✅ erro_estado_lote.py         ErroEstadoLote(caminho, motivo) (task 06)
      ✅ erro_processamento_imagem.py  ErroProcessamentoImagem(origem, motivo) (task 07)
      ✅ erro_publicacao_imagem.py     ErroPublicacaoImagem(chave_ou_url, motivo) (task 08)
      🔲                             ErroValidacaoEntrada, ErroGeracaoTexto, ErroConsultaLoja
  🔲 services/
    🔲 ports/
      ✅ leitor_planilha_entrada.py  LeitorPlanilhaEntrada.ler(caminho) -> list[ProdutoEntrada] (task 04)
      ✅ catalogo_fotos.py           CatalogoFotos.listar(sku_pai) -> dict[cor, list[caminho]]; cores_disponiveis(sku_pai) (task 05)
      ✅ processador_imagem.py       ProcessadorImagem.preparar(origem: Path) -> bytes (JPEG final) (task 07)
      ✅ armazenamento_imagens.py    ArmazenamentoImagens.publicar(chave, dados) -> url; existe(url) -> bool (task 07; contrato confirmado sem alteração na task 08 — ver ADR-006)
      🔲 gerador_textos.py           GeradorTextos.gerar(produto, estado) -> TextosProduto (task 09)
      🔲 cliente_llm.py              ClienteLlm.gerar(pedido: PedidoLlm, schema: type[T]) -> RespostaLlm[T]
      🔲 repositorio_prompts.py      RepositorioPrompts.renderizar(nome, contexto) -> PromptRenderizado
      ✅ repositorio_estado_lote.py  RepositorioEstadoLote.carregar/salvar(EstadoProduto), listar() (task 06)
      🔲 escritor_planilha_saida.py  EscritorPlanilhaSaida.escrever(linhas, destino)
      🔲 consulta_loja.py            ConsultaLoja.buscar(termo) -> list[url]; pagina(url) -> PaginaProduto
    ✅ validador_entrada.py          ValidadorEntrada(dados_mestre, catalogo_fotos, marcas_com_perfil) (task 05)
    ✅ politica_reexecucao.py        PoliticaReexecucao.decidir(...) -> ResultadoPoliticaReexecucao (task 06)
    ✅ pipeline_fotos.py             PipelineFotos(catalogo, processador, armazenamento).processar(produto, estado) -> list[FotoProduto] (task 07; confirma armazenamento.existe(url) após publicar desde a task 08)
    🔲 agente_copywriter.py          AgenteCopywriter(llm, prompts, recursos)
    🔲 agente_seo.py                 AgenteSeo(llm, prompts, recursos)
    🔲 agente_qa.py                  AgenteQa(llm, prompts, recursos)
    🔲 gerador_textos_ia.py          GeradorTextosIa: implementa o port GeradorTextos orquestrando os 3 agentes + regras + retry (task 16)
    🔲 montador_planilha.py          MontadorPlanilha(config_fisica, ativo) -> linhas pai/filhas
    🔲 processador_lote.py           ProcessarLote: caso de uso principal (loop sequencial, estado, relatório)
    🔲 gerador_relatorio.py          GeradorRelatorio(estados) -> markdown + dict
    🔲 verificador_importacao.py     VerificarImportacao(consulta_loja, estado)
  🔲 infra/
    ✅ leitor_planilha_entrada_openpyxl.py    LeitorPlanilhaEntradaOpenpyxl (task 04)
    ✅ gerador_modelo_entrada_openpyxl.py     GeradorModeloEntrada(dados_mestre).gerar(destino) (task 04)
    ✅ catalogo_fotos_diretorio.py             CatalogoFotosDiretorio (task 05)
    ✅ processador_imagem_pillow.py            ProcessadorImagemPillow(lado_max_px, tamanho_max_kb): Pillow + pillow-heif (task 07)
    ✅ armazenamento_imagens_diretorio.py       ArmazenamentoImagensDiretorio(raiz): grava em fotos-processadas/, devolve URL file:// (task 07)
    ✅ armazenamento_imagens_r2.py            ArmazenamentoImagensR2(bucket, account_id, access_key_id, secret_access_key, url_publica): boto3 (S3-compatible), existe() com httpx.head real (task 08)
    🔲 gerador_textos_dummy.py                GeradorTextosDummy: textos determinísticos dentro dos limites de §6.1 — provisório (task 09), removido na task 16 (ADR-007)
    🔲 cliente_llm_anthropic.py               SDK anthropic: parse(), caching, usage, erros → domínio
    🔲 esquemas_llm.py                        modelos pydantic de saída estruturada (por agente)
    🔲 repositorio_prompts_jinja.py           Jinja2 + recursos do pacote
    ✅ carregador_recursos.py                 lê recursos/ (md, yaml) via importlib.resources (task 02)
    ✅ repositorio_estado_lote_json.py         RepositorioEstadoLoteJson (task 06)
    🔲 escritor_planilha_saida_openpyxl.py
    🔲 consulta_loja_http.py                  httpx + selectolax
  config/
    ✅ configuracao.py                        Configuracao (frozen dataclass) lida de env/.env; exigir_anthropic()/exigir_r2() (task 01)
    ✅ leitor_ambiente.py                     LeitorAmbiente: conversão de variáveis com erro claro (task 01)
    🔲 composicao.py                          ✅ montar_gerador_modelo_entrada() (task 04); ✅ montar_leitor_planilha_entrada(), montar_validador_entrada() (task 05); 🔲 montar_gerador_textos() (task 09; troca para IA na 16), montar_processador_lote(), montar_verificador()
  🔲 recursos/                                §6.4 (dados_mestre.yaml ✅ task 02; demais arquivos pendentes)
  ✅ cli.py                                   AplicacaoCli, argparse: modelo-entrada (task 04) | validar (task 05) | processar | verificar (task 01; os 2 últimos "não implementado", código 2)
```

Cada task troca para ✅ o que entregou e ajusta nomes/arquivos para os reais. Detalhe do que
existe: `docs/specs/`.

Regras que as tasks devem respeitar:

- `models` e `services` não importam `anthropic`, `boto3`, `openpyxl`, `PIL`, `jinja2`, `httpx`.
- Toda I/O passa por um port; `services` recebem os ports pelo construtor em `config/composicao.py`.
- Erros de infra são traduzidos para `models/exceptions/` no conector.
- Uma classe por arquivo, `snake_case` espelhando a classe, type hints completos, `mypy --strict`.
- Dataclasses `frozen=True` para entidades/VOs; `EstadoProduto` é o único agregado mutável (por
  ser atualizado etapa a etapa) — mutação apenas via métodos com nome de intenção
  (`registrar_fotos`, `registrar_textos`, `reprovar`…).

Dependências instaladas: `openpyxl`, `python-dotenv` (task 01); `pyyaml` (task 02, com stub
`types-PyYAML`); `pillow`, `pillow-heif` (task 07 — wheels pré-compiladas confirmadas para
`cp314-win_amd64`, sem toolchain de compilação necessária no Windows); `boto3`, `httpx` (task 08,
com stub `boto3-stubs[s3]` para mypy). A adicionar quando a task correspondente chegar:
`anthropic`, `pydantic`, `jinja2`, `selectolax`.

Convenção de lint: exceções de domínio chamam-se `Erro<Nome>`; a regra ruff `N818` (sufixo
`Error`) está desligada no `pyproject.toml` por isso.

## 11. Configuração e segredos

✅ Implementado (task 01) — spec viva em `docs/specs/configuracao-cli.md`.

`Configuracao` (`config/configuracao.py`, frozen dataclass) é montada por
`Configuracao.do_ambiente()` a partir de variáveis de ambiente: `python-dotenv` carrega o `.env`
do **diretório corrente** (se existir, sem sobrescrever variáveis já definidas); `.env` está no
`.gitignore`; `.env.exemplo` versionado documenta as chaves. Variável ausente ou vazia usa o
padrão; valor não conversível falha com `ErroConfiguracao` nomeando variável e valor.

| Variável | Uso | Padrão |
|---|---|---|
| `ANTHROPIC_API_KEY` | API Anthropic | — (obrigatória para `processar`) |
| `LLM_MODELO_COPYWRITER` / `LLM_MODELO_SEO` / `LLM_MODELO_QA` | modelo por agente | `claude-opus-5` |
| `LLM_EFFORT_COPYWRITER` / `_SEO` / `_QA` | effort | `high` / `medium` / `medium` |
| `LLM_MAX_TENTATIVAS_QA` | retries por grupo | `2` |
| `R2_ACCOUNT_ID`, `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`, `R2_BUCKET` | credenciais R2 | — |
| `R2_URL_PUBLICA` | base das URLs públicas (ex.: `https://bucket.gleite.com`) | — |
| `IMAGEM_LADO_MAX_PX`, `IMAGEM_TAMANHO_MAX_KB` | processamento | `1600`, `500` |
| `PRODUTO_ATIVO` | `S`/`N` (outro valor é erro) | `S` |
| `PESO_KG`, `ALTURA_CM`, `LARGURA_CM`, `COMPRIMENTO_CM` | padrões físicos (`Decimal`) | `0.1`, `4`, `22`, `22` |
| `LOJA_URL` | site público para `verificar` | `https://www.kmilaamodas.com.br` |
| `LOTES_DIR` | raiz dos workspaces | `./lotes` |

Variáveis obrigatórias só são cobradas pelo comando que as usa: `exigir_anthropic()` devolve a
chave ou lança `ErroConfiguracao("ANTHROPIC_API_KEY")`; `exigir_r2()` lança na primeira `R2_*`
ausente. A CLI falha cedo e com mensagem clara se uma variável obrigatória do comando faltar
(tradução de `ErroConfiguracao` em mensagem/código de saída entra com o primeiro comando que
consumir `Configuracao`).

## 12. Testes e evals

- `tests/unit/` espelha `src/`: models e services com **fakes dos ports** (`ClienteLlmFake`
  devolve respostas roteirizadas, `ArmazenamentoImagensEmMemoria`, `CatalogoFotosFake`…).
  Nenhum mock de biblioteca externa.
- `tests/unit/models/test_layout_planilha…` confere as 54 colunas; se
  `docs/brutos/produtos-….xlsx` existir localmente, compara com a exportação real (senão, pula).
- `tests/integration/` (`@pytest.mark.integration`, desligados por padrão): R2 real (bucket de
  teste ou prefixo `testes/`), Anthropic real (1 produto), site público. Rodados manualmente.
- **Fixtures**: `tests/fixtures/lote-piloto/` com planilha de 6–8 produtos (≥ 1 marca sem
  perfil, 1 com várias cores × tamanhos, 1 de cor única, 1 de tamanho único, 1 com erro
  proposital de cor, 1 com GTIN inválido) e fotos pequenas.
- **Evals dos agentes** (`evals/`, fora do `pytest` padrão porque custam dinheiro): golden set
  de ~10 produtos reais com os textos aprovados manualmente hoje (`docs/brutos/` tem os
  exemplos da skill); métricas objetivas (limites, presença da marca, estrutura HTML, palavras
  proibidas) + QA como juiz; relatório por versão de prompt. É o mecanismo para calibrar os
  prompts sem "achismo" — ver task 17.
- Critério de pronto do projeto: o lote piloto roda ponta a ponta, o `.xlsx` importa na loja
  real sem erro, e `verificar` confirma título, meta e imagens de todos os produtos `pronto`.

## 13. Trade-offs avaliados

**Granularidade dos agentes** — por campo (4 geradores) × por grupo (2) × único (1), todos com
QA. Escolhido *por grupo*: mantém a coerência entre título e descrição (mesmo "detalhe
principal") e entre copy e SEO (SEO recebe a copy), permite retry direcionado e modelo/effort
por especialidade; custa uma chamada a mais que a opção única, mitigada por cache.

**Insumos dos prompts** — arquivos no pacote (com/sem Jinja2) × plataforma de prompt management
(Langfuse/Braintrust/PromptLayer) × pasta externa × Agent SDK rodando a skill. Escolhido
*arquivos no pacote + Jinja2*: zero rede, versionado, testável, cache máximo; a plataforma fica
como evolução atrás do port `RepositorioPrompts` se mais pessoas passarem a iterar prompts.

**Nome das fotos por IA × regra** — regra: estável entre execuções, sem acoplar fotos a
textos; perde um pouco de "detalhe principal" no nome, compensado pela marca/tipo/nome do
fornecedor.

**Sequencial × paralelo × Message Batches** — escolhido *sequencial, um produto por vez*: o
entregável é o `.xlsx` do lote inteiro, então "produto pronto cedo" não tem valor; sem thread
pool não há concorrência de rede/rate limit nem logs entrelaçados; ~40 s por produto → 50
produtos ≈ 35 min, aceitável para o volume esperado. Paralelismo por etapa (fotos de todos →
textos de todos, cada etapa com seu pool) é a evolução natural se os lotes chegarem a centenas
de produtos, e é o desenho que permite trocar a etapa de textos por Message Batches (−50%)
mantendo o QA síncrono.

**Visão** — não enviar fotos ao modelo: mais barato, previsível e sem risco de descrever detalhe
que não existe; a descrição se baseia no que a dona da loja informou.

**Validação estrita de cores** — reprova cedo, antes de gastar; o custo é manter a lista mestre
(413 cores hoje). Confirmada como correta pelo spike da task 03 (§14, risco 1 resolvido): a
própria loja rejeita cor fora da lista, inclusive com caixa diferente.

## 14. Riscos e questões em aberto

| # | Risco / dúvida | Mitigação / como resolver |
|---|---|---|
| 1 | ~~A importação cria valores novos de grade (cor)?~~ **Resolvido (task 03):** não cria — a loja rejeita a linha com "Cor não permitida em 'grade-produto-com-uma-cor'. Verifique as cores permitidas em: http://cdn.awsli.com.br/download/cores.html" e não ignora caixa (`beige` ≠ `Beige`). | Validação estrita de `DadosMestre.cor_valida` confirmada como correta, sem mudança. Detalhe em `docs/specs/tasks/03-spike-grade-importacao.md` e `poc/REGISTRO_ITERACOES.md` rodada 3. |
| 2 | Categoria precisa existir no painel; só a formatação é validada. | Relatório lista categorias usadas; aviso quando a categoria não está na lista de referência do `dados_mestre.yaml`. |
| 3 | Busca pública por título pode não localizar a página (slug divergente). | `verificar` tenta slug previsto do título e busca; registra `nao-localizado` sem falhar o lote. |
| 4 | ~~Falha silenciosa de imagem na importação (POC rodada 1).~~ **Mitigado (task 08):** compressão < 500 KB (task 07) + `HEAD` real na URL logo após publicar, antes de contar a foto (`ArmazenamentoImagensR2.existe`, `PipelineFotos.processar`) — falha aborta o produto (`erro-fotos`). | `verificar` (task 18) ainda vai acusar produto sem imagem pós-importação, como camada adicional. |
| 5 | Custo de LLM em lotes grandes. | Cache por marca, ordenação por marca, effort por agente, relatório com custo real; Batches como evolução. |
| 6 | ~~HEIC no Windows depende de `pillow-heif` (roda binário).~~ **Resolvido (task 07):** wheel pré-compilada `pillow_heif-1.7.0-cp314-cp314-win_amd64` existe e foi testada (`pip install --dry-run` + roundtrip real de encode/decode HEIC no `.venv` do projeto, Python 3.14.6) — nenhum toolchain de compilação necessário. | `ProcessadorImagemPillow` registra `pillow_heif.register_heif_opener()` com `try/except ImportError`: se a lib faltar em outro ambiente, `.heic` falha com `ErroProcessamentoImagem` pedindo JPG/PNG/WEBP (fallback ainda ativo, só não foi necessário aqui). |
| 7 | Mudança de layout da exportação da loja (nova grade). | Constante versionada + teste opcional contra exportação nova; task de atualização documentada. |
| 8 | Produto reprovado pelo QA fica fora da planilha (decisão confirmada, §6.2). | Relatório destaca reprovados no topo; CLI encerra com código ≠ 0; `--refazer-textos`/`--incluir-reprovados` para resolver. |
| 9 | Lote grande demora (execução sequencial, ~40 s/produto). | Estado permite interromper e retomar; evolução documentada em §13 (paralelismo por etapa, Batches) quando lotes passarem de centenas. |

## 15. Evolução para serviço web

Adicionar `web/` (FastAPI) ao lado de `cli.py`, reutilizando `config/composicao.py`: um
endpoint recebe planilha + zip de fotos, cria o lote e dispara `ProcessarLote` em background
(mesma classe, mesmo estado em disco ou em object storage); outro endpoint serve `relatorio.json`
e o `.xlsx`. Nenhum service muda — se mudar, o design falhou (regra do `CLAUDE.md`). O estado
por produto em JSON já é o contrato que a UI consumiria.

## 16. Registro de decisões (ADR)

Uma entrada por decisão que **mudou** ou foi **confirmada** depois do desenho inicial. Formato
fixo de quatro linhas; a mais recente por último. Tasks acrescentam entradas aqui quando um
desvio altera uma decisão de arquitetura (não para desvios locais — esses ficam na spec da task).

### ADR-001 — Destino dos produtos reprovados pelo QA (13/09/2026)
- **Contexto:** o fluxo é autônomo; o produto que esgota os ciclos de QA precisava de um destino.
- **Decisão:** fica fora do `.xlsx`, em destaque no relatório, CLI com código ≠ 0;
  `--incluir-reprovados` inclui; só gravidade `alta` reprova; 2 ciclos.
- **Consequência:** nada de qualidade duvidosa vai ao ar sem ação explícita do operador; o
  reprocessamento é por `--refazer-textos <sku>`.
- **Task:** 13, 15.

### ADR-002 — Execução sequencial do lote (13/09/2026)
- **Contexto:** o desenho inicial usava thread pool (`LLM_CONCORRENCIA=4`).
- **Decisão:** um produto por vez, ordenado por marca, sem paralelismo nem async.
- **Consequência:** código e logs simples, cache por marca máximo, ~40 s/produto; paralelismo
  por etapa e Message Batches ficam como evolução para lotes de centenas.
- **Task:** 15.

### ADR-003 — Ciclo spec → código → spec (13/09/2026)
- **Contexto:** este documento descrevia só o alvo; à medida que o código aparecesse, ficaria
  desatualizado.
- **Decisão:** toda task termina gravando spec as-built (`docs/specs/tasks/`), spec viva do
  módulo (`docs/specs/<modulo>.md`), atualizando este documento (marcadores 🔲/✅ e ADRs) e
  commitando automaticamente.
- **Consequência:** `docs/` permanece fonte de verdade do que existe; desvios têm motivo
  registrado; o custo é ~10 minutos de documentação por task.
- **Task:** todas, a partir da 01.

### ADR-004 — Padrões físicos saem de `dados_mestre.yaml`/`DadosMestre` (13/09/2026)
- **Contexto:** a task 02 previa uma seção `padroes_fisicos` no YAML e um campo correspondente
  em `DadosMestre`, mas `Configuracao` (task 01) já expõe `peso_kg`/`altura_cm`/`largura_cm`/
  `comprimento_cm` via `.env` com os mesmos defaults (`0.1`/`4`/`22`/`22`), e o futuro
  `MontadorPlanilha` (task 10) consome `Configuracao`, não `DadosMestre`, para preencher essas
  colunas na planilha de saída.
- **Decisão:** `padroes_fisicos` não entra em `dados_mestre.yaml` nem em `DadosMestre`;
  `Configuracao` continua sendo a única fonte desses valores.
- **Consequência:** dado de configuração operacional fica numa fonte só, sem duplicar/desalinhar
  com o YAML de dados de domínio; `DadosMestre` fica focado em marcas, cores, tamanhos e
  categorias de referência.
- **Task:** 02.

### ADR-005 — `faixa_tamanho` é coluna de entrada, não propriedade derivada (13/09/2026)
- **Contexto:** o desenho inicial (§4) descrevia a faixa de tamanho da família como calculada a
  partir dos tamanhos das variações ("P ao 3", "1 ao 4"), e listava como algo que "não está na
  entrada". Na prática, uma família (`sku-pai`) pode ter variações com tamanhos de **escalas
  diferentes** misturadas (letra P/M/G/GG/XG e número 1/2/3/4/6/8/...), o que inviabiliza
  calcular uma faixa única e correta automaticamente sem uma ordem canônica cruzando as duas
  escalas — informação que a dona da loja já tem e o sistema não.
- **Decisão:** `faixa-tamanho` vira a 14ª coluna da planilha de entrada (nível produto,
  obrigatória, texto livre, ex.: `"P ao G"`), preenchida pela dona da loja. `ProdutoEntrada` não
  tem mais uma property `faixa_tamanho` calculada — é um campo simples, como `marca` ou
  `tipo_peca`. Usada depois na geração de título/descrição (§6). `DadosMestre.tamanhos`
  continua sem ordem (`frozenset[str]`) — não há mais necessidade de ordem canônica cruzando
  escalas.
- **Consequência:** o layout da planilha de entrada passa de 13 para 14 colunas; o gerador do
  modelo (`modelo-entrada`) e o leitor precisam da coluna nova; nenhuma lógica de cálculo de
  faixa é necessária, evitando o caso mal definido de família com escalas misturadas.
- **Task:** 04.

### ADR-006 — Publicação no R2: contrato do port mantido, sem wiring de CLI, TTL fora do código (14/09/2026)
- **Contexto:** a task 08 (escrita em outra sessão) descrevia o port `ArmazenamentoImagens` com
  `publicar(chave, conteudo, content_type)`/`acessivel(url)`, uma flag `--sem-upload` no comando
  `processar`, e listava "limpeza de fotos antigas" como fora de escopo sem explicar por quê. Na
  hora de implementar, isso divergia do que a task 07 já tinha construído e documentado
  (`existe(url)`, sem `content_type`; nenhum wiring de CLI ainda) — três pontos confirmados com o
  usuário antes de codar.
- **Decisão:** (1) o port continua `publicar(chave, dados) -> str` / `existe(url) -> bool`, sem
  renomear nem adicionar `content_type` — `ArmazenamentoImagensR2` fixa `Content-Type:
  image/jpeg` internamente, já que a pipeline só produz JPEG. (2) Nenhuma flag `--sem-upload` nem
  wiring em `config/composicao.py`/`cli.py` nesta task — `processar` continua stub até a task 11;
  a pipeline, quando usada, sempre publica no R2. (3) O TTL de 7 dias das fotos é uma regra de
  lifecycle do bucket R2, configurada fora deste repositório (painel Cloudflare/IaC) — não por
  parâmetro de `put_object`, que não expira objetos no S3/R2.
- **Consequência:** menor ruptura em `PipelineFotos`/`ArmazenamentoImagensDiretorio`/testes já
  existentes; nenhum código morto de CLI para um comando ainda não implementado; "limpeza de
  fotos antigas" permanece fora de escopo do código porque é resolvida por configuração de
  infraestrutura, não por lógica da aplicação.
- **Task:** 08.

### ADR-007 — Port `GeradorTextos` e gerador dummy provisório antes da LLM (14/09/2026)

- **Contexto:** com as tasks 01–08 concluídas (validação, estado, fotos e R2 real), a ordem
  original exigia cinco tasks de LLM (cliente, recursos, três agentes) antes de o `processar`
  existir. O pipeline, a planilha de saída e o estado poderiam ser provados sem IA — a POC já
  importou textos dummy com sucesso — e o custo/risco da LLM ficava no caminho crítico.
- **Decisão:** o seam fica no nível do gerador de textos, não do cliente LLM: port
  `GeradorTextos.gerar(produto, estado) -> TextosProduto` (task 09). A primeira implementação é
  `infra/gerador_textos_dummy.py` (`GeradorTextosDummy`): determinística, sem rede, respeita
  os limites de §6.1 por construção, custo 0, com marca visível de placeholder nos textos.
  O backlog foi reordenado: 09 port+dummy, 10 montador, 11 `processar` (com dummy), 12–16
  LLM (antigas 09–13; a 16 entrega `GeradorTextosIa` e troca o wiring), 17 evals, 18
  `verificar`, 19 piloto.
- **Consequências:** o `processar` fica funcional ao fim da task 11 (marco intermediário:
  planilha importável com fotos reais). O dummy é **provisório**: a task 16 o remove de
  `src/` (vira fake em `tests/` se ainda útil); não há opção de CLI/configuração para
  escolhê-lo — textos dummy nunca devem ir ao ar, e a planilha de prova da task 11 é
  importada e removida da loja. `ProcessarLote` depende só do port, então a troca é apenas
  wiring em `montar_gerador_textos`. `regras_texto.py` continua na task 14 (o dummy não
  valida, garante por construção).
