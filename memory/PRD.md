# CRM SaaS Multi-Tenant — PRD & Progress Log

## Original Problem Statement (Summary)
Build a multi-tenant SaaS CRM in franchise model. Franchisor (master tenant) manages multiple
units (sub-tenants); each unit operates in isolation but franchisor has consolidated visibility.
Inspired by RD Station + HubSpot. Roles: MASTER, ADMIN, COMMERCIAL, ANALYST.

User-confirmed adapted stack:
- Frontend: React (CRA) + React Router + Zustand + React Query + shadcn/ui + @dnd-kit + Recharts
- Backend: FastAPI + Motor (async MongoDB) + JWT (PyJWT) + bcrypt
- Multi-tenant: `company_id` em todos os documentos + dependency `get_current_company` no FastAPI
- WebSockets / Celery / Workflow Builder / Webhooks → **Fase 2**

## User Personas
- **Franqueadora MASTER**: visibilidade global; pode criar empresas, ver dashboards consolidados.
- **ADMIN da unidade**: gerencia pipeline, usuários, automações da sua empresa.
- **COMMERCIAL**: vendas; só vê deals atribuídos a si mesmo (filtro automático no middleware).
- **ANALYST**: somente leitura + exportação.

## Architecture

### Backend (`/app/backend`)
- `server.py` — FastAPI app + lifespan (cria índices); router `/api`
- `db.py` — MongoDB client compartilhado
- `auth_utils.py` — bcrypt, PyJWT (HS256), access 15min + refresh 7d
- `deps.py` — `get_current_user`, `get_current_company` (valida membership), `require_roles`, `require_master`
- `models.py` — Pydantic DTOs
- `seed.py` — popular dados demo
- `routers/` — auth, contacts, pipelines, deals, analytics, companies, users, tasks, notifications

### Frontend (`/app/frontend/src`)
- `App.js` — rotas com `<ProtectedRoute>` + `<Layout>`
- `lib/api.js` — axios `withCredentials: true` + auto-refresh 401
- `stores/authStore.js` — Zustand: user, companies, activeCompanyId, login, switchCompany, logout
- `pages/` — Login, Dashboard, Contacts, ContactDetail, Pipeline (kanban), Tasks, Analytics, Settings, AdminCompanies
- `components/` — Layout, Sidebar, Header, CompanySwitcher, ProtectedRoute

## Implemented (Fase 1 — May 2026)

### Auth Multi-tenant ✓
- POST /api/auth/login (cookies httpOnly)
- POST /api/auth/refresh (auto-rotate access token)
- POST /api/auth/switch-company (reemite token para nova empresa)
- POST /api/auth/logout
- GET /api/auth/me
- POST /api/auth/forgot-password / reset-password
- PUT /api/auth/password
- Default company resolution: prioriza Franqueadora (plan=enterprise) para MASTER.

### Contatos (Leads + Clientes) ✓
- CRUD + filtros (busca, tipo, origem, score, tags, assigned_to)
- POST /:id/convert (lead → client)
- POST/DELETE /:id/tags
- POST /:id/activities (timeline + lead scoring automático)
- COMMERCIAL filtra automaticamente para `assigned_to = self`; ANALYST não pode escrever.

### Pipelines + Stages ✓
- CRUD pipeline + stages com cor, posição, SLA, conversion_probability
- PUT /pipelines/:id/stages para reordenar

### Deals (Kanban) ✓
- CRUD + listagem com nome do contato enriquecido
- PATCH /:id/stage (drag-and-drop @dnd-kit)
- POST /:id/won → marca ganho + converte contato em client + bump score
- POST /:id/lost → marca perdido com reason

### Analytics ✓
- /overview (5 KPIs)
- /funnel (stages + count + value)
- /revenue (6 meses, ganho vs previsto, labels únicos)
- /leaderboard (top vendedores via aggregation)
- /activities (volume por tipo)
- /lead-sources (distribuição por origem)

### Companies (MASTER-only) ✓
- CRUD empresas
- /companies/consolidated → métricas agregadas de todas

### Tasks ✓
- CRUD + PATCH /:id/complete (status done)

### Notifications ✓
- GET (com unread count)
- PATCH /read-all e /:id/read

### Frontend ✓
- Login com tela split (brand panel + form), credenciais demo visíveis
- Layout com Sidebar + Header com CompanySwitcher e Notifications dropdown
- Dashboard (KPI grid + Recharts AreaChart de receita + Funnel custom + Leaderboard + Lead Sources BarChart)
- Lista de Contatos com filtros avançados + Dialog de criação
- ContactDetail com timeline + ações rápidas (+Ligação, +Email, +Reunião)
- Pipeline com Kanban drag-and-drop (@dnd-kit) + atalhos won/lost por card + Dialog Novo Deal
- Tasks com pendentes/concluídas + Dialog de criação
- Analytics com PieChart + BarChart + Leaderboard table
- Settings com perfil + empresa + lista de equipe
- AdminCompanies (MASTER) com tabela consolidada + 4 KPIs totais

### Demo Data (seed.py) ✓
- 1 Franqueadora ACME (enterprise) + 3 Unidades (SP, RJ, BH)
- 1 MASTER user com acesso a todas + 4 usuários por unidade (1 ADMIN + 2 COMMERCIAL + 1 ANALYST)
- 51 contatos + 21 deals em estágios variados + tarefas + notificações
- 1 pipeline padrão por empresa com 6 stages (Novo Lead → Fechado Perdido)

### Testing ✓
- Backend: 24/24 pytest (auth, contacts, pipelines, deals, analytics, companies, tasks, notifications, multi-tenant isolation, role enforcement)
- Frontend smoke (playwright) navegação completa ok.

## Test Credentials
Ver `/app/memory/test_credentials.md`.

## Backlog (P0/P1/P2 — Fase 2)

### P0 — automações e webhooks
- Workflow Builder (canvas React Flow) com nós Gatilho/Ação/Condição/Espera
- Engine de automações (Celery + Redis substituindo BullMQ)
- Webhooks de saída (deal.won, deal.lost, contact.created, etc.) com retry
- Lead scoring assíncrono via fila

### P1 — produtividade
- Importação/Exportação CSV de contatos (job assíncrono com mapeamento)
- Custom fields configuráveis por empresa
- Produtos + deal_products (catálogo)
- WebSockets nativos FastAPI para notificações em tempo real

### P2 — diferenciais
- Gamificação (badges, ranking mensal, streaks)
- Integração WhatsApp (Evolution/Z-API) e Email (Resend/SendGrid)
- Power BI / API key endpoints (`/api/v1/export/...`)
- Audit logs UI

## Open Issues / Tech Debt
- Cookie `secure=False` em preview; mudar para `True` em produção (variável COOKIE_SECURE).
- Sem rate limiting / brute-force protection nos endpoints de auth (MVP — Fase 2).
- Sem WebSockets ainda; notificações via polling (refetchInterval 30s).
