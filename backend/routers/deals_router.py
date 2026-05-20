"""Deals router."""
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException

from db import get_db
from deps import get_current_company
from models import DealCreate, DealUpdate, LostInput, StageMoveInput

router = APIRouter(prefix="/deals", tags=["deals"])


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@router.get("")
async def list_deals(
    pipeline_id: Optional[str] = None,
    stage_id: Optional[str] = None,
    assigned_to: Optional[str] = None,
    value_min: Optional[float] = None,
    value_max: Optional[float] = None,
    search: Optional[str] = None,
    page: int = 1,
    limit: int = 200,
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

    if pipeline_id:
        conditions.append(f"pipeline_id = ${n}")
        params.append(pipeline_id)
        n += 1

    if stage_id:
        conditions.append(f"stage_id = ${n}")
        params.append(stage_id)
        n += 1

    if value_min is not None:
        conditions.append(f"value >= ${n}")
        params.append(value_min)
        n += 1

    if value_max is not None:
        conditions.append(f"value <= ${n}")
        params.append(value_max)
        n += 1

    if search:
        conditions.append(f"title ILIKE ${n}")
        params.append(f"%{search}%")
        n += 1

    where = " AND ".join(conditions)
    total = await conn.fetchval(f"SELECT COUNT(*) FROM deals WHERE {where}", *params)
    rows = await conn.fetch(
        f"SELECT * FROM deals WHERE {where} ORDER BY created_at DESC LIMIT ${n} OFFSET ${n + 1}",
        *params, limit, (page - 1) * limit,
    )
    items = [dict(r) for r in rows]

    contact_ids = list({d["contact_id"] for d in items if d.get("contact_id")})
    if contact_ids:
        c_rows = await conn.fetch(
            "SELECT id, name, email FROM contacts WHERE id = ANY($1)", contact_ids
        )
        by_id = {c["id"]: dict(c) for c in c_rows}
        for d in items:
            c = by_id.get(d.get("contact_id"))
            if c:
                d["contact_name"] = c.get("name")
                d["contact_email"] = c.get("email")

    return {"items": items, "total": total}


@router.post("", status_code=201)
async def create_deal(payload: DealCreate, membership: dict = Depends(get_current_company), conn=Depends(get_db)):
    if membership["role"] == "ANALYST":
        raise HTTPException(status_code=403, detail="ANALYST não pode criar")
    did = str(uuid.uuid4())
    now = _now_iso()
    data = payload.model_dump()
    await conn.execute(
        """INSERT INTO deals
           (id, company_id, contact_id, pipeline_id, stage_id, title, value,
            expected_close_date, assigned_to, custom_fields, won_at, lost_at, lost_reason,
            created_at, updated_at, deleted_at)
           VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,$16)""",
        did, membership["company_id"], data["contact_id"], data["pipeline_id"], data["stage_id"],
        data["title"], data.get("value", 0), data.get("expected_close_date"),
        data.get("assigned_to"), data.get("custom_fields") or {},
        None, None, None, now, now, None,
    )
    await conn.execute(
        "UPDATE contacts SET score = score + 10 WHERE id = $1 AND company_id = $2",
        data["contact_id"], membership["company_id"],
    )
    row = await conn.fetchrow("SELECT * FROM deals WHERE id = $1", did)
    return dict(row)


@router.get("/{deal_id}")
async def get_deal(deal_id: str, membership: dict = Depends(get_current_company), conn=Depends(get_db)):
    row = await conn.fetchrow(
        "SELECT * FROM deals WHERE id = $1 AND company_id = $2 AND deleted_at IS NULL",
        deal_id, membership["company_id"],
    )
    if not row:
        raise HTTPException(status_code=404, detail="Deal não encontrado")
    deal = dict(row)
    c_row = await conn.fetchrow("SELECT * FROM contacts WHERE id = $1", deal["contact_id"])
    return {**deal, "contact": dict(c_row) if c_row else None}


@router.put("/{deal_id}")
async def update_deal(deal_id: str, payload: DealUpdate, membership: dict = Depends(get_current_company), conn=Depends(get_db)):
    if membership["role"] == "ANALYST":
        raise HTTPException(status_code=403, detail="ANALYST não pode editar")

    update = {k: v for k, v in payload.model_dump().items() if v is not None}
    if not update:
        row = await conn.fetchrow("SELECT * FROM deals WHERE id = $1", deal_id)
        return dict(row) if row else {}

    update["updated_at"] = _now_iso()
    set_parts = []
    params: list = []
    n = 1
    for k, v in update.items():
        set_parts.append(f"{k} = ${n}")
        params.append(v)
        n += 1
    params.extend([deal_id, membership["company_id"]])
    result = await conn.execute(
        f"UPDATE deals SET {', '.join(set_parts)} WHERE id = ${n} AND company_id = ${n + 1}",
        *params,
    )
    if result == "UPDATE 0":
        raise HTTPException(status_code=404, detail="Deal não encontrado")
    row = await conn.fetchrow("SELECT * FROM deals WHERE id = $1", deal_id)
    return dict(row)


@router.delete("/{deal_id}", status_code=204)
async def delete_deal(deal_id: str, membership: dict = Depends(get_current_company), conn=Depends(get_db)):
    if membership["role"] not in ("MASTER", "ADMIN"):
        raise HTTPException(status_code=403, detail="Apenas ADMIN/MASTER")
    await conn.execute(
        "UPDATE deals SET deleted_at = $1 WHERE id = $2 AND company_id = $3",
        _now_iso(), deal_id, membership["company_id"],
    )
    return None


@router.patch("/{deal_id}/stage")
async def move_stage(deal_id: str, payload: StageMoveInput, membership: dict = Depends(get_current_company), conn=Depends(get_db)):
    if membership["role"] == "ANALYST":
        raise HTTPException(status_code=403, detail="ANALYST não pode mover")
    now = _now_iso()
    if payload.pipeline_id:
        result = await conn.execute(
            "UPDATE deals SET stage_id = $1, pipeline_id = $2, updated_at = $3 WHERE id = $4 AND company_id = $5",
            payload.stage_id, payload.pipeline_id, now, deal_id, membership["company_id"],
        )
    else:
        result = await conn.execute(
            "UPDATE deals SET stage_id = $1, updated_at = $2 WHERE id = $3 AND company_id = $4",
            payload.stage_id, now, deal_id, membership["company_id"],
        )
    if result == "UPDATE 0":
        raise HTTPException(status_code=404, detail="Deal não encontrado")
    deal_row = await conn.fetchrow("SELECT * FROM deals WHERE id = $1", deal_id)
    deal = dict(deal_row)
    if deal.get("contact_id"):
        await conn.execute(
            "UPDATE contacts SET score = score + 15 WHERE id = $1 AND company_id = $2",
            deal["contact_id"], membership["company_id"],
        )
    return deal


@router.post("/{deal_id}/won")
async def mark_won(deal_id: str, membership: dict = Depends(get_current_company), conn=Depends(get_db)):
    if membership["role"] == "ANALYST":
        raise HTTPException(status_code=403, detail="ANALYST não pode marcar deal como ganho")
    now = _now_iso()
    await conn.execute(
        "UPDATE deals SET won_at = $1, updated_at = $1 WHERE id = $2 AND company_id = $3",
        now, deal_id, membership["company_id"],
    )
    deal_row = await conn.fetchrow("SELECT * FROM deals WHERE id = $1", deal_id)
    deal = dict(deal_row)
    if deal.get("contact_id"):
        await conn.execute(
            "UPDATE contacts SET score = score + 20, type = 'client', updated_at = $1 WHERE id = $2 AND company_id = $3",
            now, deal["contact_id"], membership["company_id"],
        )
    return deal


@router.post("/{deal_id}/lost")
async def mark_lost(deal_id: str, payload: LostInput, membership: dict = Depends(get_current_company), conn=Depends(get_db)):
    if membership["role"] == "ANALYST":
        raise HTTPException(status_code=403, detail="ANALYST não pode marcar deal como perdido")
    now = _now_iso()
    await conn.execute(
        "UPDATE deals SET lost_at = $1, lost_reason = $2, updated_at = $1 WHERE id = $3 AND company_id = $4",
        now, payload.reason, deal_id, membership["company_id"],
    )
    deal_row = await conn.fetchrow("SELECT * FROM deals WHERE id = $1", deal_id)
    deal = dict(deal_row)
    if deal.get("contact_id"):
        await conn.execute(
            "UPDATE contacts SET score = score - 10 WHERE id = $1 AND company_id = $2",
            deal["contact_id"], membership["company_id"],
        )
    return deal
