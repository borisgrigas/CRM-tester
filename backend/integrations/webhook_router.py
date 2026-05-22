"""Webhook ingestion router — receives leads from external sources."""
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Request

from db import get_db

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# Payload normalizers
# ---------------------------------------------------------------------------

def _normalize_meta(payload: dict) -> dict:
    """Meta Lead Ads webhook → {name, email, phone}."""
    try:
        field_data = (
            payload["entry"][0]["changes"][0]["value"]["field_data"]
        )
    except (KeyError, IndexError, TypeError):
        return {}
    mapping = {
        "full_name": "name",
        "email": "email",
        "phone_number": "phone",
        "phone": "phone",
    }
    out: dict = {}
    for item in field_data:
        key = mapping.get(item.get("name", ""))
        if key:
            values = item.get("values") or []
            if values:
                out[key] = values[0]
    return out


def _normalize_rdstation(payload: dict) -> dict:
    """RD Station webhook → {name, email, phone, company_name}."""
    p = payload.get("payload") or payload
    return {
        "name": p.get("name") or p.get("full_name") or "",
        "email": p.get("email") or "",
        "phone": p.get("personal_phone") or p.get("mobile_phone") or p.get("phone") or "",
        "company_name": p.get("company_name") or p.get("company") or "",
    }


def _normalize_generic(payload: dict) -> dict:
    """Generic flat payload → {name, email, phone, company_name}."""
    return {
        "name": payload.get("name") or payload.get("full_name") or payload.get("contact_name") or "",
        "email": payload.get("email") or payload.get("email_address") or "",
        "phone": payload.get("phone") or payload.get("phone_number") or payload.get("mobile") or "",
        "company_name": payload.get("company") or payload.get("company_name") or "",
    }


_NORMALIZERS = {
    "meta": _normalize_meta,
    "rdstation": _normalize_rdstation,
}


def _normalize(source: str, payload: dict) -> dict:
    fn = _NORMALIZERS.get(source.lower(), _normalize_generic)
    return fn(payload)


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------

@router.post("/{slug}/{source}", status_code=200)
async def receive_webhook(slug: str, source: str, request: Request):
    payload = await request.json()

    # Acquire a DB connection directly (no auth dependency — public endpoint)
    async for conn in get_db():
        # 1. Resolve company by slug
        company = await conn.fetchrow(
            "SELECT id, name FROM companies WHERE slug = $1 AND deleted_at IS NULL", slug
        )
        if not company:
            raise HTTPException(status_code=404, detail=f"Empresa '{slug}' não encontrada")
        company_id = company["id"]

        # 2. Normalize payload
        data = _normalize(source, payload)
        name = (data.get("name") or "").strip()
        email = (data.get("email") or "").strip() or None
        phone = (data.get("phone") or "").strip() or None
        company_name = (data.get("company_name") or "").strip() or None

        if not name:
            return {"ok": False, "error": "name ausente no payload", "received_keys": list(payload.keys())}

        # 3. Duplicate check by email
        duplicate = False
        contact_id: str | None = None
        if email:
            existing = await conn.fetchrow(
                "SELECT id FROM contacts WHERE company_id = $1 AND email = $2 AND deleted_at IS NULL",
                company_id, email,
            )
            if existing:
                contact_id = existing["id"]
                duplicate = True

        # 4. Insert lead if not duplicate
        if not duplicate:
            contact_id = str(uuid.uuid4())
            now = _now_iso()
            await conn.execute(
                """INSERT INTO contacts
                   (id, company_id, type, name, email, phone, company_name,
                    origin, custom_fields, tags, score,
                    created_at, updated_at, deleted_at)
                   VALUES ($1,$2,'lead',$3,$4,$5,$6,$7,'{}','[]',0,$8,$8,NULL)""",
                contact_id, company_id, name, email, phone, company_name,
                source, _now_iso(),
            )

        # 5. Create deal on first stage of default pipeline
        deal_id: str | None = None
        if not duplicate:
            pipeline = await conn.fetchrow(
                "SELECT id FROM pipelines WHERE company_id = $1 AND is_default = TRUE AND deleted_at IS NULL LIMIT 1",
                company_id,
            )
            if not pipeline:
                pipeline = await conn.fetchrow(
                    "SELECT id FROM pipelines WHERE company_id = $1 AND deleted_at IS NULL ORDER BY created_at ASC LIMIT 1",
                    company_id,
                )
            if pipeline:
                stage = await conn.fetchrow(
                    "SELECT id FROM pipeline_stages WHERE pipeline_id = $1 AND deleted_at IS NULL ORDER BY position ASC LIMIT 1",
                    pipeline["id"],
                )
                if stage:
                    deal_id = str(uuid.uuid4())
                    now = _now_iso()
                    await conn.execute(
                        """INSERT INTO deals
                           (id, company_id, contact_id, pipeline_id, stage_id, title,
                            value, custom_fields, created_at, updated_at, deleted_at)
                           VALUES ($1,$2,$3,$4,$5,$6,0,'{}',current_timestamp::text,current_timestamp::text,NULL)""",
                        deal_id, company_id, contact_id,
                        pipeline["id"], stage["id"],
                        f"Lead via {source}: {name}",
                    )
                    # boost contact score
                    await conn.execute(
                        "UPDATE contacts SET score = score + 10 WHERE id = $1",
                        contact_id,
                    )

        # 6. Notify MASTER/ADMIN users
        if not duplicate:
            managers = await conn.fetch(
                "SELECT user_id FROM user_companies WHERE company_id = $1 AND role IN ('MASTER','ADMIN') AND is_active = TRUE",
                company_id,
            )
            now = _now_iso()
            for m in managers:
                await conn.execute(
                    """INSERT INTO notifications
                       (id, company_id, user_id, title, body, type, entity_type, entity_id, created_at)
                       VALUES ($1,$2,$3,$4,$5,'lead_webhook','contact',$6,$7)""",
                    str(uuid.uuid4()), company_id, m["user_id"],
                    f"Novo lead via {source}",
                    f"{name}{' · ' + email if email else ''}",
                    contact_id, now,
                )

        return {
            "ok": True,
            "duplicate": duplicate,
            "contact_id": contact_id,
            "deal_id": deal_id,
        }
