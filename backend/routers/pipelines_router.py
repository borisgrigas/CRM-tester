"""Pipelines and Stages router."""
import uuid
from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Body, Depends, HTTPException

from db import get_db
from deps import get_current_company, require_roles
from models import PipelineCreate, PipelineUpdate, StageCreate, StageReorderItem, StageUpdate

router = APIRouter(prefix="/pipelines", tags=["pipelines"])


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@router.get("")
async def list_pipelines(membership: dict = Depends(get_current_company), conn=Depends(get_db)):
    p_rows = await conn.fetch(
        "SELECT * FROM pipelines WHERE company_id = $1 AND deleted_at IS NULL",
        membership["company_id"],
    )
    out = []
    for p in p_rows:
        s_rows = await conn.fetch(
            "SELECT * FROM pipeline_stages WHERE pipeline_id = $1 AND deleted_at IS NULL ORDER BY position ASC",
            p["id"],
        )
        out.append({**dict(p), "stages": [dict(s) for s in s_rows]})
    return {"items": out}


@router.post("", status_code=201, dependencies=[Depends(require_roles("MASTER", "ADMIN"))])
async def create_pipeline(payload: PipelineCreate, membership: dict = Depends(get_current_company), conn=Depends(get_db)):
    pid = str(uuid.uuid4())
    now = _now_iso()
    await conn.execute(
        "INSERT INTO pipelines (id, company_id, name, is_default, created_at, deleted_at) VALUES ($1,$2,$3,$4,$5,$6)",
        pid, membership["company_id"], payload.name, payload.is_default, now, None,
    )
    row = await conn.fetchrow("SELECT * FROM pipelines WHERE id = $1", pid)
    return {**dict(row), "stages": []}


@router.put("/{pipeline_id}", dependencies=[Depends(require_roles("MASTER", "ADMIN"))])
async def update_pipeline(pipeline_id: str, payload: PipelineUpdate, membership: dict = Depends(get_current_company), conn=Depends(get_db)):
    update = {k: v for k, v in payload.model_dump().items() if v is not None}
    if not update:
        row = await conn.fetchrow("SELECT * FROM pipelines WHERE id = $1", pipeline_id)
        return dict(row) if row else {}

    set_parts = []
    params: list = []
    n = 1
    for k, v in update.items():
        set_parts.append(f"{k} = ${n}")
        params.append(v)
        n += 1
    params.extend([pipeline_id, membership["company_id"]])
    result = await conn.execute(
        f"UPDATE pipelines SET {', '.join(set_parts)} WHERE id = ${n} AND company_id = ${n + 1}",
        *params,
    )
    if result == "UPDATE 0":
        raise HTTPException(status_code=404, detail="Pipeline não encontrado")
    row = await conn.fetchrow("SELECT * FROM pipelines WHERE id = $1", pipeline_id)
    return dict(row)


@router.delete("/{pipeline_id}", status_code=204, dependencies=[Depends(require_roles("MASTER", "ADMIN"))])
async def delete_pipeline(pipeline_id: str, membership: dict = Depends(get_current_company), conn=Depends(get_db)):
    await conn.execute(
        "UPDATE pipelines SET deleted_at = $1 WHERE id = $2 AND company_id = $3",
        _now_iso(), pipeline_id, membership["company_id"],
    )
    return None


@router.post("/{pipeline_id}/stages", status_code=201, dependencies=[Depends(require_roles("MASTER", "ADMIN"))])
async def create_stage(pipeline_id: str, payload: StageCreate, membership: dict = Depends(get_current_company), conn=Depends(get_db)):
    sid = str(uuid.uuid4())
    now = _now_iso()
    await conn.execute(
        """INSERT INTO pipeline_stages
           (id, pipeline_id, company_id, name, position, conversion_probability, color, sla_hours, created_at, deleted_at)
           VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10)""",
        sid, pipeline_id, membership["company_id"], payload.name, payload.position,
        payload.conversion_probability, payload.color, payload.sla_hours, now, None,
    )
    row = await conn.fetchrow("SELECT * FROM pipeline_stages WHERE id = $1", sid)
    return dict(row)


@router.put("/{pipeline_id}/stages", dependencies=[Depends(require_roles("MASTER", "ADMIN"))])
async def reorder_stages(
    pipeline_id: str, items: List[StageReorderItem] = Body(...),
    membership: dict = Depends(get_current_company), conn=Depends(get_db),
):
    for it in items:
        await conn.execute(
            "UPDATE pipeline_stages SET position = $1 WHERE id = $2 AND pipeline_id = $3 AND company_id = $4",
            it.position, it.id, pipeline_id, membership["company_id"],
        )
    return {"ok": True}


@router.put("/{pipeline_id}/stages/{stage_id}", dependencies=[Depends(require_roles("MASTER", "ADMIN"))])
async def update_stage(pipeline_id: str, stage_id: str, payload: StageUpdate, membership: dict = Depends(get_current_company), conn=Depends(get_db)):
    update = {k: v for k, v in payload.model_dump().items() if v is not None}
    if not update:
        row = await conn.fetchrow("SELECT * FROM pipeline_stages WHERE id = $1", stage_id)
        return dict(row) if row else {}

    set_parts = []
    params: list = []
    n = 1
    for k, v in update.items():
        set_parts.append(f"{k} = ${n}")
        params.append(v)
        n += 1
    params.extend([stage_id, pipeline_id, membership["company_id"]])
    await conn.execute(
        f"UPDATE pipeline_stages SET {', '.join(set_parts)} WHERE id = ${n} AND pipeline_id = ${n + 1} AND company_id = ${n + 2}",
        *params,
    )
    row = await conn.fetchrow("SELECT * FROM pipeline_stages WHERE id = $1", stage_id)
    return dict(row)


@router.delete("/{pipeline_id}/stages/{stage_id}", status_code=204, dependencies=[Depends(require_roles("MASTER", "ADMIN"))])
async def delete_stage(pipeline_id: str, stage_id: str, membership: dict = Depends(get_current_company), conn=Depends(get_db)):
    await conn.execute(
        "UPDATE pipeline_stages SET deleted_at = $1 WHERE id = $2 AND pipeline_id = $3 AND company_id = $4",
        _now_iso(), stage_id, pipeline_id, membership["company_id"],
    )
    return None
