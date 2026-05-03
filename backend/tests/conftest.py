"""Shared fixtures for backend tests."""
import os

import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://vendas-pipeline-app.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"


def _login(email: str, password: str) -> requests.Session:
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    r = s.post(f"{API}/auth/login", json={"email": email, "password": password}, timeout=30)
    assert r.status_code == 200, f"login failed for {email}: {r.status_code} {r.text}"
    data = r.json()
    # also set Authorization (belt + suspenders since cookies sometimes travel awkwardly via curl/proxies)
    s.headers.update({"Authorization": f"Bearer {data['access_token']}"})
    s.last_login = data  # type: ignore[attr-defined]
    return s


@pytest.fixture(scope="session")
def base_url():
    return BASE_URL


@pytest.fixture(scope="session")
def api_url():
    return API


@pytest.fixture(scope="session")
def master_session():
    return _login("master@franqueadora.com", "master123")


@pytest.fixture(scope="session")
def admin_sp_session():
    return _login("admin@unidade-sao-paulo.com", "senha123")


@pytest.fixture(scope="session")
def commercial_sp_session():
    return _login("vendas@unidade-sao-paulo.com", "senha123")


@pytest.fixture(scope="session")
def analyst_sp_session():
    return _login("analista@unidade-sao-paulo.com", "senha123")


@pytest.fixture(scope="session")
def admin_rj_session():
    return _login("admin@unidade-rio-de-janeiro.com", "senha123")
