"""Deals router."""
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from db import get_db
from deps import get_current_company
from models import DealCreate, DealUpdate, LostInput, StageMoveInput

router = APIRouter(prefix="/deals", tags=["deals"])


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _enrich_deals(items, contacts_by_id):
    for d in items:
        c = contacts_by_id.get(d.get("contact_id"))
        if c:
            d["contact_name"] = c.get("name")
            d["contact_email"] = c.get("email")
    return items


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
    db=Depends(get_db),
):
    f = {"company_id": membership["company_id"], "deleted_at": None}
    if membership["role"] == "COMMERCIAL":
        f["assigned_to"] = membership["user_id"]
    elif assigned_to:
        f["assigned_to"] = assigned_to
    if pipeline_id:
        f["pipeline_id"] = pipeline_id
    if stage_id:
        f["stage_id"] = stage_id
    if value_min is not None or value_max is not None:
        rng = {}
        if value_min is not None:
            rng["$gte"] = value_min
        if value_max is not None:
            rng["$lte"] = value_max
        f["value"] = rng
    if search:
        f["title"] = {"$regex": search, "$options": "i"}

    total = await db.deals.count_documents(f)
    items = await db.deals.find(f, {"_id": 0}).sort("created_at", -1).skip((page - 1) * limit).limit(limit).to_list(limit)
    contact_ids = list({d["contact_id"] for d in items if d.get("contact_id")})
    contacts = await db.contacts.find({"id": {"$in": contact_ids}}, {"_id": 0, "id": 1, "name": 1, "email": 1}).to_list(len(contact_ids) or 1)
    contacts_by_id = {c["id"]: c for c in contacts}
    _enrich_deals(items, contacts_by_id)
    return {"items": items, "total": total}


@router.post("", status_code=201)
async def create_deal(payload: DealCreate, membership: dict = Depends(get_current_company), db=Depends(get_db)):
    if membership["role"] == "ANALYST":
        raise HTTPException(status_code=403, detail="ANALYST não pode criar")
    did = str(uuid.uuid4())
    doc = {
        "id": did,
        "company_id": membership["company_id"],
        "won_at": None, "lost_at": None, "lost_reason": None,
        "created_at": _now_iso(), "updated_at": _now_iso(), "deleted_at": None,
        **payload.model_dump(),
    }
    await db.deals.insert_one(doc)
    # bump score
    await db.contacts.update_one(
        {"id": payload.contact_id, "company_id": membership["company_id"]},
        {"$inc": {"score": 10}},
    )
    doc.pop("_id", None)
    return doc


@router.get("/{deal_id}")
async def get_deal(deal_id: str, membership: dict = Depends(get_current_company), db=Depends(get_db)):
    deal = await db.deals.find_one(
        {"id": deal_id, "company_id": membership["company_id"], "deleted_at": None}, {"_id": 0}
    )
    if not deal:
        raise HTTPException(status_code=404, detail="Deal não encontrado")
    contact = await db.contacts.find_one({"id": deal["contact_id"]}, {"_id": 0})
    return {**deal, "contact": contact}


@router.put("/{deal_id}")
async def update_deal(deal_id: str, payload: DealUpdate, membership: dict = Depends(get_current_company), db=Depends(get_db)):
    if membership["role"] == "ANALYST":
        raise HTTPException(status_code=403, detail="ANALYST não pode editar")
    update = {k: v for k, v in payload.model_dump().items() if v is not None}
    update["updated_at"] = _now_iso()
    res = await db.deals.update_one(
        {"id": deal_id, "company_id": membership["company_id"]}, {"$set": update}
    )
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Deal não encontrado")
    return await db.deals.find_one({"id": deal_id}, {"_id": 0})


@router.delete("/{deal_id}", status_code=204)
async def delete_deal(deal_id: str, membership: dict = Depends(get_current_company), db=Depends(get_db)):
    if membership["role"] not in ("MASTER", "ADMIN"):
        raise HTTPException(status_code=403, detail="Apenas ADMIN/MASTER")
    await db.deals.update_one(
        {"id": deal_id, "company_id": membership["company_id"]},
        {"$set": {"deleted_at": _now_iso()}},
    )
    return None


@router.patch("/{deal_id}/stage")
async def move_stage(deal_id: str, payload: StageMoveInput, membership: dict = Depends(get_current_company), db=Depends(get_db)):
    if membership["role"] == "ANALYST":
        raise HTTPException(status_code=403, detail="ANALYST não pode mover")
    update = {"stage_id": payload.stage_id, "updated_at": _now_iso()}
    if payload.pipeline_id:
        update["pipeline_id"] = payload.pipeline_id
    res = await db.deals.update_one(
        {"id": deal_id, "company_id": membership["company_id"]}, {"$set": update}
    )
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Deal não encontrado")
    deal = await db.deals.find_one({"id": deal_id}, {"_id": 0})
    if deal and deal.get("contact_id"):
        await db.contacts.update_one(
            {"id": deal["contact_id"], "company_id": membership["company_id"]},
            {"$inc": {"score": 15}},
        )
    return deal


@router.post("/{deal_id}/won")
async def mark_won(deal_id: str, membership: dict = Depends(get_current_company), db=Depends(get_db)):
    if membership["role"] == "ANALYST":
        raise HTTPException(status_code=403, detail="ANALYST não pode marcar deal como ganho")
    now = _now_iso()
    await db.deals.update_one(
        {"id": deal_id, "company_id": membership["company_id"]},
        {"$set": {"won_at": now, "updated_at": now}},
    )
    deal = await db.deals.find_one({"id": deal_id}, {"_id": 0})
    if deal and deal.get("contact_id"):
        await db.contacts.update_one(
            {"id": deal["contact_id"], "company_id": membership["company_id"]},
            {"$inc": {"score": 20}, "$set": {"type": "client", "updated_at": now}},
        )
    return deal


@router.post("/{deal_id}/lost")
async def mark_lost(deal_id: str, payload: LostInput, membership: dict = Depends(get_current_company), db=Depends(get_db)):
    if membership["role"] == "ANALYST":
        raise HTTPException(status_code=403, detail="ANALYST não pode marcar deal como perdido")
    now = _now_iso()
    await db.deals.update_one(
        {"id": deal_id, "company_id": membership["company_id"]},
        {"$set": {"lost_at": now, "lost_reason": payload.reason, "updated_at": now}},
    )
    deal = await db.deals.find_one({"id": deal_id}, {"_id": 0})
    if deal and deal.get("contact_id"):
        await db.contacts.update_one(
            {"id": deal["contact_id"], "company_id": membership["company_id"]},
            {"$inc": {"score": -10}},
        )
    return deal
