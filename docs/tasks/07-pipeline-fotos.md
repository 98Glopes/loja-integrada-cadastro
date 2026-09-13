# Task 07 — Pipeline de fotos: nomeação, compressão e seleção

- **Depende de:** 06
- **Modelo recomendado:** sonnet
- **Leia antes:** `docs/ARQUITETURA.md` §5 (inteiro), §10; `poc/REGISTRO_ITERACOES.md`
  (falha transitória de imagem)

## Objetivo

Transformar as fotos brutas do celular em JPEGs leves, com nome SEO determinístico, prontos
para publicação, e escolher quais 5 vão para o produto pai. Nesta task o "armazenamento" é
o diretório `fotos-processadas/` do workspace; o R2 entra na task 08.

## Escopo

1. `models/slug.py`: função `slugificar(texto) -> str` (minúsculas, sem acento, `[a-z0-9-]`,
   hífens únicos, sem hífen nas pontas). Reutilizada por SKU de filha, nome de foto e slug de
   título.
2. `models/foto_produto.py`: `FotoProduto` (frozen): `sku_pai`, `cor`, `ordem`,
   `arquivo_origem`, `nome`, `chave` (`produtos/<sku-pai>/<nome>`), `url: str | None`,
   `bytes: int | None`.
3. `models/nomeador_fotos.py` (puro): `NomeadorFotos.nomear(produto, cor, ordem) -> str`
   conforme §5.2 (marca-tipo-nome-fornecedor-cor-n, dedupe de tokens do tipo, truncar em 60
   antes de `-<cor>-<n>`, extensão `.jpg`). E `SeletorImagensPai.selecionar(fotos) -> list`
   (round-robin por cor na ordem da planilha, máx. 5).
4. `services/ports/processador_imagem.py`: `ProcessadorImagem` (Protocol):
   `preparar(origem: Path) -> bytes`.
   `infra/processador_imagem_pillow.py`: Pillow + `pillow-heif`; orientação EXIF; RGB;
   lado maior ≤ `IMAGEM_LADO_MAX_PX`; JPEG progressivo sem EXIF; qualidade 85 → 60 em passos
   de 5 até `< IMAGEM_TAMANHO_MAX_KB`, depois reduz para 1200 px; erro → `ErroProcessamentoImagem`.
5. `services/pipeline_fotos.py`: `PipelineFotos(catalogo, processador, armazenamento)` com
   `processar(produto) -> list[FotoProduto]`: lista, nomeia, prepara, grava a cópia local
   (via port `ArmazenamentoImagens` — nesta task, implementação
   `infra/armazenamento_imagens_diretorio.py` que escreve em `fotos-processadas/` e devolve
   uma URL `file://`), e escolhe as imagens do pai. Registra no `EstadoProduto`
   (`registrar_fotos`).
6. `pyproject.toml`: `pillow`, `pillow-heif`.
7. Testes: nomeador (tabela de casos incluindo truncamento e dedupe), seletor (2 cores × 4
   fotos → ordem esperada), processador com imagem gerada em teste (3000×4000 → ≤ 1600 e
   < 500 KB; PNG e HEIC se `pillow-heif` disponível), pipeline com fakes.

## Fora do escopo

R2 (task 08).

## Critério de aceite

- Rodar o pipeline sobre `poc/fotos_input/` (3000×4000, ~1,8 MB) produz JPEGs ≤ 1600 px e
  < 500 KB sem EXIF, com os nomes previstos em §5.2.
- Lint, mypy e pytest passam.
