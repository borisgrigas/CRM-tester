"""Users + profile router."""
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException

from auth_utils import hash_password
from db import get_db
from deps import get_current_company, get_current_user, require_roles
from models import ProfileUpdate, UserInvite, UserRoleUpdate

router = APIRouter(tags=["users"])


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@router.get("/users")
async def list_users(membership: dict = Depends(get_current_company), db=Depends(get_db)):
    memberships = await db.user_companies.find(
        {"company_id": membership["company_id"], "is_active": True}, {"_id": 0}
    ).to_list(500)
    user_ids = [m["user_id"] for m in memberships]
    users = await db.users.find(
        {"id": {"$in": user_ids}}, {"_id": 0, "password_hash": 0}
    ).to_list(500)
    by_id = {u["id"]: u for u in users}
    return {
        "items": [
            {**by_id.get(m["user_id"], {"id": m["user_id"], "name": "—"}), "role": m["role"]}
            for m in memberships
        ]
    }


@router.post("/users/invite", status_code=201, dependencies=[Depends(require_roles("MASTER", "ADMIN"))])
async def invite_user(payload: UserInvite, membership: dict = Depends(get_current_company), db=Depends(get_db)):
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
        "role": payload.role, "is_active": True,
        "invited_at": _now_iso(), "accepted_at": _now_iso(),
    })
    return {"id": user_id, "email": email, "name": payload.name, "role": payload.role}


@router.put("/users/{user_id}/role", dependencies=[Depends(require_roles("MASTER", "ADMIN"))])
async def update_role(user_id: str, payload: UserRoleUpdate, membership: dict = Depends(get_current_company), db=Depends(get_db)):
    res = await db.user_companies.update_one(
        {"user_id": user_id, "company_id": membership["company_id"]},
        {"$set": {"role": payload.role}},
    )
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Membro não encontrado")
    return {"ok": True}


@router.delete("/users/{user_id}", status_code=204, dependencies=[Depends(require_roles("MASTER", "ADMIN"))])
async def remove_user(user_id: str, membership: dict = Depends(get_current_company), db=Depends(get_db)):
    await db.user_companies.update_one(
        {"user_id": user_id, "company_id": membership["company_id"]},
        {"$set": {"is_active": False}},
    )
    return None


@router.get("/profile")
async def get_profile(user: dict = Depends(get_current_user)):
    return {k: v for k, v in user.items() if not k.startswith("_jwt")}


@router.put("/profile")
async def update_profile(payload: ProfileUpdate, user: dict = Depends(get_current_user), db=Depends(get_db)):
    update = {k: v for k, v in payload.model_dump().items() if v is not None}
    await db.users.update_one({"id": user["id"]}, {"$set": update})
    return await db.users.find_one({"id": user["id"]}, {"_id": 0, "password_hash": 0})
