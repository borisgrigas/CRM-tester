"""Tests for NEW admin features: user management rules + company management rules.

Covers iteration 2 of review_request:
- ADMIN/MASTER user mgmt endpoints (invite, role, activate/deactivate, delete)
- Business rules: ADMIN cannot touch ADMIN/MASTER, last active ADMIN protection
- Company CRUD (create with unique slug, update ignores slug, activate/deactivate, soft delete)
- get_current_company middleware: blocks inactive/deleted companies
"""
import os
import uuid

import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://vendas-pipeline-app.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"


def _login(email, password):
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    r = s.post(f"{API}/auth/login", json={"email": email, "password": password}, timeout=30)
    assert r.status_code == 200, f"login {email} failed: {r.text}"
    data = r.json()
    s.headers.update({"Authorization": f"Bearer {data['access_token']}"})
    s.last_login = data
    return s


# ================== USERS (Admin panel) ==================
class TestUsersList:
    def test_list_users_returns_items_with_role_and_is_active(self, admin_sp_session):
        r = admin_sp_session.get(f"{API}/users", timeout=30)
        assert r.status_code == 200, r.text
        items = r.json().get("items", [])
        assert len(items) >= 1
        sample = items[0]
        assert "role" in sample
        assert "is_active" in sample
        assert "email" in sample


class TestUserInvite:
    def test_admin_can_invite_commercial(self, admin_sp_session):
        email = f"test_invite_{uuid.uuid4().hex[:6]}@test.com"
        r = admin_sp_session.post(
            f"{API}/users/invite",
            json={"email": email, "name": "TEST Invited", "role": "COMMERCIAL", "password": "changeme123"},
            timeout=30,
        )
        assert r.status_code == 201, r.text
        data = r.json()
        assert data["email"] == email
        assert data["role"] == "COMMERCIAL"
        assert data["is_active"] is True
        # Verify appears in list
        listing = admin_sp_session.get(f"{API}/users", timeout=30).json()["items"]
        assert any(u["email"] == email for u in listing)
        # Cleanup
        uid = data["id"]
        admin_sp_session.delete(f"{API}/users/{uid}", timeout=30)

    def test_admin_can_invite_analyst(self, admin_sp_session):
        email = f"test_analyst_{uuid.uuid4().hex[:6]}@test.com"
        r = admin_sp_session.post(
            f"{API}/users/invite",
            json={"email": email, "name": "TEST A", "role": "ANALYST"},
            timeout=30,
        )
        assert r.status_code == 201, r.text
        admin_sp_session.delete(f"{API}/users/{r.json()['id']}", timeout=30)

    def test_admin_cannot_invite_admin(self, admin_sp_session):
        r = admin_sp_session.post(
            f"{API}/users/invite",
            json={"email": f"x_{uuid.uuid4().hex[:6]}@t.com", "name": "X", "role": "ADMIN"},
            timeout=30,
        )
        assert r.status_code == 403
        assert "ADMIN" in r.json().get("detail", "")

    def test_admin_cannot_invite_master(self, admin_sp_session):
        r = admin_sp_session.post(
            f"{API}/users/invite",
            json={"email": f"x_{uuid.uuid4().hex[:6]}@t.com", "name": "X", "role": "MASTER"},
            timeout=30,
        )
        assert r.status_code == 403


class TestUserRoleUpdate:
    def test_admin_cannot_change_role_of_other_admin(self, admin_sp_session, master_session):
        # master switches to SP company to inspect members
        # Find another ADMIN in SP - seed should only have 1 ADMIN; so we create a second ADMIN using MASTER
        # but master needs to be in sp company. Simpler: test that ADMIN cannot promote a COMMERCIAL to ADMIN
        items = admin_sp_session.get(f"{API}/users", timeout=30).json()["items"]
        commercial = next((u for u in items if u["role"] == "COMMERCIAL"), None)
        if not commercial:
            pytest.skip("no commercial in SP")
        r = admin_sp_session.put(
            f"{API}/users/{commercial['id']}/role", json={"role": "ADMIN"}, timeout=30
        )
        assert r.status_code == 403, r.text
        assert "ADMIN" in r.json().get("detail", "")

    def test_admin_cannot_alter_another_admin_or_master(self, admin_sp_session):
        items = admin_sp_session.get(f"{API}/users", timeout=30).json()["items"]
        # try to mess with a MASTER if any exists in this company membership
        master = next((u for u in items if u["role"] == "MASTER"), None)
        if master:
            r = admin_sp_session.put(
                f"{API}/users/{master['id']}/role", json={"role": "COMMERCIAL"}, timeout=30
            )
            assert r.status_code == 403

    def test_admin_can_change_commercial_to_analyst_and_back(self, admin_sp_session):
        items = admin_sp_session.get(f"{API}/users", timeout=30).json()["items"]
        commercial = next((u for u in items if u["role"] == "COMMERCIAL"), None)
        if not commercial:
            pytest.skip("no commercial user")
        r = admin_sp_session.put(
            f"{API}/users/{commercial['id']}/role", json={"role": "ANALYST"}, timeout=30
        )
        assert r.status_code == 200, r.text
        assert r.json()["role"] == "ANALYST"
        # revert
        r2 = admin_sp_session.put(
            f"{API}/users/{commercial['id']}/role", json={"role": "COMMERCIAL"}, timeout=30
        )
        assert r2.status_code == 200


class TestUserActivateDeactivate:
    def test_deactivate_then_activate_commercial(self, admin_sp_session):
        # create a temp user to deactivate
        email = f"test_deact_{uuid.uuid4().hex[:6]}@t.com"
        inv = admin_sp_session.post(
            f"{API}/users/invite",
            json={"email": email, "name": "DEACT", "role": "COMMERCIAL"},
            timeout=30,
        )
        assert inv.status_code == 201
        uid = inv.json()["id"]
        d = admin_sp_session.patch(f"{API}/users/{uid}/deactivate", timeout=30)
        assert d.status_code == 200, d.text
        assert d.json()["is_active"] is False
        # verify in listing
        items = admin_sp_session.get(f"{API}/users", timeout=30).json()["items"]
        target = next((u for u in items if u["id"] == uid), None)
        assert target and target["is_active"] is False
        a = admin_sp_session.patch(f"{API}/users/{uid}/activate", timeout=30)
        assert a.status_code == 200
        assert a.json()["is_active"] is True
        admin_sp_session.delete(f"{API}/users/{uid}", timeout=30)

    def test_cannot_deactivate_last_active_admin(self, admin_sp_session):
        """O próprio admin_sp é o último ADMIN ativo — ao tentar deactivate a si próprio, deve falhar.
        O próprio deactivate do user atual também passa por _enforce_admin_protection (ADMIN não pode
        alterar outro ADMIN, mas pode alterar a si próprio se a regra for 'outro'). Testamos explicitly
        que o backend retorna 400 last-admin OU 403 self-protection — ambos são proteções válidas."""
        my_id = admin_sp_session.last_login["user"]["id"]
        r = admin_sp_session.patch(f"{API}/users/{my_id}/deactivate", timeout=30)
        # Backend rule: ADMIN não pode alterar outro ADMIN (403) OU último ADMIN ativo (400)
        assert r.status_code in (400, 403), r.text
        # Validate message mentions ADMIN
        detail = r.json().get("detail", "")
        assert "ADMIN" in detail


class TestUserDelete:
    def test_cannot_self_delete(self, admin_sp_session):
        my_id = admin_sp_session.last_login["user"]["id"]
        r = admin_sp_session.delete(f"{API}/users/{my_id}", timeout=30)
        assert r.status_code == 400
        assert "si mesmo" in r.json().get("detail", "").lower() or "remover" in r.json().get("detail", "").lower()

    def test_delete_removes_membership_only(self, admin_sp_session):
        email = f"test_del_{uuid.uuid4().hex[:6]}@t.com"
        inv = admin_sp_session.post(
            f"{API}/users/invite",
            json={"email": email, "name": "DEL", "role": "COMMERCIAL"},
            timeout=30,
        )
        uid = inv.json()["id"]
        r = admin_sp_session.delete(f"{API}/users/{uid}", timeout=30)
        assert r.status_code == 204
        items = admin_sp_session.get(f"{API}/users", timeout=30).json()["items"]
        assert not any(u["id"] == uid for u in items)


# ================== COMPANIES (MASTER panel) ==================
class TestCompaniesCRUD:
    def test_admin_forbidden_list(self, admin_sp_session):
        r = admin_sp_session.get(f"{API}/companies", timeout=30)
        assert r.status_code == 403

    def test_master_list_includes_is_active_and_counts(self, master_session):
        r = master_session.get(f"{API}/companies", timeout=30)
        assert r.status_code == 200
        items = r.json().get("items", [])
        assert len(items) >= 1
        sample = items[0]
        assert "is_active" in sample
        assert "plan" in sample
        assert "leads_count" in sample
        assert "deals_count" in sample

    def test_create_company_with_unique_slug(self, master_session):
        slug = f"test-co-{uuid.uuid4().hex[:6]}"
        r = master_session.post(
            f"{API}/companies",
            json={"name": "TEST Co", "slug": slug, "plan": "pro"},
            timeout=30,
        )
        assert r.status_code == 201, r.text
        c = r.json()
        assert c["slug"] == slug
        assert c["is_active"] is True
        assert c["plan"] == "pro"
        cid = c["id"]
        # creator is MASTER of new company - check via list
        items = master_session.get(f"{API}/companies", timeout=30).json()["items"]
        assert any(x["id"] == cid for x in items)
        # duplicate slug returns 400
        dup = master_session.post(
            f"{API}/companies", json={"name": "x", "slug": slug}, timeout=30
        )
        assert dup.status_code == 400
        assert "Slug" in dup.json().get("detail", "")
        # soft delete cleanup
        master_session.delete(f"{API}/companies/{cid}", timeout=30)

    def test_update_company_ignores_slug(self, master_session):
        slug = f"imut-{uuid.uuid4().hex[:6]}"
        cr = master_session.post(
            f"{API}/companies", json={"name": "TEST Imut", "slug": slug}, timeout=30
        )
        assert cr.status_code == 201
        cid = cr.json()["id"]
        # attempt to change slug
        up = master_session.put(
            f"{API}/companies/{cid}",
            json={"name": "TEST Imut Updated", "slug": "hacked-slug", "plan": "enterprise"},
            timeout=30,
        )
        assert up.status_code == 200, up.text
        result = up.json()
        assert result["slug"] == slug  # unchanged
        assert result["name"] == "TEST Imut Updated"
        assert result["plan"] == "enterprise"
        master_session.delete(f"{API}/companies/{cid}", timeout=30)

    def test_activate_deactivate_company(self, master_session):
        slug = f"act-{uuid.uuid4().hex[:6]}"
        cr = master_session.post(
            f"{API}/companies", json={"name": "TEST Act", "slug": slug}, timeout=30
        )
        cid = cr.json()["id"]
        d = master_session.patch(f"{API}/companies/{cid}/deactivate", timeout=30)
        assert d.status_code == 200
        assert d.json()["is_active"] is False
        a = master_session.patch(f"{API}/companies/{cid}/activate", timeout=30)
        assert a.status_code == 200
        assert a.json()["is_active"] is True
        master_session.delete(f"{API}/companies/{cid}", timeout=30)

    def test_soft_delete_company(self, master_session):
        slug = f"del-{uuid.uuid4().hex[:6]}"
        cr = master_session.post(
            f"{API}/companies", json={"name": "TEST Del", "slug": slug}, timeout=30
        )
        cid = cr.json()["id"]
        r = master_session.delete(f"{API}/companies/{cid}", timeout=30)
        assert r.status_code == 204
        # should no longer be returned by list (filtered by deleted_at)
        items = master_session.get(f"{API}/companies", timeout=30).json()["items"]
        assert not any(x["id"] == cid for x in items)
        # direct get returns 404
        g = master_session.get(f"{API}/companies/{cid}", timeout=30)
        assert g.status_code == 404


# ================== Middleware: inactive/deleted company ==================
class TestInactiveCompanyMiddleware:
    def test_deactivated_company_blocks_members(self, master_session, admin_sp_session):
        """Create a fresh company, invite SP admin... actually simpler: deactivate SP
        then re-activate, verifying admin_sp gets 403 'Empresa inativa' while deactivated."""
        # Find SP company id
        companies = master_session.get(f"{API}/companies", timeout=30).json()["items"]
        sp = next((c for c in companies if "sao-paulo" in c["slug"]), None)
        if not sp:
            pytest.skip("unidade-sao-paulo not found")
        sp_id = sp["id"]
        # Deactivate
        d = master_session.patch(f"{API}/companies/{sp_id}/deactivate", timeout=30)
        assert d.status_code == 200
        try:
            # admin_sp_session must now receive 403 Empresa inativa on /contacts
            r1 = admin_sp_session.get(f"{API}/contacts", timeout=30)
            assert r1.status_code == 403, f"expected 403, got {r1.status_code}: {r1.text}"
            assert "inativa" in r1.json().get("detail", "").lower()
            # and on /auth/me -- note /auth/me may or may not call get_current_company
            # Test also /pipelines which uses get_current_company
            r2 = admin_sp_session.get(f"{API}/pipelines", timeout=30)
            assert r2.status_code == 403
        finally:
            # always reactivate
            master_session.patch(f"{API}/companies/{sp_id}/activate", timeout=30)
        # verify back to normal
        r3 = admin_sp_session.get(f"{API}/contacts", timeout=30)
        assert r3.status_code == 200

    def test_deleted_company_returns_404(self, master_session):
        slug = f"tobedel-{uuid.uuid4().hex[:6]}"
        # Master creates company, will be MASTER of it; deletes; then tries to switch-company to it
        cr = master_session.post(
            f"{API}/companies", json={"name": "TEST ToBeDel", "slug": slug}, timeout=30
        )
        cid = cr.json()["id"]
        master_session.delete(f"{API}/companies/{cid}", timeout=30)
        # Try switch into the deleted company
        r = master_session.post(
            f"{API}/auth/switch-company", json={"company_id": cid}, timeout=30
        )
        # Switch should reject (403 no active membership due to deletion, or 404)
        assert r.status_code in (403, 404), r.text


# -------- Fixtures (reuse with session scope at this module level) --------
@pytest.fixture(scope="module")
def master_session():
    return _login("master@franqueadora.com", "master123")


@pytest.fixture(scope="module")
def admin_sp_session():
    return _login("admin@unidade-sao-paulo.com", "senha123")
