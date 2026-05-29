"""Security tests for CRM SaaS FastAPI backend.

Covers 7 security scenarios:
  1. User with membership removed gets 401/403 on subsequent requests
  2. ANALYST is blocked from creating tasks (403)
  3. ANALYST is blocked from editing tasks (403)
  4. ANALYST and COMMERCIAL are both blocked from deleting tasks (403)
  5. COMMERCIAL cannot update a contact owned by another COMMERCIAL (403)
  6. Login response contains flags, permissions and active_modules fields
  7. PUT /contacts returns the correct tenant company_id after update
"""
import os
import uuid

import pytest
import requests

BASE_URL = os.environ.get(
    "BACKEND_URL",
    os.environ.get("REACT_APP_BACKEND_URL", "http://localhost:8001"),
).rstrip("/")
API = f"{BASE_URL}/api"

# Email for the second commercial seeded in SP (from seed.py)
_VENDAS2_EMAIL = "vendas2@unidade-sao-paulo.com"
_ADMIN_SP_EMAIL = "admin@unidade-sao-paulo.com"
_ADMIN_SP_PASS = "senha123"


def _login(email: str, password: str) -> requests.Session:
    """Returns a logged-in session with Authorization header set."""
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    r = s.post(
        f"{API}/auth/login",
        json={"email": email, "password": password},
        timeout=30,
    )
    assert r.status_code == 200, f"login failed for {email}: {r.status_code} {r.text}"
    data = r.json()
    s.headers.update({"Authorization": f"Bearer {data['access_token']}"})
    s.last_login = data  # type: ignore[attr-defined]
    return s


# ─────────────────────────────────────────────────────────────────────────────
# Test 1: Membership-removed user gets 401/403 on subsequent API calls
# ─────────────────────────────────────────────────────────────────────────────
class TestRemovedMembershipBlocksAccess:
    """After an admin removes a user from the company (DELETE /users/{id}),
    that user's existing JWT should be rejected by the company-scoped endpoints
    because the membership row no longer exists.

    The users table row remains (soft-delete of the *user* was not requested),
    so get_current_user succeeds but get_current_company returns 403
    ("Acesso negado a esta empresa") because the user_companies row is gone.
    /auth/me only uses get_current_user, so it may still return 200 with an
    empty companies list — both 200 (no companies) and 401/403 are acceptable
    for /auth/me, but a company-scoped endpoint MUST return 403.
    """

    def test_removed_member_blocked_on_company_scoped_endpoint(
        self, admin_sp_session
    ):
        # 1. Create a temporary COMMERCIAL user
        temp_email = f"sec_test_{uuid.uuid4().hex[:8]}@test.com"
        temp_pass = "changeme123"
        invite_r = admin_sp_session.post(
            f"{API}/users/invite",
            json={
                "email": temp_email,
                "name": "SEC TEST",
                "role": "COMMERCIAL",
                "password": temp_pass,
            },
            timeout=30,
        )
        assert invite_r.status_code == 201, (
            f"invite failed: {invite_r.status_code} {invite_r.text}"
        )
        user_id = invite_r.json()["id"]

        # 2. Login as that new user and capture a valid token
        new_session = _login(temp_email, temp_pass)

        # Sanity: the fresh session can reach /api/tasks (company-scoped)
        sanity_r = new_session.get(f"{API}/tasks", timeout=30)
        assert sanity_r.status_code == 200, (
            f"sanity check failed before removal: {sanity_r.status_code} {sanity_r.text}"
        )

        # 3. Admin removes the membership
        del_r = admin_sp_session.delete(f"{API}/users/{user_id}", timeout=30)
        assert del_r.status_code == 204, (
            f"delete membership failed: {del_r.status_code} {del_r.text}"
        )

        # 4. The same JWT must now be rejected on any company-scoped endpoint.
        #    get_current_company queries user_companies and the row is gone → 403.
        blocked_r = new_session.get(f"{API}/tasks", timeout=30)
        assert blocked_r.status_code in (401, 403), (
            f"expected 401 or 403 after membership removal, "
            f"got {blocked_r.status_code}: {blocked_r.text}"
        )


# ─────────────────────────────────────────────────────────────────────────────
# Test 2: ANALYST cannot create tasks
# ─────────────────────────────────────────────────────────────────────────────
class TestAnalystCannotCreateTask:
    """POST /api/tasks by an ANALYST must be rejected with 403."""

    def test_analyst_post_tasks_returns_403(self, analyst_sp_session):
        r = analyst_sp_session.post(
            f"{API}/tasks",
            json={"title": "Tarefa ANALYST bloqueada", "priority": "low"},
            timeout=30,
        )
        assert r.status_code == 403, (
            f"ANALYST should be blocked from creating tasks, "
            f"got {r.status_code}: {r.text}"
        )


# ─────────────────────────────────────────────────────────────────────────────
# Test 3: ANALYST cannot edit tasks
# ─────────────────────────────────────────────────────────────────────────────
class TestAnalystCannotEditTask:
    """PUT /api/tasks/{id} by an ANALYST must be rejected with 403.
    The task is created by admin to guarantee the task_id exists.
    """

    def test_analyst_put_task_returns_403(self, admin_sp_session, analyst_sp_session):
        # Create a task as admin
        create_r = admin_sp_session.post(
            f"{API}/tasks",
            json={"title": "Task for analyst edit test", "priority": "medium"},
            timeout=30,
        )
        assert create_r.status_code in (200, 201), (
            f"admin task creation failed: {create_r.status_code} {create_r.text}"
        )
        task_id = create_r.json()["id"]

        try:
            # ANALYST attempts to edit
            r = analyst_sp_session.put(
                f"{API}/tasks/{task_id}",
                json={"title": "ANALYST attempt to rename"},
                timeout=30,
            )
            assert r.status_code == 403, (
                f"ANALYST should be blocked from editing tasks, "
                f"got {r.status_code}: {r.text}"
            )
        finally:
            # Cleanup — ignore failures
            admin_sp_session.delete(f"{API}/tasks/{task_id}", timeout=30)


# ─────────────────────────────────────────────────────────────────────────────
# Test 4: ANALYST and COMMERCIAL cannot delete tasks
# ─────────────────────────────────────────────────────────────────────────────
class TestNonAdminCannotDeleteTask:
    """DELETE /api/tasks/{id} is restricted to ADMIN and MASTER.
    Both ANALYST and COMMERCIAL must receive 403.
    """

    def test_analyst_delete_task_returns_403(
        self, admin_sp_session, analyst_sp_session
    ):
        create_r = admin_sp_session.post(
            f"{API}/tasks",
            json={"title": "Task for analyst delete test", "priority": "low"},
            timeout=30,
        )
        assert create_r.status_code in (200, 201), (
            f"admin task creation failed: {create_r.status_code} {create_r.text}"
        )
        task_id = create_r.json()["id"]

        try:
            r = analyst_sp_session.delete(f"{API}/tasks/{task_id}", timeout=30)
            assert r.status_code == 403, (
                f"ANALYST should be blocked from deleting tasks, "
                f"got {r.status_code}: {r.text}"
            )
        finally:
            admin_sp_session.delete(f"{API}/tasks/{task_id}", timeout=30)

    def test_commercial_delete_task_returns_403(
        self, admin_sp_session, commercial_sp_session
    ):
        create_r = admin_sp_session.post(
            f"{API}/tasks",
            json={"title": "Task for commercial delete test", "priority": "high"},
            timeout=30,
        )
        assert create_r.status_code in (200, 201), (
            f"admin task creation failed: {create_r.status_code} {create_r.text}"
        )
        task_id = create_r.json()["id"]

        try:
            r = commercial_sp_session.delete(f"{API}/tasks/{task_id}", timeout=30)
            assert r.status_code == 403, (
                f"COMMERCIAL should be blocked from deleting tasks, "
                f"got {r.status_code}: {r.text}"
            )
        finally:
            admin_sp_session.delete(f"{API}/tasks/{task_id}", timeout=30)


# ─────────────────────────────────────────────────────────────────────────────
# Test 5: COMMERCIAL cannot update a contact assigned to another COMMERCIAL
# ─────────────────────────────────────────────────────────────────────────────
class TestCommercialContactOwnership:
    """contacts_router enforces: COMMERCIAL can only PUT their own contacts.

    Setup: admin creates a contact assigned to vendas2 (not vendas1).
    vendas1 (commercial_sp_session) tries to PUT → must receive 403.
    admin_sp_session can PUT the same contact → must receive 200.
    """

    def _get_vendas2_id(self, admin_sp_session: requests.Session) -> str:
        """Retrieve the user_id of vendas2@unidade-sao-paulo.com."""
        r = admin_sp_session.get(f"{API}/users", timeout=30)
        assert r.status_code == 200, f"GET /users failed: {r.status_code} {r.text}"
        items = r.json().get("items", [])
        user = next(
            (u for u in items if u.get("email") == _VENDAS2_EMAIL), None
        )
        assert user is not None, (
            f"{_VENDAS2_EMAIL} not found in users list. "
            f"Available: {[u.get('email') for u in items]}"
        )
        return user["id"]

    def test_commercial_cannot_edit_contact_of_another_commercial(
        self, admin_sp_session, commercial_sp_session
    ):
        vendas2_id = self._get_vendas2_id(admin_sp_session)

        # Create a contact owned by vendas2
        contact_name = f"SEC_CONTACT_{uuid.uuid4().hex[:6]}"
        create_r = admin_sp_session.post(
            f"{API}/contacts",
            json={
                "name": contact_name,
                "email": f"sec_{uuid.uuid4().hex[:6]}@example.com",
                "type": "lead",
                "assigned_to": vendas2_id,
            },
            timeout=30,
        )
        assert create_r.status_code in (200, 201), (
            f"admin contact creation failed: {create_r.status_code} {create_r.text}"
        )
        contact_id = create_r.json()["id"]

        try:
            # vendas1 (commercial_sp_session) tries to edit vendas2's contact
            r = commercial_sp_session.put(
                f"{API}/contacts/{contact_id}",
                json={"name": "HIJACKED"},
                timeout=30,
            )
            assert r.status_code == 403, (
                f"COMMERCIAL should not be able to edit another COMMERCIAL's contact, "
                f"got {r.status_code}: {r.text}"
            )

            # admin_sp_session must succeed on the same contact
            admin_r = admin_sp_session.put(
                f"{API}/contacts/{contact_id}",
                json={"name": f"{contact_name}_UPDATED"},
                timeout=30,
            )
            assert admin_r.status_code == 200, (
                f"ADMIN should be able to edit any contact, "
                f"got {admin_r.status_code}: {admin_r.text}"
            )
        finally:
            admin_sp_session.delete(f"{API}/contacts/{contact_id}", timeout=30)


# ─────────────────────────────────────────────────────────────────────────────
# Test 6: Login response includes flags, permissions and active_modules
# ─────────────────────────────────────────────────────────────────────────────
class TestLoginResponsePayload:
    """The login response must contain flags, permissions and active_modules so
    the frontend can gate features without extra round-trips.
    """

    def test_login_returns_flags_permissions_active_modules(self):
        r = requests.post(
            f"{API}/auth/login",
            json={"email": _ADMIN_SP_EMAIL, "password": _ADMIN_SP_PASS},
            timeout=30,
        )
        assert r.status_code == 200, (
            f"login failed: {r.status_code} {r.text}"
        )
        data = r.json()

        assert "flags" in data, (
            "login response missing 'flags' field"
        )
        assert "permissions" in data, (
            "login response missing 'permissions' field"
        )
        assert "active_modules" in data, (
            "login response missing 'active_modules' field"
        )
        assert isinstance(data["active_modules"], list), (
            f"'active_modules' must be a list, got {type(data['active_modules'])}"
        )


# ─────────────────────────────────────────────────────────────────────────────
# Test 7: PUT /contacts returns updated data with correct tenant company_id
# ─────────────────────────────────────────────────────────────────────────────
class TestContactUpdateTenantIsolation:
    """Verifies that PUT /contacts/{id} returns the RETURNING * row from the
    correct tenant, confirming:
    - the updated name is reflected in the response (RETURNING * works)
    - company_id in the response matches the SP company (not another tenant)
    """

    def test_put_contact_returns_correct_company_id_and_new_name(
        self, admin_sp_session
    ):
        sp_company_id = admin_sp_session.last_login["active_company_id"]

        # Create a contact
        original_name = f"TENANT_TEST_{uuid.uuid4().hex[:8]}"
        create_r = admin_sp_session.post(
            f"{API}/contacts",
            json={
                "name": original_name,
                "email": f"tenant_{uuid.uuid4().hex[:6]}@example.com",
                "type": "lead",
            },
            timeout=30,
        )
        assert create_r.status_code in (200, 201), (
            f"contact creation failed: {create_r.status_code} {create_r.text}"
        )
        contact_id = create_r.json()["id"]

        try:
            updated_name = f"{original_name}_UPDATED"
            put_r = admin_sp_session.put(
                f"{API}/contacts/{contact_id}",
                json={"name": updated_name},
                timeout=30,
            )
            assert put_r.status_code == 200, (
                f"PUT contact failed: {put_r.status_code} {put_r.text}"
            )
            body = put_r.json()

            # The updated name must be present in the response
            assert body.get("name") == updated_name, (
                f"Response should reflect the updated name '{updated_name}', "
                f"got '{body.get('name')}'"
            )

            # The company_id must match the SP tenant
            assert body.get("company_id") == sp_company_id, (
                f"Response company_id should be SP's '{sp_company_id}', "
                f"got '{body.get('company_id')}'"
            )
        finally:
            admin_sp_session.delete(f"{API}/contacts/{contact_id}", timeout=30)
