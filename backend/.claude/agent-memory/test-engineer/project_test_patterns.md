---
name: project-test-patterns
description: conftest fixtures, test file style, seeded users, and test commands for CRM-tester backend
metadata:
  type: project
---

## Test framework
- pytest with `requests.Session` (not httpx)
- Integration tests hitting real Docker backend at http://localhost:8001
- conftest.py is in `backend/tests/conftest.py`
- BASE_URL/API derived from env var BACKEND_URL (default http://localhost:8001)

## Test file style
- Use `class TestXxx` grouping
- Each method = one scenario, name describes expected behavior
- Cleanup resources with DELETE in finally blocks (don't fail if cleanup fails)
- Use `s.last_login` attribute (set by `_login` helper) to access login response data

## conftest.py session-scoped fixtures
- `master_session` — master@franqueadora.com / master123 (MASTER of all companies)
- `admin_sp_session` — admin@unidade-sao-paulo.com / senha123 (ADMIN of SP unit)
- `commercial_sp_session` — vendas@unidade-sao-paulo.com / senha123 (COMMERCIAL in SP)
- `analyst_sp_session` — analista@unidade-sao-paulo.com / senha123 (ANALYST in SP)
- `admin_rj_session` — admin@unidade-rio-de-janeiro.com / senha123 (ADMIN of RJ unit)

## Seeded users (from seed.py, password always "senha123")
Pattern: `{role_suffix}@{company-slug}.com`
- SP unit slug: unidade-sao-paulo
  - admin@unidade-sao-paulo.com
  - vendas@unidade-sao-paulo.com (COMMERCIAL 1)
  - vendas2@unidade-sao-paulo.com (COMMERCIAL 2 — useful for ownership tests)
  - analista@unidade-sao-paulo.com (ANALYST)
- RJ unit: same pattern with unidade-rio-de-janeiro

## Run command
```
cd backend
python -m pytest tests/test_f1_security.py -v
python -m pytest tests/ -v   # full suite
```

**Why:** Docker backend must be running at port 8001 before executing tests.
**How to apply:** Always check Docker is up before running integration tests.
