"""WhatsApp integration router."""
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from db import get_db
from deps import get_current_company, get_current_user, require_module

router = APIRouter(prefix="/whatsapp", tags=["whatsapp"])


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class InboundMessage(BaseModel):
    from_number: str
    to_number: Optional[str] = None
    body: Optional[str] = None
    media_url: Optional[str] = None
    external_id: Optional[str] = None


class SendMessage(BaseModel):
    contact_id: str
    body: str
    to_number: Optional[str] = None


# ---------------------------------------------------------------------------
# Inbound webhook — public (no JWT), company identified by slug in path
# ---------------------------------------------------------------------------

@router.post("/inbound/{company_slug}", status_code=200)
async def inbound_message(company_slug: str, payload: InboundMessage, conn=Depends(get_db)):
    # 1. Resolve company
    company = await conn.fetchrow(
        "SELECT id FROM companies WHERE slug = $1 AND deleted_at IS NULL", company_slug
    )
    if not company:
        raise HTTPException(status_code=404, detail=f"Empresa '{company_slug}' não encontrada")
    company_id = company["id"]
    from_number = payload.from_number.strip()

    # 2. Find or create contact by phone number
    contact = await conn.fetchrow(
        """SELECT id, name FROM contacts
           WHERE company_id = $1
             AND (whatsapp_phone = $2 OR phone = $2)
             AND deleted_at IS NULL
           LIMIT 1""",
        company_id, from_number,
    )
    if contact:
        contact_id = contact["id"]
        contact_name = contact["name"]
    else:
        contact_id = str(uuid.uuid4())
        contact_name = from_number
        now = _now_iso()
        await conn.execute(
            """INSERT INTO contacts
               (id, company_id, type, name, phone, whatsapp_phone, origin,
                custom_fields, tags, score, created_at, updated_at, deleted_at)
               VALUES ($1,$2,'lead',$3,$4,$4,'whatsapp','{}','[]',0,$5,$5,NULL)""",
            contact_id, company_id, contact_name, from_number, now,
        )

    # 3. Save inbound message
    msg_id = str(uuid.uuid4())
    now = _now_iso()
    await conn.execute(
        """INSERT INTO whatsapp_messages
           (id, company_id, contact_id, direction, from_number, to_number,
            body, media_url, status, external_id, created_at)
           VALUES ($1,$2,$3,'inbound',$4,$5,$6,$7,'received',$8,$9)""",
        msg_id, company_id, contact_id, from_number, payload.to_number,
        payload.body, payload.media_url, payload.external_id, now,
    )

    # 4. Record activity on contact timeline
    aid = str(uuid.uuid4())
    await conn.execute(
        """INSERT INTO contact_activities
           (id, company_id, contact_id, user_id, type, description, metadata, occurred_at, created_at)
           VALUES ($1,$2,$3,NULL,'whatsapp',$4,$5,$6,$6)""",
        aid, company_id, contact_id,
        payload.body or "(mídia)",
        {"direction": "inbound", "from": from_number, "message_id": msg_id},
        now,
    )
    # bump score
    await conn.execute(
        "UPDATE contacts SET score = score + 4, updated_at = $1 WHERE id = $2",
        now, contact_id,
    )

    return {
        "ok": True,
        "message_id": msg_id,
        "contact_id": contact_id,
        "contact_name": contact_name,
        "new_contact": contact is None,
    }


# ---------------------------------------------------------------------------
# Send — authenticated, logs outbound message
# ---------------------------------------------------------------------------

@router.post("/send", status_code=201, dependencies=[Depends(require_module("whatsapp"))])
async def send_message(
    payload: SendMessage,
    user: dict = Depends(get_current_user),
    membership: dict = Depends(get_current_company),
    conn=Depends(get_db),
):
    company_id = membership["company_id"]

    # Verify contact belongs to company
    contact = await conn.fetchrow(
        "SELECT id, name, whatsapp_phone, phone FROM contacts WHERE id = $1 AND company_id = $2 AND deleted_at IS NULL",
        payload.contact_id, company_id,
    )
    if not contact:
        raise HTTPException(status_code=404, detail="Contato não encontrado")

    to_number = payload.to_number or contact["whatsapp_phone"] or contact["phone"] or ""

    msg_id = str(uuid.uuid4())
    now = _now_iso()
    await conn.execute(
        """INSERT INTO whatsapp_messages
           (id, company_id, contact_id, direction, from_number, to_number,
            body, status, created_at)
           VALUES ($1,$2,$3,'outbound',$4,$5,$6,'sent',$7)""",
        msg_id, company_id, payload.contact_id,
        None, to_number, payload.body, now,
    )

    # Record activity
    aid = str(uuid.uuid4())
    await conn.execute(
        """INSERT INTO contact_activities
           (id, company_id, contact_id, user_id, type, description, metadata, occurred_at, created_at)
           VALUES ($1,$2,$3,$4,'whatsapp',$5,$6,$7,$7)""",
        aid, company_id, payload.contact_id, user["id"],
        payload.body,
        {"direction": "outbound", "to": to_number, "message_id": msg_id},
        now,
    )

    row = await conn.fetchrow("SELECT * FROM whatsapp_messages WHERE id = $1", msg_id)
    return dict(row)


# ---------------------------------------------------------------------------
# Conversations — list contacts with at least one message, sorted by last msg
# ---------------------------------------------------------------------------

@router.get("/conversations", dependencies=[Depends(require_module("whatsapp"))])
async def list_conversations(
    membership: dict = Depends(get_current_company),
    conn=Depends(get_db),
):
    rows = await conn.fetch(
        """SELECT DISTINCT ON (wm.contact_id)
               wm.contact_id,
               wm.body          AS last_body,
               wm.direction     AS last_direction,
               wm.created_at    AS last_at,
               c.name           AS contact_name,
               c.phone          AS contact_phone,
               c.whatsapp_phone AS contact_whatsapp_phone
           FROM whatsapp_messages wm
           LEFT JOIN contacts c ON c.id = wm.contact_id
           WHERE wm.company_id = $1
           ORDER BY wm.contact_id, wm.created_at DESC""",
        membership["company_id"],
    )
    # Sort conversations by last message time (most recent first)
    items = sorted([dict(r) for r in rows], key=lambda x: x["last_at"] or "", reverse=True)
    return {"items": items}


# ---------------------------------------------------------------------------
# Messages — list messages for a contact (existing, unchanged)
# ---------------------------------------------------------------------------

@router.get("/messages", dependencies=[Depends(require_module("whatsapp"))])
async def list_messages(
    contact_id: Optional[str] = None,
    membership: dict = Depends(get_current_company),
    conn=Depends(get_db),
):
    if contact_id:
        rows = await conn.fetch(
            "SELECT * FROM whatsapp_messages WHERE company_id = $1 AND contact_id = $2 ORDER BY created_at ASC LIMIT 200",
            membership["company_id"], contact_id,
        )
    else:
        rows = await conn.fetch(
            "SELECT * FROM whatsapp_messages WHERE company_id = $1 ORDER BY created_at DESC LIMIT 100",
            membership["company_id"],
        )
    return {"items": [dict(r) for r in rows]}
