"""Users + profile router (member management, modules, multi-company)."""
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException

from auth_utils import hash_password
from db import get_db
from deps import get_current_company, get_current_user, require_roles
from models import (
    ALL_MODULES,
    GrantCompanyAccess,
    ProfileUpdate,
    UserInvite,
    UserModulesUpdate,
    UserRoleUpdate,
)

router = APIRouter(tags=["users"])


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _validate_modules(modules: list[str]) -> list[str]:
    invalid = [m for m in modules if m not in ALL_MODULES]
    if invalid:
        raise HTTPException(status_code=400, detail=f"Módulos inválidos: {invalid}")
    return modules


async def _enforce_admin_protection(conn, target_user_id: str, company_id: str, actor_role: str):
    target = await conn.fetchrow(
        "SELECT role FROM user_companies WHERE user_id = $1 AND company_id = $2",
        target_user_id, company_id,
    )
    if not target:
        raise HTTPException(status_code=404, detail="Membro não encontrado")
    if actor_role == "ADMIN" and target["role"] in ("ADMIN", "MASTER"):
        raise HTTPException(status_code=403, detail="ADMIN não pode alterar outro ADMIN/MASTER")
    return target


async def _ensure_not_last_active_admin(conn, target_user_id: str, company_id: str):
    target = await conn.fetchrow(
        "SELECT role, is_active FROM user_companies WHERE user_id = $1 AND company_id = $2",
        target_user_id, company_id,
    )
    if not target or target["role"] != "ADMIN" or not target["is_active"]:
        return
    active_admins = await conn.fetchval(
        "SELECT COUNT(*) FROM user_companies WHERE company_id = $1 AND role = 'ADMIN' AND is_active = TRUE",
        company_id,
    )
    if active_admins <= 1:
        raise HTTPException(status_code=400, detail="Não é possível inativar o último ADMIN ativo")


async def _is_franchisor_context(conn, company_id: str) -> bool:
    row = await conn.fetchrow(
        "SELECT is_franchisor FROM companies WHERE id = $1 AND deleted_at IS NULL", company_id
    )
    return bool(row and row["is_franchisor"])


@router.get("/users")
async def list_users(membership: dict = Depends(get_current_company), conn=Depends(get_db)):
    m_rows = await conn.fetch(
        "SELECT * FROM user_companies WHERE company_id = $1", membership["company_id"]
    )
    user_ids = [m["user_id"] for m in m_rows]
    u_rows = await conn.fetch(
        "SELECT id, name, email, avatar_url, created_at FROM users WHERE id = ANY($1)", user_ids
    ) if user_ids else []
    by_id = {u["id"]: dict(u) for u in u_rows}

    items = []
    for m in m_rows:
        other = await conn.fetch(
            "SELECT company_id FROM user_companies WHERE user_id = $1 AND is_active = TRUE AND company_id != $2",
            m["user_id"], membership["company_id"],
        )
        items.append({
            **by_id.get(m["user_id"], {"id": m["user_id"], "name": "—", "email": "", "avatar_url": None}),
            "role": m["role"],
            "is_active": m["is_active"],
            "modules": m["modules"] or [],
            "invited_at": m["invited_at"],
            "accepted_at": m["accepted_at"],
            "other_company_ids": [o["company_id"] for o in other],
        })
    return {"items": items}


@router.post("/users/invite", status_code=201, dependencies=[Depends(require_roles("MASTER", "ADMIN"))])
async def invite_user(payload: UserInvite, membership: dict = Depends(get_current_company), conn=Depends(get_db)):
    if membership["role"] == "ADMIN" and payload.role in ("ADMIN", "MASTER"):
        raise HTTPException(status_code=403, detail="ADMIN não pode convidar ADMIN/MASTER")
    _validate_modules(payload.modules)

    email = payload.email.lower().strip()
    existing = await conn.fetchrow("SELECT id FROM users WHERE email = $1", email)
    if existing:
        user_id = existing["id"]
    else:
        user_id = str(uuid.uuid4())
        await conn.execute(
            "INSERT INTO users (id, name, email, password_hash, avatar_url, created_at, deleted_at) VALUES ($1,$2,$3,$4,$5,$6,$7)",
            user_id, payload.name, email, hash_password(payload.password), None, _now_iso(), None,
        )

    already = await conn.fetchrow(
        "SELECT 1 FROM user_companies WHERE user_id = $1 AND company_id = $2",
        user_id, membership["company_id"],
    )
    if already:
        raise HTTPException(status_code=400, detail="Usuário já é membro desta empresa")

    now = _now_iso()
    await conn.execute(
        "INSERT INTO user_companies (user_id, company_id, role, modules, is_active, invited_at, accepted_at) VALUES ($1,$2,$3,$4,$5,$6,$7)",
        user_id, membership["company_id"], payload.role, payload.modules, True, now, now,
    )

    granted_extras: list[str] = []
    if payload.additional_company_ids:
        is_franchisor = await _is_franchisor_context(conn, membership["company_id"])
        if not is_franchisor:
            raise HTTPException(
                status_code=403,
                detail="Apenas a franqueadora pode conceder acesso a múltiplas empresas",
            )
        for cid in payload.additional_company_ids:
            if cid == membership["company_id"]:
                continue
            target_co = await conn.fetchrow("SELECT id FROM companies WHERE id = $1 AND deleted_at IS NULL", cid)
            if not target_co:
                continue
            exists = await conn.fetchrow("SELECT 1 FROM user_companies WHERE user_id = $1 AND company_id = $2", user_id, cid)
            if exists:
                continue
            await conn.execute(
                "INSERT INTO user_companies (user_id, company_id, role, modules, is_active, invited_at, accepted_at) VALUES ($1,$2,$3,$4,$5,$6,$7)",
                user_id, cid, payload.role, payload.modules, True, now, now,
            )
            granted_extras.append(cid)

    print(f"[INVITE] activation link for {email}: /accept-invite?token={uuid.uuid4()}")
    return {
        "id": user_id, "email": email, "name": payload.name, "role": payload.role,
        "is_active": True, "modules": payload.modules,
        "additional_company_ids": granted_extras,
    }


@router.put("/users/{user_id}/role", dependencies=[Depends(require_roles("MASTER", "ADMIN"))])
async def update_role(user_id: str, payload: UserRoleUpdate, membership: dict = Depends(get_current_company), conn=Depends(get_db)):
    await _enforce_admin_protection(conn, user_id, membership["company_id"], membership["role"])
    if membership["role"] == "ADMIN" and payload.role in ("ADMIN", "MASTER"):
        raise HTTPException(status_code=403, detail="ADMIN não pode promover para ADMIN/MASTER")
    if payload.role != "ADMIN":
        await _ensure_not_last_active_admin(conn, user_id, membership["company_id"])
    result = await conn.execute(
        "UPDATE user_companies SET role = $1 WHERE user_id = $2 AND company_id = $3",
        payload.role, user_id, membership["company_id"],
    )
    if result == "UPDATE 0":
        raise HTTPException(status_code=404, detail="Membro não encontrado")
    return {"ok": True, "role": payload.role}


@router.put("/users/{user_id}/modules", dependencies=[Depends(require_roles("MASTER", "ADMIN"))])
async def update_modules(user_id: str, payload: UserModulesUpdate, membership: dict = Depends(get_current_company), conn=Depends(get_db)):
    await _enforce_admin_protection(conn, user_id, membership["company_id"], membership["role"])
    _validate_modules(payload.modules)
    result = await conn.execute(
        "UPDATE user_companies SET modules = $1 WHERE user_id = $2 AND company_id = $3",
        payload.modules, user_id, membership["company_id"],
    )
    if result == "UPDATE 0":
        raise HTTPException(status_code=404, detail="Membro não encontrado")
    return {"ok": True, "modules": payload.modules}


@router.patch("/users/{user_id}/activate", dependencies=[Depends(require_roles("MASTER", "ADMIN"))])
async def activate_user(user_id: str, membership: dict = Depends(get_current_company), conn=Depends(get_db)):
    await _enforce_admin_protection(conn, user_id, membership["company_id"], membership["role"])
    result = await conn.execute(
        "UPDATE user_companies SET is_active = TRUE WHERE user_id = $1 AND company_id = $2",
        user_id, membership["company_id"],
    )
    if result == "UPDATE 0":
        raise HTTPException(status_code=404, detail="Membro não encontrado")
    return {"ok": True, "is_active": True}


@router.patch("/users/{user_id}/deactivate", dependencies=[Depends(require_roles("MASTER", "ADMIN"))])
async def deactivate_user(user_id: str, membership: dict = Depends(get_current_company), conn=Depends(get_db)):
    if user_id == membership["user_id"]:
        raise HTTPException(status_code=400, detail="Você não pode inativar a si mesmo")
    await _enforce_admin_protection(conn, user_id, membership["company_id"], membership["role"])
    await _ensure_not_last_active_admin(conn, user_id, membership["company_id"])
    result = await conn.execute(
        "UPDATE user_companies SET is_active = FALSE WHERE user_id = $1 AND company_id = $2",
        user_id, membership["company_id"],
    )
    if result == "UPDATE 0":
        raise HTTPException(status_code=404, detail="Membro não encontrado")
    return {"ok": True, "is_active": False}


@router.delete("/users/{user_id}", status_code=204, dependencies=[Depends(require_roles("MASTER", "ADMIN"))])
async def remove_user(user_id: str, membership: dict = Depends(get_current_company), conn=Depends(get_db)):
    if user_id == membership["user_id"]:
        raise HTTPException(status_code=400, detail="Você não pode remover a si mesmo")
    await _enforce_admin_protection(conn, user_id, membership["company_id"], membership["role"])
    await _ensure_not_last_active_admin(conn, user_id, membership["company_id"])
    await conn.execute(
        "DELETE FROM user_companies WHERE user_id = $1 AND company_id = $2",
        user_id, membership["company_id"],
    )
    return None


@router.post("/users/{user_id}/grant-company", dependencies=[Depends(require_roles("MASTER"))])
async def grant_company_access(
    user_id: str, payload: GrantCompanyAccess,
    membership: dict = Depends(get_current_company), conn=Depends(get_db),
):
    is_franchisor = await _is_franchisor_context(conn, membership["company_id"])
    if not is_franchisor:
        raise HTTPException(status_code=403, detail="Apenas a franqueadora pode estender acesso a múltiplas empresas")
    if payload.company_id == membership["company_id"]:
        raise HTTPException(status_code=400, detail="Use as ações de papel/módulos para a empresa atual")
    target_co = await conn.fetchrow("SELECT id FROM companies WHERE id = $1 AND deleted_at IS NULL", payload.company_id)
    if not target_co:
        raise HTTPException(status_code=404, detail="Empresa destino não encontrada")
    user_doc = await conn.fetchrow("SELECT id FROM users WHERE id = $1", user_id)
    if not user_doc:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    _validate_modules(payload.modules)

    existing = await conn.fetchrow(
        "SELECT 1 FROM user_companies WHERE user_id = $1 AND company_id = $2", user_id, payload.company_id
    )
    now = _now_iso()
    if existing:
        await conn.execute(
            "UPDATE user_companies SET role = $1, modules = $2, is_active = TRUE WHERE user_id = $3 AND company_id = $4",
            payload.role, payload.modules, user_id, payload.company_id,
        )
        return {"ok": True, "updated": True}
    await conn.execute(
        "INSERT INTO user_companies (user_id, company_id, role, modules, is_active, invited_at, accepted_at) VALUES ($1,$2,$3,$4,$5,$6,$7)",
        user_id, payload.company_id, payload.role, payload.modules, True, now, now,
    )
    return {"ok": True, "created": True}


@router.delete("/users/{user_id}/revoke-company/{company_id}", status_code=204, dependencies=[Depends(require_roles("MASTER"))])
async def revoke_company_access(
    user_id: str, company_id: str,
    membership: dict = Depends(get_current_company), conn=Depends(get_db),
):
    is_franchisor = await _is_franchisor_context(conn, membership["company_id"])
    if not is_franchisor:
        raise HTTPException(status_code=403, detail="Apenas a franqueadora pode revogar acesso a outras empresas")
    if company_id == membership["company_id"]:
        raise HTTPException(status_code=400, detail="Use DELETE /users/:id para a empresa atual")
    await _ensure_not_last_active_admin(conn, user_id, company_id)
    await conn.execute(
        "DELETE FROM user_companies WHERE user_id = $1 AND company_id = $2", user_id, company_id
    )
    return None


@router.get("/profile")
async def get_profile(user: dict = Depends(get_current_user)):
    return {k: v for k, v in user.items() if not k.startswith("_jwt")}


@router.put("/profile")
async def update_profile(payload: ProfileUpdate, user: dict = Depends(get_current_user), conn=Depends(get_db)):
    update = {k: v for k, v in payload.model_dump().items() if v is not None}
    if update:
        set_parts = [f"{k} = ${i + 1}" for i, k in enumerate(update)]
        params = list(update.values()) + [user["id"]]
        await conn.execute(
            f"UPDATE users SET {', '.join(set_parts)} WHERE id = ${len(params)}",
            *params,
        )
    row = await conn.fetchrow(
        "SELECT id, name, email, avatar_url, created_at, deleted_at FROM users WHERE id = $1", user["id"]
    )
    return dict(row)


@router.get("/users/modules-catalog")
async def modules_catalog():
    return {"modules": ALL_MODULES}
