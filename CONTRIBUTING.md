# Contribuir

Este é um projeto pessoal de portfólio desenvolvido de forma incremental e com revisão humana.

## Fluxo

1. Crie uma issue com objetivo, escopo e critérios de aceite.
2. Crie uma branch curta a partir de `main` usando `feat/`, `fix/`, `docs/` ou `chore/`.
3. Faça alterações pequenas e acompanhadas de testes.
4. Execute as verificações locais descritas no README.
5. Abra um pull request e aguarde a CI e a revisão humana.

## Dados e segurança

Não versione bases SQLite, `.env`, credenciais, documentos carregados, evidências ou ficheiros da pasta `work/eva`. Use somente dados fictícios em testes, screenshots e documentação.

## Commits

Prefira mensagens curtas que expliquem a intenção, por exemplo:

```text
feat: add project creation endpoint
fix: prevent duplicate test case numbers
docs: explain local setup
```

## Qualidade

Uma alteração deve manter `main` executável. Mudanças de comportamento exigem testes; decisões arquiteturais relevantes exigem ADR.
