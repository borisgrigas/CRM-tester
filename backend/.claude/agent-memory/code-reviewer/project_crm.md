---
name: project-crm
description: Stack, convenções de autorização e arquitetura do CRM SaaS (FastAPI + asyncpg + React)
metadata:
  type: project
---

Backend FastAPI + asyncpg (PostgreSQL). Frontend React + React Query. Multi-tenant com `company_id` em todas as tabelas de dados.

**Roles:** MASTER > ADMIN > COMMERCIAL > ANALYST. ANALYST é somente-leitura em todas as mutações.

**Padrão de autorização em 3 camadas:**
1. `require_roles(*roles)` como `Depends` — bloqueia role inteiro antes de entrar na função
2. Checks inline `if membership["role"] == "X": raise 403` — para lógica diferenciada dentro da rota
3. Ownership check para COMMERCIAL — busca `assigned_to` antes do UPDATE

**require_module:** lista vazia = acesso total (não bloqueia MASTER/ADMIN sem módulos configurados).

**DEBT.md:** inventário de 38 dívidas técnicas em `docs/DEBT.md`. Consultar antes de revisar routers.

**Why:** Projeto em fase de hardening pós-auditoria; fases numeradas (F1, F2...) correção incremental.
**How to apply:** Checar DEBT.md para contexto de cada problema encontrado — pode já estar catalogado.
