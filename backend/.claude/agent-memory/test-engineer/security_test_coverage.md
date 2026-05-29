---
name: security-test-coverage
description: What test_f1_security.py covers and key behavioral notes about each test
metadata:
  type: project
---

File: `backend/tests/test_f1_security.py`
Created as part of F1 security hardening.

## Tests and key behaviors

### Test 1 — TestRemovedMembershipBlocksAccess
- DELETE /users/{id} removes the user_companies row only (not the users row)
- get_current_user still succeeds (user row intact, deleted_at IS NULL)
- get_current_company FAILS with 403 "Acesso negado a esta empresa" (membership gone)
- Assertion accepts 401 OR 403 — /auth/me may return 200 (no companies), but
  any company-scoped endpoint (/tasks) must return 403

### Test 2 — TestAnalystCannotCreateTask
- tasks_router.create_task raises 403 if role == ANALYST
- Confirmed in code: `if membership["role"] == "ANALYST": raise HTTPException(403)`

### Test 3 — TestAnalystCannotEditTask
- tasks_router.update_task raises 403 if role == ANALYST
- Task created by admin to guarantee the ID exists before ANALYST tries PUT

### Test 4 — TestNonAdminCannotDeleteTask
- tasks_router.delete_task: only MASTER/ADMIN allowed
- Both ANALYST and COMMERCIAL receive 403
- Two separate test methods (one per role) — each creates and cleans up its own task

### Test 5 — TestCommercialContactOwnership
- contacts_router.update_contact: COMMERCIAL only edits contacts where assigned_to == their user_id
- Helper `_get_vendas2_id` queries GET /api/users to find vendas2@unidade-sao-paulo.com
- Contact created by admin assigned to vendas2; vendas1 (commercial_sp_session) tries PUT → 403
- Admin PUT on same contact → 200 (verifies admin bypass)

### Test 6 — TestLoginResponsePayload
- auth_router.login returns: flags, permissions, active_modules (all added in F1)
- Uses bare requests.post (no fixture) — standalone login call
- Checks isinstance(active_modules, list)

### Test 7 — TestContactUpdateTenantIsolation
- contacts_router.update_contact uses RETURNING * — response must reflect new name
- Compares response.company_id to admin_sp_session.last_login["active_company_id"]
- Confirms no cross-tenant data leak in the returned row

**Why:** F1 feature flags and RBAC hardening introduced new routes and tightened
existing ones. These tests catch regressions if the enforcement logic is weakened.
**How to apply:** Run this suite after any changes to deps.py, contacts_router.py,
tasks_router.py, users_router.py, or auth_router.py.
