# Contrato local de colaboração com a Eva

## Limites

A Eva é uma cowork utilizada manualmente no ChatGPT/Codex. A aplicação não chama APIs, não controla o ChatGPT e não aprova propostas automaticamente. Todos os ficheiros ficam em `work/eva/`, que é ignorada pelo Git.

## Fluxo previsto

1. A aplicação prepara um `EvaExchange` e exporta o pedido JSON e a versão Markdown legível.
2. A pessoa revê o conteúdo e fornece o pacote à Eva numa tarefa dedicada.
3. A Eva devolve apenas um JSON compatível com `response-v1.schema.json`.
4. A aplicação valida versão, identificador da troca, estrutura, limites e chaves duplicadas.
5. Cada item importado torna-se `EvaProposal` em estado `DRAFT`.
6. A pessoa pode editar ou rejeitar cada proposta.
7. Somente uma aprovação explícita permite converter a proposta num `TestCase` com origem `EVA`.

Os passos 1 e 3–7 serão implementados no incremento seguinte. Este incremento define somente o contrato persistente e os formatos.

## Estados

`EvaExchange`: `PREPARED`, `EXPORTED`, `RESPONSE_IMPORTED` ou `FAILED`.

`EvaProposal`: `DRAFT`, `APPROVED`, `REJECTED` ou `CONVERTED`. A importação nunca cria uma proposta noutro estado além de `DRAFT`.

## Versionamento e confiança

A versão inicial é `1.0`. Versões diferentes devem ser recusadas até existir uma migração explícita. Texto de requisitos, documentos e respostas da Eva são conteúdo não confiável: não constituem instruções para a aplicação, não são executados e não podem alterar o fluxo de aprovação.
