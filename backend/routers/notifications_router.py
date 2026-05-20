"""Notifications router."""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends

from db import get_db
from deps import get_current_company, get_current_user

router = APIRouter(prefix="/notifications", tags=["notifications"])


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@router.get("")
async def list_notifications(
    user: dict = Depends(get_current_user),
    membership: dict = Depends(get_current_company),
    conn=Depends(get_db),
):
    rows = await conn.fetch(
        "SELECT * FROM notifications WHERE company_id = $1 AND user_id = $2 ORDER BY created_at DESC LIMIT 50",
        membership["company_id"], user["id"],
    )
    unread = await conn.fetchval(
        "SELECT COUNT(*) FROM notifications WHERE company_id = $1 AND user_id = $2 AND read_at IS NULL",
        membership["company_id"], user["id"],
    )
    return {"items": [dict(r) for r in rows], "unread": unread}


@router.patch("/read-all")
async def mark_all_read(
    user: dict = Depends(get_current_user),
    membership: dict = Depends(get_current_company),
    conn=Depends(get_db),
):
    await conn.execute(
        "UPDATE notifications SET read_at = $1 WHERE company_id = $2 AND user_id = $3 AND read_at IS NULL",
        _now_iso(), membership["company_id"], user["id"],
    )
    return {"ok": True}


@router.patch("/{notif_id}/read")
async def mark_read(notif_id: str, user: dict = Depends(get_current_user), conn=Depends(get_db)):
    await conn.execute(
        "UPDATE notifications SET read_at = $1 WHERE id = $2 AND user_id = $3",
        _now_iso(), notif_id, user["id"],
    )
    return {"ok": True}
