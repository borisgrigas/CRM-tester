---
name: project-crm-architecture
description: Stack, padrões arquiteturais, inconsistências e localização de módulos-chave do CRM-tester auditados em 2026-05-28; atualizado com decisões do plano F1 (2026-05-28)
metadata:
  type: project
---

## Stack confirmado (Phase 0 audit — 2026-05-28)

- Backend: FastAPI + Python 3.11 + asyncpg (sem ORM) + PyJWT HS256 + bcrypt
- Frontend: React 19 + CRA + React Router v7 + Zustand + React Query v5 + shadcn/ui + @dnd-kit + Recharts
- Banco: PostgreSQL 16; single-schema multi-tenant via campo `company_id`; IDs como TEXT(UUID); timestamps como TEXT ISO 8601; sem FKs formais
- Infra dev: Docker Compose (3 serviços); produção: Railway via Dockerfiles individuais

## Módulos-chave e localização

- Inicialização do schema: `backend/db.py` (tabelas base) + `backend/core/schema_extra.sql` (extras + ALTER TABLE)
- Auth e JWT: `backend/auth_utils.py` + `backend/routers/auth_router.py`
- Dependências de auth/multi-tenant: `backend/deps.py` (`get_current_user`, `get_current_company`, `require_roles`, `require_module`, `require_franchisor_master`, `get_franchisor`)
- Routers: `backend/routers/` (12 arquivos: auth, contacts, deals, tasks, companies, pipelines, users, analytics, notifications, map, admin, __init__) + `backend/integrations/` (2 arquivos: whatsapp_router, webhook_router)
- DTOs Pydantic: `backend/models.py`
- Feature flags: `backend/core/feature_flags.py` + tabela `feature_flags`
- Permissões granulares: `backend/core/permissions.py` + tabela `permissions`
- core/access_deps.py: apenas re-exports de deps.py (não tem lógica própria)
- Estado global frontend: `frontend/src/stores/authStore.js`
- Registro de módulos/flags frontend: `frontend/src/lib/moduleRegistry.js`
- HTTP client frontend: `frontend/src/lib/api.js`

## Inconsistências críticas (F0) — status após plano F1

1. **ENV vs APP_ENV**: docker-compose seta `APP_ENV=development` mas `auth_router.py` lê `ENV`. NÃO corrigido no F1 — escopo separado.
2. **Endpoint `/api/auth/register` inexistente**: referenciado no DEPLOY.md mas não existe. Corrigido no F1 via B5 + ADR 0002.
3. **Permissões granulares sem enforcement no backend**: persiste — F1 não adiciona enforcement de permissões no backend, apenas exposição via auth/me e admin.
4. **`require_module()` não aplicado**: corrigido no F1 via B1 — aplicado a map, admin, franchise, whatsapp.
5. **Rotas de tasks e map settings sem guard de role**: corrigido no F1 via A5.
6. **WhatsApp send é stub**: persiste — escopo de integração futura.
7. **E-mail transacional ausente**: corrigido no F1 via A3 — substituído por logger estruturado; integração real é Fase 2.

## Surpresas positivas descobertas no F1

- **authStore.js já tem flags e permissions**: campos `flags: {}` e `permissions: []` já existem e são populados nas actions login, refreshMe, switchCompany. Métodos `hasFlag()` e `hasPermission()` já implementados.
- **login e /me já retornam flags e permissions**: `auth_router.py` já chama `get_company_flags` e `get_user_permissions` e inclui os resultados em todas as respostas de auth. O único campo ausente é `active_modules` no retorno do login (presente no /me mas não no login).
- **ModuleGuard já funcional**: `ModuleGuard.jsx` já lê do store e usa `moduleLevel()` do moduleRegistry. As rotas `/whatsapp`, `/franchise`, `/map`, `/admin` já usam ModuleGuard.
- **_ensure_master_anywhere e require_franchisor_master são complementares, não duplicatas**: _ensure_master_anywhere (local em companies_router) verifica MASTER em qualquer empresa (para leitura). require_franchisor_master (em deps.py) verifica MASTER da franqueadora especificamente (para mutações de rede). Ambos são necessários.

## Read-backs sem filtro de tenant — 13 identificados (não 9)

Todos em contacts_router.py, deals_router.py e tasks_router.py. Itens 4 e 5 (tags) têm bug adicional: o próprio UPDATE não tem company_id no WHERE. Corrigidos no F1 via A2 usando RETURNING *.

asyncpg suporta UPDATE ... RETURNING * via fetchrow() — confirmado.

## Padrões de código a respeitar

- Params SQL posicionais: `$1, $2, ...`
- IDs: `str(uuid.uuid4())` gerado pela aplicação
- Timestamps: `datetime.now(timezone.utc).isoformat()` → TEXT
- Soft delete: coluna `deleted_at TEXT`, queries sempre com `deleted_at IS NULL`
- Isolamento multi-tenant: `company_id = $n` obrigatório em todas as queries de dados de negócio
- Roles: MASTER > ADMIN > COMMERCIAL > ANALYST
- Autorização: require_roles() como Depends para bloqueios binários; check inline para lógica diferenciada por role
- Módulos: lista em user_companies.modules — vazia = acesso total; require_module() bloqueia somente se lista não vazia e módulo ausente

## Planos produzidos

- `docs/F1-PLANO.md` — plano técnico completo de correções críticas + ativação da fundação (2026-05-28)
- `docs/ADR/0002-sem-registro-publico.md` — decisão de não ter endpoint público de registro

**Why:** Auditoria Phase 0 completa do codebase + planejamento Phase 1 de correções de segurança.
**How to apply:** Usar como referência para todas as decisões arquiteturais futuras neste projeto.
