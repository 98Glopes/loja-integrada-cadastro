# Módulo: armazenamento-r2

**Responsabilidade:** publicar o JPEG final de uma foto sob uma chave (`produtos/<sku-pai>/
<nome>`) e confirmar que a URL resultante está acessível.
**Estado:** implementado pelas tasks 07, 08 · última atualização 2026-09-14 (task 08)

## Arquivos

- `services/ports/armazenamento_imagens.py` — `ArmazenamentoImagens` (Protocol)
- `infra/armazenamento_imagens_diretorio.py` — `ArmazenamentoImagensDiretorio` (local, testes)
- `infra/armazenamento_imagens_r2.py` — `ArmazenamentoImagensR2` (real, `boto3`)
- `models/exceptions/erro_publicacao_imagem.py` — `ErroPublicacaoImagem`

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


# infra/armazenamento_imagens_r2.py
class ArmazenamentoImagensR2:
    def __init__(
        self,
        bucket: str,
        account_id: str,
        access_key_id: str,
        secret_access_key: str,
        url_publica: str,
        cliente: S3Client | None = None,  # injeção opcional, só para teste
    ) -> None: ...
    def publicar(self, chave: str, dados: bytes) -> str: ...
    def existe(self, url: str) -> bool: ...


# models/exceptions/erro_publicacao_imagem.py
class ErroPublicacaoImagem(Exception):
    chave_ou_url: str
    motivo: str
```

## Comportamento

**`ArmazenamentoImagensDiretorio`** — `publicar(chave, dados)` grava em `raiz/chave`
(`mkdir(parents=True, exist_ok=True)`, sempre sobrescreve) e devolve `Path.resolve().as_uri()`
(uma URL `file://`). `existe(url)` resolve a URL de volta a um caminho e checa `Path.is_file()`.
Continua existindo para testes/desenvolvimento sem tocar o R2 real (`tests/integration/
test_pipeline_fotos_poc.py`).

**`ArmazenamentoImagensR2`** — `publicar(chave, dados)` chama `put_object` no bucket
(`Bucket`, `Key=chave`, `Body=dados`, `ContentType="image/jpeg"` fixo — a pipeline só produz
JPEG —, `CacheControl="public, max-age=31536000"`), sempre sobrescrevendo (comportamento padrão
do S3/R2). Devolve `f"{url_publica}/{chave}"`. Erros de `boto3` (`BotoCoreError`, `ClientError`)
viram `ErroPublicacaoImagem(chave, motivo)`.

`existe(url)` faz um `HEAD` real (`httpx.head`, timeout 10s) — mitigação da falha silenciosa de
imagem da POC (`docs/ARQUITETURA.md` §14 risco #4). Uma resposta HTTP obtida normalmente (mesmo
que não seja 200, ou com `Content-Type` diferente de `image/jpeg`) só resulta em `False` — a
foto ainda não está pronta, não é uma falha de infraestrutura. Uma falha de transporte (timeout,
conexão recusada) vira `ErroPublicacaoImagem(url, motivo)`.

O construtor recebe credenciais como primitivos (não um objeto `Configuracao`), para não
acoplar `infra` a `config`; quem monta é o chamador (hoje, os testes de integração, via
`Configuracao.do_ambiente()` — não há wiring em `config/composicao.py` ainda, ver "Limites").

Quando `PipelineFotos` (módulo `fotos`) monta `chave = produtos/<sku-pai>/<nome>`, essa é
exatamente a chave publicada no R2 — sem transformação adicional.

## Limites

- **Contrato do port mantido como estava (decisão task 08):** o texto original da task 08 pedia
  renomear `existe` → `acessivel` e adicionar `content_type: str` a `publicar`. Confirmado com o
  usuário manter os nomes atuais e resolver o `Content-Type` (sempre `image/jpeg`) dentro da
  implementação R2, para não propagar uma mudança de assinatura por `PipelineFotos`,
  `ArmazenamentoImagensDiretorio` e testes sem um segundo valor de `content_type` real. Ver
  `docs/specs/tasks/08-publicacao-r2.md`.
- **Sem wiring em `config/composicao.py`/`cli.py`:** o comando `processar` continua stub
  (`_nao_implementado`) até a task 11, responsável registrada pelo wiring real de CLI (spec da
  task 07). Não há flag `--sem-upload` nem modo "local" acionável por linha de comando — a
  pipeline, quando usada, sempre publica no R2. `ArmazenamentoImagensR2` é instanciado
  diretamente onde necessário hoje (testes de integração).
- **TTL de 7 dias é uma regra de lifecycle do bucket, fora do código:** decisão do usuário —
  objetos em `produtos/` expiram automaticamente pela configuração do bucket (painel
  Cloudflare/IaC), não por um parâmetro do `put_object` (S3/R2 não deleta por um header
  `Expires` enviado no upload). É por isso que "limpeza/remoção de fotos antigas" continua fora
  do escopo deste módulo.
- Nenhuma lógica de retry/backoff em `publicar`/`existe` — uma falha vira `ErroPublicacaoImagem`
  e o produto fica `erro-fotos`; a reexecução (idempotente, nomes determinísticos) tenta de novo.

## Testes

- `tests/unit/infra/test_armazenamento_imagens_diretorio.py` (`tmp_path`) — inalterado da task 07.
- `tests/unit/infra/test_armazenamento_imagens_r2.py` — cliente S3 injetado (`unittest.mock.
  MagicMock`, `tests/` não é coberto por `mypy --strict`): `publicar` chama `put_object` com
  `ContentType`/`CacheControl` corretos e devolve a URL esperada (com/sem barra final em
  `url_publica`); erro do boto vira `ErroPublicacaoImagem` com a chave. `existe`
  (`httpx.head` via `monkeypatch`): 200 + `image/jpeg` → `True`; 404 → `False`; 200 com
  `Content-Type` errado → `False`; falha de transporte → `ErroPublicacaoImagem` com a URL.
- `tests/integration/test_armazenamento_imagens_r2.py` (`@pytest.mark.integration`, pula se
  `R2_*` não configurado) — publica um JPEG pequeno em `testes/<uuid>.jpg` no bucket real,
  confirma `existe(url) is True`, apaga o objeto ao final.
- `tests/integration/test_pipeline_fotos_r2.py` (`@pytest.mark.integration`) — pipeline completa
  sobre `tests/fixtures/lote-piloto/fotos/` publicando no R2 real; confirma que todo
  `FotoProduto.url` responde 200 via `existe()`. Critério de aceite da task 08.

## Histórico

- Task 07 (2026-09-14): criação do port `ArmazenamentoImagens` e da implementação local em
  diretório, para viabilizar `PipelineFotos` sem depender do R2 real.
- Task 08 (2026-09-14): `ArmazenamentoImagensR2` real (`boto3`, S3-compatível), `existe()` vira
  HEAD HTTP real, `ErroPublicacaoImagem`. Contrato do port mantido sem alteração; sem wiring em
  CLI/composição nesta task; TTL de expiração é configuração de bucket, fora do código.
