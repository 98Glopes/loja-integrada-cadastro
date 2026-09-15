# Task 02 — Dados mestre e carregador de recursos

- **Depende de:** 01
- **Modelo recomendado:** sonnet
- **Leia antes:** `docs/ARQUITETURA.md` §4 (colunas), §6.4 (recursos), §10;
  `docs/brutos/dados_mestre.md` (grafias e categorias); `docs/regras-planilha-loja-integrada.md`
  §2 (colunas 41 e 54)

## Objetivo

Versionar no pacote a lista mestre que o validador e os prompts usam: marcas canônicas com
aliases, cores da grade, tamanhos, categorias de referência e padrões físicos — extraída da
exportação real, não digitada à mão.

## Escopo

1. `scripts/extrair_dados_mestre.py` (fora do pacote, ferramenta de desenvolvedor): lê uma
   exportação da loja (`docs/brutos/produtos-*.xlsx`) e atualiza as seções `cores`,
   `tamanhos` e `categorias_referencia` de `recursos/dados_mestre.yaml`, preservando as
   seções editadas à mão (`marcas`, `padroes_fisicos`). Ordena cores por frequência
   decrescente e registra a contagem (`uso`).
2. `src/loja_integrada_cadastro/recursos/dados_mestre.yaml` gerado, com:
   - `marcas`: canônica + `aliases` (ex.: `kiki`: `[Kiki, Kiki Xodó, KIKI]`; `Colorittá`:
     `[Coloritta, colorittá]`; `Luc.boo`: `[Lucboo, Luc boo]`) + `proibidas`: `Açucena`,
     `Abrange`, cada uma com motivo (texto de `docs/brutos/dados_mestre.md` §2).
   - `cores`: as 413 grafias exatas observadas em `grade-produto-com-uma-cor`.
   - `tamanhos`: `P M G GG XG 1 2 3 4 6 8 10 12 14 16 18 20`.
   - `categorias_referencia`: os 46 caminhos observados (apenas referência/aviso).
   - `padroes_fisicos`: peso 0.1, altura 4, largura 22, comprimento 22.
3. `models/dados_mestre.py`: `@dataclass(frozen=True) DadosMestre` com métodos de intenção:
   `marca_canonica(texto) -> str | None`, `motivo_marca_proibida(texto) -> str | None`,
   `cor_valida(texto) -> bool`, `tamanho_valido(texto) -> bool`,
   `categoria_conhecida(caminho) -> bool`. Comparações de marca ignoram caixa/acento; cor e
   tamanho são **exatos** (decisão estrita — pode ser revista após a task 03).
4. `infra/carregador_recursos.py`: `CarregadorRecursos` que lê arquivos de `recursos/` via
   `importlib.resources` (`texto(nome)` e `dados_mestre()`), validando o YAML ao montar o
   dataclass (campo faltante → `ErroRecursos`, exceção nova em `models/exceptions/`).
5. `pyproject.toml`: `pyyaml`, `types-PyYAML`; incluir `recursos/**` em `package-data`.
6. Testes unitários do `DadosMestre` (aliases, proibidas, cor exata vs. caixa diferente) e
   do carregador (o YAML real do pacote carrega; YAML sem seção falha com mensagem clara).

## Fora do escopo

Prompts e perfis de marca em Markdown (task 13), validador (task 05).

## Critério de aceite

- `python scripts/extrair_dados_mestre.py docs/brutos/produtos-*.xlsx` regenera o YAML sem
  perder as seções manuais (rodar duas vezes produz o mesmo arquivo).
- `CarregadorRecursos().dados_mestre().cor_valida("Cinza Claro")` é `True`; `"cinza claro"` é
  `False`; `marca_canonica("Kiki Xodó") == "kiki"`; `motivo_marca_proibida("Açucena")`
  retorna texto.
- Lint, mypy e pytest passam.
