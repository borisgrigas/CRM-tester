"""Companies router (mostly MASTER-only)."""
import re
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException

from db import get_db
from deps import get_current_user
from models import CompanyCreate, CompanyUpdate

router = APIRouter(prefix="/companies", tags=["companies"])


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _slugify(s: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9]+", "-", s.lower()).strip("-")
    return s or str(uuid.uuid4())[:8]


async def _ensure_master(db, user_id: str):
    m = await db.user_companies.find_one({"user_id": user_id, "role": "MASTER", "is_active": True})
    if not m:
        raise HTTPException(status_code=403, detail="Apenas MASTER")


@router.get("")
async def list_companies(user: dict = Depends(get_current_user), db=Depends(get_db)):
    await _ensure_master(db, user["id"])
    items = await db.companies.find({"deleted_at": None}, {"_id": 0}).to_list(500)
    for c in items:
        c.setdefault("is_active", True)
        c["leads_count"] = await db.contacts.count_documents({"company_id": c["id"], "type": "lead", "deleted_at": None})
        c["clients_count"] = await db.contacts.count_documents({"company_id": c["id"], "type": "client", "deleted_at": None})
        c["deals_count"] = await db.deals.count_documents({"company_id": c["id"], "deleted_at": None})
    return {"items": items}


@router.post("", status_code=201)
async def create_company(payload: CompanyCreate, user: dict = Depends(get_current_user), db=Depends(get_db)):
    await _ensure_master(db, user["id"])
    slug = _slugify(payload.slug or payload.name)
    # Slug único
    existing = await db.companies.find_one({"slug": slug, "deleted_at": None})
    if existing:
        raise HTTPException(status_code=400, detail="Slug já existe — escolha outro")
    cid = str(uuid.uuid4())
    doc = {
        "id": cid, "name": payload.name, "slug": slug,
        "plan": payload.plan or "free", "logo_url": payload.logo_url,
        "settings": {}, "is_active": True,
        "created_at": _now_iso(), "deleted_at": None,
    }
    await db.companies.insert_one(doc)
    # MASTER do criador também vira MASTER da nova empresa
    await db.user_companies.insert_one({
        "user_id": user["id"], "company_id": cid, "role": "MASTER",
        "is_active": True, "invited_at": _now_iso(), "accepted_at": _now_iso(),
    })
    doc.pop("_id", None)
    return doc


@router.get("/consolidated")
async def consolidated(user: dict = Depends(get_current_user), db=Depends(get_db)):
    await _ensure_master(db, user["id"])
    companies = await db.companies.find({"deleted_at": None}, {"_id": 0}).to_list(500)
    out = []
    total_pipeline = 0.0
    total_won = 0.0
    total_leads = 0
    for c in companies:
        leads = await db.contacts.count_documents({"company_id": c["id"], "type": "lead", "deleted_at": None})
        clients = await db.contacts.count_documents({"company_id": c["id"], "type": "client", "deleted_at": None})
        deals = await db.deals.count_documents({"company_id": c["id"], "deleted_at": None})
        won = await db.deals.count_documents({"company_id": c["id"], "won_at": {"$ne": None}, "deleted_at": None})
        pipeline_value = 0.0
        won_value = 0.0
        async for d in db.deals.find({"company_id": c["id"], "deleted_at": None}, {"_id": 0, "value": 1, "won_at": 1}):
            v = float(d.get("value") or 0)
            pipeline_value += v
            if d.get("won_at"):
                won_value += v
        out.append({
            "id": c["id"], "name": c["name"], "slug": c["slug"], "logo_url": c.get("logo_url"),
            "is_active": c.get("is_active", True),
            "leads": leads, "clients": clients, "deals": deals, "deals_won": won,
            "pipeline_value": round(pipeline_value, 2), "won_value": round(won_value, 2),
        })
        total_pipeline += pipeline_value
        total_won += won_value
        total_leads += leads
    return {
        "companies": out,
        "totals": {
            "pipeline_value": round(total_pipeline, 2),
            "won_value": round(total_won, 2),
            "leads": total_leads,
            "companies_count": len(companies),
        },
    }


@router.get("/{company_id}")
async def get_company(company_id: str, user: dict = Depends(get_current_user), db=Depends(get_db)):
    await _ensure_master(db, user["id"])
    c = await db.companies.find_one({"id": company_id, "deleted_at": None}, {"_id": 0})
    if not c:
        raise HTTPException(status_code=404, detail="Empresa não encontrada")
    return c


@router.put("/{company_id}")
async def update_company(company_id: str, payload: CompanyUpdate, user: dict = Depends(get_current_user), db=Depends(get_db)):
    await _ensure_master(db, user["id"])
    update = {k: v for k, v in payload.model_dump().items() if v is not None}
    # Slug é imutável: removemos qualquer tentativa de injetar via dict diretamente
    update.pop("slug", None)
    update.pop("id", None)
    res = await db.companies.update_one(
        {"id": company_id, "deleted_at": None}, {"$set": update}
    )
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Empresa não encontrada")
    return await db.companies.find_one({"id": company_id}, {"_id": 0})


@router.patch("/{company_id}/activate")
async def activate_company(company_id: str, user: dict = Depends(get_current_user), db=Depends(get_db)):
    await _ensure_master(db, user["id"])
    res = await db.companies.update_one(
        {"id": company_id, "deleted_at": None}, {"$set": {"is_active": True}}
    )
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Empresa não encontrada")
    return {"ok": True, "is_active": True}


@router.patch("/{company_id}/deactivate")
async def deactivate_company(company_id: str, user: dict = Depends(get_current_user), db=Depends(get_db)):
    await _ensure_master(db, user["id"])
    res = await db.companies.update_one(
        {"id": company_id, "deleted_at": None}, {"$set": {"is_active": False}}
    )
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Empresa não encontrada")
    return {"ok": True, "is_active": False}


@router.delete("/{company_id}", status_code=204)
async def delete_company(company_id: str, user: dict = Depends(get_current_user), db=Depends(get_db)):
    await _ensure_master(db, user["id"])
    await db.companies.update_one(
        {"id": company_id}, {"$set": {"deleted_at": _now_iso(), "is_active": False}}
    )
    return None


@router.get("/{company_id}/users")
async def company_users(company_id: str, user: dict = Depends(get_current_user), db=Depends(get_db)):
    await _ensure_master(db, user["id"])
    memberships = await db.user_companies.find({"company_id": company_id}, {"_id": 0}).to_list(500)
    user_ids = [m["user_id"] for m in memberships]
    users = await db.users.find({"id": {"$in": user_ids}}, {"_id": 0, "password_hash": 0}).to_list(500)
    by_id = {u["id"]: u for u in users}
    return {"items": [{**by_id.get(m["user_id"], {}), "role": m["role"], "is_active": m["is_active"]} for m in memberships]}
