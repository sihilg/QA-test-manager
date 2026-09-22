# ADR 0002 — Autenticação local

## Estado

Aceite para implementação futura.

## Decisão

Usar email e palavra-passe com sessão em cookie HttpOnly. A aplicação continua local, mas a autorização por perfil permanece requisito do produto.

## Consequências

Será necessário um bootstrap explícito do primeiro Admin, proteção CSRF e armazenamento seguro de hashes. Não haverá SSO ou MFA no MVP.
