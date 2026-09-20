# Arquitetura inicial

O QA Test Manager é uma aplicação single-instance executada integralmente em localhost.

```text
Browser → React SPA → FastAPI → SQLite / ficheiros locais
```

O GitHub contém somente código e documentação pública. Dados da aplicação, uploads, evidências e ficheiros trocados com a Eva ficam fora do controlo de versão.

Nesta fase, a Eva não está integrada à aplicação. A colaboração futura será feita por pacotes locais exportados e importados pelo utilizador através do ChatGPT/Codex.
