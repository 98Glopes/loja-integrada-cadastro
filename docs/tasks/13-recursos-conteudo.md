# Task 13 — Recursos de conteúdo: loja, marcas, copy, SEO e QA

- **Depende de:** 12
- **Modelo recomendado:** opus
- **Leia antes:** `docs/ARQUITETURA.md` §6.1, §6.4; `docs/brutos/SKILL.md` (inteiro);
  `docs/brutos/brand_profiles.md` (inteiro); `docs/brutos/dados_mestre.md` §1–2;
  `docs/regras-planilha-loja-integrada.md` §4 (o que a POC mudou na skill).
  Para o SEO: explorar
  https://developers.google.com/search/docs/fundamentals/seo-starter-guide?hl=pt-br e as
  páginas que ele linka sobre `<title>`, meta description e imagens.

## Objetivo

Converter o conhecimento hoje espalhado na skill e nos perfis de marca em recursos
versionados do pacote, já corrigidos pelas descobertas da POC, escritos como texto que o
modelo lê (prosa clara, sem formatação de "entrega para copiar e colar").

## Escopo

Criar em `src/loja_integrada_cadastro/recursos/`:

1. `loja.md` — posicionamento da Kmilaa Modas (o que é, para quem, promessa, tom, Big Idea,
   diferenciais permitidos: 3x sem juros, frete grátis SP, entrega Brasil, retirada em
   Sorocaba, WhatsApp). Grafia oficial "Kmilaa Modas".
2. `copy.md` — regras do Copywriter: escrever para a mãe; fórmula e limite do título (68);
   estrutura HTML obrigatória da descrição (h2, p, p, ul, h3 "Sobre a [Marca]", h3 "Compre na
   Kmilaa Modas" com o parágrafo fixo), tags permitidas; mínimo 120 palavras; característica →
   benefício (tabela da skill); o que nunca escrever (adjetivos vazios, clichês, texto igual
   entre marcas); não repetir o título na abertura; não inventar atributo que não esteja nos
   dados do produto. **Remover** URL e nome de fotos (não são mais gerados pela IA).
3. `seo.md` — regras do agente SEO e do validador de regra: tag title ≤ 60 caracteres,
   específica, com tipo + marca + detalhe/tamanho, **sem** `| Kmilaa Modas` (a loja anexa
   sufixo); meta description 140–155 com benefício + marca + CTA; sem keyword stuffing;
   headings semânticos; conteúdo original; lista de adjetivos/clichês proibidos (usada também
   pelo validador de regra). Citar a fonte (Google SEO Starter Guide) e a data de consulta.
4. `qa.md` — checklist do revisor com critérios objetivos e gravidade (`alta` reprova,
   `baixa` observa): fato não presente nos dados de entrada; tom fora do perfil da marca;
   promessa que a loja não faz; erro de português; campo genérico/intercambiável entre
   produtos; estrutura HTML fora do padrão; título sem marca; palavra proibida.
5. `marcas/<slug>.md` para as 9 marcas de `brand_profiles.md` (posicionamento, promessa,
   atributos que não podem faltar, tom, palavras-chave, Big Idea) e `marcas/_generico.md`
   (usa o posicionamento da loja). Nome do arquivo = slug da marca canônica
   (`kiki.md`, `onda-marinha.md`, `coloritta.md`, `luc-boo.md`…).
6. `CarregadorRecursos` (task 02) ganha `perfil_marca(marca_canonica) -> str` (cai em
   `_generico.md` e sinaliza que é genérico) e `texto("loja"|"copy"|"seo"|"qa")`.
7. Testes: todos os arquivos carregam; cada marca do `dados_mestre.yaml` (exceto proibidas)
   tem perfil ou cai no genérico; `seo.md` contém a lista de palavras proibidas em um bloco
   parseável (ex.: seção com lista Markdown) e o carregador expõe
   `palavras_proibidas() -> frozenset[str]`.

## Fora do escopo

Templates `.j2` e agentes (tasks 14–16).

## Critério de aceite

- Revisão de conteúdo: nenhum recurso pede URL, nome de foto ou sufixo `| Kmilaa Modas`;
  limites batem com `ARQUITETURA.md` §6.1.
- `CarregadorRecursos().perfil_marca("Menina Anjo")` devolve o perfil correto;
  `perfil_marca("Kyly")` idem; marca inexistente → genérico + flag.
- Lint, mypy e pytest passam.
