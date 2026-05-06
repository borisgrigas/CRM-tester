"""Users + profile router (com gestão de membros, módulos e multi-empresa)."""
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


async def _enforce_admin_protection(db, target_user_id: str, company_id: str, actor_role: str):
    target = await db.user_companies.find_one(
        {"user_id": target_user_id, "company_id": company_id}, {"_id": 0, "role": 1}
    )
    if not target:
        raise HTTPException(status_code=404, detail="Membro não encontrado")
    if actor_role == "ADMIN" and target["role"] in ("ADMIN", "MASTER"):
        raise HTTPException(status_code=403, detail="ADMIN não pode alterar outro ADMIN/MASTER")
    return target


async def _ensure_not_last_active_admin(db, target_user_id: str, company_id: str):
    target = await db.user_companies.find_one(
        {"user_id": target_user_id, "company_id": company_id}, {"_id": 0, "role": 1, "is_active": 1}
    )
    if not target or target["role"] != "ADMIN" or not target.get("is_active"):
        return
    active_admins = await db.user_companies.count_documents(
        {"company_id": company_id, "role": "ADMIN", "is_active": True}
    )
    if active_admins <= 1:
        raise HTTPException(status_code=400, detail="Não é possível inativar o último ADMIN ativo")


async def _is_franchisor_context(db, company_id: str) -> bool:
    company = await db.companies.find_one({"id": company_id, "deleted_at": None}, {"_id": 0, "is_franchisor": 1})
    return bool(company and company.get("is_franchisor"))


@router.get("/users")
async def list_users(membership: dict = Depends(get_current_company), db=Depends(get_db)):
    memberships = await db.user_companies.find(
        {"company_id": membership["company_id"]}, {"_id": 0}
    ).to_list(500)
    user_ids = [m["user_id"] for m in memberships]
    users = await db.users.find(
        {"id": {"$in": user_ids}}, {"_id": 0, "password_hash": 0}
    ).to_list(500)
    by_id = {u["id"]: u for u in users}
    items = []
    for m in memberships:
        # Empresas adicionais a que o usuário tem acesso (apenas para visão da franqueadora)
        other = await db.user_companies.find(
            {"user_id": m["user_id"], "is_active": True, "company_id": {"$ne": membership["company_id"]}},
            {"_id": 0, "company_id": 1, "role": 1},
        ).to_list(50)
        items.append({
            **by_id.get(m["user_id"], {"id": m["user_id"], "name": "—", "email": "", "avatar_url": None}),
            "role": m["role"],
            "is_active": m.get("is_active", True),
            "modules": m.get("modules", []),
            "invited_at": m.get("invited_at"),
            "accepted_at": m.get("accepted_at"),
            "other_company_ids": [o["company_id"] for o in other],
        })
    return {"items": items}


@router.post("/users/invite", status_code=201, dependencies=[Depends(require_roles("MASTER", "ADMIN"))])
async def invite_user(payload: UserInvite, membership: dict = Depends(get_current_company), db=Depends(get_db)):
    if membership["role"] == "ADMIN" and payload.role in ("ADMIN", "MASTER"):
        raise HTTPException(status_code=403, detail="ADMIN não pode convidar ADMIN/MASTER")
    _validate_modules(payload.modules)

    email = payload.email.lower().strip()
    existing = await db.users.find_one({"email": email})
    if existing:
        user_id = existing["id"]
    else:
        user_id = str(uuid.uuid4())
        await db.users.insert_one({
            "id": user_id, "name": payload.name, "email": email,
            "password_hash": hash_password(payload.password),
            "avatar_url": None, "created_at": _now_iso(), "deleted_at": None,
        })
    already = await db.user_companies.find_one(
        {"user_id": user_id, "company_id": membership["company_id"]}
    )
    if already:
        raise HTTPException(status_code=400, detail="Usuário já é membro desta empresa")
    await db.user_companies.insert_one({
        "user_id": user_id, "company_id": membership["company_id"],
        "role": payload.role, "modules": payload.modules, "is_active": True,
        "invited_at": _now_iso(), "accepted_at": _now_iso(),
    })

    # Multi-empresa: SOMENTE quando o convite parte da franqueadora
    granted_extras: list[str] = []
    if payload.additional_company_ids:
        is_franchisor = await _is_franchisor_context(db, membership["company_id"])
        if not is_franchisor:
            raise HTTPException(
                status_code=403,
                detail="Apenas a franqueadora pode conceder acesso a múltiplas empresas",
            )
        for cid in payload.additional_company_ids:
            if cid == membership["company_id"]:
                continue
            target = await db.companies.find_one({"id": cid, "deleted_at": None}, {"_id": 0, "id": 1})
            if not target:
                continue
            exists = await db.user_companies.find_one({"user_id": user_id, "company_id": cid})
            if exists:
                continue
            await db.user_companies.insert_one({
                "user_id": user_id, "company_id": cid,
                "role": payload.role, "modules": payload.modules, "is_active": True,
                "invited_at": _now_iso(), "accepted_at": _now_iso(),
            })
            granted_extras.append(cid)

    print(f"[INVITE] activation link for {email}: /accept-invite?token={uuid.uuid4()}")
    return {
        "id": user_id, "email": email, "name": payload.name, "role": payload.role,
        "is_active": True, "modules": payload.modules,
        "additional_company_ids": granted_extras,
    }


@router.put("/users/{user_id}/role", dependencies=[Depends(require_roles("MASTER", "ADMIN"))])
async def update_role(user_id: str, payload: UserRoleUpdate, membership: dict = Depends(get_current_company), db=Depends(get_db)):
    await _enforce_admin_protection(db, user_id, membership["company_id"], membership["role"])
    if membership["role"] == "ADMIN" and payload.role in ("ADMIN", "MASTER"):
        raise HTTPException(status_code=403, detail="ADMIN não pode promover para ADMIN/MASTER")
    if payload.role != "ADMIN":
        await _ensure_not_last_active_admin(db, user_id, membership["company_id"])
    res = await db.user_companies.update_one(
        {"user_id": user_id, "company_id": membership["company_id"]},
        {"$set": {"role": payload.role}},
    )
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Membro não encontrado")
    return {"ok": True, "role": payload.role}


@router.put("/users/{user_id}/modules", dependencies=[Depends(require_roles("MASTER", "ADMIN"))])
async def update_modules(user_id: str, payload: UserModulesUpdate, membership: dict = Depends(get_current_company), db=Depends(get_db)):
    await _enforce_admin_protection(db, user_id, membership["company_id"], membership["role"])
    _validate_modules(payload.modules)
    res = await db.user_companies.update_one(
        {"user_id": user_id, "company_id": membership["company_id"]},
        {"$set": {"modules": payload.modules}},
    )
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Membro não encontrado")
    return {"ok": True, "modules": payload.modules}


@router.patch("/users/{user_id}/activate", dependencies=[Depends(require_roles("MASTER", "ADMIN"))])
async def activate_user(user_id: str, membership: dict = Depends(get_current_company), db=Depends(get_db)):
    await _enforce_admin_protection(db, user_id, membership["company_id"], membership["role"])
    res = await db.user_companies.update_one(
        {"user_id": user_id, "company_id": membership["company_id"]},
        {"$set": {"is_active": True}},
    )
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Membro não encontrado")
    return {"ok": True, "is_active": True}


@router.patch("/users/{user_id}/deactivate", dependencies=[Depends(require_roles("MASTER", "ADMIN"))])
async def deactivate_user(user_id: str, membership: dict = Depends(get_current_company), db=Depends(get_db)):
    if user_id == membership["user_id"]:
        raise HTTPException(status_code=400, detail="Você não pode inativar a si mesmo")
    await _enforce_admin_protection(db, user_id, membership["company_id"], membership["role"])
    await _ensure_not_last_active_admin(db, user_id, membership["company_id"])
    res = await db.user_companies.update_one(
        {"user_id": user_id, "company_id": membership["company_id"]},
        {"$set": {"is_active": False}},
    )
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Membro não encontrado")
    return {"ok": True, "is_active": False}


@router.delete("/users/{user_id}", status_code=204, dependencies=[Depends(require_roles("MASTER", "ADMIN"))])
async def remove_user(user_id: str, membership: dict = Depends(get_current_company), db=Depends(get_db)):
    if user_id == membership["user_id"]:
        raise HTTPException(status_code=400, detail="Você não pode remover a si mesmo")
    await _enforce_admin_protection(db, user_id, membership["company_id"], membership["role"])
    await _ensure_not_last_active_admin(db, user_id, membership["company_id"])
    await db.user_companies.delete_one(
        {"user_id": user_id, "company_id": membership["company_id"]}
    )
    return None


# --------- Multi-empresa: apenas via franqueadora ---------

@router.post("/users/{user_id}/grant-company", dependencies=[Depends(require_roles("MASTER"))])
async def grant_company_access(
    user_id: str, payload: GrantCompanyAccess,
    membership: dict = Depends(get_current_company), db=Depends(get_db),
):
    """Apenas no contexto da franqueadora um MASTER pode dar acesso a outra empresa."""
    is_franchisor = await _is_franchisor_context(db, membership["company_id"])
    if not is_franchisor:
        raise HTTPException(status_code=403, detail="Apenas a franqueadora pode estender acesso a múltiplas empresas")
    if payload.company_id == membership["company_id"]:
        raise HTTPException(status_code=400, detail="Use as ações de papel/módulos para a empresa atual")
    target = await db.companies.find_one({"id": payload.company_id, "deleted_at": None}, {"_id": 0, "id": 1})
    if not target:
        raise HTTPException(status_code=404, detail="Empresa destino não encontrada")
    user_doc = await db.users.find_one({"id": user_id})
    if not user_doc:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    _validate_modules(payload.modules)

    existing = await db.user_companies.find_one({"user_id": user_id, "company_id": payload.company_id})
    if existing:
        await db.user_companies.update_one(
            {"user_id": user_id, "company_id": payload.company_id},
            {"$set": {"role": payload.role, "modules": payload.modules, "is_active": True}},
        )
        return {"ok": True, "updated": True}
    await db.user_companies.insert_one({
        "user_id": user_id, "company_id": payload.company_id,
        "role": payload.role, "modules": payload.modules, "is_active": True,
        "invited_at": _now_iso(), "accepted_at": _now_iso(),
    })
    return {"ok": True, "created": True}


@router.delete("/users/{user_id}/revoke-company/{company_id}", status_code=204, dependencies=[Depends(require_roles("MASTER"))])
async def revoke_company_access(
    user_id: str, company_id: str,
    membership: dict = Depends(get_current_company), db=Depends(get_db),
):
    is_franchisor = await _is_franchisor_context(db, membership["company_id"])
    if not is_franchisor:
        raise HTTPException(status_code=403, detail="Apenas a franqueadora pode revogar acesso a outras empresas")
    if company_id == membership["company_id"]:
        raise HTTPException(status_code=400, detail="Use DELETE /users/:id para a empresa atual")
    # Não permitir remover o último ADMIN ativo da empresa destino
    await _ensure_not_last_active_admin(db, user_id, company_id)
    await db.user_companies.delete_one({"user_id": user_id, "company_id": company_id})
    return None


# --------- Profile ---------

@router.get("/profile")
async def get_profile(user: dict = Depends(get_current_user)):
    return {k: v for k, v in user.items() if not k.startswith("_jwt")}


@router.put("/profile")
async def update_profile(payload: ProfileUpdate, user: dict = Depends(get_current_user), db=Depends(get_db)):
    update = {k: v for k, v in payload.model_dump().items() if v is not None}
    await db.users.update_one({"id": user["id"]}, {"$set": update})
    return await db.users.find_one({"id": user["id"]}, {"_id": 0, "password_hash": 0})


# --------- Metadados ---------

@router.get("/users/modules-catalog")
async def modules_catalog():
    return {"modules": ALL_MODULES}
