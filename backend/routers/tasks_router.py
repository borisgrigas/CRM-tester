"""Tasks router."""
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException

from db import get_db
from deps import get_current_company, get_current_user
from models import TaskCreate, TaskUpdate

router = APIRouter(prefix="/tasks", tags=["tasks"])


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@router.get("")
async def list_tasks(
    status: Optional[str] = None,
    priority: Optional[str] = None,
    assigned_to: Optional[str] = None,
    membership: dict = Depends(get_current_company),
    db=Depends(get_db),
):
    f = {"company_id": membership["company_id"]}
    if membership["role"] == "COMMERCIAL":
        f["assigned_to"] = membership["user_id"]
    if status:
        f["status"] = status
    if priority:
        f["priority"] = priority
    if assigned_to:
        f["assigned_to"] = assigned_to
    items = await db.tasks.find(f, {"_id": 0}).sort("due_date", 1).limit(500).to_list(500)
    return {"items": items}


@router.post("", status_code=201)
async def create_task(
    payload: TaskCreate,
    user: dict = Depends(get_current_user),
    membership: dict = Depends(get_current_company),
    db=Depends(get_db),
):
    if membership["role"] == "ANALYST":
        raise HTTPException(status_code=403, detail="ANALYST não pode criar")
    tid = str(uuid.uuid4())
    doc = {
        "id": tid,
        "company_id": membership["company_id"],
        "created_by": user["id"],
        "status": "pending",
        "completed_at": None,
        "created_at": _now_iso(),
        "updated_at": _now_iso(),
        **payload.model_dump(),
    }
    await db.tasks.insert_one(doc)
    doc.pop("_id", None)
    return doc


@router.put("/{task_id}")
async def update_task(task_id: str, payload: TaskUpdate, membership: dict = Depends(get_current_company), db=Depends(get_db)):
    update = {k: v for k, v in payload.model_dump().items() if v is not None}
    update["updated_at"] = _now_iso()
    res = await db.tasks.update_one(
        {"id": task_id, "company_id": membership["company_id"]}, {"$set": update}
    )
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Tarefa não encontrada")
    return await db.tasks.find_one({"id": task_id}, {"_id": 0})


@router.patch("/{task_id}/complete")
async def complete_task(task_id: str, membership: dict = Depends(get_current_company), db=Depends(get_db)):
    now = _now_iso()
    await db.tasks.update_one(
        {"id": task_id, "company_id": membership["company_id"]},
        {"$set": {"status": "done", "completed_at": now, "updated_at": now}},
    )
    return await db.tasks.find_one({"id": task_id}, {"_id": 0})


@router.delete("/{task_id}", status_code=204)
async def delete_task(task_id: str, membership: dict = Depends(get_current_company), db=Depends(get_db)):
    await db.tasks.delete_one({"id": task_id, "company_id": membership["company_id"]})
    return None
