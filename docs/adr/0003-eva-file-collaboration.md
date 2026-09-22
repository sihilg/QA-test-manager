# ADR 0003 — Colaboração com a Eva por ficheiros

## Estado

Aceite.

## Contexto

A aplicação deve funcionar sem integração com APIs de LLM. A Eva será utilizada como cowork no ChatGPT/Codex.

## Decisão

A aplicação exportará um pacote legível em Markdown e estruturado em JSON. O utilizador fornecerá esse pacote à Eva e importará uma resposta JSON validada por schema. Toda proposta permanecerá editável e exigirá aprovação humana.

## Consequências

Não haverá chat embutido, execução autónoma ou processamento em background. A pasta de troca será local e ignorada pelo Git.
