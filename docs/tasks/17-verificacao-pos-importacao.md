# Task 17 — Verificação pós-importação e comando `verificar`

- **Depende de:** 15
- **Modelo recomendado:** sonnet
- **Leia antes:** `docs/ARQUITETURA.md` §9, §14 riscos 3 e 4; `poc/REGISTRO_ITERACOES.md`
  (o que foi conferido no HTML público na POC: `<title>`, meta, CDN, `grades = [...]`,
  `/marca/<slug>`); `poc/saida/*.html` se existirem localmente (páginas reais capturadas)

## Objetivo

Depois que o desenvolvedor importa o `.xlsx` no painel, confirmar automaticamente, pelo site
público, que cada produto está no ar com título, meta description, imagens e grades — e
apontar os que precisam de correção manual.

## Escopo

1. `models/pagina_produto.py`: `PaginaProduto` (frozen: `url`, `title`, `meta_description`,
   `imagens_cdn: tuple[str, ...]`, `tem_grade_cor`, `tem_grade_tamanho`, `marca_slug`).
   `models/resultado_verificacao.py`: `ResultadoVerificacao` por produto (`localizado`,
   `title_ok`, `meta_ok`, `imagens_esperadas/encontradas`, `grades_ok`, `marca_ok`,
   `problemas`).
2. `services/ports/consulta_loja.py`: `ConsultaLoja` (Protocol): `buscar(termo) ->
   list[str]` (URLs de produto) e `pagina(url) -> PaginaProduto | None` (None em 404).
   `infra/consulta_loja_http.py`: `httpx` + `selectolax`; seletores baseados nas páginas
   reais; User-Agent identificando o sistema; timeout; erros → `ErroConsultaLoja`.
3. `services/verificador_importacao.py`: `VerificarImportacao(consulta, repositorio_estado,
   relogio)` com `executar(lote, esperar) -> list[ResultadoVerificacao]`: para cada
   `pronto`, tenta a URL prevista (`LOJA_URL/<slug do título>`), senão busca pelo título;
   retry com backoff até `esperar` para 404; compara com o estado (`seo_tag_title` como
   prefixo do `<title>`, meta exata, nº de imagens = `len(imagens_pai)`, grades, marca);
   grava `registrar_verificacao` e acrescenta seção ao `relatorio.md`/`.json`.
4. `cli.py`: `verificar --lote [--esperar 5m]`; código de saída 1 se algum produto não
   localizado ou sem imagem.
5. Testes: verificador com `ConsultaLojaFake` (404 → depois 200; sem imagem; meta divergente);
   parser HTML com um arquivo de página real reduzido em `tests/fixtures/`.
   Integração (`@pytest.mark.integration`): consulta um produto `POC-*` ainda existente na
   loja ou um produto real conhecido.

## Critério de aceite

- Após importar o lote piloto na loja real, `verificar --lote <lote>` localiza todos os
  produtos, confirma `<title>`/meta/imagens e o relatório recebe a seção de verificação.
- Um produto sem imagem (simulado no fake) aparece em destaque com a orientação de correção
  manual.
- Lint, mypy e pytest passam.
