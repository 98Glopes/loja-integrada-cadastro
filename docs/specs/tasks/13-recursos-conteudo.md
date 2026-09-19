# Spec as-built — Task 13: Recursos de conteúdo: loja, marcas, copy, SEO e QA

- **Data:** 2026-09-19 · **Task:** `docs/tasks/13-recursos-conteudo.md` · **Módulos:**
  `agentes-textos` (novo), `dados-mestre-recursos`, `validacao` (só `composicao.py`)

## Entregue

O conhecimento da skill de copywriting e dos perfis de marca virou texto versionado no pacote,
já corrigido pela POC (sem URL, sem nome de foto, sem sufixo `| Kmilaa Modas`): `recursos/loja.md`,
`copy.md`, `seo.md`, `qa.md` e `recursos/marcas/<slug>.md` para as 9 marcas canônicas mais
`_generico.md`. `CarregadorRecursos` passou a servir esses recursos com semântica:
`perfil_marca(marca)` devolve `PerfilMarca` (texto + flag `generico` quando caiu no genérico),
`marcas_com_perfil()` lista as canônicas com perfil próprio e `palavras_proibidas()` extrai a
lista fechada da seção `## Palavras proibidas` de `seo.md`. O comando `validar` já usa
`marcas_com_perfil()`: hoje nenhuma marca canônica recebe o aviso "sem perfil de marca".
Comando que roda: `pytest` (341 testes, 20 novos).

## Arquivos

| Camada | Criados | Alterados |
|---|---|---|
| models | `perfil_marca.py` (`PerfilMarca`) | — |
| infra | — | `carregador_recursos.py` (`perfil_marca`, `marcas_com_perfil`, `palavras_proibidas`, `_existe`, `_recurso`, `extrair_palavras_proibidas`) |
| config | — | `composicao.py` (`montar_validador_entrada` liga `marcas_com_perfil()`) |
| recursos | `loja.md`, `copy.md`, `seo.md`, `qa.md`, `marcas/_generico.md`, `marcas/{kiki,onda-marinha,coloritta,somnii,menina-anjo,luc-boo,nina-go,kyly,lemon}.md` | — |
| tests | — | `unit/infra/test_carregador_recursos.py`, `unit/config/test_composicao.py` |

## Contratos

```python
# models/perfil_marca.py
@dataclass(frozen=True)
class PerfilMarca:
    marca: str        # marca canônica pedida
    texto: str        # Markdown do perfil (próprio ou _generico.md)
    generico: bool    # True quando não existe recursos/marcas/<slug>.md

# infra/carregador_recursos.py
class CarregadorRecursos:
    def texto(self, nome: str) -> str                      # "loja.md", "copy.md", "seo.md", "qa.md", "marcas/kiki.md"…
    def perfil_marca(self, marca_canonica: str) -> PerfilMarca
    def marcas_com_perfil(self) -> frozenset[str]          # canônicas de dados_mestre.yaml com perfil próprio
    def palavras_proibidas(self) -> frozenset[str]         # itens de "## Palavras proibidas", em casefold()

def extrair_palavras_proibidas(markdown_seo: str) -> frozenset[str]   # pura, ErroRecursos se seção ausente/vazia
```

Nome do arquivo de perfil = `models/slug.slugificar(marca_canonica)` + `.md`:
`kiki`, `Onda Marinha` → `onda-marinha`, `Colorittá` → `coloritta`, `somnii`, `Menina Anjo` →
`menina-anjo`, `Luc.boo` → `luc-boo`, `Nina Go` → `nina-go`, `Kyly`, `Lemon`.

Formato parseável em `seo.md`: uma seção iniciada pela linha exata `## Palavras proibidas`,
terminada no próximo heading (`#…`); cada item `- palavra` (uma ou mais palavras) vira uma
entrada. Texto corrido dentro da seção é ignorado.

Estrutura dos recursos (headings `##`): `loja.md` — O que é, Para quem, Promessa, Big Idea, Tom
da loja, Diferenciais que podem aparecer nos textos, O que a loja não faz. `copy.md` — título
(fórmula, limite 68), descrição HTML (estrutura obrigatória, tags permitidas, ≥ 120 palavras),
característica → benefício, o que nunca escrever. `seo.md` — O que o Google pede (fonte e data
de consulta), Tag title (≤ 60, sem sufixo), Meta description (140–155), Palavras proibidas,
Palavras a usar com cuidado. `qa.md` — Veredito, Gravidade alta (reprova), Gravidade baixa
(observa), Como revisar. `marcas/<slug>.md` — posicionamento, promessa, atributos que não podem
faltar, tom, palavras-chave, Big Idea. `_generico.md` — Como escrever, O que não fazer.

## Regras de negócio implementadas

- Marca canônica com `recursos/marcas/<slug>.md` → `PerfilMarca(generico=False)` com o texto
  próprio; sem arquivo → texto de `_generico.md` e `generico=True` (nunca `ErroRecursos`).
- Todas as 9 marcas canônicas de `dados_mestre.yaml` têm perfil próprio (teste garante que
  adicionar marca ao YAML sem criar o `.md` quebra a suíte).
- `palavras_proibidas()` normaliza com `casefold()` e devolve só os itens da seção; seção
  ausente ou sem itens → `ErroRecursos("seo.md", …)`.
- Nenhum recurso de texto contém `| Kmilaa Modas`, `.jpg` ou `Foto 1` (a IA não gera URL, nome
  de foto nem sufixo); limites citados batem com `ARQUITETURA.md` §6.1 (68 / 60 / 140–155 /
  ≥ 120 palavras).
- `validar` avisa "sem perfil de marca" só para canônica fora de `marcas_com_perfil()`.

## Desvios e decisões

| Pedido (task/arquitetura) | Feito | Motivo |
|---|---|---|
| `perfil_marca(marca_canonica) -> str` "sinalizando que é genérico" | Devolve `PerfilMarca(marca, texto, generico)` | Uma `str` não carrega a flag; o relatório (task 16) precisa saber que o produto usou o genérico. Value object imutável no lugar de tupla/parâmetro de saída. |
| `texto("loja"\|"copy"\|"seo"\|"qa")` | Mantido `texto(nome_do_arquivo)` já existente: `texto("loja.md")` | Não criar API paralela para o mesmo I/O; os agentes (14–16) conhecem o nome do arquivo que leem. |
| `ARQUITETURA.md` §6.4 marcava `prompts/*.j2` como "🔲 task 13" | Marcação corrigida para tasks 14/15/16 | A task 13 declara os `.j2` fora do escopo e cada task de agente cria o seu template. Correção de documento, não de decisão. |
| Não pedido pela task | `montar_validador_entrada` passa `CarregadorRecursos().marcas_com_perfil()` | Pendência registrada em `docs/specs/validacao.md` §Limites ("até a task 13 ligar ao carregador"); sem isso toda marca seguia com aviso falso. |
| Não pedido | `_recurso(nome)` privado em `CarregadorRecursos` | Achado do `/python-clean-architecture:check-quality` (`texto` e `_existe` montavam o mesmo `Traversable`). |

## Verificação executada

- `ruff check . && ruff format --check . && mypy src && pytest` → 341 passed, 5 deselected
  (integração); mypy 75 arquivos sem erro.
- Testes de conteúdo sobre o pacote real: 14 arquivos carregam com `# ` inicial e > 50 palavras;
  nenhum contém `| Kmilaa Modas`/`.jpg`/`Foto 1`; `perfil_marca("Menina Anjo")` e `("Kyly")`
  devolvem perfil próprio com "Big Idea"; `perfil_marca("Marca Nova")` → genérico + flag;
  `marcas_com_perfil()` == 9 canônicas; `palavras_proibidas()` contém `lindo`, `incrível`,
  `qualidade incomparável` e não contém `especial`.
- `/python-clean-architecture:check-quality` sobre os 3 arquivos de código → 1 achado
  (duplicação em `texto`/`_existe`), corrigido com `_recurso`.

## Pendências para tasks futuras

- Task 14: `recursos/prompts/copywriter.j2` + `models/regras_texto.py` consumindo
  `palavras_proibidas()`; task 15: `seo.j2`; task 16: `qa.j2`, `GeradorTextosIa` e o aviso de
  perfil genérico no relatório (`PerfilMarca.generico`).
- Ordem dos produtos por marca (cache) e a montagem do bloco `sistema_marca` a partir de
  `PerfilMarca.texto` ficam para a task 16.
- Conteúdo dos `.md` é insumo de prompt: a calibração (task 17) pode reescrever trechos sem
  mudar o formato parseável de `## Palavras proibidas`.
