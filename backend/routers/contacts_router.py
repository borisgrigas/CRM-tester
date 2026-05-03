"""Contacts (leads + clients) router."""
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from db import get_db
from deps import get_current_company, get_current_user
from models import ActivityCreate, ContactCreate, ContactUpdate, TagsInput

router = APIRouter(prefix="/contacts", tags=["contacts"])


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _scope(membership: dict) -> dict:
    """Returns mongo filter scoping to current company (and self if COMMERCIAL)."""
    f = {"company_id": membership["company_id"], "deleted_at": None}
    return f


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
    db=Depends(get_db),
):
    f = _scope(membership)
    if membership["role"] == "COMMERCIAL":
        f["assigned_to"] = membership["user_id"]
    if type:
        f["type"] = type
    if assigned_to:
        f["assigned_to"] = assigned_to
    if tag:
        f["tags"] = tag
    if origin:
        f["origin"] = origin
    if score_min is not None or score_max is not None:
        rng: dict = {}
        if score_min is not None:
            rng["$gte"] = score_min
        if score_max is not None:
            rng["$lte"] = score_max
        f["score"] = rng
    if search:
        f["$or"] = [
            {"name": {"$regex": search, "$options": "i"}},
            {"email": {"$regex": search, "$options": "i"}},
            {"company_name": {"$regex": search, "$options": "i"}},
        ]
    direction = -1 if sort.startswith("-") else 1
    sort_field = sort.lstrip("-")

    total = await db.contacts.count_documents(f)
    items = await db.contacts.find(f, {"_id": 0}).sort(sort_field, direction).skip((page - 1) * limit).limit(limit).to_list(limit)
    return {"items": items, "total": total, "page": page, "limit": limit}


@router.post("", status_code=201)
async def create_contact(
    payload: ContactCreate,
    membership: dict = Depends(get_current_company),
    db=Depends(get_db),
):
    if membership["role"] == "ANALYST":
        raise HTTPException(status_code=403, detail="ANALYST não pode criar contatos")
    doc = {
        "id": str(uuid.uuid4()),
        "company_id": membership["company_id"],
        "score": 0,
        "created_at": _now_iso(),
        "updated_at": _now_iso(),
        "deleted_at": None,
        **payload.model_dump(),
    }
    await db.contacts.insert_one(doc)
    doc.pop("_id", None)
    return doc


@router.get("/{contact_id}")
async def get_contact(contact_id: str, membership: dict = Depends(get_current_company), db=Depends(get_db)):
    contact = await db.contacts.find_one({"id": contact_id, **_scope(membership)}, {"_id": 0})
    if not contact:
        raise HTTPException(status_code=404, detail="Contato não encontrado")
    activities = await db.contact_activities.find(
        {"contact_id": contact_id, "company_id": membership["company_id"]}, {"_id": 0}
    ).sort("occurred_at", -1).limit(50).to_list(50)
    deals = await db.deals.find(
        {"contact_id": contact_id, "company_id": membership["company_id"], "deleted_at": None}, {"_id": 0}
    ).to_list(50)
    return {**contact, "activities": activities, "deals": deals}


@router.put("/{contact_id}")
async def update_contact(
    contact_id: str, payload: ContactUpdate,
    membership: dict = Depends(get_current_company), db=Depends(get_db),
):
    if membership["role"] == "ANALYST":
        raise HTTPException(status_code=403, detail="ANALYST não pode editar")
    update = {k: v for k, v in payload.model_dump().items() if v is not None}
    update["updated_at"] = _now_iso()
    result = await db.contacts.update_one(
        {"id": contact_id, **_scope(membership)}, {"$set": update}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Contato não encontrado")
    contact = await db.contacts.find_one({"id": contact_id}, {"_id": 0})
    return contact


@router.delete("/{contact_id}", status_code=204)
async def delete_contact(contact_id: str, membership: dict = Depends(get_current_company), db=Depends(get_db)):
    if membership["role"] not in ("MASTER", "ADMIN"):
        raise HTTPException(status_code=403, detail="Apenas ADMIN/MASTER")
    await db.contacts.update_one(
        {"id": contact_id, "company_id": membership["company_id"]},
        {"$set": {"deleted_at": _now_iso()}},
    )
    return None


@router.post("/{contact_id}/convert")
async def convert_to_client(contact_id: str, membership: dict = Depends(get_current_company), db=Depends(get_db)):
    if membership["role"] == "ANALYST":
        raise HTTPException(status_code=403, detail="ANALYST não pode converter")
    res = await db.contacts.update_one(
        {"id": contact_id, **_scope(membership)},
        {"$set": {"type": "client", "updated_at": _now_iso()}},
    )
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Contato não encontrado")
    return await db.contacts.find_one({"id": contact_id}, {"_id": 0})


@router.post("/{contact_id}/tags")
async def add_tags(contact_id: str, payload: TagsInput, membership: dict = Depends(get_current_company), db=Depends(get_db)):
    await db.contacts.update_one(
        {"id": contact_id, **_scope(membership)},
        {"$addToSet": {"tags": {"$each": payload.tags}}, "$set": {"updated_at": _now_iso()}},
    )
    return await db.contacts.find_one({"id": contact_id}, {"_id": 0})


@router.delete("/{contact_id}/tags")
async def remove_tags(contact_id: str, payload: TagsInput, membership: dict = Depends(get_current_company), db=Depends(get_db)):
    await db.contacts.update_one(
        {"id": contact_id, **_scope(membership)},
        {"$pull": {"tags": {"$in": payload.tags}}, "$set": {"updated_at": _now_iso()}},
    )
    return await db.contacts.find_one({"id": contact_id}, {"_id": 0})


@router.get("/{contact_id}/activities")
async def list_activities(contact_id: str, membership: dict = Depends(get_current_company), db=Depends(get_db)):
    items = await db.contact_activities.find(
        {"contact_id": contact_id, "company_id": membership["company_id"]}, {"_id": 0}
    ).sort("occurred_at", -1).to_list(200)
    return {"items": items}


@router.post("/{contact_id}/activities", status_code=201)
async def add_activity(
    contact_id: str, payload: ActivityCreate,
    user: dict = Depends(get_current_user),
    membership: dict = Depends(get_current_company),
    db=Depends(get_db),
):
    contact = await db.contacts.find_one({"id": contact_id, **_scope(membership)})
    if not contact:
        raise HTTPException(status_code=404, detail="Contato não encontrado")
    activity = {
        "id": str(uuid.uuid4()),
        "company_id": membership["company_id"],
        "contact_id": contact_id,
        "user_id": user["id"],
        "type": payload.type,
        "description": payload.description,
        "metadata": payload.metadata,
        "occurred_at": (payload.occurred_at or datetime.now(timezone.utc)).isoformat() if not isinstance(payload.occurred_at, str) else payload.occurred_at,
        "created_at": _now_iso(),
    }
    await db.contact_activities.insert_one(activity)
    # simple lead scoring
    delta = {"call": 8, "email": 5, "meeting": 6, "note": 1, "whatsapp": 4, "task": 2}.get(payload.type, 0)
    if delta:
        await db.contacts.update_one(
            {"id": contact_id, "company_id": membership["company_id"]},
            {"$inc": {"score": delta}, "$set": {"updated_at": _now_iso()}},
        )
    activity.pop("_id", None)
    return activity
