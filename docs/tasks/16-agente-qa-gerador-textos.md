# Task 16 — Agente QA e orquestração `GeradorTextosIa`

- **Depende de:** 15, 11 (substitui o dummy na composição do `processar`)
- **Modelo recomendado:** opus
- **Leia antes:** `docs/ARQUITETURA.md` §6.2 (loop completo), §6.5, §8 (tentativas no
  estado), ADR-007; `recursos/qa.md`; `docs/specs/tasks/09-gerador-textos-dummy.md` (port
  `GeradorTextos` e `TextosProduto` já existem — implementar, não recriar)

## Objetivo

Fechar o ciclo de IA: um revisor (LLM como juiz) que devolve veredito estruturado por campo,
e o orquestrador que encadeia Copywriter → SEO → QA com retry direcionado ao grupo culpado,
registrando cada tentativa no `EstadoProduto`. Ao final, o `processar` (task 11) passa a gerar
textos reais: o `GeradorTextosDummy` sai da composição.

## Escopo

1. `models/veredicto_qa.py`: `VeredictoQa` (frozen: `aprovado`, `problemas:
   tuple[ProblemaQa, ...]`) e `ProblemaQa` (`campo` ∈ {titulo, descricao_html,
   seo_tag_title, seo_tag_description}, `gravidade` ∈ {alta, baixa}, `motivo`, `sugestao`).
   Método `problemas_do_grupo(grupo) -> list` (copy = título+descrição; seo = tag title+meta).
   `aprovado` é derivado: nenhum problema `alta`.
2. `recursos/prompts/qa.j2`: `sistema_fixo` (papel de revisor, `qa.md`, instrução explícita
   de que só pode apontar como "fato inventado" algo ausente do `<produto>`, e de responder
   apenas pelo esquema), `sistema_marca`, `usuario` (`<produto>` + os 4 campos).
3. `services/agente_qa.py`: `AgenteQa.revisar(produto, textos) -> ResultadoAgente[VeredictoQa]`.
4. `services/gerador_textos_ia.py`: `GeradorTextosIa(copywriter, seo, qa, max_tentativas)`,
   implementação do port `GeradorTextos` (task 09), com `gerar(produto, estado) ->
   TextosProduto`:
   - copy → seo → qa; se o QA reprovar, reexecuta **só** o grupo com problema `alta`
     (passando `motivo`+`sugestao` como feedback); se a copy mudar, o SEO roda de novo
     (depende dela); QA roda de novo ao final; até `max_tentativas` ciclos.
   - Cada chamada vira uma `TentativaLlm` no estado (agente, tentativa, modelo, uso, custo,
     veredito de regra, veredito de QA, request_id, timestamp) via `registrar_tentativa`.
   - Esgotou → `ErroReprovacaoQa` com o último `TextosProduto` e o veredito (o orquestrador
     do lote decide marcar `reprovado-qa`; o texto fica no estado para o relatório).
   - `ErroGeracaoTexto` não retentável → propaga; retentável → uma nova tentativa depois de
     espera curta, depois propaga.
5. Testes com fakes roteirizados: aprovado de primeira; reprovação só do SEO (copy não é
   regerada); reprovação da copy (SEO roda de novo); esgotamento; erro não retentável.
6. `scripts/rodar_agente.py textos <planilha> <sku>` rodando o ciclo completo e imprimindo
   os 4 campos, o veredito e o custo total.
7. Troca na composição: `montar_gerador_textos` passa a devolver `GeradorTextosIa`;
   `infra/gerador_textos_dummy.py` é removido — se o teste do `ProcessarLote` ainda precisar
   de um gerador roteirizado, vira fake em `tests/` (não em `src/`). Nenhuma opção de CLI para
   escolher o dummy (ADR-007).

## Critério de aceite

- Ciclo completo na fixture: ≥ 5 produtos aprovados; para um produto com `detalhes`
  propositalmente pobres, o QA não inventa reprovação por "fato inventado" sem evidência.
- Estado do produto contém todas as tentativas com custo somado em `custo_usd_estimado`.
- `processar` sobre a fixture do lote piloto, com API real e R2 real: gera a planilha com
  textos reais, custo total e por produto no relatório; rodar de novo termina em segundos sem
  nova chamada à API (estado). `GeradorTextosDummy` não existe mais em `src/`.
- Lint, mypy e pytest passam.
