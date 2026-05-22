# CRM SaaS Multi-Tenant (Franquia)

CRM no modelo franqueadora/franqueados, inspirado no RD Station e HubSpot.  
Uma franqueadora (tenant master) gerencia múltiplas unidades (sub-tenants).  
Cada unidade opera de forma isolada; a franqueadora tem visibilidade consolidada de todas.

---

## Sumário

- [Stack](#stack)
- [Arquitetura](#arquitetura)
- [Pré-requisitos](#pré-requisitos)
- [Subir o sistema (dev local)](#subir-o-sistema-dev-local)
- [Variáveis de ambiente](#variáveis-de-ambiente)
- [Credenciais de demonstração](#credenciais-de-demonstração)
- [Dados populados pelo seed](#dados-populados-pelo-seed)
- [Módulos e Feature Flags](#módulos-e-feature-flags)
- [Estrutura do projeto](#estrutura-do-projeto)
- [Schema do banco de dados](#schema-do-banco-de-dados)
- [Rotas da API](#rotas-da-api)
- [Matriz de permissões](#matriz-de-permissões)
- [Regras de negócio](#regras-de-negócio)
- [Integrações externas](#integrações-externas)
- [Testes](#testes)
- [Deploy em produção](#deploy-em-produção)
- [Roadmap](#roadmap)
- [Licença](#licença)

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
| **Containers** | Docker Compose (dev) · Dockerfiles individuais (produção) |

---

## Arquitetura

```
Internet
   │
   ├─► Frontend  (React SPA — build estático via serve)
   │       └── chama ──► Backend API  (FastAPI + uvicorn, 2 workers)
   │                          └── conecta ──► PostgreSQL
   │
   ├─► Webhooks públicos  POST /api/webhooks/{slug}/{source}
   │
   └─► WhatsApp inbound   POST /api/whatsapp/inbound/{slug}
```

O `docker-compose.yml` é para **desenvolvimento local** apenas.  
Em produção, cada serviço é implantado pelo seu próprio Dockerfile (ver [docs/DEPLOY.md](docs/DEPLOY.md)).

---

## Pré-requisitos

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) instalado e em execução

Não é necessário Python, Node ou PostgreSQL instalados localmente.

---

## Subir o sistema (dev local)

### 1. Configurar variáveis

```bash
cp .env.example .env
# Edite .env se quiser ajustar credenciais, portas, etc.
```

### 2. Build e subida

```bash
docker-compose up --build
```

Na primeira execução o build leva alguns minutos (download de imagens e dependências).  
Nas execuções seguintes:

```bash
docker-compose up
```

O seed popula automaticamente o banco com dados de demonstração a cada inicialização.

| Serviço | URL |
|---|---|
| Frontend | http://localhost:3000 |
| Backend API | http://localhost:8001/api |
| Swagger UI | http://localhost:8001/docs |
| PostgreSQL | localhost:5432 |

### 3. Parar / resetar

```bash
# Parar sem apagar dados
docker-compose down

# Resetar banco (apaga volumes)
docker-compose down -v
```

> **Atenção:** `seed.py` roda a cada `docker-compose up` e **trunca todos os dados** antes de repopular. Não use para persistir dados reais em desenvolvimento.

---

## Variáveis de ambiente

Copie `.env.example` para `.env` — os valores padrão já funcionam localmente.

| Variável | Padrão (dev) | Descrição |
|---|---|---|
| `JWT_SECRET` | `local-dev-secret-not-for-production` | Chave de assinatura JWT — use `openssl rand -hex 64` em produção |
| `ADMIN_EMAIL` | `master@franqueadora.com` | E-mail do usuário master criado pelo seed |
| `ADMIN_PASSWORD` | `master123` | Senha do usuário master |
| `POSTGRES_DB` | `crm_saas` | Nome do banco |
| `POSTGRES_USER` | `crm_user` | Usuário do banco |
| `POSTGRES_PASSWORD` | `crm_pass` | Senha do banco |
| `POSTGRES_PORT` | `5432` | Porta exposta do PostgreSQL |
| `BACKEND_PORT` | `8001` | Porta do backend |
| `FRONTEND_PORT` | `3000` | Porta do frontend |
| `CORS_ORIGINS` | `http://localhost:3000` | Origens CORS permitidas (sem `*` em produção) |
| `REACT_APP_BACKEND_URL` | `http://localhost:8001` | URL do backend — **build-time ARG** do React |

---

## Credenciais de demonstração

| Papel | E-mail | Senha | Empresa |
|---|---|---|---|
| MASTER | `master@franqueadora.com` | `master123` | Franqueadora ACME (acesso a todas) |
| ADMIN | `admin@unidade-sao-paulo.com` | `senha123` | Unidade São Paulo |
| COMMERCIAL | `vendas@unidade-sao-paulo.com` | `senha123` | Unidade São Paulo |
| COMMERCIAL | `vendas2@unidade-sao-paulo.com` | `senha123` | Unidade São Paulo |
| ANALYST | `analista@unidade-sao-paulo.com` | `senha123` | Unidade São Paulo |

> O mesmo padrão de e-mail (`admin@`, `vendas@`, `analista@`) existe para `unidade-rio-de-janeiro` e `unidade-belo-horizonte`.

---

## Dados populados pelo seed

- **1 Franqueadora ACME** (plan: enterprise, `is_franchisor: true`) + **3 Unidades** (SP, RJ, BH)
- **1 usuário MASTER** com membership em todas as 4 empresas
- **4 usuários por unidade**: 1 ADMIN + 2 COMMERCIAL + 1 ANALYST = 12 usuários
- **17 contatos** por unidade (leads + clientes) = 51 no total
- **7 deals** por unidade em estágios variados = 21 no total
- **1 pipeline padrão** por empresa com 6 estágios:  
  `Novo Lead → Contato Feito → Proposta Enviada → Negociação → Fechado Ganho → Fechado Perdido`
- **Feature flags** ativas: `franchise` e `whatsapp` para a franqueadora; `whatsapp` para as unidades
- Tarefas e notificações de exemplo por unidade

---

## Módulos e Feature Flags

O sistema usa um mecanismo de **feature flags por empresa** para controlar o acesso a módulos opcionais.

### Módulos disponíveis

| ID | Label | Flag obrigatória | Acesso mínimo |
|---|---|---|---|
| `dashboard` | Dashboard | — (sempre visível) | view |
| `contacts` | Contatos | — | view |
| `pipeline` | Pipeline | — | view |
| `tasks` | Tarefas | — | view |
| `analytics` | Analytics | — | view |
| `settings` | Configurações | — | view |
| `franchise` | Franquias | `franchise` | view |
| `whatsapp` | WhatsApp | `whatsapp` | view |
| `map` | Mapa | — | view |

### Como funciona

1. **Feature flags** são registros na tabela `feature_flags` (por empresa).  
   Ex: `{ company_id, name: "franchise", value: true, is_active: true }`.

2. **`ModuleGuard`** (frontend) lê as flags da empresa ativa e o role do usuário.  
   Se a flag não existir ou `is_active = false`, o módulo não aparece no sidebar.

3. **MASTER e ADMIN** recebem nível `"manage"` em todos os módulos.  
   **COMMERCIAL** recebe `"use"`. **ANALYST** recebe `"view"`.

4. Flags podem ser gerenciadas via API:
   ```
   GET  /api/admin/flags          → lista flags da empresa
   PUT  /api/admin/flags/{name}   → ativa/desativa ou atualiza valor
   ```

---

## Estrutura do projeto

```
crm-saas/
├── .env.example                  Variáveis de dev (copie para .env)
├── .env.production.example       Template de produção (placeholders)
├── docker-compose.yml            Dev local — postgres + backend + frontend
├── docs/
│   └── DEPLOY.md                 Guia completo de deploy (Railway, Render, Fly.io, VPS)
│
├── backend/
│   ├── server.py                 FastAPI app + lifespan (init/close pool PostgreSQL)
│   ├── auth_utils.py             bcrypt + PyJWT (HS256)
│   ├── deps.py                   get_current_user · get_current_company · require_roles
│   ├── db.py                     pool asyncpg + CREATE TABLE (11 tabelas base) + codec JSONB
│   ├── models.py                 Pydantic DTOs compartilhados
│   ├── seed.py                   Dados de demonstração (truncate + inserts SQL) — dev apenas
│   ├── requirements.txt
│   ├── Dockerfile                prod: uvicorn --workers 2 (sem seed)
│   │
│   ├── core/
│   │   ├── schema_extra.sql      Tabelas extras + ALTER TABLE idempotentes
│   │   ├── feature_flags.py      get_company_flags(conn, company_id) → dict
│   │   ├── permissions.py        get_user_permissions(conn, user_id, company_id) → list
│   │   └── access_deps.py        Dependências de acesso granular
│   │
│   ├── routers/
│   │   ├── auth_router.py        Login, refresh, logout, switch-company, senha
│   │   ├── contacts_router.py    CRUD contatos + atividades + tags + score
│   │   ├── pipelines_router.py   CRUD pipelines e estágios
│   │   ├── deals_router.py       CRUD deals + Kanban move + won/lost
│   │   ├── analytics_router.py   KPIs, funil, receita, leaderboard, atividades, origens
│   │   ├── companies_router.py   CRUD empresas + visão consolidada (MASTER/ADMIN)
│   │   ├── users_router.py       Convite, roles, ativação, perfil
│   │   ├── tasks_router.py       CRUD tarefas
│   │   ├── notifications_router.py  Listagem + marcar lida
│   │   ├── map_router.py         Pins georreferenciados + heatmap + settings
│   │   └── admin_router.py       Feature flags + permissões granulares
│   │
│   ├── integrations/
│   │   ├── webhook_router.py     Ingestão de leads externos (Meta, RD Station, genérico)
│   │   └── whatsapp_router.py    Mensagens inbound/outbound + conversas
│   │
│   └── tests/
│       ├── conftest.py           Fixtures: pool, tokens, helpers de empresa/usuário
│       ├── backend_test.py       Auth, contatos, deals, pipelines, analytics (integração)
│       └── test_admin_features.py   RBAC, empresas, usuários, regras de negócio
│
└── frontend/
    ├── Dockerfile                Multi-stage: yarn build → serve@14 runtime
    ├── package.json
    └── src/
        ├── App.js                Rotas + ProtectedRoute + Layout
        ├── lib/
        │   ├── api.js            axios + interceptor de auto-refresh em 401
        │   ├── moduleRegistry.js Definição dos módulos e flags
        │   └── utils.js          cn() e helpers
        ├── stores/
        │   └── authStore.js      Zustand: user, companies, switchCompany
        ├── components/
        │   ├── Sidebar.jsx       Navegação lateral com visibilidade por módulo
        │   ├── Header.jsx        Barra superior + notificações
        │   ├── CompanySwitcher.jsx  Troca de empresa sem logout
        │   ├── ModuleGuard.jsx   HOC de controle de acesso por módulo/nível
        │   ├── Layout.jsx        Wrapper sidebar + header
        │   └── ui/               shadcn/ui — 30+ componentes
        ├── pages/
        │   ├── Login.jsx
        │   ├── Dashboard.jsx     KPIs + gráficos Recharts
        │   ├── Contacts.jsx      Listagem com filtros avançados
        │   ├── ContactDetail.jsx Timeline de atividades + deals vinculados
        │   ├── Pipeline.jsx      Kanban drag-and-drop (@dnd-kit)
        │   ├── Tasks.jsx
        │   ├── Analytics.jsx     Funil, receita, leaderboard, origens de lead
        │   ├── Settings.jsx
        │   ├── AdminUsers.jsx    Gestão de usuários (ADMIN + MASTER)
        │   └── AdminCompanies.jsx  Gestão de empresas (MASTER)
        └── features/
            ├── admin/
            │   └── AdminPanel.jsx  Painel de feature flags e permissões
            ├── franchise/
            │   └── FranchisePage.jsx  Visão consolidada da rede de franquias
            ├── map/
            │   └── MapPage.jsx    Mapa interativo com pins e heatmap
            └── whatsapp/
                └── WhatsAppPage.jsx  Conversas e envio de mensagens
```

---

## Schema do banco de dados

### Tabelas base (`db.py`)

| Tabela | Descrição |
|---|---|
| `users` | Usuários (e-mail único, senha com bcrypt) |
| `companies` | Empresas/tenants (slug único e imutável) |
| `user_companies` | Membership usuário↔empresa (role, is_active) |
| `contacts` | Leads e clientes por empresa |
| `contact_activities` | Timeline de atividades por contato |
| `pipelines` | Pipelines de vendas por empresa |
| `pipeline_stages` | Estágios de cada pipeline (posição, cor, SLA) |
| `deals` | Oportunidades vinculadas a contato e pipeline |
| `tasks` | Tarefas por empresa |
| `notifications` | Notificações por usuário e empresa |
| `password_reset_tokens` | Tokens de recuperação de senha (expiram em 1h) |

### Tabelas extras (`core/schema_extra.sql`)

| Tabela | Descrição |
|---|---|
| `feature_flags` | Flags de módulos opcionais por empresa |
| `permissions` | Permissões granulares por usuário e empresa |
| `map_settings` | Configurações do mapa por empresa (centro, zoom, cores) |
| `whatsapp_messages` | Log de mensagens WhatsApp (inbound e outbound) |

### Colunas extras em tabelas base

| Tabela | Colunas adicionadas |
|---|---|
| `contacts` | `address`, `latitude`, `longitude`, `whatsapp_phone`, `cep`, `street`, `street_number`, `neighborhood`, `city`, `state`, `notes`, `region_interest`, `is_sold_store` |
| `users` | `phone`, `cpf` (com índice único parcial `WHERE cpf IS NOT NULL`) |

### Índices

```sql
idx_contacts_company_type         ON contacts(company_id, type)
idx_deals_company_pipeline_stage  ON deals(company_id, pipeline_id, stage_id)
idx_activities_contact            ON contact_activities(contact_id, occurred_at DESC)
idx_uc_user                       ON user_companies(user_id)
idx_uc_company                    ON user_companies(company_id)
idx_feature_flags_company         ON feature_flags(company_id) WHERE is_active
idx_permissions_user              ON permissions(company_id, user_id)
idx_whatsapp_contact              ON whatsapp_messages(company_id, contact_id)
idx_users_cpf                     ON users(cpf) WHERE cpf IS NOT NULL
```

---

## Rotas da API

Todas as rotas autenticadas exigem:
- `Authorization: Bearer <access_token>`
- `X-Company-ID: <uuid>` (ou `company_id` no payload do JWT)

Exceções: rotas de auth, `/api/webhooks/{slug}/{source}` e `/api/whatsapp/inbound/{slug}`.

---

### Auth

```
POST   /api/auth/login              { email, password }
                                    → access_token, refresh_token (cookie), user, companies
POST   /api/auth/refresh            (cookie refresh_token) → novo access_token
POST   /api/auth/logout             204
POST   /api/auth/switch-company     { company_id } → reemite token para outra empresa
GET    /api/auth/me                 → user + companies + active_company_id + active_role
POST   /api/auth/forgot-password    { email } → 204 (sempre, mesmo e-mail inexistente)
POST   /api/auth/reset-password     { token, new_password } → 204
PUT    /api/auth/password           { current_password, new_password } → 204
```

---

### Contatos

```
GET    /api/contacts                ?page&limit&search&type&assigned_to&tag
                                    &origin&score_min&score_max&sort
POST   /api/contacts                Cria contato (lead ou cliente)
GET    /api/contacts/:id            Detalhe
PUT    /api/contacts/:id            Atualiza campos
DELETE /api/contacts/:id            Soft delete (ADMIN/MASTER)
POST   /api/contacts/:id/convert    Converte lead → cliente
POST   /api/contacts/:id/tags       { tags: ["VIP"] } — adiciona tags
DELETE /api/contacts/:id/tags       { tags: ["VIP"] } — remove tags
GET    /api/contacts/:id/activities Timeline de atividades (paginada)
POST   /api/contacts/:id/activities Registra atividade (incrementa score)
```

**Score automático por tipo de atividade:**

| Tipo | Pontos |
|---|---|
| `call` | +8 |
| `meeting` | +6 |
| `email` | +5 |
| `whatsapp` | +4 |
| `task` | +2 |
| `note` | +1 |

---

### Pipelines e Estágios

```
GET    /api/pipelines                    Lista pipelines com estágios aninhados
POST   /api/pipelines                    Cria pipeline
PUT    /api/pipelines/:id                Atualiza nome/config
DELETE /api/pipelines/:id                Soft delete
POST   /api/pipelines/:id/stages         Cria estágio
PUT    /api/pipelines/:id/stages         Reordena: [{ id, position }]
PUT    /api/pipelines/:id/stages/:stageId   Atualiza nome, cor, SLA, conversão
DELETE /api/pipelines/:id/stages/:stageId   Soft delete do estágio
```

---

### Deals

```
GET    /api/deals                   ?pipeline_id&stage_id&assigned_to
                                    &value_min&value_max&search
POST   /api/deals                   Cria deal
GET    /api/deals/:id               Detalhe + contato vinculado
PUT    /api/deals/:id               Atualiza campos
DELETE /api/deals/:id               Soft delete
PATCH  /api/deals/:id/stage         { stage_id } — drag-and-drop no Kanban
POST   /api/deals/:id/won           Marca como ganho + converte contato para cliente
POST   /api/deals/:id/lost          { reason } — marca como perdido
```

---

### Analytics

```
GET    /api/analytics/overview      ?from&to&pipeline_id
                                    → KPIs: leads, clientes, deals, conversão, valor
GET    /api/analytics/funnel        ?pipeline_id → contagem e valor por estágio
GET    /api/analytics/revenue       ?months=6 → receita ganha vs. prevista por mês
GET    /api/analytics/leaderboard   Top vendedores por valor ganho
GET    /api/analytics/activities    Volume de atividades por tipo
GET    /api/analytics/lead-sources  Distribuição de leads por origem
```

---

### Empresas

> Requer role **MASTER** (ou **ADMIN** para visão consolidada).

```
GET    /api/companies               Lista todas as empresas
POST   /api/companies               Cria empresa (slug único e imutável)
GET    /api/companies/consolidated  Métricas agregadas de todas as unidades (MASTER/ADMIN)
GET    /api/companies/:id           Detalhe
PUT    /api/companies/:id           Atualiza (slug não pode ser alterado)
PATCH  /api/companies/:id/activate  Ativa empresa
PATCH  /api/companies/:id/deactivate  Inativa empresa (bloqueia login dos membros)
DELETE /api/companies/:id           Soft delete
GET    /api/companies/:id/users     Membros da empresa
```

**Resposta de `/companies/consolidated`:**

```json
{
  "totals": {
    "companies": 3,
    "leads": 51,
    "clients": 12,
    "open_deals": 15,
    "won_deals": 6,
    "won_value": 125000.0
  },
  "companies": [
    {
      "id": "...",
      "name": "Unidade São Paulo",
      "slug": "unidade-sao-paulo",
      "is_franchisor": false,
      "leads": 17,
      "clients": 4,
      "open_deals": 5,
      "won_deals": 2,
      "won_value": 42000.0,
      "conversion_rate": 0.28
    }
  ]
}
```

---

### Usuários

> Requer role **ADMIN** ou **MASTER**.

```
GET    /api/users                   Lista membros da empresa ativa
POST   /api/users/invite            { name, email, role, password } — convida membro
PUT    /api/users/:id/role          { role } — ADMIN não pode alterar outro ADMIN/MASTER
PATCH  /api/users/:id/activate      Ativa membro na empresa
PATCH  /api/users/:id/deactivate    Inativa (protegido: não pode ser o último ADMIN)
DELETE /api/users/:id               Remove da empresa (registro users preservado)
GET    /api/profile                 Perfil do usuário autenticado
PUT    /api/profile                 Atualiza nome e avatar
```

---

### Tarefas

```
GET    /api/tasks                   ?status&priority&assigned_to
POST   /api/tasks                   Cria tarefa
PUT    /api/tasks/:id               Atualiza
PATCH  /api/tasks/:id/complete      Marca como concluída
DELETE /api/tasks/:id               Remove (hard delete)
```

---

### Notificações

```
GET    /api/notifications           Lista (não lidas primeiro) + unread_count
PATCH  /api/notifications/read-all  Marca todas como lidas
PATCH  /api/notifications/:id/read  Marca uma como lida
```

---

### Mapa (Geolocalização)

```
GET    /api/map/settings            Configurações do mapa da empresa
PUT    /api/map/settings            { center_lat, center_lng, zoom, store_color, lead_color }
GET    /api/map/pins                ?filter=all|stores|leads
                                    → contatos com lat/lng preenchidos
GET    /api/map/heatmap             → [[lat, lng, weight], ...]
```

---

### Admin (Feature Flags e Permissões)

> Requer role **MASTER** ou **ADMIN**.

```
GET    /api/admin/flags                         Lista feature flags da empresa
PUT    /api/admin/flags/{name}                  { value, is_active } — cria ou atualiza flag
GET    /api/admin/permissions                   Lista permissões granulares da empresa
PUT    /api/admin/permissions/{user_id}         { permission } — concede permissão (ex: "contacts:manage")
DELETE /api/admin/permissions/{user_id}/{perm}  Revoga permissão
```

---

### Webhooks (Ingestão de Leads)

> **Endpoint público** — sem autenticação. A empresa é identificada pelo `slug` na URL.

```
POST   /api/webhooks/{slug}/{source}   Recebe lead de fonte externa
```

**Fontes suportadas:**

| `source` | Formato esperado | Campos extraídos |
|---|---|---|
| `meta` | Meta Lead Ads webhook (nested `entry[0].changes[0].value.field_data`) | `full_name`, `email`, `phone_number` |
| `rdstation` | RD Station webhook (`payload.{name,email,personal_phone}`) | `name`, `email`, `personal_phone` |
| qualquer outro | Payload flat (JSON simples) | `name`/`full_name`/`contact_name`, `email`, `phone`/`mobile` |

**Fluxo de processamento:**

1. Resolve empresa pelo `slug`
2. Normaliza payload conforme a `source`
3. Verifica duplicata por e-mail (retorna `duplicate: true` se existir)
4. Insere contato do tipo `lead` com `origin = source`
5. Cria deal no primeiro estágio do pipeline padrão (score +10)
6. Envia notificação para MASTER e ADMIN da empresa

**Resposta:**

```json
{
  "ok": true,
  "duplicate": false,
  "contact_id": "uuid",
  "deal_id": "uuid"
}
```

**Exemplo de teste (Meta Lead Ads):**

```bash
curl -X POST http://localhost:8001/api/webhooks/unidade-sao-paulo/meta \
  -H "Content-Type: application/json" \
  -d '{
    "entry": [{
      "changes": [{
        "value": {
          "field_data": [
            {"name": "full_name", "values": ["Ana Pereira"]},
            {"name": "email", "values": ["ana@exemplo.com"]},
            {"name": "phone_number", "values": ["+5511999990001"]}
          ]
        }
      }]
    }]
  }'
```

---

### WhatsApp

#### Inbound (público — sem JWT)

```
POST   /api/whatsapp/inbound/{company_slug}
```

Payload:
```json
{
  "from_number": "+5511999990001",
  "to_number": "+5511988880001",
  "body": "Olá, gostaria de mais informações",
  "media_url": null,
  "external_id": "whatsapp-msg-id-123"
}
```

Fluxo:
1. Resolve empresa pelo slug
2. Busca contato por `whatsapp_phone` ou `phone` — cria novo se não encontrar
3. Salva mensagem em `whatsapp_messages` (direction: `inbound`)
4. Registra atividade na timeline do contato
5. Incrementa score do contato (+4)

#### Outbound e Conversas (autenticado)

```
POST   /api/whatsapp/send           { contact_id, body, to_number? }
                                    → salva mensagem outbound + atividade no contato
GET    /api/whatsapp/conversations  → lista contatos com mensagens (última msg por contato)
GET    /api/whatsapp/messages       ?contact_id=... → histórico de mensagens (ASC, máx 200)
```

---

## Matriz de permissões

| Recurso | MASTER | ADMIN | COMMERCIAL | ANALYST |
|---|:---:|:---:|:---:|:---:|
| Criar/editar/excluir empresas | ✓ | ✗ | ✗ | ✗ |
| Ativar/inativar empresa | ✓ | ✗ | ✗ | ✗ |
| Visão consolidada de franquias | ✓ | ✓ | ✗ | ✗ |
| Convidar usuários | ✓ | ✓ ¹ | ✗ | ✗ |
| Alterar role / ativar / inativar usuário | ✓ | ✓ ¹ | ✗ | ✗ |
| Gerenciar feature flags e permissões | ✓ | ✓ | ✗ | ✗ |
| Gerenciar pipelines e estágios | ✓ | ✓ | ✗ | ✗ |
| Criar e editar contatos | ✓ | ✓ | ✓ | ✗ |
| Deletar contatos | ✓ | ✓ | ✗ | ✗ |
| Criar e mover deals (Kanban) | ✓ | ✓ | ✓ | ✗ |
| Ver deals de outros vendedores | ✓ | ✓ | ✗ | ✓ |
| Ver dashboards e analytics | ✓ | ✓ | ✓ | ✓ |
| Configurar mapa | ✓ | ✓ | ✗ | ✗ |
| Enviar mensagens WhatsApp | ✓ | ✓ | ✓ | ✗ |

¹ ADMIN não pode atuar sobre outro ADMIN ou sobre um MASTER.

---

## Regras de negócio

- **Slug imutável** — não pode ser alterado após a criação da empresa.
- **Último ADMIN protegido** — não é possível inativar ou remover o único ADMIN ativo de uma empresa.
- **Empresa inativa bloqueia login** — `get_current_company` valida `is_active` e `deleted_at` a cada requisição.
- **Soft delete** — empresas, contatos, pipelines, estágios e deals usam `deleted_at`. O registro de membership é deletado permanentemente mas o registro `users` é preservado.
- **Isolamento multi-tenant** — todas as queries filtram por `company_id`. Um tenant jamais vê dados de outro.
- **Feature flags** — módulos opcionais só aparecem se a empresa tiver a flag ativa (`is_active = true`).
- **Webhook idempotência por e-mail** — se um lead com o mesmo e-mail já existe, o webhook retorna `duplicate: true` sem duplicar o registro.
- **Deal automático no webhook** — ao receber um lead via webhook, o sistema cria automaticamente um deal no primeiro estágio do pipeline padrão.
- **Score automático** — cada atividade registrada incrementa o score do contato conforme tabela de pontos.

---

## Integrações externas

### Configurar webhook no Meta (Facebook Lead Ads)

1. No Meta for Developers, configure o webhook para:
   ```
   POST https://seu-backend.railway.app/api/webhooks/{slug}/meta
   ```
2. Não é necessário verificação de assinatura (endpoint público por slug).

### Configurar webhook no RD Station

1. No RD Station Marketing, configure o webhook de conversão para:
   ```
   POST https://seu-backend.railway.app/api/webhooks/{slug}/rdstation
   ```

### Configurar WhatsApp (Evolution API / Z-API / Twilio)

Configure o webhook de mensagens recebidas para:
```
POST https://seu-backend.railway.app/api/whatsapp/inbound/{company_slug}
```

Payload esperado (adapte o mapeamento conforme o provider):
```json
{
  "from_number": "+5511999990001",
  "body": "Texto da mensagem",
  "external_id": "id-unico-da-mensagem"
}
```

---

## Testes

Os testes são de integração HTTP — sobem um banco PostgreSQL real e disparam requisições contra o servidor.

```bash
# Rodar dentro do container (banco já disponível)
docker exec crm_backend python -m pytest tests/ -v

# Apenas autenticação e multi-tenant
docker exec crm_backend python -m pytest tests/backend_test.py -v

# Apenas RBAC, empresas e usuários
docker exec crm_backend python -m pytest tests/test_admin_features.py -v
```

**Cobertura atual:** 44 testes cobrindo autenticação, refresh, switch-company, isolamento multi-tenant, CRUD completo de contatos/deals/pipelines, analytics, RBAC, gestão de empresas e usuários.

---

## Deploy em produção

Consulte o guia completo em [docs/DEPLOY.md](docs/DEPLOY.md), que cobre:

- **Railway** (host padrão documentado)
- Render, Fly.io e VPS com Docker
- Geração de segredos (`JWT_SECRET`, `ADMIN_PASSWORD`)
- Checklist de segurança com 22 itens (segredos, rede, banco, aplicação, operação)

**Resumo rápido para Railway:**

```bash
# 1. Gere o JWT_SECRET antes de abrir o Railway
openssl rand -hex 64

# 2. No Railway: New Project → PostgreSQL (managed)
# 3. Backend service: Root Directory = backend, Dockerfile = Dockerfile
# 4. Frontend service: Root Directory = frontend, REACT_APP_BACKEND_URL como Build Variable
# 5. CORS_ORIGINS = URL do frontend após gerar domínio
```

> `seed.py` **não roda em produção**. O Dockerfile usa diretamente `uvicorn` sem chamar o seed.  
> Crie o primeiro admin via `POST /api/auth/register` ou inserindo diretamente no banco.

---

## Roadmap

- Workflow Builder (canvas de automações) + Engine assíncrona (Celery + Redis)
- WebSockets para notificações em tempo real (substituindo polling de 5s)
- Importação/Exportação CSV de contatos
- Webhooks de saída (`deal.won`, `contact.created`) com retry automático
- Lead scoring assíncrono em fila
- Campos customizáveis por empresa via UI (custom_fields configuráveis)
- Gamificação: badges e ranking mensal por vendedor
- Verificação de assinatura HMAC para webhooks (Meta `X-Hub-Signature-256`)
- Integração de e-mail transacional (Resend / SendGrid)
- Endpoints de API key para integrações externas / Power BI
- UI de audit logs
- App mobile (React Native)

---

## Licença

Privado — uso interno.
