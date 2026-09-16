# Módulo: geracao-textos

**Responsabilidade:** produzir os 4 campos de texto de um produto (título, descrição HTML, tag
title, meta description) atrás de um único port, para o pipeline não conhecer se o texto veio
de um gerador dummy ou de LLM.
**Estado:** implementado pela task 09 · última atualização 2026-09-16 (consumido pela task 11,
sem mudança de contrato)

## Arquivos

- `models/textos_produto.py` — `TextosProduto`
- `services/ports/gerador_textos.py` — `GeradorTextos` (Protocol)
- `infra/gerador_textos_dummy.py` — `GeradorTextosDummy` (provisório, ADR-007 — sai na task 16)
- `config/composicao.py` — `montar_gerador_textos`

## Contratos

```python
# models/textos_produto.py
@dataclass(frozen=True)
class TextosProduto:
    titulo: str
    descricao_html: str
    seo_tag_title: str
    seo_tag_description: str

    def como_mapa(self) -> Mapping[str, str]: ...


# services/ports/gerador_textos.py
class GeradorTextos(Protocol):
    def gerar(self, produto: ProdutoEntrada, estado: EstadoProduto) -> TextosProduto: ...


# infra/gerador_textos_dummy.py
class GeradorTextosDummy:
    def __init__(self, dados_mestre: DadosMestre) -> None: ...
    def gerar(self, produto: ProdutoEntrada, estado: EstadoProduto) -> TextosProduto: ...


# config/composicao.py
def montar_gerador_textos(configuracao: Configuracao) -> GeradorTextos: ...
```

## Comportamento

`GeradorTextosDummy.gerar` deriva os 4 campos só de `produto` (mais `DadosMestre` para a
grafia canônica da marca) — não olha `estado.entrada` nem histórico, e nunca lança. Garante os
limites de `docs/ARQUITETURA.md` §6.1 **por construção**:

- **Título**: `[DUMMY] {tipo_peca} {marca} {detalhe} {faixa_tamanho}`, ≤ 68 caracteres. O
  orçamento de caracteres do detalhe é calculado subtraindo do limite o tamanho de todas as
  partes fixas; truncamento em fronteira de palavra (função privada `_truncar_em_palavra`),
  nunca corta `tipo_peca`/`marca`/`faixa_tamanho`.
- **Descrição HTML**: estrutura fixa `h2 (com [DUMMY]) → p → p → ul(4 li) → h3 "Sobre a
  {marca}" → p → h3 "Compre na Kmilaa Modas" → p`, só tags `h2 h3 p ul li`. Se a contagem de
  palavras (sem tags) ficar abaixo de 120, `_garantir_minimo_de_palavras` acrescenta frases
  fixas determinísticas ao 2º parágrafo até bater o mínimo.
- **Tag title**: `{tipo_peca} {marca} {detalhe}`, ≤ 60 caracteres, sem `[DUMMY]` e sem sufixo
  `| Kmilaa Modas`; mesmo truncamento em fronteira de palavra do detalhe.
- **Meta description**: `[DUMMY] {tipo_peca} {marca}, {composição}. {CTA fixo}`, ajustada para
  ficar entre 140 e 155 caracteres — completa com um sufixo fixo se curta, corta em fronteira
  de palavra se longa.
- **Marca**: `dados_mestre.marca_canonica(produto.marca)`; se `None`, usa `produto.marca` bruto
  (grafia literal — sem title-case, mesmo quando a canônica é minúscula, ex. `kiki`/`somnii`).
- **Detalhe principal**: primeiro segmento de `produto.detalhes` antes da primeira vírgula.

Cada chamada de `gerar` registra exatamente uma tentativa em `estado`
(`estado.registrar_tentativa`) com `agente="dummy"`, `tentativa=1`, `modelo="dummy"`, `usage`
zerado (4 chaves: `input_tokens`, `output_tokens`, `cache_read_tokens`, `cache_write_tokens`),
`veredito_regra`/`veredito_qa`/`request_id` como `None`, `em` como timestamp ISO 8601 UTC, e
custo `Decimal("0")` — não muda o status do produto (exige `estado` em `fotos-publicadas` ou
`erro-llm`, ver `docs/specs/estado-lote.md`). Quem chama `gerar` é responsável por
`estado.registrar_textos(textos.como_mapa())` — o gerador não faz isso sozinho.

`montar_gerador_textos(configuracao)` (composition root) monta `DadosMestre` via
`CarregadorRecursos` e devolve `GeradorTextosDummy(dados_mestre)`; `configuracao` não é usado
pelo dummy (existe só para a assinatura já ficar estável para a task 16).

## Limites

- Não valida os 4 campos contra regras reutilizáveis — isso é `models/regras_texto.py`, task
  14. O dummy garante os limites pela forma como monta o texto, não checando depois.
- Provisório (ADR-007): `GeradorTextosDummy` sai de `infra/` na task 16, quando
  `GeradorTextosIa` assume `montar_gerador_textos`. Sem opção de CLI/configuração para
  escolher o dummy.
- Não sabe nada de custo real, tokens de LLM ou retry — o `usage`/`custo_usd` que registra é
  sempre zero.
- `TextosProduto` não valida seus próprios campos (é um `frozen dataclass` simples); quem
  garante os limites é quem constrói (`GeradorTextosDummy` hoje; `GeradorTextosIa` + validação
  de regra depois).

## Testes

- `tests/unit/models/test_textos_produto.py` — `como_mapa()` devolve as 4 chaves certas.
- `tests/unit/infra/test_gerador_textos_dummy.py` — parametrizado sobre os 6 produtos de
  `tests/fixtures/lote-piloto` (lidos com `LeitorPlanilhaEntradaOpenpyxl`, `DadosMestre` real
  do pacote): limites de título/descrição/tag title/meta description, ordem dos `h3` finais,
  determinismo, exatamente uma tentativa com custo 0, round-trip
  `como_mapa()` → `registrar_textos` → `RepositorioEstadoLoteJson`.
- `tests/unit/config/test_composicao.py` — `montar_gerador_textos` devolve `GeradorTextosDummy`.
- Nenhum fake de `GeradorTextos` extraído para um módulo compartilhado — `_GeradorTextosFake`
  de `tests/unit/services/test_processador_lote.py` (task 11) é local ao arquivo de teste.

## Histórico

- Task 09 (2026-09-14): criação do módulo — `TextosProduto`, `GeradorTextos`,
  `GeradorTextosDummy`, `montar_gerador_textos`. Ver "Desvios e decisões" na spec as-built
  (`docs/specs/tasks/09-gerador-textos-dummy.md`) para os pontos confirmados com o usuário
  (placeholder também no título, marca literal, estrutura da descrição com `p` após cada
  `h3`).
- Task 11 (2026-09-16): primeiro consumidor real — `ProcessarLote` chama
  `gerador_textos.gerar(estado.entrada, estado)` e `estado.registrar_textos(textos.como_mapa())`
  na etapa de textos do laço por produto. Nenhuma mudança de contrato neste módulo.
