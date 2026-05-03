"""End-to-end backend tests covering all features in the review request."""
import os
import uuid

import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://vendas-pipeline-app.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"


# ---------------- AUTH ----------------
class TestAuth:
    def test_login_master_returns_tokens_and_companies(self, master_session):
        data = master_session.last_login
        assert data["access_token"]
        assert data["refresh_token"]
        assert data["user"]["email"] == "master@franqueadora.com"
        assert isinstance(data["companies"], list)
        assert len(data["companies"]) == 4
        assert data["active_role"] == "MASTER"
        assert data["active_company_id"]

    def test_login_invalid_credentials(self):
        r = requests.post(f"{API}/auth/login", json={"email": "no@no.com", "password": "x"}, timeout=30)
        assert r.status_code == 401

    def test_me_endpoint(self, master_session):
        r = master_session.get(f"{API}/auth/me", timeout=30)
        assert r.status_code == 200
        d = r.json()
        assert d["user"]["email"] == "master@franqueadora.com"
        assert d["active_company_id"]
        assert d["active_role"] == "MASTER"
        assert len(d["companies"]) == 4

    def test_switch_company(self, master_session):
        cur = master_session.last_login["active_company_id"]
        other = next(c for c in master_session.last_login["companies"] if c["id"] != cur)
        r = master_session.post(f"{API}/auth/switch-company", json={"company_id": other["id"]}, timeout=30)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["active_company_id"] == other["id"]
        assert d["active_role"] == other["role"]
        # update Authorization to new token
        master_session.headers.update({"Authorization": f"Bearer {d['access_token']}"})
        # revert back to original
        revert = master_session.post(f"{API}/auth/switch-company", json={"company_id": cur}, timeout=30)
        assert revert.status_code == 200
        master_session.headers.update({"Authorization": f"Bearer {revert.json()['access_token']}"})

    def test_switch_company_unauthorized(self, admin_sp_session, admin_rj_session):
        rj_company_id = admin_rj_session.last_login["active_company_id"]
        r = admin_sp_session.post(f"{API}/auth/switch-company", json={"company_id": rj_company_id}, timeout=30)
        assert r.status_code == 403

    def test_logout(self, master_session):
        s = requests.Session()
        s.post(f"{API}/auth/login", json={"email": "master@franqueadora.com", "password": "master123"}, timeout=30)
        r = s.post(f"{API}/auth/logout", timeout=30)
        assert r.status_code == 204


# ---------------- CONTACTS ----------------
class TestContacts:
    def test_list_contacts_admin_sp(self, admin_sp_session):
        r = admin_sp_session.get(f"{API}/contacts", timeout=30)
        assert r.status_code == 200
        d = r.json()
        assert "items" in d or isinstance(d, list)

    def test_multitenant_isolation_sp_vs_rj(self, admin_sp_session, admin_rj_session):
        sp = admin_sp_session.get(f"{API}/contacts?limit=200", timeout=30).json()
        rj = admin_rj_session.get(f"{API}/contacts?limit=200", timeout=30).json()
        sp_items = sp.get("items", sp if isinstance(sp, list) else [])
        rj_items = rj.get("items", rj if isinstance(rj, list) else [])
        sp_ids = {c["id"] for c in sp_items}
        rj_ids = {c["id"] for c in rj_items}
        assert sp_ids.isdisjoint(rj_ids), "SP admin should not see RJ contacts (or vice versa)"

    def test_create_contact_as_admin(self, admin_sp_session):
        payload = {
            "name": f"TEST_{uuid.uuid4().hex[:6]}",
            "email": f"test_{uuid.uuid4().hex[:6]}@example.com",
            "phone": "+5511999999999",
            "type": "lead",
            "source": "website",
        }
        r = admin_sp_session.post(f"{API}/contacts", json=payload, timeout=30)
        assert r.status_code in (200, 201), r.text
        c = r.json()
        assert c["name"] == payload["name"]
        cid = c["id"]
        # GET back
        g = admin_sp_session.get(f"{API}/contacts/{cid}", timeout=30)
        assert g.status_code == 200
        assert g.json()["name"] == payload["name"] or g.json().get("contact", {}).get("name") == payload["name"]
        # cleanup
        admin_sp_session.delete(f"{API}/contacts/{cid}", timeout=30)

    def test_analyst_cannot_create_contact(self, analyst_sp_session):
        payload = {"name": "TEST_blocked", "email": "blocked@example.com", "type": "lead"}
        r = analyst_sp_session.post(f"{API}/contacts", json=payload, timeout=30)
        assert r.status_code == 403

    def test_add_activity_to_contact(self, admin_sp_session):
        # pick first contact
        listing = admin_sp_session.get(f"{API}/contacts?limit=1", timeout=30).json()
        items = listing.get("items", listing if isinstance(listing, list) else [])
        if not items:
            pytest.skip("no contacts available")
        cid = items[0]["id"]
        r = admin_sp_session.post(
            f"{API}/contacts/{cid}/activities",
            json={"type": "note", "description": "TEST activity", "occurred_at": None},
            timeout=30,
        )
        assert r.status_code in (200, 201), r.text


# ---------------- PIPELINE & DEALS ----------------
class TestPipelineAndDeals:
    def test_list_pipelines(self, admin_sp_session):
        r = admin_sp_session.get(f"{API}/pipelines", timeout=30)
        assert r.status_code == 200
        items = r.json()
        if isinstance(items, dict) and "items" in items:
            items = items["items"]
        assert len(items) >= 1
        first = items[0]
        # pipeline should have stages
        stages = first.get("stages") or []
        if not stages:
            # maybe stages endpoint separate
            sr = admin_sp_session.get(f"{API}/pipelines/{first['id']}", timeout=30)
            assert sr.status_code == 200
            stages = sr.json().get("stages", [])
        assert len(stages) == 6, f"expected 6 stages, got {len(stages)}"

    def test_list_deals_filter_pipeline(self, admin_sp_session):
        pls = admin_sp_session.get(f"{API}/pipelines", timeout=30).json()
        if isinstance(pls, dict) and "items" in pls:
            pls = pls["items"]
        pid = pls[0]["id"]
        r = admin_sp_session.get(f"{API}/deals?pipeline_id={pid}", timeout=30)
        assert r.status_code == 200

    def test_move_deal_stage(self, admin_sp_session):
        deals = admin_sp_session.get(f"{API}/deals", timeout=30).json()
        items = deals.get("items", deals if isinstance(deals, list) else [])
        if not items:
            pytest.skip("no deals")
        deal = items[0]
        pls = admin_sp_session.get(f"{API}/pipelines", timeout=30).json()
        if isinstance(pls, dict) and "items" in pls:
            pls = pls["items"]
        pl = next((p for p in pls if p["id"] == deal["pipeline_id"]), pls[0])
        stages = pl.get("stages") or admin_sp_session.get(f"{API}/pipelines/{pl['id']}").json().get("stages", [])
        new_stage = next((s for s in stages if s["id"] != deal["stage_id"]), None)
        if not new_stage:
            pytest.skip("no alternative stage")
        r = admin_sp_session.patch(
            f"{API}/deals/{deal['id']}/stage", json={"stage_id": new_stage["id"]}, timeout=30
        )
        assert r.status_code == 200, r.text

    def test_won_and_lost_endpoints_exist(self, admin_sp_session):
        deals = admin_sp_session.get(f"{API}/deals", timeout=30).json()
        items = deals.get("items", deals if isinstance(deals, list) else [])
        if len(items) < 2:
            pytest.skip("need at least 2 deals")
        # use two distinct deals to mark one won and one lost
        won_target = items[0]["id"]
        lost_target = items[1]["id"]
        r1 = admin_sp_session.post(f"{API}/deals/{won_target}/won", timeout=30)
        assert r1.status_code in (200, 201, 400, 409), r1.text  # 400/409 if already won — accepted
        r2 = admin_sp_session.post(
            f"{API}/deals/{lost_target}/lost", json={"reason": "TEST_lost"}, timeout=30
        )
        assert r2.status_code in (200, 201, 400, 409), r2.text


# ---------------- ANALYTICS ----------------
class TestAnalytics:
    def test_overview(self, admin_sp_session):
        r = admin_sp_session.get(f"{API}/analytics/overview", timeout=30)
        assert r.status_code == 200, r.text
        d = r.json()
        for k in ("total_leads", "conversion_rate", "pipeline_value", "won_value", "avg_ticket"):
            assert k in d, f"missing key {k}"

    def test_funnel(self, admin_sp_session):
        r = admin_sp_session.get(f"{API}/analytics/funnel", timeout=30)
        assert r.status_code == 200
        d = r.json()
        stages = d if isinstance(d, list) else d.get("stages", [])
        assert len(stages) >= 1

    def test_revenue(self, admin_sp_session):
        r = admin_sp_session.get(f"{API}/analytics/revenue", timeout=30)
        assert r.status_code == 200
        d = r.json()
        items = d if isinstance(d, list) else d.get("items", d.get("data", d.get("months", [])))
        assert len(items) >= 1

    def test_leaderboard(self, admin_sp_session):
        r = admin_sp_session.get(f"{API}/analytics/leaderboard", timeout=30)
        assert r.status_code == 200


# ---------------- COMPANIES (MASTER) ----------------
class TestCompanies:
    def test_list_companies_master(self, master_session):
        r = master_session.get(f"{API}/companies", timeout=30)
        assert r.status_code == 200
        items = r.json()
        if isinstance(items, dict) and "items" in items:
            items = items["items"]
        assert len(items) >= 4

    def test_consolidated_master(self, master_session):
        r = master_session.get(f"{API}/companies/consolidated", timeout=30)
        assert r.status_code == 200, r.text
        d = r.json()
        items = d if isinstance(d, list) else d.get("items", d.get("companies", []))
        assert len(items) >= 1

    def test_companies_blocked_for_admin(self, admin_sp_session):
        r = admin_sp_session.get(f"{API}/companies", timeout=30)
        assert r.status_code == 403


# ---------------- TASKS ----------------
class TestTasks:
    def test_create_and_complete_task(self, admin_sp_session):
        payload = {"title": "TEST_task", "description": "test", "due_date": None}
        r = admin_sp_session.post(f"{API}/tasks", json=payload, timeout=30)
        assert r.status_code in (200, 201), r.text
        t = r.json()
        tid = t["id"]
        c = admin_sp_session.patch(f"{API}/tasks/{tid}/complete", timeout=30)
        assert c.status_code in (200, 204), c.text


# ---------------- NOTIFICATIONS ----------------
class TestNotifications:
    def test_list_notifications(self, admin_sp_session):
        r = admin_sp_session.get(f"{API}/notifications", timeout=30)
        assert r.status_code == 200
