"""Companies router — management restricted to MASTER of the franchisor."""
import re
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException

from db import get_db
from deps import get_current_user, require_franchisor_master
from models import CompanyCreate, CompanyUpdate

router = APIRouter(prefix="/companies", tags=["companies"])


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _slugify(s: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9]+", "-", s.lower()).strip("-")
    return s or str(uuid.uuid4())[:8]


async def _ensure_master_anywhere(conn, user_id: str):
    row = await conn.fetchrow(
        "SELECT 1 FROM user_companies WHERE user_id = $1 AND role = 'MASTER' AND is_active = TRUE",
        user_id,
    )
    if not row:
        raise HTTPException(status_code=403, detail="Apenas MASTER")


async def _ensure_master_or_admin_anywhere(conn, user_id: str):
    row = await conn.fetchrow(
        "SELECT 1 FROM user_companies WHERE user_id = $1 AND role IN ('MASTER', 'ADMIN') AND is_active = TRUE",
        user_id,
    )
    if not row:
        raise HTTPException(status_code=403, detail="Apenas MASTER ou ADMIN")


@router.get("")
async def list_companies(user: dict = Depends(get_current_user), conn=Depends(get_db)):
    await _ensure_master_anywhere(conn, user["id"])
    rows = await conn.fetch("SELECT * FROM companies WHERE deleted_at IS NULL")
    items = []
    for row in rows:
        c = dict(row)
        c.setdefault("is_active", True)
        c.setdefault("is_franchisor", False)
        c["leads_count"] = await conn.fetchval(
            "SELECT COUNT(*) FROM contacts WHERE company_id = $1 AND type = 'lead' AND deleted_at IS NULL", c["id"]
        )
        c["clients_count"] = await conn.fetchval(
            "SELECT COUNT(*) FROM contacts WHERE company_id = $1 AND type = 'client' AND deleted_at IS NULL", c["id"]
        )
        c["deals_count"] = await conn.fetchval(
            "SELECT COUNT(*) FROM deals WHERE company_id = $1 AND deleted_at IS NULL", c["id"]
        )
        items.append(c)
    return {"items": items}


@router.post("", status_code=201)
async def create_company(
    payload: CompanyCreate,
    actor: dict = Depends(require_franchisor_master),
    conn=Depends(get_db),
):
    slug = _slugify(payload.slug or payload.name)
    existing = await conn.fetchrow(
        "SELECT 1 FROM companies WHERE slug = $1 AND deleted_at IS NULL", slug
    )
    if existing:
        raise HTTPException(status_code=400, detail="Slug já existe — escolha outro")
    cid = str(uuid.uuid4())
    now = _now_iso()
    await conn.execute(
        """INSERT INTO companies (id, name, slug, plan, logo_url, settings, is_active, is_franchisor, created_at, deleted_at)
           VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10)""",
        cid, payload.name, slug, payload.plan or "free", payload.logo_url,
        {}, True, False, now, None,
    )
    await conn.execute(
        """INSERT INTO user_companies (user_id, company_id, role, modules, is_active, invited_at, accepted_at)
           VALUES ($1,$2,$3,$4,$5,$6,$7)""",
        actor["id"], cid, "MASTER", [], True, now, now,
    )
    row = await conn.fetchrow("SELECT * FROM companies WHERE id = $1", cid)
    return dict(row)


@router.get("/consolidated")
async def consolidated(user: dict = Depends(get_current_user), conn=Depends(get_db)):
    await _ensure_master_or_admin_anywhere(conn, user["id"])
    rows = await conn.fetch("SELECT * FROM companies WHERE deleted_at IS NULL")
    out = []
    total_pipeline = 0.0
    total_won = 0.0
    total_leads = 0
    for row in rows:
        c = dict(row)
        leads = await conn.fetchval(
            "SELECT COUNT(*) FROM contacts WHERE company_id = $1 AND type = 'lead' AND deleted_at IS NULL", c["id"]
        )
        clients = await conn.fetchval(
            "SELECT COUNT(*) FROM contacts WHERE company_id = $1 AND type = 'client' AND deleted_at IS NULL", c["id"]
        )
        deals = await conn.fetchval(
            "SELECT COUNT(*) FROM deals WHERE company_id = $1 AND deleted_at IS NULL", c["id"]
        )
        won = await conn.fetchval(
            "SELECT COUNT(*) FROM deals WHERE company_id = $1 AND won_at IS NOT NULL AND deleted_at IS NULL", c["id"]
        )
        v_rows = await conn.fetch(
            "SELECT value, won_at FROM deals WHERE company_id = $1 AND deleted_at IS NULL", c["id"]
        )
        pipeline_value = sum(float(r["value"] or 0) for r in v_rows)
        won_value = sum(float(r["value"] or 0) for r in v_rows if r["won_at"])
        out.append({
            "id": c["id"], "name": c["name"], "slug": c["slug"], "logo_url": c.get("logo_url"),
            "is_active": c.get("is_active", True), "is_franchisor": c.get("is_franchisor", False),
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
            "companies_count": len(rows),
        },
    }


@router.get("/{company_id}")
async def get_company(company_id: str, user: dict = Depends(get_current_user), conn=Depends(get_db)):
    await _ensure_master_anywhere(conn, user["id"])
    row = await conn.fetchrow("SELECT * FROM companies WHERE id = $1 AND deleted_at IS NULL", company_id)
    if not row:
        raise HTTPException(status_code=404, detail="Empresa não encontrada")
    return dict(row)


@router.put("/{company_id}")
async def update_company(
    company_id: str, payload: CompanyUpdate,
    actor: dict = Depends(require_franchisor_master), conn=Depends(get_db),
):
    update = {k: v for k, v in payload.model_dump().items() if v is not None}
    update.pop("slug", None)
    update.pop("id", None)
    update.pop("is_franchisor", None)
    if not update:
        row = await conn.fetchrow("SELECT * FROM companies WHERE id = $1", company_id)
        return dict(row) if row else {}

    set_parts = []
    params: list = []
    n = 1
    for k, v in update.items():
        set_parts.append(f"{k} = ${n}")
        params.append(v)
        n += 1
    params.extend([company_id])
    result = await conn.execute(
        f"UPDATE companies SET {', '.join(set_parts)} WHERE id = ${n} AND deleted_at IS NULL",
        *params,
    )
    if result == "UPDATE 0":
        raise HTTPException(status_code=404, detail="Empresa não encontrada")
    row = await conn.fetchrow("SELECT * FROM companies WHERE id = $1", company_id)
    return dict(row)


@router.patch("/{company_id}/activate")
async def activate_company(company_id: str, actor: dict = Depends(require_franchisor_master), conn=Depends(get_db)):
    result = await conn.execute(
        "UPDATE companies SET is_active = TRUE WHERE id = $1 AND deleted_at IS NULL", company_id
    )
    if result == "UPDATE 0":
        raise HTTPException(status_code=404, detail="Empresa não encontrada")
    return {"ok": True, "is_active": True}


@router.patch("/{company_id}/deactivate")
async def deactivate_company(company_id: str, actor: dict = Depends(require_franchisor_master), conn=Depends(get_db)):
    row = await conn.fetchrow("SELECT * FROM companies WHERE id = $1 AND deleted_at IS NULL", company_id)
    if not row:
        raise HTTPException(status_code=404, detail="Empresa não encontrada")
    if row["is_franchisor"]:
        raise HTTPException(status_code=400, detail="A franqueadora não pode ser inativada")
    await conn.execute("UPDATE companies SET is_active = FALSE WHERE id = $1", company_id)
    return {"ok": True, "is_active": False}


@router.delete("/{company_id}", status_code=204)
async def delete_company(company_id: str, actor: dict = Depends(require_franchisor_master), conn=Depends(get_db)):
    row = await conn.fetchrow("SELECT * FROM companies WHERE id = $1", company_id)
    if not row:
        raise HTTPException(status_code=404, detail="Empresa não encontrada")
    if row["is_franchisor"]:
        raise HTTPException(status_code=400, detail="A franqueadora não pode ser excluída")
    await conn.execute(
        "UPDATE companies SET deleted_at = $1, is_active = FALSE WHERE id = $2",
        _now_iso(), company_id,
    )
    return None


@router.get("/{company_id}/users")
async def company_users(company_id: str, user: dict = Depends(get_current_user), conn=Depends(get_db)):
    await _ensure_master_anywhere(conn, user["id"])
    m_rows = await conn.fetch("SELECT * FROM user_companies WHERE company_id = $1", company_id)
    user_ids = [m["user_id"] for m in m_rows]
    u_rows = await conn.fetch(
        "SELECT id, name, email, avatar_url, created_at FROM users WHERE id = ANY($1)", user_ids
    ) if user_ids else []
    by_id = {u["id"]: dict(u) for u in u_rows}
    return {
        "items": [
            {
                **by_id.get(m["user_id"], {}),
                "role": m["role"],
                "is_active": m["is_active"],
                "modules": m["modules"] or [],
            }
            for m in m_rows
        ]
    }
