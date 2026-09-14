# Testes de integração

Testam conectores reais de `infra/` (R2, e futuramente Anthropic, site público) contra a
infraestrutura de verdade. Ficam desligados por padrão (`addopts = "-m 'not integration'"` em
`pyproject.toml`) para não rodar em CI nem exigir credenciais em toda execução de `pytest`.

## Como rodar

```bash
pytest -m integration
```

Ou um arquivo específico:

```bash
pytest -m integration tests/integration/test_armazenamento_imagens_r2.py
```

## Pré-requisitos

Um `.env` na raiz do projeto (nunca commitado) com as credenciais reais usadas por
`Configuracao.do_ambiente()`. Para os testes de R2 (`test_armazenamento_imagens_r2.py`,
`test_pipeline_fotos_r2.py`):

```
R2_ACCOUNT_ID=...
R2_ACCESS_KEY_ID=...
R2_SECRET_ACCESS_KEY=...
R2_BUCKET=...
R2_URL_PUBLICA=...
```

Sem essas variáveis, os testes de R2 são pulados automaticamente (`pytest.skip`) — não falham,
para não travar quem roda `pytest -m integration` sem as credenciais.

## O que esses testes fazem no ambiente real

- `test_armazenamento_imagens_r2.py`: publica um JPEG pequeno em `testes/<uuid>.jpg` e apaga o
  objeto ao final do teste.
- `test_pipeline_fotos_r2.py`: roda a pipeline de fotos completa sobre
  `tests/fixtures/lote-piloto/fotos/` e publica as fotos resultantes em `produtos/<sku-pai>/...`
  no bucket real — **não apaga** os objetos ao final; eles expiram pela regra de lifecycle de 7
  dias configurada no bucket (ver `docs/specs/tasks/08-publicacao-r2.md`, seção "Desvios e
  decisões").
- `test_pipeline_fotos_poc.py` (task 07): processa fotos reais de `poc/fotos_input/`, mas grava
  localmente (`ArmazenamentoImagensDiretorio`) — não toca o R2.
