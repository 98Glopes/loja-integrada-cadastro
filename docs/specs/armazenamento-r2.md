# Módulo: armazenamento-r2

**Responsabilidade:** publicar o JPEG final de uma foto sob uma chave (`produtos/<sku-pai>/
<nome>`) e confirmar que a URL resultante está acessível.
**Estado:** port e implementação local em diretório implementados pela task 07; publicação real
no Cloudflare R2 é da task 08 · última atualização 2026-09-14 (task 07)

## Arquivos

- `services/ports/armazenamento_imagens.py` — `ArmazenamentoImagens` (Protocol)
- `infra/armazenamento_imagens_diretorio.py` — `ArmazenamentoImagensDiretorio`
- 🔲 `infra/armazenamento_imagens_r2.py` — implementação real com `boto3` (task 08)

## Contratos

```python
# services/ports/armazenamento_imagens.py
class ArmazenamentoImagens(Protocol):
    def publicar(self, chave: str, dados: bytes) -> str: ...
    def existe(self, url: str) -> bool: ...


# infra/armazenamento_imagens_diretorio.py
class ArmazenamentoImagensDiretorio:
    def __init__(self, raiz: Path) -> None: ...
    def publicar(self, chave: str, dados: bytes) -> str: ...
    def existe(self, url: str) -> bool: ...
```

## Comportamento

**`ArmazenamentoImagensDiretorio`** — `publicar(chave, dados)` grava em `raiz/chave`
(`mkdir(parents=True, exist_ok=True)`, sempre sobrescreve — mesma semântica de "sempre
sobrescreve" que o R2 real terá) e devolve `Path.resolve().as_uri()` (uma URL `file://`).
`existe(url)` resolve a URL de volta a um caminho (`urllib.parse.urlparse` +
`urllib.request.url2pathname`, que trata corretamente o prefixo de drive do Windows) e checa
`Path.is_file()`.

Quando `PipelineFotos` (módulo `fotos`) usa `raiz = lotes/<lote>/fotos-processadas` e
`chave = produtos/<sku-pai>/<nome>`, o caminho físico final é
`lotes/<lote>/fotos-processadas/produtos/<sku-pai>/<nome>.jpg` — o mesmo valor de `chave` que a
task 08 vai publicar no R2, então local e remoto usam a identidade de arquivo.

## Limites

- Nenhuma publicação real acontece nesta task — `ArmazenamentoImagensDiretorio` é só o
  "armazenamento" local do workspace, para permitir testar o pipeline de fotos ponta a ponta
  sem depender de credenciais R2.
- `existe()` aqui só confere arquivo local; a versão R2 (task 08) fará um `HEAD` HTTP real
  (mitigação da falha silenciosa de imagem da POC, `docs/ARQUITETURA.md` §14 risco #4).
- Sem `Content-Type`/`Cache-Control` (`docs/ARQUITETURA.md` §5.3 itens 5–6) — atributos de objeto
  do R2, sem equivalente em arquivo local; entram com a implementação real.
- Nenhum wiring em `config/composicao.py`/`cli.py` — sem consumidor até a task 15 (`processar`).

## Testes

- `tests/unit/infra/test_armazenamento_imagens_diretorio.py` (`tmp_path`) — `publicar` grava no
  caminho esperado e devolve URL `file://` que lê de volta o mesmo conteúdo; `existe` confirma
  `True` após publicar e `False` para uma URL nunca publicada; publicar a mesma chave duas vezes
  sobrescreve.
- Nenhum fake de `ArmazenamentoImagens` extraído em módulo compartilhado ainda —
  `tests/unit/services/test_pipeline_fotos.py` tem um `_ArmazenamentoImagensEmMemoria` inline;
  se um segundo consumidor precisar do mesmo fake, vale extrair.

## Histórico

- Task 07 (2026-09-14): criação do port `ArmazenamentoImagens` e da implementação local em
  diretório, para viabilizar `PipelineFotos` sem depender do R2 real.
