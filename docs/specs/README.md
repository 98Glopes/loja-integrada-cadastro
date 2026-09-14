# Specs — o que existe de verdade

`docs/ARQUITETURA.md` diz o que o sistema **deve** ser; esta pasta diz o que ele **é**. Cada
task, ao terminar (ciclo spec → código → spec do `CLAUDE.md`), grava aqui:

- `tasks/NN-<nome>.md` — **spec as-built da task**: registro histórico do que aquela task
  entregou, com desvios em relação ao pedido.
- `<modulo>.md` — **spec viva do módulo**: estado atual de cada parte do sistema, reescrita
  por toda task que a toca. É o documento que a próxima task lê antes de codar.

Regras: descrever o que existe (assinaturas, nomes de arquivo, comandos que rodam), não a
intenção; nada entra como implementado sem teste passando; "Desvios e decisões" nunca fica em
branco.

## Mapa de módulos

| Módulo (`docs/specs/<modulo>.md`) | Cobre (§10 da arquitetura) | Tasks | Spec |
|---|---|---|---|
| `configuracao-cli` | `config/configuracao.py`, `config/leitor_ambiente.py`, `cli.py`, `.env.exemplo`, subcomandos | 01, 15, 17 | [spec](configuracao-cli.md) |
| `dados-mestre-recursos` | `models/dados_mestre.py`, `infra/carregador_recursos.py`, `recursos/dados_mestre.yaml`, `scripts/extrair_dados_mestre.py` | 02 | [spec](dados-mestre-recursos.md) |
| `planilha-entrada` | `models/produto_entrada.py`, `variacao_entrada.py`, port `LeitorPlanilhaEntrada`, leitor e gerador de modelo openpyxl | 04 | [spec](planilha-entrada.md) |
| `validacao` | `services/validador_entrada.py`, `models/resultado_validacao.py`, port `CatalogoFotos` e implementação em diretório | 05 | [spec](validacao.md) |
| `estado-lote` | `models/estado_produto.py`, `status_produto.py`, port `RepositorioEstadoLote`, implementação JSON, política de reexecução | 06 | — |
| `fotos` | `models/slug.py`, `foto_produto.py`, `nomeador_fotos.py`, port `ProcessadorImagem` (Pillow), `services/pipeline_fotos.py` | 07 | — |
| `armazenamento-r2` | port `ArmazenamentoImagens`, `infra/armazenamento_imagens_r2.py` (+ diretório) | 07, 08 | — |
| `llm-cliente-prompts` | ports `ClienteLlm` e `RepositorioPrompts`, `infra/cliente_llm_anthropic.py`, `esquemas_llm.py`, `repositorio_prompts_jinja.py`, `recursos/precos_llm.yaml` | 09 | — |
| `agentes-textos` | `recursos/{loja,copy,seo,qa}.md`, `recursos/marcas/`, `recursos/prompts/*.j2`, `models/regras_texto.py`, agentes Copywriter/SEO/QA, `services/gerador_textos.py` | 10, 11, 12, 13 | — |
| `planilha-saida` | `models/layout_planilha_loja_integrada.py`, `linha_planilha.py`, `services/montador_planilha.py`, port `EscritorPlanilhaSaida` | 14 | — |
| `processamento-lote-relatorio` | `services/processador_lote.py`, `gerador_relatorio.py`, subcomando `processar` | 15 | — |
| `verificacao-pos-importacao` | port `ConsultaLoja`, `infra/consulta_loja_http.py`, `services/verificador_importacao.py`, subcomando `verificar` | 17 | — |
| `evals` | `evals/` (casos, `rodar.py`, `REGISTRO.md`) | 16 | — |

A coluna "Spec" recebe o link quando o arquivo existir. Se uma task precisar de um módulo
fora deste mapa, adiciona a linha aqui.

## Template — spec as-built de task (`tasks/NN-<nome>.md`)

```markdown
# Spec as-built — Task NN: <nome>

- **Data:** AAAA-MM-DD · **Task:** `docs/tasks/NN-<nome>.md` · **Módulos:** `<modulo>`, …

## Entregue
<3–6 linhas: o comportamento observável que passou a existir. Comandos que rodam.>

## Arquivos
| Camada | Criados | Alterados |
|---|---|---|
| models / services / ports / infra / config / cli / recursos / scripts / tests | … | … |

## Contratos
<Assinaturas reais: ports (Protocol + métodos), dataclasses (campos e tipos), subcomandos e
argumentos, variáveis de ambiente, exceções de domínio.>

## Regras de negócio implementadas
- <uma por linha, verificável por teste>

## Desvios e decisões
| Pedido (task/arquitetura) | Feito | Motivo |
|---|---|---|
| … | … | … |
<"nenhum" se não houver. Mudança de decisão de arquitetura → também ADR em ARQUITETURA.md §16.>

## Verificação executada
- `ruff check . && ruff format --check . && mypy src && pytest` → <resultado>
- <testes de integração/manuais rodados, com resultado>

## Pendências para tasks futuras
- <o que ficou de fora e em qual task entra>
```

## Template — spec viva de módulo (`<modulo>.md`)

```markdown
# Módulo: <nome>

**Responsabilidade:** <uma frase.>
**Estado:** implementado pelas tasks NN, NN · última atualização AAAA-MM-DD (task NN)

## Arquivos
<lista por camada, caminhos reais>

## Contratos
<ports, models, subcomandos, variáveis de ambiente, exceções — como estão no código>

## Comportamento
<fluxo, regras de negócio, tratamento de erros, defaults>

## Limites
<o que o módulo não faz de propósito e quem faz>

## Testes
<arquivos de teste e o que cobrem; fakes disponíveis para outros módulos>

## Histórico
- Task NN (AAAA-MM-DD): <uma linha do que mudou>
```
