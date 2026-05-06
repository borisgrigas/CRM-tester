# CRM SaaS Multi-Tenant (Franquia) — MVP

CRM SaaS no modelo franqueadora/franqueados, inspirado no RD Station + HubSpot.
Uma franqueadora (tenant master) gerencia múltiplas unidades (sub-tenants).
Cada unidade opera de forma isolada, mas a franqueadora tem visibilidade consolidada.

---

## Stack

- **Backend:** FastAPI (Python 3.11) + Motor (MongoDB async) + PyJWT + bcrypt
- **Frontend:** React 19 (CRA) + React Router 7 + Zustand + React Query v5 + shadcn/ui + @dnd-kit + Recharts + @phosphor-icons/react
- **Multi-tenant:** campo `company_id` em todos os documentos + dependency `get_current_company` injetada via JWT
- **Auth:** JWT access (15min) + refresh (7d) em **cookies httpOnly**, com switch-company
- **Roles:** MASTER, ADMIN, COMMERCIAL, ANALYST

---

## Pré-requisitos

- Python 3.11+
- Node.js 18+
- Yarn 1.22+ (`npm install -g yarn`)
- MongoDB 7+ rodando localmente em `mongodb://localhost:27017` (ou ajuste `MONGO_URL`)

---

## Como rodar localmente

### Opção A — Script único

```bash
chmod +x build.sh
./build.sh
```

Depois:

```bash
# Terminal 1
cd backend && uvicorn server:app --host 0.0.0.0 --port 8001 --reload

# Terminal 2
cd frontend && yarn start
```

A app abre em **http://localhost:3000**.

### Opção B — Docker Compose

```bash
docker-compose up --build
```

Sobe MongoDB + backend + frontend juntos.

### Opção C — Manual

```bash
# 1. .env
cp .env.example backend/.env
# edite backend/.env conforme necessário
echo "REACT_APP_BACKEND_URL=http://localhost:8001" > frontend/.env
echo "WDS_SOCKET_PORT=0" >> frontend/.env

# 2. Backend
cd backend
pip install -r requirements.txt
python seed.py        # popula dados demo
uvicorn server:app --host 0.0.0.0 --port 8001 --reload

# 3. Frontend
cd ../frontend
yarn install
yarn start
```

---

## Credenciais de demonstração (criadas pelo seed)

| Papel       | Email                                | Senha       | Empresa             |
|-------------|---------------------------------------|-------------|---------------------|
| MASTER      | `master@franqueadora.com`             | `master123` | Franqueadora ACME   |
| ADMIN       | `admin@unidade-sao-paulo.com`         | `senha123`  | Unidade São Paulo   |
| COMMERCIAL  | `vendas@unidade-sao-paulo.com`        | `senha123`  | Unidade São Paulo   |
| COMMERCIAL  | `vendas2@unidade-sao-paulo.com`       | `senha123`  | Unidade São Paulo   |
| ANALYST     | `analista@unidade-sao-paulo.com`      | `senha123`  | Unidade São Paulo   |

> O mesmo padrão se aplica a `unidade-rio-de-janeiro` e `unidade-belo-horizonte`.
> O usuário **MASTER** tem acesso (role MASTER) a todas as 4 empresas.

---

## Dados de demonstração populados

- 1 Franqueadora ACME (plan: enterprise) + 3 Unidades (SP, RJ, BH)
- 1 usuário MASTER + 4 usuários por unidade (1 ADMIN + 2 COMMERCIAL + 1 ANALYST)
- 51 contatos (leads + clientes) distribuídos
- 21 deals em estágios variados
- 1 pipeline padrão por empresa com 6 estágios (Novo Lead → Fechado Perdido)
- Tarefas e notificações de exemplo

---

## Matriz de Permissões

| Recurso                    | MASTER | ADMIN  | COMMERCIAL | ANALYST |
|----------------------------|--------|--------|------------|---------|
| Ver todas as empresas      | ✓      | ✗      | ✗          | ✗       |
| Criar/Editar empresa       | ✓      | ✗      | ✗          | ✗       |
| Convidar usuário           | ✓      | ✓ ¹   | ✗          | ✗       |
| Alterar role               | ✓      | ✓ ¹   | ✗          | ✗       |
| Ativar/Inativar usuário    | ✓      | ✓ ¹   | ✗          | ✗       |
| Gerenciar pipelines        | ✓      | ✓      | ✗          | ✗       |
| Criar/editar contatos      | ✓      | ✓      | ✓          | ✗       |
| Mover deals (kanban)       | ✓      | ✓      | ✓          | ✗       |
| Ver todos os deals         | ✓      | ✓      | apenas seus| ✓       |
| Ver dashboards             | ✓      | ✓      | ✓          | ✓       |

¹ ADMIN não pode atuar sobre outro ADMIN ou MASTER.

### Regras de negócio adicionais

- ❌ **Slug imutável** após criação da empresa.
- ❌ **Não é possível inativar o último ADMIN** ativo de uma empresa.
- ❌ **Empresa inativa** rejeita o JWT de qualquer usuário daquela empresa (`get_current_company` valida `is_active` e `deleted_at`).
- ❌ **Soft delete** em empresas (campo `deleted_at`); usuários removidos da empresa têm o registro de membership deletado, mas o documento `users` permanece.

---

## Rotas da API (todas com prefixo `/api`)

### Auth
```
POST   /api/auth/login              { email, password } → cookies + user + companies
POST   /api/auth/refresh            (cookie) → novo access_token
POST   /api/auth/logout             204
POST   /api/auth/switch-company     { company_id } → reemite token
GET    /api/auth/me                 → user + companies + active_company_id + active_role
POST   /api/auth/forgot-password    { email } → 204
POST   /api/auth/reset-password     { token, new_password } → 204
PUT    /api/auth/password           { current_password, new_password } → 204
```

### Contatos
```
GET    /api/contacts                ?page&limit&search&type&assigned_to&tag&origin&score_min&score_max&sort
POST   /api/contacts                cria contato
GET    /api/contacts/:id            detalhe + activities + deals
PUT    /api/contacts/:id            atualiza
DELETE /api/contacts/:id            soft delete (apenas ADMIN/MASTER)
POST   /api/contacts/:id/convert    lead → cliente
POST   /api/contacts/:id/tags       { tags: [] }
DELETE /api/contacts/:id/tags       { tags: [] }
GET    /api/contacts/:id/activities timeline
POST   /api/contacts/:id/activities registra atividade (incrementa score)
```

### Pipelines & Stages
```
GET    /api/pipelines               lista pipelines + stages aninhados
POST   /api/pipelines               cria pipeline
PUT    /api/pipelines/:id           atualiza
DELETE /api/pipelines/:id           soft delete
POST   /api/pipelines/:id/stages    cria estágio
PUT    /api/pipelines/:id/stages    reordena: [{ id, position }]
PUT    /api/pipelines/:id/stages/:stageId   atualiza
DELETE /api/pipelines/:id/stages/:stageId   soft delete
```

### Deals
```
GET    /api/deals                   ?pipeline_id&stage_id&assigned_to&value_min&value_max&search
POST   /api/deals                   cria
GET    /api/deals/:id               detalhe + contato
PUT    /api/deals/:id               atualiza
DELETE /api/deals/:id               soft delete
PATCH  /api/deals/:id/stage         { stage_id, pipeline_id? } — drag-and-drop
POST   /api/deals/:id/won           marca ganho + converte contato
POST   /api/deals/:id/lost          { reason }
```

### Analytics
```
GET    /api/analytics/overview      ?from&to&pipeline_id → 5 KPIs
GET    /api/analytics/funnel        ?pipeline_id → stages com count + value
GET    /api/analytics/revenue       ?months=6 → ganho vs previsto por mês
GET    /api/analytics/leaderboard   top vendedores
GET    /api/analytics/activities    volume por tipo
GET    /api/analytics/lead-sources  distribuição por origem
```

### Companies (apenas MASTER, exceto onde indicado)
```
GET    /api/companies                     lista todas
POST   /api/companies                     cria nova empresa (slug único)
GET    /api/companies/consolidated        métricas agregadas de todas
GET    /api/companies/:id                 detalhe
PUT    /api/companies/:id                 atualiza (slug imutável)
PATCH  /api/companies/:id/activate        ativa empresa
PATCH  /api/companies/:id/deactivate      inativa (bloqueia login dos membros)
DELETE /api/companies/:id                 soft delete
GET    /api/companies/:id/users           usuários da empresa
```

### Users (ADMIN/MASTER)
```
GET    /api/users                         lista membros da empresa ativa
POST   /api/users/invite                  convida { name, email, role, password }
PUT    /api/users/:id/role                { role } — ADMIN não pode promover ADMIN/MASTER
PATCH  /api/users/:id/activate            ativa membro na empresa
PATCH  /api/users/:id/deactivate          inativa (não pode ser o último ADMIN)
DELETE /api/users/:id                     remove da empresa (mantém users doc)
GET    /api/profile                       perfil próprio
PUT    /api/profile                       atualiza nome/avatar
```

### Tarefas e Notificações
```
GET    /api/tasks                         ?status&priority&assigned_to
POST   /api/tasks                         cria
PUT    /api/tasks/:id                     atualiza
PATCH  /api/tasks/:id/complete            conclui
DELETE /api/tasks/:id                     remove

GET    /api/notifications                 lista (não lidas primeiro) + unread count
PATCH  /api/notifications/read-all        marca todas como lidas
PATCH  /api/notifications/:id/read        marca uma
```

---

## Estrutura do projeto

```
crm-saas/
├── backend/
│   ├── server.py                FastAPI app + lifespan (índices)
│   ├── auth_utils.py            bcrypt + PyJWT (HS256)
│   ├── deps.py                  get_current_user, get_current_company, require_roles
│   ├── db.py                    Motor client compartilhado
│   ├── models.py                Pydantic DTOs
│   ├── seed.py                  dados de demonstração
│   ├── requirements.txt
│   ├── .env                     (criado pelo build.sh)
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
│   └── tests/                   24 testes pytest (auth, multi-tenant, CRUD, RBAC)
├── frontend/
│   ├── src/
│   │   ├── App.js               rotas + ProtectedRoute + Layout
│   │   ├── lib/api.js           axios + auto-refresh 401
│   │   ├── stores/authStore.js  Zustand: user, companies, switchCompany
│   │   ├── components/
│   │   │   ├── Sidebar.jsx
│   │   │   ├── Header.jsx
│   │   │   ├── CompanySwitcher.jsx
│   │   │   ├── Layout.jsx
│   │   │   ├── ProtectedRoute.jsx
│   │   │   └── ui/              shadcn/ui
│   │   └── pages/
│   │       ├── Login.jsx
│   │       ├── Dashboard.jsx    KPIs + gráficos
│   │       ├── Contacts.jsx
│   │       ├── ContactDetail.jsx
│   │       ├── Pipeline.jsx     Kanban @dnd-kit
│   │       ├── Tasks.jsx
│   │       ├── Analytics.jsx
│   │       ├── Settings.jsx
│   │       ├── AdminUsers.jsx       gestão de usuários (ADMIN+MASTER)
│   │       └── AdminCompanies.jsx   gestão de empresas (MASTER)
│   └── package.json
├── docker-compose.yml
├── .env.example
├── build.sh
└── README.md
```

---

## Testes

### Backend

```bash
cd backend
python -m pytest tests/ -v
```

24 testes cobrindo: auth, switch-company, isolamento multi-tenant, CRUD de contatos/deals/pipelines, analytics, RBAC, gestão de empresas e usuários.

### Frontend

Smoke tests rodam via Playwright no Chromium (login → dashboard → contatos → kanban → admin).

---

## O que está fora do MVP (Fase 2)

- Workflow Builder (canvas) + Engine de automações (Celery + Redis)
- WebSockets nativos (notificações em tempo real)
- Importação/Exportação CSV de contatos
- Webhooks de saída (deal.won, contact.created…) com retry
- Lead scoring assíncrono em fila
- Produtos + custom_fields configuráveis
- Gamificação (badges, ranking mensal)
- Integrações WhatsApp (Evolution/Z-API), Email (Resend/SendGrid)
- Power BI / API key endpoints
- UI de audit logs

---

## Licença

Privado — uso interno da franqueadora.
