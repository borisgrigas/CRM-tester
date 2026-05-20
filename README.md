# CRM SaaS Multi-Tenant (Franquia)

CRM no modelo franqueadora/franqueados, inspirado no RD Station e HubSpot.  
Uma franqueadora (tenant master) gerencia múltiplas unidades (sub-tenants).  
Cada unidade opera de forma isolada; a franqueadora tem visibilidade consolidada de todas.

---

## Stack

| Camada | Tecnologia |
|---|---|
| **Backend** | FastAPI (Python 3.11) + asyncpg (PostgreSQL async) + PyJWT + bcrypt |
| **Banco de dados** | PostgreSQL 16 |
| **Frontend** | React 19 + React Router 7 + Zustand + React Query v5 |
| **UI** | shadcn/ui + @dnd-kit (Kanban) + Recharts + @phosphor-icons/react |
| **Auth** | JWT access (15 min) + refresh (7 d) em cookies httpOnly, com switch-company |
| **Multi-tenant** | campo `company_id` em todas as tabelas + dependência `get_current_company` injetada via JWT |
| **Roles** | MASTER · ADMIN · COMMERCIAL · ANALYST |
| **Containers** | Docker Compose (postgres + backend + frontend) |

---

## Pré-requisitos

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) instalado e em execução

Não é necessário Python, Node ou PostgreSQL instalados localmente.

---

## Subir o sistema

```bash
docker-compose up --build
```

Na primeira execução o build leva alguns minutos (download de imagens e dependências).  
Nas execuções seguintes é quase instantâneo:

```bash
docker-compose up
```

O seed popula automaticamente o banco com dados de demonstração na inicialização.

| Serviço | URL |
|---|---|
| Frontend | http://localhost:3000 |
| Backend API | http://localhost:8001/api |
| PostgreSQL | localhost:5432 |

Para parar:

```bash
docker-compose down
```

Para resetar o banco (apaga os volumes):

```bash
docker-compose down -v
```

---

## Variáveis de ambiente

As variáveis abaixo podem ser sobrescritas em um arquivo `.env` na raiz do projeto:

| Variável | Padrão | Descrição |
|---|---|---|
| `JWT_SECRET` | `change-me-in-production-64-chars` | Chave de assinatura JWT |
| `ADMIN_EMAIL` | `master@franqueadora.com` | E-mail do usuário master gerado pelo seed |
| `ADMIN_PASSWORD` | `master123` | Senha do usuário master |
| `DATABASE_URL` | `postgresql://crm_user:crm_pass@postgres:5432/crm_saas` | Conexão PostgreSQL |
| `CORS_ORIGINS` | `http://localhost:3000` | Origens permitidas pelo CORS |

---

## Credenciais de demonstração

| Papel | E-mail | Senha | Empresa |
|---|---|---|---|
| MASTER | `master@franqueadora.com` | `master123` | Franqueadora ACME (acesso a todas) |
| ADMIN | `admin@unidade-sao-paulo.com` | `senha123` | Unidade São Paulo |
| COMMERCIAL | `vendas@unidade-sao-paulo.com` | `senha123` | Unidade São Paulo |
| COMMERCIAL | `vendas2@unidade-sao-paulo.com` | `senha123` | Unidade São Paulo |
| ANALYST | `analista@unidade-sao-paulo.com` | `senha123` | Unidade São Paulo |

> O mesmo padrão de e-mail se aplica a `unidade-rio-de-janeiro` e `unidade-belo-horizonte`.

---

## Dados populados pelo seed

- 1 Franqueadora ACME (plan: enterprise) + 3 Unidades (SP, RJ, BH)
- 1 usuário MASTER com acesso a todas as 4 empresas
- 4 usuários por unidade: 1 ADMIN + 2 COMMERCIAL + 1 ANALYST
- 17 contatos (leads + clientes) por unidade = 51 no total
- 7 deals por unidade em estágios variados = 21 no total
- 1 pipeline padrão por empresa com 6 estágios:
  `Novo Lead → Contato Feito → Proposta Enviada → Negociação → Fechado Ganho → Fechado Perdido`
- Tarefas e notificações de exemplo por unidade

---

## Rotas da API

Todas as rotas exigem `Authorization: Bearer <token>` e `X-Company-ID: <uuid>`, exceto as de auth.

### Auth

```
POST   /api/auth/login              { email, password } → access_token + refresh_token + user + companies
POST   /api/auth/refresh            (cookie refresh_token) → novo access_token
POST   /api/auth/logout             204
POST   /api/auth/switch-company     { company_id } → reemite token para outra empresa
GET    /api/auth/me                 → user + companies + active_company_id + active_role
POST   /api/auth/forgot-password    { email } → 204 (sempre, mesmo e-mail inexistente)
POST   /api/auth/reset-password     { token, new_password } → 204
PUT    /api/auth/password           { current_password, new_password } → 204
```

### Contatos

```
GET    /api/contacts                ?page&limit&search&type&assigned_to&tag&origin&score_min&score_max&sort
POST   /api/contacts                cria contato (lead ou cliente)
GET    /api/contacts/:id            detalhe
PUT    /api/contacts/:id            atualiza campos
DELETE /api/contacts/:id            soft delete (ADMIN/MASTER)
POST   /api/contacts/:id/convert    converte lead → cliente
POST   /api/contacts/:id/tags       { tags: ["VIP"] } — adiciona tags
DELETE /api/contacts/:id/tags       { tags: ["VIP"] } — remove tags
GET    /api/contacts/:id/activities timeline de atividades
POST   /api/contacts/:id/activities registra atividade (incrementa score automaticamente)
```

Score automático por tipo de atividade: `call +8 · meeting +6 · email +5 · whatsapp +4 · task +2 · note +1`

### Pipelines & Estágios

```
GET    /api/pipelines               lista pipelines com estágios aninhados
POST   /api/pipelines               cria pipeline
PUT    /api/pipelines/:id           atualiza nome/config
DELETE /api/pipelines/:id           soft delete
POST   /api/pipelines/:id/stages    cria estágio
PUT    /api/pipelines/:id/stages    reordena: [{ id, position }]
PUT    /api/pipelines/:id/stages/:stageId   atualiza estágio
DELETE /api/pipelines/:id/stages/:stageId   soft delete do estágio
```

### Deals

```
GET    /api/deals                   ?pipeline_id&stage_id&assigned_to&value_min&value_max&search
POST   /api/deals                   cria deal
GET    /api/deals/:id               detalhe + contato vinculado
PUT    /api/deals/:id               atualiza campos
DELETE /api/deals/:id               soft delete
PATCH  /api/deals/:id/stage         { stage_id } — drag-and-drop no Kanban
POST   /api/deals/:id/won           marca como ganho + converte contato para cliente
POST   /api/deals/:id/lost          { reason } — marca como perdido
```

### Analytics

```
GET    /api/analytics/overview      ?from&to&pipeline_id → KPIs: leads, clientes, deals, conversão, valor
GET    /api/analytics/funnel        ?pipeline_id → contagem e valor por estágio
GET    /api/analytics/revenue       ?months=6 → receita ganha vs. prevista por mês
GET    /api/analytics/leaderboard   top vendedores por valor ganho
GET    /api/analytics/activities    volume de atividades por tipo
GET    /api/analytics/lead-sources  distribuição de leads por origem
```

### Empresas (MASTER)

```
GET    /api/companies               lista todas as empresas
POST   /api/companies               cria empresa (slug único e imutável)
GET    /api/companies/consolidated  métricas agregadas de todas as unidades
GET    /api/companies/:id           detalhe
PUT    /api/companies/:id           atualiza (slug não pode ser alterado)
PATCH  /api/companies/:id/activate  ativa empresa
PATCH  /api/companies/:id/deactivate inativa empresa (bloqueia login dos membros)
DELETE /api/companies/:id           soft delete
GET    /api/companies/:id/users     membros da empresa
```

### Usuários (ADMIN/MASTER)

```
GET    /api/users                   lista membros da empresa ativa
POST   /api/users/invite            convida: { name, email, role, password }
PUT    /api/users/:id/role          { role } — ADMIN não pode alterar outro ADMIN/MASTER
PATCH  /api/users/:id/activate      ativa membro na empresa
PATCH  /api/users/:id/deactivate    inativa (protegido: não pode ser o último ADMIN)
DELETE /api/users/:id               remove da empresa (registro de usuário é preservado)
GET    /api/profile                 perfil do usuário autenticado
PUT    /api/profile                 atualiza nome e avatar
```

### Tarefas e Notificações

```
GET    /api/tasks                   ?status&priority&assigned_to
POST   /api/tasks                   cria tarefa
PUT    /api/tasks/:id               atualiza
PATCH  /api/tasks/:id/complete      marca como concluída
DELETE /api/tasks/:id               remove (hard delete)

GET    /api/notifications           lista (não lidas primeiro) + unread count
PATCH  /api/notifications/read-all  marca todas como lidas
PATCH  /api/notifications/:id/read  marca uma como lida
```

---

## Matriz de permissões

| Recurso | MASTER | ADMIN | COMMERCIAL | ANALYST |
|---|:---:|:---:|:---:|:---:|
| Ver/criar/editar empresas | ✓ | ✗ | ✗ | ✗ |
| Ativar/inativar empresa | ✓ | ✗ | ✗ | ✗ |
| Convidar usuários | ✓ | ✓ ¹ | ✗ | ✗ |
| Alterar role / ativar / inativar usuário | ✓ | ✓ ¹ | ✗ | ✗ |
| Gerenciar pipelines e estágios | ✓ | ✓ | ✗ | ✗ |
| Criar e editar contatos | ✓ | ✓ | ✓ | ✗ |
| Deletar contatos | ✓ | ✓ | ✗ | ✗ |
| Criar e mover deals (Kanban) | ✓ | ✓ | ✓ | ✗ |
| Ver deals de outros vendedores | ✓ | ✓ | ✗ | ✓ |
| Ver dashboards e analytics | ✓ | ✓ | ✓ | ✓ |

¹ ADMIN não pode atuar sobre outro ADMIN ou sobre um MASTER.

### Regras de negócio

- **Slug imutável** — não pode ser alterado após a criação da empresa.
- **Último ADMIN protegido** — não é possível inativar ou remover o único ADMIN ativo de uma empresa.
- **Empresa inativa bloqueia login** — `get_current_company` valida `is_active` e `deleted_at` a cada requisição.
- **Soft delete** — empresas e contatos usam `deleted_at`; o registro de membership é deletado mas o `users` é preservado.
- **Isolamento multi-tenant** — todas as queries filtram por `company_id`; um tenant jamais vê dados de outro.

---

## Testes

Os testes são de integração HTTP — sobem um banco PostgreSQL real e disparam requisições contra o servidor.

```bash
# Rodar dentro do container (banco já disponível)
docker exec crm_backend python -m pytest tests/ -v
```

44 testes cobrindo: autenticação, refresh, switch-company, isolamento multi-tenant, CRUD completo de contatos/deals/pipelines, analytics, RBAC, gestão de empresas e usuários.

---

## Estrutura do projeto

```
crm-saas/
├── backend/
│   ├── server.py                FastAPI app + lifespan (init/close pool PostgreSQL)
│   ├── auth_utils.py            bcrypt + PyJWT (HS256)
│   ├── deps.py                  get_current_user · get_current_company · require_roles
│   ├── db.py                    pool asyncpg + CREATE TABLE (11 tabelas) + codec JSONB
│   ├── models.py                Pydantic DTOs
│   ├── seed.py                  dados de demonstração (truncate + inserts SQL)
│   ├── requirements.txt
│   ├── Dockerfile
│   ├── routers/
│   │   ├── auth_router.py
│   │   ├── contacts_router.py
│   │   ├── pipelines_router.py
│   │   ├── deals_router.py
│   │   ├── analytics_router.py
│   │   ├── companies_router.py
│   │   ├── users_router.py
│   │   ├── tasks_router.py
│   │   └── notifications_router.py
│   └── tests/
│       ├── conftest.py          fixtures: pool, tokens, company/user helpers
│       ├── backend_test.py      auth, contatos, deals, pipelines, analytics (integração)
│       └── test_admin_features.py  RBAC, empresas, usuários, regras de negócio
├── frontend/
│   ├── src/
│   │   ├── App.js               rotas + ProtectedRoute + Layout
│   │   ├── lib/api.js           axios + interceptor de auto-refresh 401
│   │   ├── stores/authStore.js  Zustand: user, companies, switchCompany
│   │   ├── components/
│   │   │   ├── Sidebar.jsx
│   │   │   ├── Header.jsx
│   │   │   ├── CompanySwitcher.jsx
│   │   │   └── ui/              shadcn/ui
│   │   └── pages/
│   │       ├── Login.jsx
│   │       ├── Dashboard.jsx        KPIs + gráficos Recharts
│   │       ├── Contacts.jsx         listagem com filtros
│   │       ├── ContactDetail.jsx    timeline de atividades + deals vinculados
│   │       ├── Pipeline.jsx         Kanban drag-and-drop (@dnd-kit)
│   │       ├── Tasks.jsx
│   │       ├── Analytics.jsx        funil, receita, leaderboard, origens
│   │       ├── Settings.jsx
│   │       ├── AdminUsers.jsx       gestão de usuários (ADMIN + MASTER)
│   │       └── AdminCompanies.jsx   gestão de empresas (MASTER)
│   ├── Dockerfile
│   └── package.json
├── docker-compose.yml
└── README.md
```

---

## Roadmap (fora do MVP)

- Workflow Builder (canvas de automações) + Engine assíncrona (Celery + Redis)
- WebSockets para notificações em tempo real
- Importação/Exportação CSV de contatos
- Webhooks de saída (`deal.won`, `contact.created`) com retry
- Lead scoring assíncrono em fila
- Campos customizáveis por empresa (custom_fields configuráveis via UI)
- Gamificação: badges e ranking mensal por vendedor
- Integração WhatsApp (Evolution API / Z-API)
- Integração de e-mail transacional (Resend / SendGrid)
- Endpoints de API key para integrações externas / Power BI
- UI de audit logs

---

## Licença

Privado — uso interno.
