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


def _set_cookies(response: Response, access: str, refresh: str | None = None) -> None:
    response.set_cookie(
        key="access_token", value=access, httponly=True, secure=False,
        samesite="lax", max_age=60 * 15, path="/",
    )
    if refresh:
        response.set_cookie(
            key="refresh_token", value=refresh, httponly=True, secure=False,
            samesite="lax", max_age=60 * 60 * 24 * 7, path="/",
        )


async def _user_companies_payload(db, user_id: str) -> list[dict]:
    memberships = await db.user_companies.find(
        {"user_id": user_id, "is_active": True}, {"_id": 0}
    ).to_list(100)
    company_ids = [m["company_id"] for m in memberships]
    companies = await db.companies.find({"id": {"$in": company_ids}}, {"_id": 0}).to_list(100)
    by_id = {c["id"]: c for c in companies}
    out = []
    for m in memberships:
        c = by_id.get(m["company_id"])
        if c:
            out.append({**c, "role": m["role"]})
    return out


@router.post("/login")
async def login(payload: LoginInput, response: Response, db=Depends(get_db)):
    email = payload.email.lower().strip()
    user = await db.users.find_one({"email": email})
    if not user or not verify_password(payload.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Email ou senha incorretos")

    companies = await _user_companies_payload(db, user["id"])
    if not companies:
        raise HTTPException(status_code=403, detail="Usuário sem empresa ativa")

    # default to first (or first MASTER if any)
    default_company = next((c for c in companies if c["role"] == "MASTER"), companies[0])
    access = create_access_token(user["id"], user["email"], default_company["id"], default_company["role"])
    refresh = create_refresh_token(user["id"])
    _set_cookies(response, access, refresh)

    user.pop("password_hash", None)
    user.pop("_id", None)
    return {
        "access_token": access,
        "refresh_token": refresh,
        "user": user,
        "companies": companies,
        "active_company_id": default_company["id"],
        "active_role": default_company["role"],
    }


@router.post("/refresh")
async def refresh(request: Request, response: Response, db=Depends(get_db)):
    token = request.cookies.get("refresh_token")
    if not token:
        raise HTTPException(status_code=401, detail="Refresh token ausente")
    try:
        payload = decode_token(token)
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=401, detail="Token inválido")
    except Exception:
        raise HTTPException(status_code=401, detail="Token inválido")

    user = await db.users.find_one({"id": payload["sub"]}, {"_id": 0, "password_hash": 0})
    if not user:
        raise HTTPException(status_code=401, detail="Usuário não encontrado")

    companies = await _user_companies_payload(db, user["id"])
    default_company = next((c for c in companies if c["role"] == "MASTER"), companies[0]) if companies else None
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
    user: dict = Depends(get_current_user), db=Depends(get_db),
):
    membership = await db.user_companies.find_one(
        {"user_id": user["id"], "company_id": payload.company_id, "is_active": True},
        {"_id": 0},
    )
    if not membership:
        raise HTTPException(status_code=403, detail="Empresa não autorizada")
    access = create_access_token(user["id"], user["email"], payload.company_id, membership["role"])
    _set_cookies(response, access)
    company = await db.companies.find_one({"id": payload.company_id}, {"_id": 0})
    return {
        "access_token": access,
        "active_company_id": payload.company_id,
        "active_role": membership["role"],
        "company": company,
    }


@router.get("/me")
async def me(user: dict = Depends(get_current_user), db=Depends(get_db)):
    companies = await _user_companies_payload(db, user["id"])
    return {
        "user": {k: v for k, v in user.items() if not k.startswith("_jwt")},
        "companies": companies,
        "active_company_id": user.get("_jwt_company_id"),
        "active_role": user.get("_jwt_role"),
    }


@router.post("/forgot-password", status_code=204)
async def forgot_password(payload: ForgotPasswordInput, db=Depends(get_db)):
    user = await db.users.find_one({"email": payload.email.lower().strip()})
    if user:
        token = secrets.token_urlsafe(32)
        await db.password_reset_tokens.insert_one({
            "id": str(uuid.uuid4()),
            "token": token,
            "user_id": user["id"],
            "expires_at": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
            "used": False,
        })
        print(f"[RESET LINK] /reset-password?token={token}")
    return Response(status_code=204)


@router.post("/reset-password", status_code=204)
async def reset_password(payload: ResetPasswordInput, db=Depends(get_db)):
    record = await db.password_reset_tokens.find_one({"token": payload.token, "used": False})
    if not record:
        raise HTTPException(status_code=400, detail="Token inválido")
    if datetime.fromisoformat(record["expires_at"]) < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="Token expirado")
    await db.users.update_one(
        {"id": record["user_id"]},
        {"$set": {"password_hash": hash_password(payload.new_password)}},
    )
    await db.password_reset_tokens.update_one({"token": payload.token}, {"$set": {"used": True}})
    return Response(status_code=204)


@router.put("/password", status_code=204)
async def change_password(
    payload: PasswordChangeInput,
    user: dict = Depends(get_current_user), db=Depends(get_db),
):
    full = await db.users.find_one({"id": user["id"]})
    if not full or not verify_password(payload.current_password, full["password_hash"]):
        raise HTTPException(status_code=400, detail="Senha atual incorreta")
    await db.users.update_one(
        {"id": user["id"]},
        {"$set": {"password_hash": hash_password(payload.new_password)}},
    )
    return Response(status_code=204)
