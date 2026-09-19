# Módulo: agentes-textos

**Responsabilidade:** versionar e servir os insumos de conteúdo dos agentes de IA
(posicionamento da loja, regras de copy/SEO/QA e perfis de marca) e, nas tasks seguintes,
os agentes Copywriter/SEO/QA e o `GeradorTextosIa` que substitui o dummy.
**Estado:** implementado pela task 13 (só recursos e carregamento) · última atualização
2026-09-19 (task 13)

## Arquivos

| Camada | Arquivo |
|---|---|
| models | `models/perfil_marca.py` (`PerfilMarca`) |
| infra | `infra/carregador_recursos.py` (`perfil_marca`, `marcas_com_perfil`, `palavras_proibidas`, `extrair_palavras_proibidas`) — classe compartilhada com o módulo `dados-mestre-recursos` |
| recursos | `recursos/loja.md`, `copy.md`, `seo.md`, `qa.md`, `recursos/marcas/_generico.md`, `recursos/marcas/{kiki,onda-marinha,coloritta,somnii,menina-anjo,luc-boo,nina-go,kyly,lemon}.md` |
| recursos (pendente) | `recursos/prompts/copywriter.j2` (task 14), `seo.j2` (15), `qa.j2` (16) |
| models/services (pendente) | `models/regras_texto.py` (14), `services/agente_copywriter.py` (14), `agente_seo.py` (15), `agente_qa.py` + `gerador_textos_ia.py` (16) |

## Contratos

```python
@dataclass(frozen=True)
class PerfilMarca:
    marca: str
    texto: str
    generico: bool


class CarregadorRecursos:
    def texto(self, nome: str) -> str                       # "loja.md", "copy.md", "seo.md", "qa.md", "marcas/<slug>.md"
    def perfil_marca(self, marca_canonica: str) -> PerfilMarca
    def marcas_com_perfil(self) -> frozenset[str]
    def palavras_proibidas(self) -> frozenset[str]


def extrair_palavras_proibidas(markdown_seo: str) -> frozenset[str]
```

Exceção: `ErroRecursos(recurso, motivo)` (módulo `dados-mestre-recursos`). Variáveis de
ambiente: nenhuma.

## Comportamento

- Os `.md` são prosa para o modelo (sem formato "copie e cole"), lidos como texto puro via
  `importlib.resources` — funcionam com o pacote instalado. Nenhum pede URL, nome de foto ou
  sufixo `| Kmilaa Modas`; os limites citados são os de `ARQUITETURA.md` §6.1.
- `perfil_marca(marca)`: procura `marcas/<slugificar(marca)>.md`; se não existir, devolve o
  texto de `marcas/_generico.md` com `generico=True`. Nunca falha por marca desconhecida —
  quem valida a marca é o `ValidadorEntrada`.
- `marcas_com_perfil()`: percorre `DadosMestre.marcas_canonicas` e devolve as que têm perfil
  próprio; `montar_validador_entrada` injeta esse conjunto para o aviso "sem perfil de marca".
- `palavras_proibidas()`: `extrair_palavras_proibidas(texto("seo.md"))`. A função pura procura a
  linha exata `## Palavras proibidas`, lê os itens `- …` até o próximo heading e devolve
  `frozenset` em `casefold()`. Seção ausente ou sem itens → `ErroRecursos("seo.md", …)`.
- Conteúdo por arquivo: `loja.md` (o que é, para quem, promessa, Big Idea, tom, diferenciais
  permitidos — 3x sem juros, frete grátis SP, entrega Brasil, retirada em Sorocaba, WhatsApp —
  e o que a loja não faz); `copy.md` (escrever para a mãe; título `[Tipo] [Marca] [detalhe]
  [faixa]` ≤ 68; descrição `h2 → p → p → ul → h3 Sobre a [Marca] → h3 Compre na Kmilaa Modas`
  com parágrafo fixo, só `h2 h3 p ul li strong`, ≥ 120 palavras; característica → benefício;
  nunca inventar atributo, repetir o título na abertura ou usar texto intercambiável entre
  marcas); `seo.md` (Google SEO Starter Guide com data de consulta; tag title ≤ 60 sem sufixo;
  meta 140–155 com benefício + marca + CTA; sem keyword stuffing; palavras proibidas e
  palavras a usar com cuidado); `qa.md` (veredito, gravidade `alta` reprova / `baixa` observa,
  como revisar); `marcas/<slug>.md` (posicionamento, promessa, atributos obrigatórios, tom,
  palavras-chave, Big Idea); `_generico.md` (usa o posicionamento da loja).

## Limites

- Não renderiza prompt nem chama LLM — templates `.j2` e agentes são das tasks 14–16
  (`RepositorioPromptsJinja` e `ClienteLlmAnthropic` já existem no módulo
  `llm-cliente-prompts`).
- Não aplica as palavras proibidas a texto nenhum — `models/regras_texto.py` (task 14) consome
  `palavras_proibidas()`.
- Não decide a marca do produto — recebe a canônica já resolvida por `DadosMestre`.
- O aviso "produto usou perfil genérico" no relatório é da task 16 (`PerfilMarca.generico`).

## Testes

- `tests/unit/infra/test_carregador_recursos.py` (seção "recursos de conteúdo (task 13)"):
  os 14 arquivos carregam do pacote real (`# ` inicial, > 50 palavras) e não contêm
  `| Kmilaa Modas`/`.jpg`/`Foto 1`; `perfil_marca` próprio (`Menina Anjo`, `Kyly`) e genérico
  (`Marca Nova`); toda canônica do YAML tem perfil próprio; `marcas_com_perfil()` == 9 marcas;
  `palavras_proibidas()` do `seo.md` real; `extrair_palavras_proibidas` com Markdown sintético
  (só a seção, `casefold`, seção ausente, seção vazia).
- `tests/unit/config/test_composicao.py`: `montar_validador_entrada` não emite aviso "sem
  perfil de marca" para `Kiki Xodó` (alias de `kiki`).

## Histórico

- Task 13 (2026-09-19): criação do módulo — `PerfilMarca`, recursos `loja/copy/seo/qa.md` e
  `marcas/*.md`, `perfil_marca`/`marcas_com_perfil`/`palavras_proibidas` em `CarregadorRecursos`,
  validador ligado aos perfis.
