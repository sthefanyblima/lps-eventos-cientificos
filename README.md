# LPS para Sistemas de Gerenciamento de Eventos Científicos

**Projeto de modelagem e implementação de uma Linha de Produto de Software (LPS) usando microsserviços, componentes de software e agentes de IA.**

Alunas: Carla Evellyn Ferreira dos Santos e Sthefany Barboza de Lima · Disciplina: Tópicos em Engenharia de Software 2026.2 — Instituto de Computação, UFAL · Seminário-base: *Tizzei et al., “Using Microservices and Software Product Line Engineering to Support Reuse of Evolving Multi-tenant SaaS”, SPLC 2017.*

A LPS produz sistemas de gerenciamento de eventos científicos, como simpósios, escolas regionais e semanas acadêmicas. Cada produto derivado é um **tenant**: executa sobre o mesmo núcleo de microsserviços e varia de acordo com as features e os componentes selecionados. O relatório completo está em `docs/Relatorio_LPS_Eventos_Cientificos.pdf`.

Repositório: [github.com/sthefanyblima/lps-eventos-cientificos](https://github.com/sthefanyblima/lps-eventos-cientificos)

```bash
git clone https://github.com/sthefanyblima/lps-eventos-cientificos.git
cd lps-eventos-cientificos
```

## Arquitetura

- **API Gateway** (porta 8080, papel do Zuul): entrada única, valida JWT, roteia `/api/<serviço>/...`, injeta `X-Tenant` e `X-User-*` e usa circuit breaker.
- **Service Registry** (porta 8761, papel do Eureka): recebe registros e heartbeats dos microsserviços; o gateway consulta o registro para descobrir endereços.
- **Microsserviços**: seguem a estrutura `controller.py` (API REST) → `service.py` (regras de negócio) → `repository.py` (acesso a dados) → `model.py` (entidades ORM), com `dto.py` (Pydantic).
- **MySQL**: um banco por microsserviço e por tenant (`lps_<tenant>_<serviço>`), com tabelas normalizadas (3FN). O DDL completo está em `docs/schema_mysql.sql`; os modelos ER estão em `docs/diagramas/`.
- **Agente de IA** (opcional): organizado em interação, memória, planejamento, execução, guardrails, caixa-preta e explicações.

| Microsserviço | Porta | Feature | Banco MySQL |
| --- | ---: | --- | --- |
| Service Registry | 8761 | Núcleo | — (em memória) |
| API Gateway | 8080 | Núcleo | — |
| Users | 8001 | Gestão de Usuários (obrigatória) | `lps_<t>_users` |
| Events | 8002 | Gestão do Evento (obrigatória) | `lps_<t>_events` |
| Registration | 8003 | Inscrição e Agenda (obrigatória) | `lps_<t>_registration` |
| Recommendation | 8004 | Recomendação por perfil e histórico (obrigatória) | `lps_<t>_recommendation` |
| Submissions | 8005 | Submissão (opcional) | `lps_<t>_submissions` |
| Reviews | 8006 | Revisão por Pares (opcional) | `lps_<t>_reviews` |
| Certificates | 8007 | Certificados (opcional) | `lps_<t>_certificates` |
| Notifications | 8008 | Notificações (opcional) | `lps_<t>_notifications` |
| AI Agent | 8009 | Assistente de IA (opcional) | `lps_<t>_ai_agent` |
| Configurador | 7000 | Tela de configuração da LPS | Arquivos JSON |

## Técnicas de reuso

| Técnica | Onde está no código |
| --- | --- |
| Modelo de features (FODA) com mandatory, optional, xor, or e `requires` | `feature_model.json`, `spl/feature_model.py` |
| Derivação de produto (feature → microsserviço; ponto de variação → componente) | `spl/derivation.py` |
| Componentes com pontos de variação (padrão Strategy) | `components/*.py` |
| Parametrização por produto e tenant (`X-Tenant`, banco por tenant) | `common/config.py`, `common/database.py`, `products/*.json` |
| Microsserviços, database per service, API Gateway e Service Registry | `services/*`, `gateway/main.py`, `services/registry/main.py`, `common/discovery.py` |
| Segurança (PBKDF2 e JWT) | `common/security.py`, `services/users/`, `gateway/main.py` |
| Circuit breaker e observabilidade (`/health`, `/ports`) | `common/circuit_breaker.py`, `common/client.py` |
| Coreografia por eventos de domínio | `common/events.py` → Notifications Service |
| Agentic AI (ferramentas = microsserviços do produto) | `components/agent.py`, `services/ai_agent/` |

## Como executar localmente

### Requisitos

- Python 3.10 ou superior.
- MySQL 8 ou MariaDB 10.6 ou superior para executar com esses bancos.
- Docker Desktop, caso queira usar o MySQL em container.

### Preparar o ambiente Python

Na pasta do projeto, crie o ambiente virtual e instale as dependências.

No Windows PowerShell:

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

No macOS ou Linux:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r requirements.txt
```

### Executar a aplicação com MySQL local

O projeto usa por padrão a URL `mysql+pymysql://lps:lps123@127.0.0.1:3306/{db}`. Inicie o serviço MySQL e crie um usuário de desenvolvimento com permissão para criar os bancos da aplicação. O projeto cria as tabelas automaticamente na primeira conexão.

Depois, inicie um produto:

```powershell
\.venv\Scripts\python.exe -m spl.cli run semana-ic-ufal
```

No macOS ou Linux:

```bash
.venv/bin/python -m spl.cli run semana-ic-ufal
```

Para usar outro produto, substitua `semana-ic-ufal` por `sbes-2026`, `erbase-2026` ou pelo identificador do produto derivado.

### Executar a aplicação com Docker Compose e MySQL

O Compose inicia o MySQL, o Service Registry, o gateway e os microsserviços do produto escolhido. No Windows, mantenha o Docker Desktop aberto com o motor de Linux containers ativo.

```powershell
docker compose -f products/semana-ic-ufal.compose.yml up --build
```

Para iniciar o produto SBES 2026:

```powershell
docker compose -f products/sbes-2026.compose.yml up --build
```

Na primeira execução, o Docker baixa as imagens e compila os containers. Deixe o terminal aberto enquanto usa a aplicação. Pressione **Ctrl+C** para interromper os serviços.

### Acessar a aplicação e as APIs

- Interface: [http://127.0.0.1:8080/](http://127.0.0.1:8080/)
- Portas e estado dos serviços: [http://127.0.0.1:8080/ports](http://127.0.0.1:8080/ports)
- Swagger do gateway: [http://127.0.0.1:8080/docs](http://127.0.0.1:8080/docs)
- Painel do Service Registry: [http://127.0.0.1:8761/](http://127.0.0.1:8761/)
- Swagger de um microsserviço: `http://127.0.0.1:<porta>/docs`

### Outros comandos da LPS

```powershell
# Mostrar o modelo de features
\.venv\Scripts\python.exe -m spl.cli tree

# Abrir o configurador em http://127.0.0.1:7000
\.venv\Scripts\python.exe -m spl.cli configurator

# Derivar um produto pela linha de comando
\.venv\Scripts\python.exe -m spl.cli derive "Meu Evento" Gratuito Popularidade Certificados CertParticipacao
```

No macOS ou Linux, substitua `\.venv\Scripts\python.exe` por `.venv/bin/python`.

## Testes

Os testes ficam na pasta `tests/`:

- `test_spl.py`: testes do modelo de features, derivação, componentes, segurança, banco e agente.
- `test_extended.py`: testes de regras e componentes sem acesso ao banco de dados.
- `test_database.py`: testes que gravam e leem dados usando SQLAlchemy. Por padrão, usam arquivos SQLite temporários; com `TEST_DATABASE_URL`, podem usar o MySQL.

### Executar os testes sem banco de dados

Para rodar somente os testes sem SQL:

```powershell
\.venv\Scripts\python.exe -m pytest -q tests/test_extended.py
```

### Executar os testes de banco com SQLite

Por padrão, os testes de `test_database.py` usam SQLite temporário e não precisam de um servidor MySQL:

```powershell
\.venv\Scripts\python.exe -m pytest -q tests/test_database.py
```

### Executar os testes de banco com MySQL

O Compose pode iniciar apenas o MySQL para os testes. Execute este comando na raiz do projeto; se o serviço MySQL já estiver rodando pelo Compose, pule esta etapa:

```powershell
docker compose -f products/semana-ic-ufal.compose.yml up -d mysql
```

No mesmo terminal PowerShell, configure a URL do MySQL e rode os testes de banco:

```powershell
$env:TEST_DATABASE_URL = 'mysql+pymysql://lps:lps123@127.0.0.1:3306/{db}'
\.venv\Scripts\python.exe -m pytest -q tests/test_database.py
```

Para rodar toda a suíte, incluindo os testes de banco usando MySQL:

```powershell
\.venv\Scripts\python.exe -m pytest -q
```

Os testes do banco criam tenants temporários e removem os bancos de teste criados no MySQL ao final. Para voltar ao modo SQLite no terminal atual, remova a variável:

```powershell
Remove-Item Env:TEST_DATABASE_URL
```

## Variáveis de ambiente

| Variável | Padrão | Uso |
| --- | --- | --- |
| `DATABASE_URL` | `mysql+pymysql://lps:lps123@127.0.0.1:3306/{db}` | URL de conexão da aplicação; `{db}` vira `lps_<tenant>_<serviço>`. Para executar sem servidor MySQL, use `sqlite:///data/{db}.db`. |
| `TEST_DATABASE_URL` | Não definida | Quando definida, faz `tests/test_database.py` usar essa URL em vez de SQLite temporário. |
| `JWT_SECRET` | Segredo de desenvolvimento | Chave de assinatura dos tokens JWT. |
| `ANTHROPIC_API_KEY` | Não definida | Chave opcional para usar o provedor Claude no agente. Sem a chave, o agente usa a variante local. |
| `ANTHROPIC_MODEL` | Modelo padrão do projeto | Nome do modelo Claude usado quando `ANTHROPIC_API_KEY` está configurada. |

## Produtos de exemplo

| Produto | Microsserviços | Variantes |
| --- | ---: | --- |
| `sbes-2026` | 9 (todos) | Cartão, Híbrida, Duplo-cego, Artigo + Resumo, Participação + Apresentação, E-mail + In-app, Agente LLM e memória de longo prazo |
| `erbase-2026` | 9 | PIX, Conteúdo, Simples-cego, Resumo + Pôster, Participação, In-app e agente local |
| `semana-ic-ufal` | 5 | Gratuito, Popularidade e Participação (sem submissão, revisão, notificações ou agente) |

Contas de demonstração (senha **`senha123`**): `ana@exemplo.edu.br` (participante), `bruno@exemplo.edu.br` (autor), `carla@exemplo.edu.br` (revisor), `diego@exemplo.edu.br` (participante) e `elisa@exemplo.edu.br` (organizador). O pagamento é **simulado**; o cartão de teste é `4111 1111 1111 1111`.

## Estrutura do projeto

```text
feature_model.json     modelo de features (engenharia de domínio)
spl/                   feature model, derivação, CLI, launcher e configurador
components/            componentes reutilizáveis e variantes
common/                configuração, banco, segurança, descoberta, cliente e eventos
services/registry/     Service Registry
services/<svc>/        controller.py, dto.py, service.py, repository.py, model.py e main.py
gateway/               API Gateway
frontend/              interface web do produto
products/              configurações JSON e arquivos Docker Compose dos produtos
docs/                  relatório, schema MySQL e diagramas
seeds/                 dados de demonstração
tests/                 testes pytest
```
