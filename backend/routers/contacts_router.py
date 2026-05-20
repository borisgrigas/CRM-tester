"""Contacts (leads + clients) router."""
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException

from db import get_db
from deps import get_current_company, get_current_user
from models import ActivityCreate, ContactCreate, ContactUpdate, TagsInput

router = APIRouter(prefix="/contacts", tags=["contacts"])

_ALLOWED_SORT = {"created_at", "updated_at", "name", "score", "email"}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@router.get("")
async def list_contacts(
    page: int = 1, limit: int = 20,
    search: Optional[str] = None,
    type: Optional[str] = None,
    assigned_to: Optional[str] = None,
    tag: Optional[str] = None,
    origin: Optional[str] = None,
    score_min: Optional[int] = None,
    score_max: Optional[int] = None,
    sort: str = "-created_at",
    membership: dict = Depends(get_current_company),
    conn=Depends(get_db),
):
    conditions = ["company_id = $1", "deleted_at IS NULL"]
    params: list = [membership["company_id"]]
    n = 2

    if membership["role"] == "COMMERCIAL":
        conditions.append(f"assigned_to = ${n}")
        params.append(membership["user_id"])
        n += 1
    elif assigned_to:
        conditions.append(f"assigned_to = ${n}")
        params.append(assigned_to)
        n += 1

    if type:
        conditions.append(f"type = ${n}")
        params.append(type)
        n += 1

    if tag:
        conditions.append(f"tags ? ${n}")
        params.append(tag)
        n += 1

    if origin:
        conditions.append(f"origin = ${n}")
        params.append(origin)
        n += 1

    if score_min is not None:
        conditions.append(f"score >= ${n}")
        params.append(score_min)
        n += 1

    if score_max is not None:
        conditions.append(f"score <= ${n}")
        params.append(score_max)
        n += 1

    if search:
        conditions.append(f"(name ILIKE ${n} OR email ILIKE ${n} OR company_name ILIKE ${n})")
        params.append(f"%{search}%")
        n += 1

    where = " AND ".join(conditions)
    direction = "DESC" if sort.startswith("-") else "ASC"
    sort_field = sort.lstrip("-")
    if sort_field not in _ALLOWED_SORT:
        sort_field = "created_at"

    total = await conn.fetchval(f"SELECT COUNT(*) FROM contacts WHERE {where}", *params)
    rows = await conn.fetch(
        f"SELECT * FROM contacts WHERE {where} ORDER BY {sort_field} {direction} LIMIT ${n} OFFSET ${n + 1}",
        *params, limit, (page - 1) * limit,
    )
    return {"items": [dict(r) for r in rows], "total": total, "page": page, "limit": limit}


@router.post("", status_code=201)
async def create_contact(
    payload: ContactCreate,
    membership: dict = Depends(get_current_company),
    conn=Depends(get_db),
):
    if membership["role"] == "ANALYST":
        raise HTTPException(status_code=403, detail="ANALYST não pode criar contatos")
    cid = str(uuid.uuid4())
    now = _now_iso()
    data = payload.model_dump()
    await conn.execute(
        """INSERT INTO contacts
           (id, company_id, type, name, email, phone, company_name, position, origin,
            assigned_to, custom_fields, tags, score, created_at, updated_at, deleted_at)
           VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,$16)""",
        cid, membership["company_id"], data.get("type", "lead"), data["name"],
        data.get("email"), data.get("phone"), data.get("company_name"), data.get("position"),
        data.get("origin"), data.get("assigned_to"), data.get("custom_fields") or {},
        data.get("tags") or [], 0, now, now, None,
    )
    row = await conn.fetchrow("SELECT * FROM contacts WHERE id = $1", cid)
    return dict(row)


@router.get("/{contact_id}")
async def get_contact(contact_id: str, membership: dict = Depends(get_current_company), conn=Depends(get_db)):
    row = await conn.fetchrow(
        "SELECT * FROM contacts WHERE id = $1 AND company_id = $2 AND deleted_at IS NULL",
        contact_id, membership["company_id"],
    )
    if not row:
        raise HTTPException(status_code=404, detail="Contato não encontrado")
    activities = await conn.fetch(
        "SELECT * FROM contact_activities WHERE contact_id = $1 AND company_id = $2 ORDER BY occurred_at DESC LIMIT 50",
        contact_id, membership["company_id"],
    )
    deals = await conn.fetch(
        "SELECT * FROM deals WHERE contact_id = $1 AND company_id = $2 AND deleted_at IS NULL",
        contact_id, membership["company_id"],
    )
    return {
        **dict(row),
        "activities": [dict(a) for a in activities],
        "deals": [dict(d) for d in deals],
    }


@router.put("/{contact_id}")
async def update_contact(
    contact_id: str, payload: ContactUpdate,
    membership: dict = Depends(get_current_company), conn=Depends(get_db),
):
    if membership["role"] == "ANALYST":
        raise HTTPException(status_code=403, detail="ANALYST não pode editar")

    update = {k: v for k, v in payload.model_dump().items() if v is not None}
    if not update:
        row = await conn.fetchrow("SELECT * FROM contacts WHERE id = $1", contact_id)
        return dict(row) if row else {}

    update["updated_at"] = _now_iso()
    set_parts = []
    params: list = []
    n = 1
    for k, v in update.items():
        set_parts.append(f"{k} = ${n}")
        params.append(v)
        n += 1
    params.extend([contact_id, membership["company_id"]])
    result = await conn.execute(
        f"UPDATE contacts SET {', '.join(set_parts)} WHERE id = ${n} AND company_id = ${n + 1} AND deleted_at IS NULL",
        *params,
    )
    if result == "UPDATE 0":
        raise HTTPException(status_code=404, detail="Contato não encontrado")
    row = await conn.fetchrow("SELECT * FROM contacts WHERE id = $1", contact_id)
    return dict(row)


@router.delete("/{contact_id}", status_code=204)
async def delete_contact(contact_id: str, membership: dict = Depends(get_current_company), conn=Depends(get_db)):
    if membership["role"] not in ("MASTER", "ADMIN"):
        raise HTTPException(status_code=403, detail="Apenas ADMIN/MASTER")
    await conn.execute(
        "UPDATE contacts SET deleted_at = $1 WHERE id = $2 AND company_id = $3",
        _now_iso(), contact_id, membership["company_id"],
    )
    return None


@router.post("/{contact_id}/convert")
async def convert_to_client(contact_id: str, membership: dict = Depends(get_current_company), conn=Depends(get_db)):
    if membership["role"] == "ANALYST":
        raise HTTPException(status_code=403, detail="ANALYST não pode converter")
    result = await conn.execute(
        "UPDATE contacts SET type = 'client', updated_at = $1 WHERE id = $2 AND company_id = $3 AND deleted_at IS NULL",
        _now_iso(), contact_id, membership["company_id"],
    )
    if result == "UPDATE 0":
        raise HTTPException(status_code=404, detail="Contato não encontrado")
    row = await conn.fetchrow("SELECT * FROM contacts WHERE id = $1", contact_id)
    return dict(row)


@router.post("/{contact_id}/tags")
async def add_tags(contact_id: str, payload: TagsInput, membership: dict = Depends(get_current_company), conn=Depends(get_db)):
    row = await conn.fetchrow(
        "SELECT tags FROM contacts WHERE id = $1 AND company_id = $2 AND deleted_at IS NULL",
        contact_id, membership["company_id"],
    )
    if not row:
        raise HTTPException(status_code=404, detail="Contato não encontrado")
    current = list(row["tags"] or [])
    new_tags = list(set(current + payload.tags))
    await conn.execute(
        "UPDATE contacts SET tags = $1, updated_at = $2 WHERE id = $3",
        new_tags, _now_iso(), contact_id,
    )
    row = await conn.fetchrow("SELECT * FROM contacts WHERE id = $1", contact_id)
    return dict(row)


@router.delete("/{contact_id}/tags")
async def remove_tags(contact_id: str, payload: TagsInput, membership: dict = Depends(get_current_company), conn=Depends(get_db)):
    row = await conn.fetchrow(
        "SELECT tags FROM contacts WHERE id = $1 AND company_id = $2 AND deleted_at IS NULL",
        contact_id, membership["company_id"],
    )
    if not row:
        raise HTTPException(status_code=404, detail="Contato não encontrado")
    current = list(row["tags"] or [])
    new_tags = [t for t in current if t not in payload.tags]
    await conn.execute(
        "UPDATE contacts SET tags = $1, updated_at = $2 WHERE id = $3",
        new_tags, _now_iso(), contact_id,
    )
    row = await conn.fetchrow("SELECT * FROM contacts WHERE id = $1", contact_id)
    return dict(row)


@router.get("/{contact_id}/activities")
async def list_activities(contact_id: str, membership: dict = Depends(get_current_company), conn=Depends(get_db)):
    rows = await conn.fetch(
        "SELECT * FROM contact_activities WHERE contact_id = $1 AND company_id = $2 ORDER BY occurred_at DESC LIMIT 200",
        contact_id, membership["company_id"],
    )
    return {"items": [dict(r) for r in rows]}


@router.post("/{contact_id}/activities", status_code=201)
async def add_activity(
    contact_id: str, payload: ActivityCreate,
    user: dict = Depends(get_current_user),
    membership: dict = Depends(get_current_company),
    conn=Depends(get_db),
):
    contact = await conn.fetchrow(
        "SELECT id FROM contacts WHERE id = $1 AND company_id = $2 AND deleted_at IS NULL",
        contact_id, membership["company_id"],
    )
    if not contact:
        raise HTTPException(status_code=404, detail="Contato não encontrado")

    aid = str(uuid.uuid4())
    now = _now_iso()
    occurred = (payload.occurred_at or datetime.now(timezone.utc)).isoformat()
    await conn.execute(
        """INSERT INTO contact_activities
           (id, company_id, contact_id, user_id, type, description, metadata, occurred_at, created_at)
           VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9)""",
        aid, membership["company_id"], contact_id, user["id"],
        payload.type, payload.description, payload.metadata or {}, occurred, now,
    )

    delta = {"call": 8, "email": 5, "meeting": 6, "note": 1, "whatsapp": 4, "task": 2}.get(payload.type, 0)
    if delta:
        await conn.execute(
            "UPDATE contacts SET score = score + $1, updated_at = $2 WHERE id = $3 AND company_id = $4",
            delta, now, contact_id, membership["company_id"],
        )

    row = await conn.fetchrow("SELECT * FROM contact_activities WHERE id = $1", aid)
    return dict(row)
