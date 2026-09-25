# Modelo de ameaças da Release 1

## Âmbito

Esta análise cobre a aplicação single-instance executada em localhost, a base SQLite, as sessões locais, os ficheiros exportados e o repositório público. A Eva, uploads, incidências, Jira e leitura de repositórios ainda não fazem parte da aplicação.

## Ativos e fronteiras

- credenciais e sessões dos utilizadores locais;
- projetos, casos de teste e registos de auditoria na base SQLite;
- ficheiros DOCX, XLSX e PDF descarregados pelo utilizador;
- código e documentação públicos no GitHub;
- fronteira Browser → React → FastAPI → SQLite.

O sistema confia no utilizador autenticado apenas dentro das permissões do seu perfil. Campos enviados pelo browser, nomes, filtros e conteúdo textual são sempre considerados não confiáveis.

## Ameaças e controlos

| Ameaça | Impacto | Controlos atuais | Limitação residual |
| --- | --- | --- | --- |
| Roubo de sessão | Acesso aos dados locais | Cookie HttpOnly, SameSite Lax, expiração e revogação no logout | `Secure` permanece desligado porque o MVP usa HTTP em localhost |
| Pedido de alteração forjado | Alteração sem consentimento | Token CSRF em todas as operações mutáveis | Malware já executado na máquina permanece fora do modelo |
| Escalada de perfil | Administração indevida | Autorização no backend para Admin, Tester e Dev | A segurança depende também da conta do sistema operativo |
| Acesso entre projetos | Exposição de casos | Verificação de associação ao projeto no backend e testes | Admin possui acesso global por decisão do produto |
| Injeção em XLSX | Fórmula executada ao abrir | Valores iniciados por caracteres de fórmula são neutralizados | O utilizador ainda deve tratar exportações como dados locais |
| Exposição por mensagens ou logs | Credenciais ou detalhes internos | Erros genéricos, logging sem corpo, senha, cookie ou token; request ID | Logs do servidor continuam acessíveis ao utilizador da máquina |
| Clickjacking e interpretação incorreta | Ações induzidas ou MIME confundido | `X-Frame-Options`, `X-Content-Type-Options`, política de permissões e referrer | Cabeçalhos protegem o browser, não aplicações desktop |
| Publicação acidental de dados | PII ou dados reais no GitHub | `.gitignore`, documentação e dados de teste fictícios | A revisão humana antes do push continua obrigatória |
| Seed conhecido na base normal | Conta previsível | Seed exige autorização, senha explícita e nome de base contendo `demo` ou `e2e` | O seed não deve ser usado com dados reais |
| Negação de serviço local | Consumo de memória ou disco | Limites de campos, passos, paginação e até 1.000 casos por exportação | Não existem quotas por utilizador numa instalação local |

## Regras operacionais

- Não versionar `.db`, `.env`, documentos, evidências ou exportações reais.
- Usar apenas dados fictícios no seed, testes e screenshots.
- Não expor a API à rede; executar em `127.0.0.1`.
- Não reutilizar a palavra-passe de demonstração noutras contas.
- Rever dependências e o histórico Git antes de publicar o portfólio.
- Investigar erros pelo `X-Request-ID`, nunca copiando cookies ou tokens para issues públicas.

## Riscos aceites nesta release

Não há TLS em localhost, recuperação automática de senha, segundo fator, encriptação da base em repouso ou proteção contra um atacante com controlo da máquina. Esses controlos não são proporcionais ao MVP local e devem ser reavaliados antes de qualquer exposição em rede ou uso com dados sensíveis.
