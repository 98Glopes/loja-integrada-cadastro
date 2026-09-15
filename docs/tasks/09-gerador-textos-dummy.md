# Task 09 — Port `GeradorTextos`, `TextosProduto` e gerador dummy

- **Depende de:** 06
- **Modelo recomendado:** sonnet
- **Leia antes:** `docs/ARQUITETURA.md` §6.1 (limites dos 4 campos), §6.2 (só o contrato de
  saída — a topologia de agentes é das tasks 12–16), §8, §10, ADR-007; `docs/specs/estado-lote.md`
  (`registrar_textos`, `registrar_tentativa`); `poc/gerar_planilha_poc.py` (textos dummy que a
  loja já importou com sucesso — referência de formato, não copiar)

## Objetivo

Criar o seam entre o pipeline e a geração de textos — o port `GeradorTextos` — com uma
implementação **determinística e sem rede** que permita rodar `processar` ponta a ponta
(fotos reais no R2, planilha importável) antes de existir qualquer integração com LLM. A
orquestração de IA (task 16) implementa o mesmo port e substitui esta na composição.

## Escopo

1. `models/textos_produto.py`: `TextosProduto` (frozen) com `titulo`, `descricao_html`,
   `seo_tag_title`, `seo_tag_description` e `como_mapa() -> Mapping[str, str]` (chaves iguais
   aos nomes dos campos) — é o que vai para `EstadoProduto.registrar_textos` e, depois, para
   as colunas `nome`, `descricao-completa`, `seo-tag-title`, `seo-tag-description`.
2. `services/ports/gerador_textos.py`: `GeradorTextos` (Protocol) —
   `gerar(produto: ProdutoEntrada, estado: EstadoProduto) -> TextosProduto`. Assinatura
   idêntica à que a task 16 vai implementar (`GeradorTextosIa`), para a troca ser só wiring.
   O gerador registra as próprias tentativas no `estado` (`registrar_tentativa`); quem chama
   registra o resultado (`registrar_textos`).
3. `infra/gerador_textos_dummy.py`: `GeradorTextosDummy(dados_mestre)` — deriva os 4 campos
   dos dados do produto (tipo, marca canônica, detalhe principal de `detalhes`, faixa de
   tamanho, composição), respeitando §6.1 **por construção**:
   - título `[Tipo] [Marca] [detalhe] [faixa]` ≤ 68 caracteres (trunca o detalhe, nunca a
     marca nem a faixa);
   - descrição HTML com a estrutura obrigatória `h2 → p → p → ul → h3 Sobre a [Marca] →
     h3 Compre na Kmilaa Modas`, só tags `h2 h3 p ul li strong`, ≥ 120 palavras;
   - tag title ≤ 60, com marca e tipo, **sem** sufixo `| Kmilaa Modas`;
   - meta description entre 140 e 155 caracteres (preencher/cortar de forma determinística).
   - Marca visível de placeholder nos textos (ex.: `[DUMMY]` no início do `h2` e da meta),
     para que uma planilha gerada com o dummy nunca vá ao ar por engano — confirmar a forma
     com o usuário no início da sessão.
   - Registra uma `tentativa` no estado com `agente="dummy"`, `tentativa=1`, `modelo="dummy"`,
     uso zerado e custo `Decimal("0")`.
4. `config/composicao.py`: `montar_gerador_textos(configuracao) -> GeradorTextos` devolvendo
   o dummy (única implementação até a task 16).
5. Testes:
   - para **todos** os produtos da fixture `lote-piloto`, os 4 campos respeitam os limites de
     §6.1 (asserções explícitas de tamanho, estrutura de tags e contagem de palavras);
   - determinismo: mesma entrada → mesmo `TextosProduto`;
   - `como_mapa()` → `registrar_textos` → round-trip pelo `RepositorioEstadoLoteJson`;
   - o estado recebe exatamente uma tentativa, custo 0.

## Fora do escopo

`models/regras_texto.py` (validador de regra reutilizável — task 14), prompts, recursos de
conteúdo, qualquer chamada de LLM. O dummy garante os limites por construção, não valida.

## Provisoriedade (ler antes de estender)

`GeradorTextosDummy` é **provisório**: existe para provar o pipeline e a planilha antes do
custo/risco da LLM. A task 16 troca `montar_gerador_textos` para `GeradorTextosIa` e tira o
dummy de `infra/` — vira fake em `tests/` se o teste do `ProcessarLote` ainda precisar dele, ou
é apagado. Não adicionar opção de CLI nem configuração para escolhê-lo.

## Critério de aceite

- Para os 6 produtos da fixture `tests/fixtures/lote-piloto`, `GeradorTextosDummy.gerar`
  devolve textos que passam nos limites de §6.1.
- Lint, mypy e pytest passam.
