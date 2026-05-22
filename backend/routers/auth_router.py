"""Auth router: login, refresh, logout, switch-company, me."""
import os
import secrets
import uuid
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, Response

from auth_utils import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from core.feature_flags import get_company_flags
from core.permissions import get_user_permissions
from db import get_db
from deps import get_current_user
from models import (
    ForgotPasswordInput,
    LoginInput,
    PasswordChangeInput,
    ResetPasswordInput,
    SwitchCompanyInput,
)

router = APIRouter(prefix="/auth", tags=["auth"])

_IS_PROD = os.environ.get("ENV", "development").lower() == "production"
_SAMESITE = "none" if _IS_PROD else "lax"


def _set_cookies(response: Response, access: str, refresh: str | None = None) -> None:
    response.set_cookie(
        key="access_token", value=access, httponly=True, secure=_IS_PROD,
        samesite=_SAMESITE, max_age=60 * 15, path="/",
    )
    if refresh:
        response.set_cookie(
            key="refresh_token", value=refresh, httponly=True, secure=_IS_PROD,
            samesite=_SAMESITE, max_age=60 * 60 * 24 * 7, path="/",
        )


async def _user_companies_payload(conn, user_id: str) -> list[dict]:
    memberships = await conn.fetch(
        "SELECT * FROM user_companies WHERE user_id = $1 AND is_active = TRUE", user_id
    )
    if not memberships:
        return []
    company_ids = [m["company_id"] for m in memberships]
    companies = await conn.fetch(
        "SELECT * FROM companies WHERE id = ANY($1) AND deleted_at IS NULL AND is_active = TRUE",
        company_ids,
    )
    by_id = {c["id"]: dict(c) for c in companies}
    out = []
    for m in memberships:
        c = by_id.get(m["company_id"])
        if c:
            out.append({
                **c,
                "is_franchisor": c.get("is_franchisor", False),
                "role": m["role"],
                "modules": m["modules"] or [],
            })
    return out


async def _membership_modules(conn, user_id: str, company_id: str) -> list[str]:
    row = await conn.fetchrow(
        "SELECT modules FROM user_companies WHERE user_id = $1 AND company_id = $2 AND is_active = TRUE",
        user_id, company_id,
    )
    if not row:
        return []
    return row["modules"] or []


@router.post("/login")
async def login(payload: LoginInput, response: Response, conn=Depends(get_db)):
    email = payload.email.lower().strip()
    user_row = await conn.fetchrow("SELECT * FROM users WHERE email = $1", email)
    if not user_row or not verify_password(payload.password, user_row["password_hash"]):
        raise HTTPException(status_code=401, detail="Email ou senha incorretos")

    user = dict(user_row)
    companies = await _user_companies_payload(conn, user["id"])
    if not companies:
        raise HTTPException(status_code=403, detail="Usuário sem empresa ativa")

    default_company = (
        next((c for c in companies if c["role"] == "MASTER" and c.get("plan") == "enterprise"), None)
        or next((c for c in companies if c["role"] == "MASTER"), None)
        or companies[0]
    )
    access = create_access_token(user["id"], user["email"], default_company["id"], default_company["role"])
    refresh = create_refresh_token(user["id"])
    _set_cookies(response, access, refresh)

    flags = await get_company_flags(conn, default_company["id"])
    permissions = await get_user_permissions(conn, user["id"], default_company["id"])
    user.pop("password_hash", None)
    return {
        "access_token": access,
        "refresh_token": refresh,
        "user": user,
        "companies": companies,
        "active_company_id": default_company["id"],
        "active_role": default_company["role"],
        "flags": flags,
        "permissions": permissions,
    }


@router.post("/refresh")
async def refresh(request: Request, response: Response, conn=Depends(get_db)):
    token = request.cookies.get("refresh_token")
    if not token:
        raise HTTPException(status_code=401, detail="Refresh token ausente")
    try:
        payload = decode_token(token)
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=401, detail="Token inválido")
    except Exception:
        raise HTTPException(status_code=401, detail="Token inválido")

    row = await conn.fetchrow(
        "SELECT id, name, email, avatar_url, created_at FROM users WHERE id = $1", payload["sub"]
    )
    if not row:
        raise HTTPException(status_code=401, detail="Usuário não encontrado")

    user = dict(row)
    companies = await _user_companies_payload(conn, user["id"])
    default_company = (
        next((c for c in companies if c["role"] == "MASTER" and c.get("plan") == "enterprise"), None)
        or next((c for c in companies if c["role"] == "MASTER"), None)
        or (companies[0] if companies else None)
    )
    cid = default_company["id"] if default_company else None
    role = default_company["role"] if default_company else None
    access = create_access_token(user["id"], user["email"], cid, role)
    _set_cookies(response, access)
    return {"access_token": access}


@router.post("/logout", status_code=204)
async def logout(response: Response):
    response.delete_cookie("access_token", path="/")
    response.delete_cookie("refresh_token", path="/")
    return Response(status_code=204)


@router.post("/switch-company")
async def switch_company(
    payload: SwitchCompanyInput, response: Response,
    user: dict = Depends(get_current_user), conn=Depends(get_db),
):
    membership_row = await conn.fetchrow(
        "SELECT * FROM user_companies WHERE user_id = $1 AND company_id = $2 AND is_active = TRUE",
        user["id"], payload.company_id,
    )
    if not membership_row:
        raise HTTPException(status_code=403, detail="Empresa não autorizada")
    company_row = await conn.fetchrow(
        "SELECT * FROM companies WHERE id = $1 AND deleted_at IS NULL", payload.company_id
    )
    if not company_row:
        raise HTTPException(status_code=404, detail="Empresa não encontrada")
    if not company_row["is_active"]:
        raise HTTPException(status_code=403, detail="Empresa inativa")

    membership = dict(membership_row)
    access = create_access_token(user["id"], user["email"], payload.company_id, membership["role"])
    _set_cookies(response, access)
    flags = await get_company_flags(conn, payload.company_id)
    permissions = await get_user_permissions(conn, user["id"], payload.company_id)
    return {
        "access_token": access,
        "active_company_id": payload.company_id,
        "active_role": membership["role"],
        "active_modules": membership.get("modules") or [],
        "company": dict(company_row),
        "flags": flags,
        "permissions": permissions,
    }


@router.get("/me")
async def me(user: dict = Depends(get_current_user), conn=Depends(get_db)):
    companies = await _user_companies_payload(conn, user["id"])
    active_company_id = user.get("_jwt_company_id")
    active_modules = await _membership_modules(conn, user["id"], active_company_id) if active_company_id else []
    flags = await get_company_flags(conn, active_company_id) if active_company_id else {}
    permissions = await get_user_permissions(conn, user["id"], active_company_id) if active_company_id else []
    return {
        "user": {k: v for k, v in user.items() if not k.startswith("_jwt")},
        "companies": companies,
        "active_company_id": active_company_id,
        "active_role": user.get("_jwt_role"),
        "active_modules": active_modules,
        "flags": flags,
        "permissions": permissions,
    }


@router.post("/forgot-password", status_code=204)
async def forgot_password(payload: ForgotPasswordInput, conn=Depends(get_db)):
    user_row = await conn.fetchrow(
        "SELECT id FROM users WHERE email = $1", payload.email.lower().strip()
    )
    if user_row:
        token = secrets.token_urlsafe(32)
        expires = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
        await conn.execute(
            "INSERT INTO password_reset_tokens (id, token, user_id, expires_at, used) VALUES ($1, $2, $3, $4, $5)",
            str(uuid.uuid4()), token, user_row["id"], expires, False,
        )
        print(f"[RESET LINK] /reset-password?token={token}")
    return Response(status_code=204)


@router.post("/reset-password", status_code=204)
async def reset_password(payload: ResetPasswordInput, conn=Depends(get_db)):
    record = await conn.fetchrow(
        "SELECT * FROM password_reset_tokens WHERE token = $1 AND used = FALSE", payload.token
    )
    if not record:
        raise HTTPException(status_code=400, detail="Token inválido")
    if datetime.fromisoformat(record["expires_at"]) < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="Token expirado")
    await conn.execute(
        "UPDATE users SET password_hash = $1 WHERE id = $2",
        hash_password(payload.new_password), record["user_id"],
    )
    await conn.execute(
        "UPDATE password_reset_tokens SET used = TRUE WHERE token = $1", payload.token
    )
    return Response(status_code=204)


@router.put("/password", status_code=204)
async def change_password(
    payload: PasswordChangeInput,
    user: dict = Depends(get_current_user), conn=Depends(get_db),
):
    full = await conn.fetchrow("SELECT password_hash FROM users WHERE id = $1", user["id"])
    if not full or not verify_password(payload.current_password, full["password_hash"]):
        raise HTTPException(status_code=400, detail="Senha atual incorreta")
    await conn.execute(
        "UPDATE users SET password_hash = $1 WHERE id = $2",
        hash_password(payload.new_password), user["id"],
    )
    return Response(status_code=204)
