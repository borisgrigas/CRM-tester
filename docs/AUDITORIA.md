# Auditoria Técnica — CRM SaaS Multi-Tenant

> Data da auditoria: 2026-05-28
> Auditor: Architect Agent (Phase 0 — diagnóstico apenas, sem implementação)

---

## 1. Mapa de Rotas da API

Todas as rotas são montadas sob o prefixo `/api` em `server.py`.

### Auth (`/api/auth` — `routers/auth_router.py`)

| Método | Rota | Arquivo | Papel mínimo | Descrição |
|--------|------|---------|-------------|-----------|
| POST | `/api/auth/login` | auth_router.py | Público | Autentica usuário; seta cookies `access_token` e `refresh_token` |
| POST | `/api/auth/refresh` | auth_router.py | Público (cookie refresh_token) | Renova access_token a partir do refresh_token em cookie |
| POST | `/api/auth/logout` | auth_router.py | Público | Remove cookies; retorna 204 |
| POST | `/api/auth/switch-company` | auth_router.py | Autenticado | Reemite access_token para outra empresa do usuário |
| GET | `/api/auth/me` | auth_router.py | Autenticado | Retorna usuário, empresas, flags e permissões |
| POST | `/api/auth/forgot-password` | auth_router.py | Público | Cria token de reset; imprime link no console (não envia e-mail) |
| POST | `/api/auth/reset-password` | auth_router.py | Público | Valida token e atualiza senha |
| PUT | `/api/auth/password` | auth_router.py | Autenticado | Altera senha do usuário autenticado |

### Contatos (`/api/contacts` — `routers/contacts_router.py`)

| Método | Rota | Arquivo | Papel mínimo | Descrição |
|--------|------|---------|-------------|-----------|
| GET | `/api/contacts` | contacts_router.py | Qualquer autenticado | Lista com filtros: page, limit, search, type, assigned_to, tag, origin, score_min, score_max, sort |
| POST | `/api/contacts` | contacts_router.py | COMMERCIAL, ADMIN, MASTER | Cria contato (ANALYST bloqueado explicitamente) |
| GET | `/api/contacts/{contact_id}` | contacts_router.py | Qualquer autenticado | Detalhe + atividades (últimas 50) + deals vinculados |
| PUT | `/api/contacts/{contact_id}` | contacts_router.py | COMMERCIAL, ADMIN, MASTER | Atualiza contato (ANALYST bloqueado explicitamente) |
| DELETE | `/api/contacts/{contact_id}` | contacts_router.py | ADMIN, MASTER | Soft delete (`deleted_at`) |
| POST | `/api/contacts/{contact_id}/convert` | contacts_router.py | COMMERCIAL, ADMIN, MASTER | Converte lead → client |
| POST | `/api/contacts/{contact_id}/tags` | contacts_router.py | Qualquer autenticado | Adiciona tags (merge com tags existentes) |
| DELETE | `/api/contacts/{contact_id}/tags` | contacts_router.py | Qualquer autenticado | Remove tags |
| GET | `/api/contacts/{contact_id}/activities` | contacts_router.py | Qualquer autenticado | Lista atividades (até 200, DESC) |
| POST | `/api/contacts/{contact_id}/activities` | contacts_router.py | Qualquer autenticado | Registra atividade e incrementa score |

### Pipelines (`/api/pipelines` — `routers/pipelines_router.py`)

| Método | Rota | Arquivo | Papel mínimo | Descrição |
|--------|------|---------|-------------|-----------|
| GET | `/api/pipelines` | pipelines_router.py | Qualquer autenticado | Lista pipelines com estágios aninhados |
| POST | `/api/pipelines` | pipelines_router.py | MASTER, ADMIN | Cria pipeline |
| PUT | `/api/pipelines/{pipeline_id}` | pipelines_router.py | MASTER, ADMIN | Atualiza nome/is_default |
| DELETE | `/api/pipelines/{pipeline_id}` | pipelines_router.py | MASTER, ADMIN | Soft delete do pipeline |
| POST | `/api/pipelines/{pipeline_id}/stages` | pipelines_router.py | MASTER, ADMIN | Cria estágio no pipeline |
| PUT | `/api/pipelines/{pipeline_id}/stages` | pipelines_router.py | MASTER, ADMIN | Reordena estágios (lista `[{id, position}]`) |
| PUT | `/api/pipelines/{pipeline_id}/stages/{stage_id}` | pipelines_router.py | MASTER, ADMIN | Atualiza estágio |
| DELETE | `/api/pipelines/{pipeline_id}/stages/{stage_id}` | pipelines_router.py | MASTER, ADMIN | Soft delete do estágio |

### Deals (`/api/deals` — `routers/deals_router.py`)

| Método | Rota | Arquivo | Papel mínimo | Descrição |
|--------|------|---------|-------------|-----------|
| GET | `/api/deals` | deals_router.py | Qualquer autenticado | Lista deals com filtros; COMMERCIAL vê apenas os próprios |
| POST | `/api/deals` | deals_router.py | COMMERCIAL, ADMIN, MASTER | Cria deal; adiciona +10 ao score do contato |
| GET | `/api/deals/{deal_id}` | deals_router.py | Qualquer autenticado | Detalhe + contato vinculado |
| PUT | `/api/deals/{deal_id}` | deals_router.py | COMMERCIAL, ADMIN, MASTER | Atualiza deal (ANALYST bloqueado) |
| DELETE | `/api/deals/{deal_id}` | deals_router.py | ADMIN, MASTER | Soft delete |
| PATCH | `/api/deals/{deal_id}/stage` | deals_router.py | COMMERCIAL, ADMIN, MASTER | Move deal de estágio (Kanban); +15 ao score do contato |
| POST | `/api/deals/{deal_id}/won` | deals_router.py | COMMERCIAL, ADMIN, MASTER | Marca won; converte contato para client; +20 ao score |
| POST | `/api/deals/{deal_id}/lost` | deals_router.py | COMMERCIAL, ADMIN, MASTER | Marca lost com reason; -10 ao score do contato |

### Analytics (`/api/analytics` — `routers/analytics_router.py`)

| Método | Rota | Arquivo | Papel mínimo | Descrição |
|--------|------|---------|-------------|-----------|
| GET | `/api/analytics/overview` | analytics_router.py | Qualquer autenticado | KPIs: leads, clientes, deals, conversão, valor médio |
| GET | `/api/analytics/funnel` | analytics_router.py | Qualquer autenticado | Contagem e valor de deals por estágio do pipeline padrão |
| GET | `/api/analytics/revenue` | analytics_router.py | Qualquer autenticado | Receita ganha vs. prevista por mês (padrão: 6 meses) |
| GET | `/api/analytics/leaderboard` | analytics_router.py | Qualquer autenticado | Top 10 vendedores por valor ganho |
| GET | `/api/analytics/activities` | analytics_router.py | Qualquer autenticado | Volume de atividades agrupado por tipo |
| GET | `/api/analytics/lead-sources` | analytics_router.py | Qualquer autenticado | Distribuição de leads por origem (top 20) |

### Empresas (`/api/companies` — `routers/companies_router.py`)

| Método | Rota | Arquivo | Papel mínimo | Descrição |
|--------|------|---------|-------------|-----------|
| GET | `/api/companies` | companies_router.py | MASTER (qualquer empresa) | Lista todas as empresas com contagens |
| POST | `/api/companies` | companies_router.py | MASTER da franqueadora | Cria empresa; auto-adiciona ator como MASTER na nova empresa |
| GET | `/api/companies/consolidated` | companies_router.py | MASTER ou ADMIN (qualquer empresa) | Métricas consolidadas de todas as unidades |
| GET | `/api/companies/{company_id}` | companies_router.py | MASTER (qualquer empresa) | Detalhe de uma empresa |
| PUT | `/api/companies/{company_id}` | companies_router.py | MASTER da franqueadora | Atualiza empresa (slug imutável, is_franchisor protegido) |
| PATCH | `/api/companies/{company_id}/activate` | companies_router.py | MASTER da franqueadora | Ativa empresa |
| PATCH | `/api/companies/{company_id}/deactivate` | companies_router.py | MASTER da franqueadora | Inativa empresa (franqueadora não pode ser inativada) |
| DELETE | `/api/companies/{company_id}` | companies_router.py | MASTER da franqueadora | Soft delete (franqueadora não pode ser excluída) |
| GET | `/api/companies/{company_id}/users` | companies_router.py | MASTER (qualquer empresa) | Lista membros e suas roles na empresa |

### Usuários (`routers/users_router.py` — sem prefixo de grupo no router)

| Método | Rota | Arquivo | Papel mínimo | Descrição |
|--------|------|---------|-------------|-----------|
| GET | `/api/users` | users_router.py | Qualquer autenticado | Lista membros da empresa ativa |
| POST | `/api/users/invite` | users_router.py | MASTER, ADMIN | Convida membro; cria usuário se não existir; busca por CPF primeiro, depois e-mail |
| PUT | `/api/users/{user_id}/role` | users_router.py | MASTER, ADMIN | Altera papel (ADMIN não pode promover para ADMIN/MASTER) |
| PUT | `/api/users/{user_id}/modules` | users_router.py | MASTER, ADMIN | Atualiza lista de módulos do membro |
| PATCH | `/api/users/{user_id}/activate` | users_router.py | MASTER, ADMIN | Ativa membro na empresa |
| PATCH | `/api/users/{user_id}/deactivate` | users_router.py | MASTER, ADMIN | Inativa membro (protegido: não pode ser o último ADMIN) |
| DELETE | `/api/users/{user_id}` | users_router.py | MASTER, ADMIN | Remove membro (hard delete da membership, users preservado) |
| POST | `/api/users/{user_id}/grant-company` | users_router.py | MASTER | Concede acesso a empresa adicional (apenas franqueadora) |
| DELETE | `/api/users/{user_id}/revoke-company/{company_id}` | users_router.py | MASTER | Revoga acesso a empresa adicional (apenas franqueadora) |
| GET | `/api/profile` | users_router.py | Qualquer autenticado | Perfil do usuário autenticado |
| PUT | `/api/profile` | users_router.py | Qualquer autenticado | Atualiza nome e avatar |
| GET | `/api/users/modules-catalog` | users_router.py | Público (sem dep. de auth) | Lista módulos válidos para o sistema |

### Tarefas (`/api/tasks` — `routers/tasks_router.py`)

| Método | Rota | Arquivo | Papel mínimo | Descrição |
|--------|------|---------|-------------|-----------|
| GET | `/api/tasks` | tasks_router.py | Qualquer autenticado | Lista tarefas; COMMERCIAL vê apenas as próprias |
| POST | `/api/tasks` | tasks_router.py | COMMERCIAL, ADMIN, MASTER | Cria tarefa (ANALYST bloqueado) |
| PUT | `/api/tasks/{task_id}` | tasks_router.py | Qualquer autenticado | Atualiza tarefa (sem validação de role!) |
| PATCH | `/api/tasks/{task_id}/complete` | tasks_router.py | Qualquer autenticado | Marca como concluída (sem validação de role!) |
| DELETE | `/api/tasks/{task_id}` | tasks_router.py | Qualquer autenticado | Hard delete (sem validação de role!) |

### Notificações (`/api/notifications` — `routers/notifications_router.py`)

| Método | Rota | Arquivo | Papel mínimo | Descrição |
|--------|------|---------|-------------|-----------|
| GET | `/api/notifications` | notifications_router.py | Qualquer autenticado | Lista notificações do usuário (até 50); retorna unread_count |
| PATCH | `/api/notifications/read-all` | notifications_router.py | Qualquer autenticado | Marca todas as notificações do usuário como lidas |
| PATCH | `/api/notifications/{notif_id}/read` | notifications_router.py | Qualquer autenticado | Marca uma notificação como lida |

### Mapa (`/api/map` — `routers/map_router.py`)

| Método | Rota | Arquivo | Papel mínimo | Descrição |
|--------|------|---------|-------------|-----------|
| GET | `/api/map/settings` | map_router.py | Qualquer autenticado | Configurações do mapa da empresa (com defaults) |
| PUT | `/api/map/settings` | map_router.py | Qualquer autenticado | Atualiza configurações do mapa (sem validação de role!) |
| GET | `/api/map/pins` | map_router.py | Qualquer autenticado | Contatos georreferenciados; filtro: all, stores, leads |
| GET | `/api/map/heatmap` | map_router.py | Qualquer autenticado | Pontos para heatmap: `[[lat, lng, 1.0]]` |

### Admin — Feature Flags e Permissões (`/api/admin` — `routers/admin_router.py`)

| Método | Rota | Arquivo | Papel mínimo | Descrição |
|--------|------|---------|-------------|-----------|
| GET | `/api/admin/flags` | admin_router.py | MASTER, ADMIN | Lista feature flags da empresa |
| PUT | `/api/admin/flags/{name}` | admin_router.py | MASTER, ADMIN | Cria ou atualiza flag (upsert) |
| GET | `/api/admin/permissions` | admin_router.py | MASTER, ADMIN | Lista permissões granulares da empresa |
| PUT | `/api/admin/permissions/{user_id}` | admin_router.py | MASTER, ADMIN | Concede permissão granular a usuário |
| DELETE | `/api/admin/permissions/{user_id}/{permission}` | admin_router.py | MASTER, ADMIN | Revoga permissão granular |

### Webhooks — Ingestão de Leads (`/api/webhooks` — `integrations/webhook_router.py`)

| Método | Rota | Arquivo | Papel mínimo | Descrição |
|--------|------|---------|-------------|-----------|
| POST | `/api/webhooks/{slug}/{source}` | webhook_router.py | Público (sem JWT) | Recebe lead de fonte externa; cria contato e deal; notifica MASTER/ADMIN |

Sources suportadas explicitamente: `meta`, `rdstation`. Qualquer outro valor cai no normalizador genérico.

### WhatsApp (`/api/whatsapp` — `integrations/whatsapp_router.py`)

| Método | Rota | Arquivo | Papel mínimo | Descrição |
|--------|------|---------|-------------|-----------|
| POST | `/api/whatsapp/inbound/{company_slug}` | whatsapp_router.py | Público (sem JWT) | Recebe mensagem inbound; cria contato se não existir; registra atividade |
| POST | `/api/whatsapp/send` | whatsapp_router.py | Qualquer autenticado | Registra mensagem outbound + atividade (não há envio real de mensagem!) |
| GET | `/api/whatsapp/conversations` | whatsapp_router.py | Qualquer autenticado | Lista contatos com mensagens (última por contato) |
| GET | `/api/whatsapp/messages` | whatsapp_router.py | Qualquer autenticado | Histórico de mensagens por contato (até 200, ASC) |

### Raiz

| Método | Rota | Arquivo | Papel mínimo | Descrição |
|--------|------|---------|-------------|-----------|
| GET | `/api/` | server.py | Público | Health check: retorna `{"message": "CRM SaaS API", "version": "1.0.0"}` |

**Total de rotas: 57**

---

## 2. Módulos do Frontend

### Páginas e rotas (App.js)

| Rota | Componente | Módulo/Guard | Descrição |
|------|-----------|-------------|-----------|
| `/login` | `Login` | Público | Autenticação |
| `/` | `Dashboard` | ProtectedRoute | Redireciona para dashboard |
| `/dashboard` | `Dashboard` | ProtectedRoute | KPIs + gráficos |
| `/contacts` | `Contacts` | ProtectedRoute | Listagem de contatos com filtros |
| `/contacts/:id` | `ContactDetail` | ProtectedRoute | Detalhe do contato: timeline + deals |
| `/pipeline` | `Pipeline` | ProtectedRoute | Kanban drag-and-drop |
| `/tasks` | `Tasks` | ProtectedRoute | Gestão de tarefas |
| `/analytics` | `Analytics` | ProtectedRoute | Funil, receita, leaderboard, origens |
| `/settings` | `Settings` | ProtectedRoute | Configurações |
| `/whatsapp` | `WhatsAppPage` | ProtectedRoute + ModuleGuard(`whatsapp`, `view`) | Conversas WhatsApp |
| `/franchise` | `FranchisePage` | ProtectedRoute + ModuleGuard(`franchise`, `view`) | Visão consolidada da rede |
| `/map` | `MapPage` | ProtectedRoute + ModuleGuard(`map`) | Mapa interativo de contatos |
| `/admin` | `AdminPanel` | ProtectedRoute + ModuleGuard(`admin`, `manage`) | Feature flags e permissões granulares |
| `/admin/users` | `AdminUsers` | ProtectedRoute | Gestão de usuários |
| `/admin/companies` | `AdminCompanies` | ProtectedRoute | Gestão de empresas |
| `*` | Redireciona para `/` | — | Catch-all |

### Componentes por domínio

**Auth / Sessão**
- `pages/Login.jsx` — formulário de login
- `stores/authStore.js` — Zustand: user, companies, activeCompanyId, activeRole, flags, permissions; login, logout, switchCompany, refreshMe
- `components/ProtectedRoute` — redireciona para `/login` se não autenticado
- `components/CompanySwitcher.jsx` — troca de empresa sem logout

**Layout / Navegação**
- `components/Layout.jsx` — wrapper Sidebar + Header
- `components/Sidebar.jsx` — navegação lateral com visibilidade por módulo
- `components/Header.jsx` — barra superior + notificações
- `components/ModuleGuard.jsx` — HOC de controle de acesso por módulo/nível

**Contatos**
- `pages/Contacts.jsx` — listagem com filtros avançados
- `pages/ContactDetail.jsx` — timeline de atividades + deals vinculados

**Pipeline / Deals**
- `pages/Pipeline.jsx` — Kanban drag-and-drop (@dnd-kit)

**Tarefas**
- `pages/Tasks.jsx`

**Analytics**
- `pages/Analytics.jsx` — funil, receita, leaderboard, origens de lead (Recharts)
- `pages/Dashboard.jsx` — KPIs + gráficos resumidos

**Configurações**
- `pages/Settings.jsx`

**Admin**
- `pages/AdminUsers.jsx` — gestão de membros (ADMIN + MASTER)
- `pages/AdminCompanies.jsx` — gestão de empresas (MASTER)
- `features/admin/AdminPanel.jsx` — feature flags e permissões granulares

**Módulos opcionais (feature-flagged)**
- `features/franchise/FranchisePage.jsx` — visão consolidada (flag: `franchise`)
- `features/map/MapPage.jsx` — mapa interativo com pins e heatmap (flag: `map` — sem flag no registry)
- `features/whatsapp/WhatsAppPage.jsx` — conversas e envio (flag: `whatsapp`)

**Infraestrutura Frontend**
- `lib/api.js` — instância axios com `withCredentials: true`; interceptor de auto-refresh em 401
- `lib/moduleRegistry.js` — definição dos 9 módulos; função `moduleLevel()` e `visibleModules()`
- `lib/utils.js` — cn() e helpers
- `hooks/use-toast.js` — hook de notificação local

---

## 3. Mapa de Tabelas do Banco

### Tabelas base (`db.py`)

| Tabela | Tipo de PK | Colunas-chave | Foreign keys | Índices |
|--------|-----------|--------------|-------------|---------|
| `users` | TEXT (UUID) | id, name, email (UNIQUE), password_hash, avatar_url, created_at, deleted_at | — | — |
| `companies` | TEXT (UUID) | id, name, slug (UNIQUE), plan, logo_url, settings (JSONB), is_active, is_franchisor, created_at, deleted_at | — | — |
| `user_companies` | Composta (user_id, company_id) | user_id, company_id, role, modules (JSONB), is_active, invited_at, accepted_at | user_id → users.id (sem FK formal), company_id → companies.id (sem FK formal) | `idx_uc_user` (user_id), `idx_uc_company` (company_id) |
| `contacts` | TEXT (UUID) | id, company_id, type, name, email, phone, company_name, position, origin, assigned_to, custom_fields (JSONB), tags (JSONB), score, created_at, updated_at, deleted_at | company_id → companies.id (sem FK formal) | `idx_contacts_company_type` (company_id, type) |
| `contact_activities` | TEXT (UUID) | id, company_id, contact_id, user_id, type, description, metadata (JSONB), occurred_at, created_at | contact_id → contacts.id (sem FK formal) | `idx_activities_contact` (contact_id, occurred_at DESC) |
| `pipelines` | TEXT (UUID) | id, company_id, name, is_default, created_at, deleted_at | company_id → companies.id (sem FK formal) | — |
| `pipeline_stages` | TEXT (UUID) | id, pipeline_id, company_id, name, position, conversion_probability, color, sla_hours, created_at, deleted_at | pipeline_id → pipelines.id (sem FK formal) | — |
| `deals` | TEXT (UUID) | id, company_id, contact_id, pipeline_id, stage_id, title, value, expected_close_date, assigned_to, custom_fields (JSONB), won_at, lost_at, lost_reason, created_at, updated_at, deleted_at | company_id, contact_id, pipeline_id, stage_id (sem FKs formais) | `idx_deals_company_pipeline_stage` (company_id, pipeline_id, stage_id) |
| `tasks` | TEXT (UUID) | id, company_id, title, description, contact_id, deal_id, assigned_to, created_by, due_date, priority, status, completed_at, created_at, updated_at | company_id, contact_id, deal_id (sem FKs formais) | — |
| `notifications` | TEXT (UUID) | id, company_id, user_id, title, body, type, entity_type, entity_id, read_at, created_at | company_id, user_id (sem FKs formais) | — |
| `password_reset_tokens` | TEXT (UUID) | id, token (UNIQUE), user_id, expires_at, used | user_id → users.id (sem FK formal) | — |

### Tabelas extras (`core/schema_extra.sql`)

| Tabela | Tipo de PK | Colunas-chave | Foreign keys | Índices |
|--------|-----------|--------------|-------------|---------|
| `feature_flags` | TEXT (UUID) | id, company_id, name, value (JSONB), is_active, created_at — UNIQUE(company_id, name) | company_id (sem FK formal) | `idx_feature_flags_company` (company_id) WHERE is_active |
| `permissions` | TEXT (UUID) | id, company_id, user_id, permission, granted_by, created_at — UNIQUE(company_id, user_id, permission) | company_id, user_id (sem FKs formais) | `idx_permissions_user` (company_id, user_id) |
| `map_settings` | TEXT (UUID) | id, company_id (UNIQUE), center_lat, center_lng, zoom, provider, api_key, created_at, updated_at, store_color, lead_color | company_id (sem FK formal) | — |
| `whatsapp_messages` | TEXT (UUID) | id, company_id, contact_id, direction, from_number, to_number, body, media_url, status, external_id, created_at | company_id, contact_id (sem FKs formais) | `idx_whatsapp_contact` (company_id, contact_id) |

### Colunas adicionadas por ALTER TABLE (schema_extra.sql)

**contacts:** `address`, `latitude`, `longitude`, `whatsapp_phone`, `cep`, `street`, `street_number`, `neighborhood`, `city`, `state`, `notes`, `region_interest`, `is_sold_store`

**users:** `phone`, `cpf` (com índice único parcial: `idx_users_cpf` WHERE cpf IS NOT NULL)

**map_settings:** `store_color`, `lead_color`

**Total de tabelas: 15** (11 base + 4 extras)

---

## 4. Modelo de Autorização

### JWT — Estrutura e política de cookies

O sistema usa **JWT HS256** com dois tokens distintos:

**Access token** (duração: 15 minutos):
- Claims: `sub` (user_id), `email`, `company_id`, `role`, `type: "access"`, `exp`
- Entregue via: cookie `access_token` (httpOnly) **e** no corpo da resposta como `access_token`
- Usado pelo frontend via cookie; testes e integrações podem usar `Authorization: Bearer`

**Refresh token** (duração: 7 dias):
- Claims: `sub` (user_id), `type: "refresh"`, `exp`
- Entregue via: cookie `refresh_token` (httpOnly) **e** no corpo da resposta como `refresh_token`
- Não contém `company_id` — ao renovar, o backend escolhe a empresa padrão

**Política de cookies:**
- Em desenvolvimento (`ENV != production`): `secure=False`, `samesite="lax"`
- Em produção (`ENV == production`): `secure=True`, `samesite="none"`

[INCONSISTÊNCIA] `docker-compose.yml` seta `APP_ENV=development` mas `auth_router.py` lê `ENV` (variável diferente). A variável verificada é `os.environ.get("ENV", "development")`, não `APP_ENV`. Portanto, os cookies nunca são `secure=True` ao usar o docker-compose mesmo que `APP_ENV=production` seja setado.

### Multi-tenant — Scoping por company_id

1. O `company_id` ativo vive no JWT do access token.
2. A dependência `get_current_company` (em `deps.py`):
   - Lê `company_id` do JWT
   - Verifica `user_companies` (membership ativo)
   - Verifica `companies` (empresa não deletada e `is_active = TRUE`)
   - Retorna o dict de membership enriquecido com `_company`
3. Todas as queries de dados filtram por `company_id = membership["company_id"]`.
4. Não há foreign key formal no banco — o isolamento é garantido exclusivamente pela aplicação.

**Troca de empresa** (`switch-company`): emite novo access token com o novo `company_id`; o refresh token permanece o mesmo.

### Roles e hierarquia

Hierarquia: `MASTER > ADMIN > COMMERCIAL > ANALYST`

| Role | Acesso padrão |
|------|--------------|
| MASTER | Acesso total; único que pode agir na franqueadora; pode ver/criar todas as empresas |
| ADMIN | Gestão de usuários e pipelines; não pode agir sobre outros ADMIN/MASTER |
| COMMERCIAL | CRUD de contatos e deals; vê apenas os próprios registros |
| ANALYST | Somente leitura; bloqueado em criação/edição na maioria das rotas |

**Implementação:**
- `require_roles(*allowed_roles)` — factory que usa `get_current_company` e verifica `membership["role"]`
- `require_franchisor_master` — exige que o usuário seja MASTER **e** que a empresa ativa seja a franqueadora
- Checks diretos no corpo das funções (pattern `if membership["role"] == "ANALYST": raise 403`)

[INCONSISTÊNCIA] Há dois mecanismos paralelos de controle de acesso: `require_roles()` como dependência e checks manuais inline. As rotas de tasks (PUT, PATCH, DELETE) e map (PUT settings) não têm verificação de role.

### Permissões granulares

Além dos roles, existe uma camada adicional: a tabela `permissions` armazena entradas no formato `"module:action"` (ex: `"contacts:manage"`). Essas permissões são retornadas na autenticação e usadas pelo frontend via `moduleLevel()` do `moduleRegistry.js`. No backend, as permissões granulares são lidas mas **não verificadas nas dependências** — apenas expostas via `/api/admin/permissions`.

[INCONSISTÊNCIA] As permissões granulares da tabela `permissions` são retornadas ao frontend mas não são verificadas nas rotas backend. A aplicação de permissões granulares existe apenas no frontend (`ModuleGuard`).

### Módulos por usuário

A coluna `modules` em `user_companies` é uma lista JSON de módulo IDs. Se a lista estiver vazia ou ausente, o usuário tem acesso a todos os módulos. Isso é verificado por `require_module()` em `deps.py`. Nos routers atuais, `require_module()` não está aplicado a nenhuma rota.

---

## 5. Integrações Externas

| Integração | Direção | Implementação | Observação |
|-----------|---------|--------------|-----------|
| Meta Lead Ads (Facebook) | Inbound | `integrations/webhook_router.py` — normalizador `_normalize_meta()` | Sem verificação de assinatura HMAC (`X-Hub-Signature-256`) |
| RD Station Marketing | Inbound | `integrations/webhook_router.py` — normalizador `_normalize_rdstation()` | Sem verificação de token de autenticação RD Station |
| WhatsApp (Evolution API / Z-API / Twilio) | Inbound e Outbound (parcial) | `integrations/whatsapp_router.py` | O envio outbound (`/send`) apenas **registra no banco** — não chama nenhuma API externa de WhatsApp |
| E-mail transacional | — | **Não implementado** | Recuperação de senha imprime o link no console (`print(...)`) em vez de enviar e-mail |
| Geolocalização / mapas | Frontend | `features/map/MapPage.jsx` | Map provider configurável (`provider` em `map_settings`); `api_key` armazenado na tabela `map_settings` |

**Resumo:** O sistema não faz chamadas HTTP de saída para APIs externas. A única "integração" de saída (WhatsApp) é um stub que grava no banco. Meta e RD Station são inbound-only (webhooks recebidos). Não há clientes HTTP externos (`httpx`, `requests`) no código dos routers.

---

## 6. Estado do Sistema em Produção

### Pronto para produção

| Item | Status | Observação |
|------|--------|-----------|
| Banco de dados | OK | PostgreSQL 16 com pool asyncpg (min 2, max 10 conexões) |
| Schema de inicialização | OK | `db.py` + `schema_extra.sql` — idempotente via `CREATE IF NOT EXISTS` e `ALTER ... IF NOT EXISTS` |
| JWT com expiração curta | OK | Access: 15 min; Refresh: 7 dias |
| Cookies httpOnly | OK (parcial) | Correto; `secure=True` condicionado ao env `ENV=production` (ver inconsistência abaixo) |
| CORS configurável por env | OK | `CORS_ORIGINS` via variável de ambiente |
| Seed não roda em produção | OK | Dockerfile usa `uvicorn` diretamente; seed só roda no `command` do docker-compose |
| Uvicorn com 2 workers | OK | Dockerfile: `uvicorn server:app --host 0.0.0.0 --port 8001 --workers 2` |
| Soft delete | OK | Empresas, contatos, pipelines, estágios e deals usam `deleted_at` |
| Último ADMIN protegido | OK | Lógica em `users_router.py` |
| Franqueadora não pode ser deletada/inativada | OK | Lógica em `companies_router.py` |

### Apenas para desenvolvimento / incompleto

| Item | Status | Observação |
|------|--------|-----------|
| Recuperação de senha | Incompleto | Token é gravado no banco mas o e-mail não é enviado — link impresso no console |
| Convite de usuário | Incompleto | Link de ativação impresso no console (`print(...)`) |
| `samesite="none"` em produção | Risco | Cookies com `samesite="none"` exigem obrigatoriamente `secure=True`; se HTTPS não estiver ativo, cookies serão rejeitados pelos browsers |
| Variável de ambiente `ENV` vs `APP_ENV` | [INCONSISTÊNCIA] | docker-compose seta `APP_ENV=development`; auth_router lê `ENV`; os cookies nunca ativam o modo produção via docker-compose |
| Webhook sem autenticação de assinatura | Risco | Endpoints públicos de webhook não verificam HMAC — qualquer requisição ao URL pode inserir leads |
| WhatsApp send sem integração real | Incompleto | `POST /api/whatsapp/send` apenas grava no banco; não existe chamada a provider externo |
| `api_key` de mapa armazenada no banco | Risco | Chaves de API de serviços de mapa ficam em plaintext na tabela `map_settings` |
| Foreign keys sem restrição no banco | Risco de integridade | Todas as relações entre tabelas são mantidas apenas pela aplicação; o banco não tem FKs formais |
| `/api/auth/register` mencionado no DEPLOY.md | [INCONSISTÊNCIA] | O endpoint `POST /api/auth/register` é referenciado no guia de deploy para criar o primeiro admin, mas **não existe** em nenhum router registrado |
| `REACT_APP_BACKEND_URL` é build-time | Limitação | O valor é embutido no bundle JS em build — mudanças de URL exigem rebuild do frontend |
| Polling de notificações (5s) | Desenvolvimento | O frontend usa polling; sem WebSockets |

---

*Fim da Auditoria — 2026-05-28*
