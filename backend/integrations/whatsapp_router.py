"""WhatsApp integration router."""
from fastapi import APIRouter, Depends

from db import get_db
from deps import get_current_company

router = APIRouter(prefix="/whatsapp", tags=["whatsapp"])


@router.get("/messages")
async def list_messages(
    contact_id: str | None = None,
    membership: dict = Depends(get_current_company),
    conn=Depends(get_db),
):
    if contact_id:
        rows = await conn.fetch(
            "SELECT * FROM whatsapp_messages WHERE company_id = $1 AND contact_id = $2 ORDER BY created_at DESC LIMIT 100",
            membership["company_id"], contact_id,
        )
    else:
        rows = await conn.fetch(
            "SELECT * FROM whatsapp_messages WHERE company_id = $1 ORDER BY created_at DESC LIMIT 100",
            membership["company_id"],
        )
    return {"items": [dict(r) for r in rows]}
