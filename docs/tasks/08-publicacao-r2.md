# Task 08 — Publicação no Cloudflare R2

- **Depende de:** 07
- **Modelo recomendado:** sonnet
- **Leia antes:** `docs/ARQUITETURA.md` §5.3, §11 (variáveis `R2_*`), §12 (integração)

## Objetivo

Publicar os JPEGs processados no bucket R2 com a chave `produtos/<sku-pai>/<nome>.jpg`,
obter a URL pública e confirmar que ela responde — a URL só entra na planilha depois disso.

## Escopo

1. `services/ports/armazenamento_imagens.py` (já existe da task 07; confirmar contrato):
   `publicar(chave, conteudo: bytes, content_type) -> str` (URL pública) e
   `acessivel(url) -> bool` (HEAD 200 + `image/jpeg`).
2. `infra/armazenamento_imagens_r2.py`: `ArmazenamentoImagensR2` com `boto3` (`endpoint_url
   = https://<R2_ACCOUNT_ID>.r2.cloudflarestorage.com`, região `auto`), `put_object` com
   `ContentType` e `CacheControl: public, max-age=31536000`, sempre sobrescrevendo. URL =
   `R2_URL_PUBLICA + "/" + chave`. `acessivel` usa `httpx.head`. Erros de boto/httpx →
   `ErroPublicacaoImagem` com a chave no texto.
3. `PipelineFotos`: após publicar, chamar `acessivel(url)`; falha → `ErroPublicacaoImagem`
   (produto fica `erro-fotos`; reexecução tenta de novo).
4. `config/composicao.py`: escolher `ArmazenamentoImagensR2` quando `R2_*` estiver
   configurado; manter o de diretório para testes/`--sem-upload` (flag opcional do
   `processar`, útil para ensaiar um lote sem publicar).
5. `pyproject.toml`: `boto3`, `boto3-stubs[s3]`, `httpx`.
6. Testes: unitários com fake do port (já existem) e **integração**
   (`@pytest.mark.integration`) que publica um JPEG pequeno em `testes/<uuid>.jpg`, confere
   `acessivel`, e apaga ao final. Documentar no README de `tests/integration/` como rodar
   (`pytest -m integration`).

## Fora do escopo

Limpeza/remoção de fotos antigas no bucket (não requisitada).

## Critério de aceite

- Teste de integração passa contra o bucket real com o `.env` do desenvolvedor.
- Pipeline de fotos ponta a ponta sobre a fixture do lote piloto deixa `EstadoProduto.fotos`
  com URLs `https://` que respondem 200.
- Lint, mypy e pytest (unitários) passam.
