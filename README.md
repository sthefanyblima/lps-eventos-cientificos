# LPS para Sistemas de Gerenciamento de Eventos Científicos

**Projeto (Modelagem) e Implementação de uma Linha de Produto de Software (LPS) usando Microservices e Componentes de Software [e Agentes de IA]**

Alunas: Carla Evellyn Ferreira dos Santos e Sthefany Barboza de Lima · Disciplina: Tópicos em Engenharia de Software 2026.2 — Instituto de Computação, UFAL · Seminário base: *Tizzei et al., "Using Microservices and Software Product Line Engineering to Support Reuse of Evolving Multi-tenant SaaS", SPLC 2017.*

A LPS produz sistemas de gerenciamento de eventos científicos (simpósios, escolas regionais, semanas acadêmicas). Cada produto derivado é um **tenant**, como no WISE: roda no mesmo núcleo de microservices e se diferencia pelas features selecionadas e pelas variantes dos componentes. O relatório completo está em `docs/Relatorio_LPS_Eventos_Cientificos.pdf`.

Repositório: https://github.com/sthefanyblima/lps-eventos-cientificos

```bash
git clone https://github.com/sthefanyblima/lps-eventos-cientificos.git
cd lps-eventos-cientificos
```

## Arquitetura

- **API Gateway** (:8080, papel do Zuul): entrada única, valida o **JWT**, roteia `/api/<serviço>/...`, injeta `X-Tenant`/`X-User-*`, circuit breaker.
- **Service Registry** (:8761, papel do Eureka): os microservices se registram e enviam heartbeat; o gateway descobre os endereços por ele.
- **9 microservices**, todos com a mesma estrutura de componentes: `controller.py` (API REST) → `service.py` (regras) → `repository.py` (acesso a dados) → `model.py` (entidades ORM), com `dto.py` (Pydantic).
- **MySQL**: um banco por microservice e por tenant (`lps_<tenant>_<serviço>`), tabelas normalizadas (3FN). DDL completa em `docs/schema_mysql.sql`; Modelo ER em `docs/diagramas/`.
- **Agente de IA** (opcional) organizado segundo a arquitetura de referência de Lu et al. (2024): interação, memória, planejamento, execução, guardrails, caixa-preta e explainer.

| Microservice | Porta | Feature | Banco MySQL |
|---|---|---|---|
| Service Registry | 8761 | núcleo | — (em memória) |
| API Gateway | 8080 | núcleo | — |
| Users | 8001 | Gestão de Usuários (obrigatória) | `lps_<t>_users` |
| Events | 8002 | Gestão do Evento (obrigatória) | `lps_<t>_events` |
| Registration | 8003 | Inscrição e Agenda (obrigatória) | `lps_<t>_registration` |
| Recommendation | 8004 | Recomendação por perfil + histórico (obrigatória) | `lps_<t>_recommendation` |
| Submissions | 8005 | Submissão (opcional) | `lps_<t>_submissions` |
| Reviews | 8006 | Revisão por Pares (opcional) | `lps_<t>_reviews` |
| Certificates | 8007 | Certificados (opcional) | `lps_<t>_certificates` |
| Notifications | 8008 | Notificações (opcional) | `lps_<t>_notifications` |
| AI Agent | 8009 | Assistente IA (opcional) | `lps_<t>_ai_agent` |
| Configurador | 7000 | Tela de Configuração da LPS | arquivos JSON |

## Técnicas de reuso

| Técnica | Onde no código |
|---|---|
| Modelo de features (FODA) com mandatory / optional / xor / or e `requires` | `feature_model.json`, `spl/feature_model.py` |
| Derivação de produto (feature → microservice, ponto de variação → componente) | `spl/derivation.py` |
| Componentes com pontos de variação (padrão **Strategy**) | `components/*.py` |
| Parametrização por produto/tenant (`X-Tenant`, banco por tenant) | `common/config.py`, `common/database.py`, `products/*.json` |
| Microservices, database per service, API Gateway, Service Registry | `services/*`, `gateway/main.py`, `services/registry/main.py`, `common/discovery.py` |
| Segurança (senha PBKDF2 + JWT) | `common/security.py`, `services/users/`, `gateway/main.py` |
| Circuit Breaker e observabilidade (`/health`, `/ports`) | `common/circuit_breaker.py`, `common/client.py` |
| Coreografia por eventos de domínio | `common/events.py` → Notifications Service |
| Agentic AI (ferramentas = microservices do produto) | `components/agent.py`, `services/ai_agent/` |

## Como executar

Requisitos: Python 3.10+ e MySQL 8 (ou MariaDB 10.6+).

```bash
pip install -r requirements.txt

# MySQL: usuário da aplicação (os bancos lps_* são criados automaticamente)
mysql -u root -p -e "CREATE USER IF NOT EXISTS 'lps'@'%' IDENTIFIED BY 'lps123';
                     GRANT ALL PRIVILEGES ON \`lps\_%\`.* TO 'lps'@'%'; FLUSH PRIVILEGES;"

# 1) Ver o modelo de features
python -m spl.cli tree

# 2) Tela de Configuração (seletor de features) → http://127.0.0.1:7000
python -m spl.cli configurator

# 3) Ou derivar um produto pela linha de comando
python -m spl.cli derive "Meu Evento" Gratuito Popularidade Certificados CertParticipacao

# 4) Executar um produto (registry + microservices do produto + gateway)
python -m spl.cli run sbes-2026        # ou erbase-2026, semana-ic-ufal, meu-evento
#    Interface: http://127.0.0.1:8080/   Portas: http://127.0.0.1:8080/ports
#    Registry:  http://127.0.0.1:8761/   Swagger: http://127.0.0.1:<porta>/docs

# 5) Testes
python -m pytest -q
```

Variáveis de ambiente opcionais:

| Variável | Padrão | Uso |
|---|---|---|
| `DATABASE_URL` | `mysql+pymysql://lps:lps123@127.0.0.1:3306/{db}` | template de conexão; `{db}` vira `lps_<tenant>_<serviço>`. Sem servidor MySQL: `sqlite:///data/{db}.db` |
| `JWT_SECRET` | segredo de desenvolvimento | chave de assinatura dos tokens |
| `ANTHROPIC_API_KEY` / `ANTHROPIC_MODEL` | — | variante `AgenteLLM` com Claude; sem a chave, cai para o agente local |

### Docker

Cada produto derivado gera `products/<id>.compose.yml`, com MySQL, Service Registry, gateway e apenas os microservices desse produto:

```bash
docker compose -f products/sbes-2026.compose.yml up --build
```

## Produtos de exemplo

| Produto | Microservices | Variantes |
|---|---|---|
| `sbes-2026` | 9 (todos) | Cartão, Híbrida, Duplo-cego, Artigo + Resumo, Participação + Apresentação, E-mail + In-app, Agente LLM, memória de longo prazo |
| `erbase-2026` | 9 | PIX, Conteúdo, Simples-cego, Resumo + Pôster, Participação, In-app, Agente local |
| `semana-ic-ufal` | 5 | Gratuito, Popularidade, Participação (sem submissão, revisão, notificações ou agente) |

Contas de demonstração (senha **`senha123`**): `ana@exemplo.edu.br` (participante), `bruno@exemplo.edu.br` (autor), `carla@exemplo.edu.br` (revisor), `diego@exemplo.edu.br` (participante), `elisa@exemplo.edu.br` (organizador). O pagamento é **simulado**; o cartão de teste é `4111 1111 1111 1111`.

## Estrutura

```
feature_model.json     modelo de features (engenharia de domínio)
spl/                   feature model, derivação, CLI, launcher, Tela de Configuração
components/            componentes reutilizáveis (pontos de variação + variantes)
common/                núcleo comum: service, config, database, security, discovery,
                       client + circuit breaker, eventos
services/registry/     Service Registry (Eureka)
services/<svc>/        controller.py · dto.py · service.py · repository.py · model.py · main.py
gateway/               API Gateway (Zuul)
frontend/              interface web do produto
products/              produtos derivados (.json + .compose.yml) e mysql-init.sql
docs/                  relatório (PDF), schema_mysql.sql e diagramas
seeds/                 dados de demonstração
tests/                 testes (pytest)
```
