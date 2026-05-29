---
name: project-stack
description: CRM-tester stack, architecture, and key recurring debt patterns observed in technical audit
metadata:
  type: project
---

FastAPI (Python) + React (JS) multi-tenant CRM SaaS. PostgreSQL via asyncpg (no ORM). Frontend uses Zustand + React Query + Axios.

**Why:** Migrated from MongoDB to PostgreSQL; some schema decisions reflect that legacy (TEXT PKs instead of UUID type, dates stored as ISO TEXT strings instead of TIMESTAMPTZ).

**Recurring debt patterns observed (2026-05-28 audit):**
- Dynamic f-string SQL in UPDATE paths across all routers (contacts, deals, tasks, users, pipelines, companies) — column names from Pydantic dicts inserted into SQL strings. Low injection risk today (keys come from model_dump()) but fragile pattern.
- `_now_iso()` helper copy-pasted in 12 files — should live in a `utils.py`.
- No FK constraints in schema — all relations are logical only.
- All date/time columns stored as TEXT (ISO string) instead of TIMESTAMPTZ — prevents native date arithmetic in SQL.
- `print()` used instead of `logger` for reset tokens and invite links — leaks sensitive tokens to stdout in production.
- Default password `changeme123` hardcoded in UserInvite model.
- No rate limiting on auth endpoints (login, forgot-password).
- `_ensure_master_anywhere` in companies_router checks if user is MASTER in *any* company, not necessarily the current tenant — cross-tenant privilege escalation risk.
- N+1 queries in companies_router list_companies and consolidated endpoints.
- Tasks list endpoint has hardcoded LIMIT 500 with no pagination.
- `deleted_at` on users is fetched but never checked in `get_current_user` — soft-deleted users can still authenticate.

**How to apply:** Flag any new router that repeats these patterns. Prioritize FK constraints, TIMESTAMPTZ migration, and the soft-delete auth bypass as highest-impact fixes.
