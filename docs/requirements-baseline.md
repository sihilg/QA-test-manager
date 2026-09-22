# Baseline de requisitos

As decisões abaixo foram revistas antes do início do modelo de dados:

- a aplicação é local, single-instance e não é multi-tenant;
- todo caso pertence obrigatoriamente a um projeto;
- projetos e casos usam arquivo/soft delete para preservar o histórico;
- números de caso são imutáveis e sequenciais por projeto, começando em `CT001`, sem reutilização;
- os resultados são `NOT_EXECUTED`, `PASSED`, `FAILED` e `BLOCKED`;
- datas são guardadas em UTC;
- casos usam optimistic locking para impedir sobrescrita silenciosa;
- a Eva colabora por ficheiros locais e nunca aprova casos automaticamente.

A matriz completa de requisitos permanece no plano de implementação revisto. Este resumo regista apenas as decisões vinculativas necessárias para o incremento atual.
