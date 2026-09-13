# Task 13 — Agente QA e orquestração `GeradorTextos`

- **Depende de:** 12
- **Modelo recomendado:** opus
- **Leia antes:** `docs/ARQUITETURA.md` §6.2 (loop completo), §6.5, §8 (tentativas no
  estado); `recursos/qa.md`

## Objetivo

Fechar o ciclo de IA: um revisor (LLM como juiz) que devolve veredito estruturado por campo,
e o orquestrador que encadeia Copywriter → SEO → QA com retry direcionado ao grupo culpado,
registrando cada tentativa no `EstadoProduto`.

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
4. `services/gerador_textos.py`: `GeradorTextos(copywriter, seo, qa, max_tentativas)` com
   `gerar(produto, estado) -> TextosProduto`:
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

## Critério de aceite

- Ciclo completo na fixture: ≥ 5 produtos aprovados; para um produto com `detalhes`
  propositalmente pobres, o QA não inventa reprovação por "fato inventado" sem evidência.
- Estado do produto contém todas as tentativas com custo somado em `custo_usd_estimado`.
- Lint, mypy e pytest passam.
