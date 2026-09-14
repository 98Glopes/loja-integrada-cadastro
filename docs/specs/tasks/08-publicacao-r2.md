# Spec as-built — Task 08: Publicação no Cloudflare R2

- **Data:** 2026-09-14 · **Task:** `docs/tasks/08-publicacao-r2.md` · **Módulos:**
  `armazenamento-r2`, `fotos`

## Entregue

`PipelineFotos` agora publica de verdade no bucket R2 (`boto3`, S3-compatível) via
`ArmazenamentoImagensR2`, e confirma com um `HEAD` HTTP real que cada foto ficou acessível antes
de contá-la — mitigando a falha silenciosa de imagem observada na POC. Falha de upload ou de
confirmação aborta o produto inteiro (`erro-fotos`, reexecução idempotente tenta de novo). Não
há comando de CLI usando isso ainda (`processar` continua stub, task 15); o consumo real, por
enquanto, é via testes de integração.

Comandos:

```bash
pytest                                                    # unitários, R2 não é tocado
pytest -m integration                                     # inclui os testes reais de R2 (skip sem .env)
pytest -m integration tests/integration/test_armazenamento_imagens_r2.py
pytest -m integration tests/integration/test_pipeline_fotos_r2.py
```

## Arquivos

| Camada | Criados | Alterados |
|---|---|---|
| models | `exceptions/erro_publicacao_imagem.py` | — |
| services | — | `pipeline_fotos.py` |
| infra | `armazenamento_imagens_r2.py` | — |
| config | — | — |
| cli | — | — |
| tests | `unit/infra/test_armazenamento_imagens_r2.py`, `integration/test_armazenamento_imagens_r2.py`, `integration/test_pipeline_fotos_r2.py`, `integration/README.md` | `unit/services/test_pipeline_fotos.py` |
| docs | `specs/tasks/08-publicacao-r2.md` | `specs/armazenamento-r2.md`, `specs/fotos.md`, `ARQUITETURA.md`, `tasks/README.md` |

`pyproject.toml`: dependências `boto3`, `httpx` (runtime) e `boto3-stubs[s3]` (dev).

## Contratos

```python
# services/ports/armazenamento_imagens.py — inalterado
class ArmazenamentoImagens(Protocol):
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
        cliente: S3Client | None = None,
    ) -> None: ...
    def publicar(self, chave: str, dados: bytes) -> str: ...  # put_object + ContentType/CacheControl
    def existe(self, url: str) -> bool: ...                    # httpx.head, 200 + image/jpeg


# models/exceptions/erro_publicacao_imagem.py
class ErroPublicacaoImagem(Exception):
    chave_ou_url: str
    motivo: str
```

Variáveis de ambiente consumidas (já existiam desde a task 01, `Configuracao.exigir_r2()`):
`R2_ACCOUNT_ID`, `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`, `R2_BUCKET`, `R2_URL_PUBLICA`.

## Regras de negócio implementadas

- `publicar` grava com `ContentType: image/jpeg` e `CacheControl: public, max-age=31536000`,
  sempre sobrescrevendo.
- URL pública = `R2_URL_PUBLICA.rstrip("/") + "/" + chave`.
- `existe` confirma `200` + `Content-Type` iniciando em `image/jpeg` via `HEAD`; qualquer outra
  resposta HTTP válida é `False` (não erro).
- Falha de transporte (timeout, conexão recusada) em `publicar` ou `existe` vira
  `ErroPublicacaoImagem` com a chave/URL no texto.
- `PipelineFotos` chama `existe(url)` logo após `publicar`; `False` também vira
  `ErroPublicacaoImagem`. Tanto essa quanto `ErroProcessamentoImagem` abortam o produto inteiro
  (`estado.registrar_erro_fotos()`, exceção relançada) — mesmo fail-fast da task 07.

## Desvios e decisões

| Pedido (task/arquitetura) | Feito | Motivo |
|---|---|---|
| Renomear o port para `publicar(chave, conteudo, content_type)` / `acessivel(url)` | Mantidos os nomes atuais `publicar(chave, dados)` / `existe(url)`; `Content-Type` fixado como `"image/jpeg"` dentro de `ArmazenamentoImagensR2` | Confirmado com o usuário. O contrato já implementado (task 07) e a spec viva previam `existe()` virar HEAD real "task 08" sem prever renome; a pipeline só produz JPEG, então `content_type` seria sempre o mesmo valor — generalização sem segundo uso real (`docs/specs/armazenamento-r2.md`) |
| Flag `--sem-upload` no comando `processar`, wiring em `config/composicao.py` | Não implementado nesta task | Confirmado com o usuário: `processar` continua stub (`_nao_implementado`) até a task 15, já registrada como responsável pelo wiring de CLI (spec da task 07); adicionar uma flag inerte a um comando que não roda seria plumbing especulativo. A pipeline, quando usada, sempre publica no R2 — não há modo "local" acionável |
| Limpeza/remoção de fotos antigas no bucket (era "fora de escopo, não requisitada") | Confirmado fora do escopo do código; usuário informou que os objetos têm TTL de 7 dias configurado como regra de lifecycle do bucket (fora do código Python) | S3/R2 não expira objetos por um header enviado no `put_object` — só por lifecycle rule do bucket. Nenhuma chamada de lifecycle foi adicionada ao código |
| Task cita "Leia antes: ... §12 (integração)" | Lido §12 real de `ARQUITETURA.md`, que é "Testes e evals" — não existe seção dedicada a "integração com serviços externos" | Desalinhamento de numeração entre o texto da task (escrito em outra sessão) e o `ARQUITETURA.md` atual; registrado aqui, sem ação de código |

## Verificação executada

- `ruff check . && ruff format .` → sem erros (121 arquivos, 2 arquivos corrigidos durante o
  desenvolvimento: linha longa em docstring, `Any` em teste substituído por `MagicMock`).
- `mypy src` → `Success: no issues found in 47 source files`.
- `pytest` (unitários, sem os de integração) → `202 passed, 4 deselected`.
- `/python-clean-architecture:check-quality` sobre os arquivos da mudança → 0 issues.
- `pytest -m integration` **não foi executado nesta sessão** — publica objetos num bucket R2
  real; fica para o usuário rodar com o `.env` dele.

## Pendências para tasks futuras

- Wiring de `config/composicao.py`/`cli.py` (escolher `ArmazenamentoImagensR2` a partir de
  `Configuracao`, montar `PipelineFotos` completo) — task 15, junto do comando `processar` real.
- Confirmar/criar a regra de lifecycle de 7 dias no bucket R2 (fora do código; ação de
  infraestrutura do usuário, não deste repositório).
