# Task 14 — Montador da planilha de saída (Loja Integrada)

- **Depende de:** 06 (pode ser feita em paralelo às tasks 07–13)
- **Modelo recomendado:** sonnet
- **Leia antes:** `docs/regras-planilha-loja-integrada.md` (inteiro — fonte de verdade do
  formato); `docs/ARQUITETURA.md` §7; `poc/gerar_planilha_poc.py` (lógica validada, a
  reaproveitar sem copiar os dummies)

## Objetivo

Transformar um `EstadoProduto` pronto (entrada normalizada + textos + URLs de imagem) nas
linhas pai/filhas no layout exato de 54 colunas, e gravar o `.xlsx` que a loja importa.

## Escopo

1. `models/layout_planilha_loja_integrada.py`: constante `COLUNAS` (tupla com os 54 nomes na
   ordem da exportação real) e conjunto das colunas que a Kmilaa preenche.
2. `models/linha_planilha.py`: `LinhaPlanilha` (frozen) com `valores: Mapping[str, object]`
   restrito a colunas do layout (validação no `__post_init__`) e `tipo`.
3. `services/montador_planilha.py`: `MontadorPlanilha(padroes_fisicos, ativo)` com
   `montar(estado) -> list[LinhaPlanilha]`: pai conforme §7 (categoria em níveis, imagens
   1–5, marca canônica, textos), filhas por variação na ordem da planilha de entrada com
   `sku = <sku-pai>-<slug cor>-<slug tamanho>`, `gtin`, preço (`Decimal` → float com ponto),
   estoque, padrões físicos, grades; e `montar_lote(estados, incluir_reprovados) ->
   list[LinhaPlanilha]` (filtra `pronto`, opcionalmente `reprovado-qa`).
4. `services/ports/escritor_planilha_saida.py` + `infra/escritor_planilha_saida_openpyxl.py`:
   uma aba `Sheet1`, cabeçalho = `COLUNAS`, células numéricas para preço/estoque/peso/
   dimensões, texto para o resto; erro se > 9.997 linhas.
5. Testes: montador com estado construído no teste (2 cores × 3 tamanhos → 1 pai + 6 filhas,
   valores exatos coluna a coluna, incluindo GTIN); layout tem 54 colunas; teste opcional
   que compara `COLUNAS` com a linha 1 de `docs/brutos/produtos-*.xlsx` se o arquivo existir
   (`pytest.skip` caso contrário); escritor em `tmp_path` relido com openpyxl.
6. Atualizar `docs/regras-planilha-loja-integrada.md` §2 (col. 9 `gtin`: **F, obrigatória,
   informada na entrada**) e §5.

## Critério de aceite

- Para o estado de um produto da fixture, a planilha gerada é idêntica, exceto pelos valores
  de negócio, à estrutura que a POC importou com sucesso (mesmos cabeçalhos, mesmas colunas
  preenchidas por tipo de linha).
- Lint, mypy e pytest passam.
