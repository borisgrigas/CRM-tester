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
async def list_pipelines(membership: dict = Depends(get_current_company), db=Depends(get_db)):
    pipelines = await db.pipelines.find(
        {"company_id": membership["company_id"], "deleted_at": None}, {"_id": 0}
    ).to_list(50)
    out = []
    for p in pipelines:
        stages = await db.pipeline_stages.find(
            {"pipeline_id": p["id"], "deleted_at": None}, {"_id": 0}
        ).sort("position", 1).to_list(50)
        out.append({**p, "stages": stages})
    return {"items": out}


@router.post("", status_code=201, dependencies=[Depends(require_roles("MASTER", "ADMIN"))])
async def create_pipeline(payload: PipelineCreate, membership: dict = Depends(get_current_company), db=Depends(get_db)):
    pid = str(uuid.uuid4())
    doc = {
        "id": pid, "company_id": membership["company_id"],
        "name": payload.name, "is_default": payload.is_default,
        "created_at": _now_iso(), "deleted_at": None,
    }
    await db.pipelines.insert_one(doc)
    doc.pop("_id", None)
    return {**doc, "stages": []}


@router.put("/{pipeline_id}", dependencies=[Depends(require_roles("MASTER", "ADMIN"))])
async def update_pipeline(pipeline_id: str, payload: PipelineUpdate, membership: dict = Depends(get_current_company), db=Depends(get_db)):
    update = {k: v for k, v in payload.model_dump().items() if v is not None}
    res = await db.pipelines.update_one(
        {"id": pipeline_id, "company_id": membership["company_id"]}, {"$set": update}
    )
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Pipeline não encontrado")
    return await db.pipelines.find_one({"id": pipeline_id}, {"_id": 0})


@router.delete("/{pipeline_id}", status_code=204, dependencies=[Depends(require_roles("MASTER", "ADMIN"))])
async def delete_pipeline(pipeline_id: str, membership: dict = Depends(get_current_company), db=Depends(get_db)):
    await db.pipelines.update_one(
        {"id": pipeline_id, "company_id": membership["company_id"]},
        {"$set": {"deleted_at": _now_iso()}},
    )
    return None


@router.post("/{pipeline_id}/stages", status_code=201, dependencies=[Depends(require_roles("MASTER", "ADMIN"))])
async def create_stage(pipeline_id: str, payload: StageCreate, membership: dict = Depends(get_current_company), db=Depends(get_db)):
    sid = str(uuid.uuid4())
    doc = {
        "id": sid, "pipeline_id": pipeline_id, "company_id": membership["company_id"],
        "name": payload.name, "position": payload.position,
        "conversion_probability": payload.conversion_probability,
        "color": payload.color, "sla_hours": payload.sla_hours,
        "created_at": _now_iso(), "deleted_at": None,
    }
    await db.pipeline_stages.insert_one(doc)
    doc.pop("_id", None)
    return doc


@router.put("/{pipeline_id}/stages", dependencies=[Depends(require_roles("MASTER", "ADMIN"))])
async def reorder_stages(
    pipeline_id: str, items: List[StageReorderItem] = Body(...),
    membership: dict = Depends(get_current_company), db=Depends(get_db),
):
    for it in items:
        await db.pipeline_stages.update_one(
            {"id": it.id, "pipeline_id": pipeline_id, "company_id": membership["company_id"]},
            {"$set": {"position": it.position}},
        )
    return {"ok": True}


@router.put("/{pipeline_id}/stages/{stage_id}", dependencies=[Depends(require_roles("MASTER", "ADMIN"))])
async def update_stage(pipeline_id: str, stage_id: str, payload: StageUpdate, membership: dict = Depends(get_current_company), db=Depends(get_db)):
    update = {k: v for k, v in payload.model_dump().items() if v is not None}
    await db.pipeline_stages.update_one(
        {"id": stage_id, "pipeline_id": pipeline_id, "company_id": membership["company_id"]},
        {"$set": update},
    )
    return await db.pipeline_stages.find_one({"id": stage_id}, {"_id": 0})


@router.delete("/{pipeline_id}/stages/{stage_id}", status_code=204, dependencies=[Depends(require_roles("MASTER", "ADMIN"))])
async def delete_stage(pipeline_id: str, stage_id: str, membership: dict = Depends(get_current_company), db=Depends(get_db)):
    await db.pipeline_stages.update_one(
        {"id": stage_id, "pipeline_id": pipeline_id, "company_id": membership["company_id"]},
        {"$set": {"deleted_at": _now_iso()}},
    )
    return None
