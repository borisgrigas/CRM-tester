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
    conn=Depends(get_db),
):
    conditions = ["company_id = $1"]
    params: list = [membership["company_id"]]
    n = 2

    if membership["role"] == "COMMERCIAL":
        conditions.append(f"assigned_to = ${n}")
        params.append(membership["user_id"])
        n += 1

    if status:
        conditions.append(f"status = ${n}")
        params.append(status)
        n += 1

    if priority:
        conditions.append(f"priority = ${n}")
        params.append(priority)
        n += 1

    if assigned_to:
        conditions.append(f"assigned_to = ${n}")
        params.append(assigned_to)
        n += 1

    where = " AND ".join(conditions)
    rows = await conn.fetch(
        f"SELECT * FROM tasks WHERE {where} ORDER BY due_date ASC NULLS LAST LIMIT 500",
        *params,
    )
    return {"items": [dict(r) for r in rows]}


@router.post("", status_code=201)
async def create_task(
    payload: TaskCreate,
    user: dict = Depends(get_current_user),
    membership: dict = Depends(get_current_company),
    conn=Depends(get_db),
):
    if membership["role"] == "ANALYST":
        raise HTTPException(status_code=403, detail="ANALYST não pode criar")
    tid = str(uuid.uuid4())
    now = _now_iso()
    data = payload.model_dump()
    await conn.execute(
        """INSERT INTO tasks
           (id, company_id, title, description, contact_id, deal_id, assigned_to, created_by,
            due_date, priority, status, completed_at, created_at, updated_at)
           VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14)""",
        tid, membership["company_id"], data["title"], data.get("description"),
        data.get("contact_id"), data.get("deal_id"), data.get("assigned_to"), user["id"],
        data.get("due_date"), data.get("priority", "medium"), "pending", None, now, now,
    )
    row = await conn.fetchrow("SELECT * FROM tasks WHERE id = $1", tid)
    return dict(row)


@router.put("/{task_id}")
async def update_task(task_id: str, payload: TaskUpdate, membership: dict = Depends(get_current_company), conn=Depends(get_db)):
    update = {k: v for k, v in payload.model_dump().items() if v is not None}
    if not update:
        row = await conn.fetchrow("SELECT * FROM tasks WHERE id = $1", task_id)
        return dict(row) if row else {}

    update["updated_at"] = _now_iso()
    set_parts = []
    params: list = []
    n = 1
    for k, v in update.items():
        set_parts.append(f"{k} = ${n}")
        params.append(v)
        n += 1
    params.extend([task_id, membership["company_id"]])
    result = await conn.execute(
        f"UPDATE tasks SET {', '.join(set_parts)} WHERE id = ${n} AND company_id = ${n + 1}",
        *params,
    )
    if result == "UPDATE 0":
        raise HTTPException(status_code=404, detail="Tarefa não encontrada")
    row = await conn.fetchrow("SELECT * FROM tasks WHERE id = $1", task_id)
    return dict(row)


@router.patch("/{task_id}/complete")
async def complete_task(task_id: str, membership: dict = Depends(get_current_company), conn=Depends(get_db)):
    now = _now_iso()
    await conn.execute(
        "UPDATE tasks SET status = 'done', completed_at = $1, updated_at = $1 WHERE id = $2 AND company_id = $3",
        now, task_id, membership["company_id"],
    )
    row = await conn.fetchrow("SELECT * FROM tasks WHERE id = $1", task_id)
    return dict(row) if row else {}


@router.delete("/{task_id}", status_code=204)
async def delete_task(task_id: str, membership: dict = Depends(get_current_company), conn=Depends(get_db)):
    await conn.execute(
        "DELETE FROM tasks WHERE id = $1 AND company_id = $2", task_id, membership["company_id"]
    )
    return None
