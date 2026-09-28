# Arquitetura inicial

O QA Test Manager é uma aplicação single-instance executada integralmente em localhost.

```text
Browser → React SPA → FastAPI → SQLite / ficheiros locais
```

O GitHub contém somente código e documentação pública. Dados da aplicação, uploads, evidências e ficheiros trocados com a Eva ficam fora do controlo de versão.

A Eva não está integrada por API. O contrato versionado de colaboração usa pacotes locais JSON e Markdown revistos pelo utilizador através do ChatGPT/Codex. Propostas importadas permanecem em rascunho e nunca se tornam casos de teste sem aprovação humana explícita.

O formato e os estados persistentes estão documentados em [eva/file-contract.md](eva/file-contract.md). A interface de exportação, importação e revisão pertence ao incremento seguinte.
