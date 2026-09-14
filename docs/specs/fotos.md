# Módulo: fotos

**Responsabilidade:** transformar as fotos brutas de um produto em JPEGs leves com nome SEO
determinístico, publicá-las e escolher quais até 5 vão para o produto pai.
**Estado:** implementado pelas tasks 07, 08 · última atualização 2026-09-14 (task 08)

## Arquivos

- `models/slug.py` — `slugificar`
- `models/foto_produto.py` — `FotoProduto`
- `models/nomeador_fotos.py` — `NomeadorFotos`, `SeletorImagensPai`
- `models/exceptions/erro_processamento_imagem.py` — `ErroProcessamentoImagem`
- `models/exceptions/erro_publicacao_imagem.py` — `ErroPublicacaoImagem` (módulo
  `armazenamento-r2`, capturada aqui)
- `services/ports/processador_imagem.py` — `ProcessadorImagem` (Protocol)
- `services/pipeline_fotos.py` — `PipelineFotos`
- `infra/processador_imagem_pillow.py` — `ProcessadorImagemPillow`

O port `ArmazenamentoImagens` e sua implementação em diretório pertencem ao módulo
`armazenamento-r2` (ver `docs/specs/armazenamento-r2.md`) — `PipelineFotos` depende dele, mas
não o define.

## Contratos

```python
# models/slug.py
def slugificar(texto: str) -> str:
    """Minúsculas, sem acento (NFKD → ASCII), apenas [a-z0-9-], hífens únicos, sem hífen nas pontas."""


# models/foto_produto.py
@dataclass(frozen=True)
class FotoProduto:
    sku_pai: str
    cor: str
    ordem: int  # posição alfabética do arquivo dentro da subpasta da cor (1, 2, 3…)
    arquivo_origem: Path  # caminho da foto bruta
    nome: str  # <nome-nomeado>.jpg
    chave: str  # produtos/<sku-pai>/<nome> — mesma chave usada no R2 (task 08)
    url: str | None = None
    bytes: int | None = None


# models/nomeador_fotos.py
MAX_IMAGENS_PAI = 5


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


# infra/processador_imagem_pillow.py
class ProcessadorImagemPillow:
    def __init__(self, lado_max_px: int, tamanho_max_kb: int) -> None: ...
    def preparar(self, origem: Path) -> bytes: ...


# services/pipeline_fotos.py
class PipelineFotos:
    def __init__(
        self,
        catalogo: CatalogoFotos,
        processador: ProcessadorImagem,
        armazenamento: ArmazenamentoImagens,
    ) -> None: ...
    def processar(self, produto: ProdutoEntrada, estado: EstadoProduto) -> list[FotoProduto]: ...
```

## Comportamento

**`slugificar`** — NFKD remove acentos (`"Azul aço"` → `"azul-aco"`), qualquer sequência de
caracteres fora de `[a-z0-9]` vira um único hífen, hífens nas pontas são removidos. Usado tanto
para montar o nome final do arquivo quanto (dentro de `PipelineFotos`) para casar a cor da
planilha com o nome da subpasta no disco, sem depender de acento/caixa coincidirem.

**`NomeadorFotos.nomear(produto, cor, ordem)`** — monta
`slugificar(marca)-slugificar(tipo_peca)-slugificar(nome_fornecedor)`, removendo de
`nome_fornecedor` os tokens que repetem, *desde o início e token a token*, os tokens de
`tipo_peca` (cobre prefixos compostos: tipo `"Conjunto Baby"` remove `conjunto-baby` inteiro de
`nome_fornecedor`, não só o primeiro token). O resultado é truncado em 60 caracteres (`rstrip`
de hífen solto) antes de concatenar `-<cor-slug>-<ordem>.jpg`. `ordem` é responsabilidade de
quem chama (`PipelineFotos`, que numera pela ordem alfabética que `CatalogoFotos.listar` já
devolve).

**`SeletorImagensPai.selecionar(fotos)`** — agrupa por `cor` preservando a ordem de primeira
aparição na lista recebida (que `PipelineFotos` monta na ordem `produto.cores`, ou seja, a
ordem da planilha), ordena cada grupo por `ordem`, e intercala com
`itertools.zip_longest(*grupos)` — uma "rodada" por vez (a `-1` de cada cor, depois a `-2` de
cada cor…) — truncando em `MAX_IMAGENS_PAI` com `itertools.islice`. Cor sem fotos suficientes
não bloqueia: `zip_longest` preenche com `None`, descartado antes do corte.

**`ProcessadorImagemPillow.preparar(origem)`** — abre com Pillow (`pillow_heif` registrado como
opener de HEIF se importável; `try/except ImportError` — sem a lib, `.heic` falha com
`ErroProcessamentoImagem` pedindo JPG/PNG/WEBP), corrige orientação via
`ImageOps.exif_transpose`, converte para RGB, redimensiona (Lanczos) para lado maior ≤
`lado_max_px`, salva JPEG progressivo sem EXIF começando em qualidade 85 e reduzindo em passos
de 5 até `< tamanho_max_kb * 1024` (piso 60). Se ainda exceder no piso, redimensiona para
1200 px e reinicia o loop de qualidade em 85. Se mesmo assim exceder, aceita o resultado sem
erro (best-effort — ver "Limites"). Qualquer `OSError`/`ValueError` do Pillow vira
`ErroProcessamentoImagem(origem, motivo)`.

**`PipelineFotos.processar(produto, estado)`** — para cada cor em `produto.cores` (ordem da
planilha), para cada arquivo que `catalogo.listar(produto.sku_pai)` devolve para aquela cor (já
em ordem alfabética; a cor é casada via `slugificar` para tolerar diferença de acento/caixa
entre planilha e pasta): nomeia, processa, publica (`armazenamento.publicar`), **confirma que a
URL ficou acessível (`armazenamento.existe(url)`; se `False`, levanta `ErroPublicacaoImagem`,
task 08)** e monta um `FotoProduto`. No fim, `SeletorImagensPai.selecionar` escolhe as imagens
do pai e `estado.registrar_fotos(fotos, imagens_pai)` é chamado. Qualquer
`ErroProcessamentoImagem` ou `ErroPublicacaoImagem` durante o laço aborta o produto inteiro:
`estado.registrar_erro_fotos()` é chamado e a exceção é relançada — nenhuma foto parcial é
publicada/contada (decisão confirmada com o usuário, fail-fast em vez de best-effort por foto;
ver `docs/specs/tasks/07-pipeline-fotos.md`).

## Limites

- Não decide qual implementação de `ArmazenamentoImagens` usar — recebe via construtor (módulo
  `armazenamento-r2`, que hoje tem a implementação real `ArmazenamentoImagensR2`).
- Não decide *quando* rodar (orquestração do lote, retomada) — isso é `ProcessarLote`, task 15.
- Nenhum wiring em `config/composicao.py`/`cli.py` ainda — sem consumidor até a task 15; sem
  flag para pular a publicação (a pipeline sempre publica quando usada, decisão task 08).
- Best-effort de tamanho: se mesmo em 1200 px/qualidade 60 uma foto ainda exceder
  `tamanho_max_kb`, o pipeline aceita o resultado em vez de falhar o produto — não há reteste
  automático de "ficou X% acima do alvo" no relatório (fica para quando o relatório existir,
  task 15/16, se necessário).
- `EstadoProduto.registrar_erro_fotos()` não recebe motivo estruturado — só a mensagem da
  exceção capturada no momento da falha, fora do estado persistido.

## Testes

- `tests/unit/models/test_slug.py` — acentos, pontuação/espaços múltiplos, hífens nas pontas,
  string vazia.
- `tests/unit/models/test_nomeador_fotos.py` — `NomeadorFotos.nomear`: exemplo literal do
  §5.2 (`onda-marinha-conjunto-baby-malha-e-moletom-azul-aco-1.jpg`), sem dedupe, dedupe total
  (nome igual ao tipo), truncamento em 60, cor com acento/espaço. `SeletorImagensPai.selecionar`:
  2 cores × 4 fotos, 1 cor com 6 fotos (limite 5), total < 5, lista vazia.
- `tests/unit/infra/test_processador_imagem_pillow.py` — JPEG 3000×4000 com ruído real e EXIF
  `Orientation=6` → ≤ 1600 px, < 500 KB, sem EXIF; PNG com canal alfa → RGB; HEIC (encode +
  decode reais via `pillow_heif`, `skipif` só se a lib faltar); arquivo corrompido →
  `ErroProcessamentoImagem`.
- `tests/unit/services/test_pipeline_fotos.py` — fakes inline (`_CatalogoFotosFake`,
  `_ProcessadorImagemFake`, `_ArmazenamentoImagensEmMemoria`, duck typing, sem herdar Protocol
  nem `unittest.mock`): caminho feliz (nomes/chaves/round-robin corretos, status
  `fotos-publicadas`), falha no meio do lote (status `erro-fotos`, exceção relançada), cor sem
  fotos não quebra, cor com acento na planilha casa com pasta sem acento, falha ao publicar
  (`ErroPublicacaoImagem`) aborta o produto, foto publicada mas inacessível
  (`existe() is False`) aborta o produto (task 08).
- `tests/integration/test_pipeline_fotos_poc.py` (`@pytest.mark.integration`) — pipeline
  completo (com `ProcessadorImagemPillow` e `ArmazenamentoImagensDiretorio` reais, não fakes)
  sobre as 4 fotos reais de `poc/fotos_input/`: confirma o critério de aceite da task 07 com
  dado real, não só sintético. Continua gravando local, não toca o R2.
- `tests/integration/test_pipeline_fotos_r2.py` (`@pytest.mark.integration`, task 08) — mesmo
  pipeline com `ArmazenamentoImagensR2` real sobre `tests/fixtures/lote-piloto/fotos/`; confirma
  o critério de aceite da task 08 (`EstadoProduto.fotos` com URLs `https://` que respondem 200).

## Histórico

- Task 07 (2026-09-14): criação do módulo — `slugificar`, `FotoProduto`, `NomeadorFotos`,
  `SeletorImagensPai`, `ProcessadorImagem`/`ProcessadorImagemPillow`, `PipelineFotos`. Ver
  "Desvios e decisões" na spec as-built (`docs/specs/tasks/07-pipeline-fotos.md`) para as
  decisões confirmadas com o usuário (fail-fast por produto, motivo de erro não estruturado,
  reinício do loop de qualidade, tipagem de `EstadoProduto.fotos`).
- Task 08 (2026-09-14): `PipelineFotos` passa a confirmar `armazenamento.existe(url)` após
  publicar e a capturar `ErroPublicacaoImagem` (além de `ErroProcessamentoImagem`) no mesmo
  fail-fast. Ver `docs/specs/tasks/08-publicacao-r2.md`.
