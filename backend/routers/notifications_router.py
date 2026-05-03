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
    db=Depends(get_db),
):
    items = await db.notifications.find(
        {"company_id": membership["company_id"], "user_id": user["id"]}, {"_id": 0}
    ).sort("created_at", -1).limit(50).to_list(50)
    unread = await db.notifications.count_documents(
        {"company_id": membership["company_id"], "user_id": user["id"], "read_at": None}
    )
    return {"items": items, "unread": unread}


@router.patch("/read-all")
async def mark_all_read(
    user: dict = Depends(get_current_user),
    membership: dict = Depends(get_current_company),
    db=Depends(get_db),
):
    await db.notifications.update_many(
        {"company_id": membership["company_id"], "user_id": user["id"], "read_at": None},
        {"$set": {"read_at": _now_iso()}},
    )
    return {"ok": True}


@router.patch("/{notif_id}/read")
async def mark_read(notif_id: str, user: dict = Depends(get_current_user), db=Depends(get_db)):
    await db.notifications.update_one(
        {"id": notif_id, "user_id": user["id"]},
        {"$set": {"read_at": _now_iso()}},
    )
    return {"ok": True}
