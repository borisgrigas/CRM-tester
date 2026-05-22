"""Admin router — feature flags and permissions management."""
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from db import get_db
from deps import get_current_company, require_roles

router = APIRouter(prefix="/admin", tags=["admin"])


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------- Feature flags ----------

class FlagUpsert(BaseModel):
    value: Any = True
    is_active: bool = True


@router.get("/flags")
async def list_flags(
    membership: dict = Depends(require_roles("MASTER", "ADMIN")),
    conn=Depends(get_db),
):
    rows = await conn.fetch(
        "SELECT * FROM feature_flags WHERE company_id = $1 ORDER BY name",
        membership["company_id"],
    )
    return {"items": [dict(r) for r in rows]}


@router.put("/flags/{name}")
async def upsert_flag(
    name: str,
    payload: FlagUpsert,
    membership: dict = Depends(require_roles("MASTER", "ADMIN")),
    conn=Depends(get_db),
):
    existing = await conn.fetchrow(
        "SELECT id FROM feature_flags WHERE company_id = $1 AND name = $2",
        membership["company_id"], name,
    )
    if existing:
        await conn.execute(
            "UPDATE feature_flags SET value = $1, is_active = $2 WHERE company_id = $3 AND name = $4",
            payload.value, payload.is_active, membership["company_id"], name,
        )
    else:
        await conn.execute(
            "INSERT INTO feature_flags (id, company_id, name, value, is_active, created_at) VALUES ($1,$2,$3,$4,$5,$6)",
            str(uuid.uuid4()), membership["company_id"], name, payload.value, payload.is_active, _now_iso(),
        )
    row = await conn.fetchrow(
        "SELECT * FROM feature_flags WHERE company_id = $1 AND name = $2",
        membership["company_id"], name,
    )
    return dict(row)


# ---------- Permissions ----------

class PermissionUpsert(BaseModel):
    permission: str  # e.g. "contacts:manage"


@router.get("/permissions")
async def list_permissions(
    membership: dict = Depends(require_roles("MASTER", "ADMIN")),
    conn=Depends(get_db),
):
    rows = await conn.fetch(
        "SELECT * FROM permissions WHERE company_id = $1 ORDER BY user_id, permission",
        membership["company_id"],
    )
    return {"items": [dict(r) for r in rows]}


@router.put("/permissions/{user_id}")
async def grant_permission(
    user_id: str,
    payload: PermissionUpsert,
    membership: dict = Depends(require_roles("MASTER", "ADMIN")),
    conn=Depends(get_db),
):
    existing = await conn.fetchrow(
        "SELECT id FROM permissions WHERE company_id = $1 AND user_id = $2 AND permission = $3",
        membership["company_id"], user_id, payload.permission,
    )
    if not existing:
        await conn.execute(
            "INSERT INTO permissions (id, company_id, user_id, permission, granted_by, created_at) VALUES ($1,$2,$3,$4,$5,$6)",
            str(uuid.uuid4()), membership["company_id"], user_id, payload.permission,
            membership["user_id"], _now_iso(),
        )
    return {"ok": True, "permission": payload.permission}


@router.delete("/permissions/{user_id}/{permission}", status_code=204)
async def revoke_permission(
    user_id: str,
    permission: str,
    membership: dict = Depends(require_roles("MASTER", "ADMIN")),
    conn=Depends(get_db),
):
    await conn.execute(
        "DELETE FROM permissions WHERE company_id = $1 AND user_id = $2 AND permission = $3",
        membership["company_id"], user_id, permission,
    )
    return None
