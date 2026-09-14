# Spec as-built — Task 07: Pipeline de fotos: nomeação, compressão e seleção

- **Data:** 2026-09-14 · **Task:** `docs/tasks/07-pipeline-fotos.md` · **Módulos:** `fotos`,
  `armazenamento-r2` (parte diretório)

## Entregue

- `slugificar` (`models/slug.py`): normalização determinística (NFKD, ASCII, `[a-z0-9-]`,
  hífens únicos) reutilizada para nome de foto e para casar cor da planilha com pasta em disco.
- `FotoProduto` (`models/foto_produto.py`, frozen): uma foto processada, com `chave` já no
  formato `produtos/<sku-pai>/<nome>` (mesma chave que a task 08 usa no R2).
- `NomeadorFotos.nomear` + `SeletorImagensPai.selecionar` (`models/nomeador_fotos.py`, puros):
  nome SEO determinístico (§5.2) e seleção round-robin de até 5 fotos para o produto pai (§5.3).
- `ProcessadorImagem` (port) + `ProcessadorImagemPillow` (infra): abre com Pillow/`pillow-heif`,
  corrige orientação EXIF, converte para RGB, redimensiona e comprime em JPEG progressivo sem
  EXIF.
- `ArmazenamentoImagens` (port) + `ArmazenamentoImagensDiretorio` (infra): grava em
  `fotos-processadas/` do workspace do lote e devolve URL `file://` — provisório até a task 08
  trocar por R2 real sem mudar o port.
- `PipelineFotos` (`services/pipeline_fotos.py`): orquestra catálogo → nomeador → processador →
  armazenamento → `EstadoProduto.registrar_fotos`/`registrar_erro_fotos`.
- `EstadoProduto.fotos` deixou de ser `tuple[Mapping[str, object], ...]` (tipo mínimo da task 06)
  e passou a ser `tuple[FotoProduto, ...]`; a (de)serialização em
  `infra/repositorio_estado_lote_json.py` foi atualizada junto (`_foto_para_dict`/`_foto_de_dict`).
- `pillow>=10.4`, `pillow-heif>=0.18` adicionados a `pyproject.toml` — wheels pré-compiladas
  confirmadas para `cp314-win_amd64` (Python 3.14.6 do `.venv` do projeto), sem toolchain de
  compilação; HEIC testado de verdade (encode + decode em memória e via `Image.open`).

Comando manual: `poc/fotos_input/` (4 fotos reais 3000×4000 ~1,8 MB) processado via
`PipelineFotos` produz JPEGs ≤ 1600 px e < 500 KB sem EXIF (teste de integração, ver abaixo).

## Arquivos

| Camada | Criados | Alterados |
|---|---|---|
| models | `models/slug.py`, `models/foto_produto.py`, `models/nomeador_fotos.py` | `models/estado_produto.py` (campo `fotos` e assinatura de `registrar_fotos`) |
| models/exceptions | `models/exceptions/erro_processamento_imagem.py` | — |
| services/ports | `services/ports/processador_imagem.py`, `services/ports/armazenamento_imagens.py` | — |
| services | `services/pipeline_fotos.py` | — |
| infra | `infra/processador_imagem_pillow.py`, `infra/armazenamento_imagens_diretorio.py` | `infra/repositorio_estado_lote_json.py` (serialização de `FotoProduto`) |
| tests | `tests/unit/models/test_slug.py`, `tests/unit/models/test_nomeador_fotos.py`, `tests/unit/infra/test_processador_imagem_pillow.py`, `tests/unit/infra/test_armazenamento_imagens_diretorio.py`, `tests/unit/services/test_pipeline_fotos.py`, `tests/integration/test_pipeline_fotos_poc.py` | `tests/unit/models/test_estado_produto.py`, `tests/unit/infra/test_repositorio_estado_lote_json.py` (fixtures com `FotoProduto` real) |
| config | — | — (nenhum wiring; ver "Fora do escopo") |

## Contratos

```python
# models/slug.py
def slugificar(texto: str) -> str: ...


# models/foto_produto.py
@dataclass(frozen=True)
class FotoProduto:
    sku_pai: str
    cor: str
    ordem: int
    arquivo_origem: Path
    nome: str
    chave: str
    url: str | None = None
    bytes: int | None = None


# models/nomeador_fotos.py
MAX_IMAGENS_PAI = (
    5  # duplica services.validador_entrada.MAX_FOTOS_POR_PRODUTO (models não importa services)
)


class NomeadorFotos:
    @staticmethod
    def nomear(produto: ProdutoEntrada, cor: str, ordem: int) -> str: ...


class SeletorImagensPai:
    @staticmethod
    def selecionar(fotos: list[FotoProduto]) -> list[FotoProduto]: ...


# models/exceptions/erro_processamento_imagem.py
class ErroProcessamentoImagem(Exception):
    origem: Path
    motivo: str


# services/ports/processador_imagem.py
class ProcessadorImagem(Protocol):
    def preparar(self, origem: Path) -> bytes: ...


# services/ports/armazenamento_imagens.py
class ArmazenamentoImagens(Protocol):
    def publicar(self, chave: str, dados: bytes) -> str: ...
    def existe(self, url: str) -> bool: ...


# infra/processador_imagem_pillow.py
class ProcessadorImagemPillow:
    def __init__(self, lado_max_px: int, tamanho_max_kb: int) -> None: ...
    def preparar(self, origem: Path) -> bytes: ...


# infra/armazenamento_imagens_diretorio.py
class ArmazenamentoImagensDiretorio:
    def __init__(self, raiz: Path) -> None: ...
    def publicar(self, chave: str, dados: bytes) -> str: ...
    def existe(self, url: str) -> bool: ...


# services/pipeline_fotos.py
class PipelineFotos:
    def __init__(
        self,
        catalogo: CatalogoFotos,
        processador: ProcessadorImagem,
        armazenamento: ArmazenamentoImagens,
    ) -> None: ...
    def processar(self, produto: ProdutoEntrada, estado: EstadoProduto) -> list[FotoProduto]: ...


# models/estado_produto.py — alterado
fotos: tuple[FotoProduto, ...] = ()


def registrar_fotos(self, fotos: tuple[FotoProduto, ...], imagens_pai: tuple[str, ...]) -> None: ...
```

## Regras de negócio implementadas

- `NomeadorFotos.nomear`: `<marca>-<tipo-peca>-<nome-fornecedor>-<cor>-<n>.jpg`, todos os
  segmentos slugificados; tokens de `tipo-peca` removidos do início de `nome-fornecedor` token a
  token (cobre prefixos compostos, ex. "Conjunto Baby"); truncamento em 60 caracteres antes de
  `-<cor>-<n>.jpg`.
- `SeletorImagensPai.selecionar`: round-robin por cor na ordem de primeira aparição em `fotos`
  (que `PipelineFotos` já monta na ordem da planilha), até `MAX_IMAGENS_PAI = 5`.
- `ProcessadorImagemPillow.preparar`: orientação EXIF corrigida, RGB, lado maior ≤
  `lado_max_px`, JPEG progressivo sem EXIF, qualidade 85→60 em passos de 5 até
  `< tamanho_max_kb`; se ainda exceder, redimensiona para 1200 px e reinicia o loop de
  qualidade em 85; se mesmo assim exceder, aceita o resultado sem erro (best-effort).
- `PipelineFotos.processar`: uma falha ao processar qualquer foto (`ErroProcessamentoImagem`)
  aborta o produto inteiro — chama `estado.registrar_erro_fotos()` e relança a exceção; nenhuma
  foto parcial é publicada/contada. Cor da planilha sem pasta correspondente no catálogo (ou
  vice-versa) não quebra o pipeline, casadas por `slugificar` (acento/caixa não importam).
- `EstadoProduto.registrar_erro_fotos()` continua sem parâmetro de motivo — decisão confirmada
  (ver "Desvios e decisões").

## Desvios e decisões

| Pedido (task/arquitetura) | Feito | Motivo |
|---|---|---|
| Task 06 deixou em aberto se `registrar_erro_fotos()` ganharia `motivo: str` | Mantido sem parâmetro | Confirmado com o usuário: motivo trafega na mensagem de `ErroProcessamentoImagem`, capturada e logada por quem chamar o pipeline (fora de escopo — tasks 15/16); menor superfície de mudança em `estado_produto.py`. |
| Task não especifica o que fazer quando uma foto individual falha ao processar | Fail-fast por produto: primeira `ErroProcessamentoImagem` aborta o produto, chama `registrar_erro_fotos()` e relança | Confirmado com o usuário: evita repetir a falha silenciosa de imagem da POC (produto com imagem faltando sem ninguém perceber); reexecução é idempotente (nomes determinísticos). |
| §5.3 não detalha se o fallback de 1200 px reinicia o loop de qualidade em 85 ou usa direto o piso 60 | Reinicia em 85 no tamanho reduzido | Confirmado com o usuário: imagem menor comprime mais fácil, então uma qualidade mais alta ainda deve caber no limite; custo de reencodar é irrelevante em lote. |
| Caso extremo não coberto pela spec: mesmo em 1200 px/qualidade 60 o arquivo ainda excede 500 KB | Aceita o resultado sem erro (best-effort) | Julgamento técnico, não regra de negócio nova: falhar a foto inteira por poucos KB acima do alvo é pior que publicar levemente acima do limite. |
| `docs/specs/estado-lote.md` já antecipava `EstadoProduto.fotos` virando `tuple[FotoProduto, ...]` | Feito — `estado_produto.py` e a (de)serialização em `repositorio_estado_lote_json.py` atualizados nesta task | Confirmado com o usuário: é exatamente o próximo passo já anunciado; dá tipagem forte onde a task 08 (publicação R2) mais precisa dela. |
| §5.3 item 4 descrevia a cópia local como `fotos-processadas/<sku-pai>/<nome>.jpg` | Implementado como `fotos-processadas/produtos/<sku-pai>/<nome>.jpg` (o segmento extra `produtos/` vem de `FotoProduto.chave`, reaproveitada como caminho local) | `chave` já é o identificador que a task 08 vai publicar no R2 sem mudança; manter o mesmo valor como caminho local evita duas convenções de nome para a mesma foto. Texto do §5.3 atualizado para refletir isso. |
| `models/nomeador_fotos.py` precisa do limite "até 5 fotos no pai", já existente como `MAX_FOTOS_POR_PRODUTO` em `services/validador_entrada.py` | Duplicado como `MAX_IMAGENS_PAI = 5` local a `models/nomeador_fotos.py` | `models` não pode importar de `services` (regra de dependência inviolável); duplicar uma constante de 1 linha é mais barato que criar um módulo compartilhado só para isso (arquitetura evolutiva). |
| Regra 16 do `check-quality` (exceção ampla) — primeira versão de `ProcessadorImagemPillow.preparar` usava `except Exception` | Restrito a `except (OSError, ValueError)` | `Image.open`/`.convert`/`.resize`/`.save` do Pillow falham com `OSError` (`UnidentifiedImageError` é subclasse) ou `ValueError`; nenhum teste (incluindo arquivo corrompido e HEIC inválido) exigiu um catch mais amplo. |
| Regra 6 do `check-quality` (nesting profundo) — primeira versão de `SeletorImagensPai.selecionar` usava `while` + `for` + `if` aninhados | Reescrito com `itertools.zip_longest`/`islice` (uma geradora, sem laços aninhados) | Mesmo resultado, menos nesting; comportamento coberto pelos mesmos testes (round-robin, limite de 5, lista vazia). |

## Verificação executada

- `ruff check . && ruff format --check . && mypy src && pytest` → tudo passando (195 testes:
  193 unit + 2 integration; 30 novos nesta task — 165 já existiam da task 06; `mypy --strict`:
  sem problemas em 45 arquivos fonte).
- `/python-clean-architecture:check-quality` sobre os arquivos novos/alterados: 2 ajustes
  aplicados (ver tabela acima — exceção ampla em `processador_imagem_pillow.py`, nesting em
  `SeletorImagensPai.selecionar`). Demais regras sem violação.
- Teste de integração (`tests/integration/test_pipeline_fotos_poc.py`, `@pytest.mark.integration`)
  roda o pipeline completo sobre as 4 fotos reais de `poc/fotos_input/` (3000×4000, ~1,8 MB,
  EXIF `Orientation=6`): confirma ≤ 1600 px, < 500 KB, sem EXIF, nomes no formato esperado —
  critério de aceite da task cumprido com dado real, não só sintético.
- HEIC testado de verdade (não só `skipif`): roundtrip de encode/decode em memória e via
  `ProcessadorImagemPillow.preparar` num arquivo `.heic` gerado em teste — risco #6 do §14
  resolvido, wheel `pillow-heif` funciona no ambiente sem compilação.

## Pendências para tasks futuras

- Publicação real no R2 (`infra/armazenamento_imagens_r2.py`, `boto3`) — task 08, mesmo port
  `ArmazenamentoImagens`; o `HEAD` de confirmação pós-upload (§5.3 item 6) também é dela.
- Nenhum wiring em `config/composicao.py` ou `cli.py` — o comando `processar` (task 15) é quem
  vai montar `PipelineFotos` de verdade; adicionar `montar_pipeline_fotos()` antes disso seria
  antecipar uma camada sem consumidor (arquitetura evolutiva).
- Motivo estruturado para `erro-fotos` (campo em `EstadoProduto`) continua em aberto — se uma
  task futura (relatório, tasks 15/16) precisar mostrar por que um produto falhou nas fotos, ela
  decide o formato; por ora a mensagem só existe na exceção capturada no momento da falha.
