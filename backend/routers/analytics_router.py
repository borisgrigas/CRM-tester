"""Analytics: dashboards and KPIs."""
from datetime import datetime, timezone, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, Query

from db import get_db
from deps import get_current_company

router = APIRouter(prefix="/analytics", tags=["analytics"])


def _date_filter(field: str, frm: Optional[str], to: Optional[str]) -> dict:
    if not frm and not to:
        return {}
    rng = {}
    if frm:
        rng["$gte"] = frm
    if to:
        rng["$lte"] = to
    return {field: rng}


@router.get("/overview")
async def overview(
    frm: Optional[str] = Query(None, alias="from"),
    to: Optional[str] = None,
    pipeline_id: Optional[str] = None,
    membership: dict = Depends(get_current_company),
    db=Depends(get_db),
):
    base = {"company_id": membership["company_id"], "deleted_at": None}
    if pipeline_id:
        base["pipeline_id"] = pipeline_id

    total_leads = await db.contacts.count_documents({**base, "type": "lead"})
    total_clients = await db.contacts.count_documents({**base, "type": "client"})

    deal_filter = {**base, **_date_filter("created_at", frm, to)}
    deals_total = await db.deals.count_documents(deal_filter)
    deals_won = await db.deals.count_documents({**deal_filter, "won_at": {"$ne": None}})
    deals_lost = await db.deals.count_documents({**deal_filter, "lost_at": {"$ne": None}})

    pipeline_value = 0.0
    won_value = 0.0
    async for d in db.deals.find(deal_filter, {"_id": 0, "value": 1, "won_at": 1}):
        v = float(d.get("value") or 0)
        pipeline_value += v
        if d.get("won_at"):
            won_value += v

    activities_count = await db.contact_activities.count_documents(
        {"company_id": membership["company_id"], **_date_filter("occurred_at", frm, to)}
    )

    conversion = (deals_won / deals_total * 100) if deals_total else 0
    avg_ticket = (won_value / deals_won) if deals_won else 0

    return {
        "total_leads": total_leads,
        "total_clients": total_clients,
        "deals_total": deals_total,
        "deals_won": deals_won,
        "deals_lost": deals_lost,
        "conversion_rate": round(conversion, 2),
        "pipeline_value": round(pipeline_value, 2),
        "won_value": round(won_value, 2),
        "avg_ticket": round(avg_ticket, 2),
        "activities_count": activities_count,
    }


@router.get("/funnel")
async def funnel(
    pipeline_id: Optional[str] = None,
    membership: dict = Depends(get_current_company),
    db=Depends(get_db),
):
    pipe_filter = {"company_id": membership["company_id"], "deleted_at": None}
    if pipeline_id:
        pipe_filter["id"] = pipeline_id
    pipeline = await db.pipelines.find_one(pipe_filter, {"_id": 0}, sort=[("is_default", -1)])
    if not pipeline:
        return {"stages": []}
    stages = await db.pipeline_stages.find(
        {"pipeline_id": pipeline["id"], "deleted_at": None}, {"_id": 0}
    ).sort("position", 1).to_list(50)

    out = []
    for s in stages:
        count = await db.deals.count_documents(
            {"company_id": membership["company_id"], "pipeline_id": pipeline["id"], "stage_id": s["id"], "deleted_at": None}
        )
        value = 0.0
        async for d in db.deals.find(
            {"company_id": membership["company_id"], "pipeline_id": pipeline["id"], "stage_id": s["id"], "deleted_at": None},
            {"_id": 0, "value": 1},
        ):
            value += float(d.get("value") or 0)
        out.append({"stage_id": s["id"], "name": s["name"], "color": s.get("color"), "count": count, "value": round(value, 2)})
    return {"pipeline": pipeline, "stages": out}


@router.get("/revenue")
async def revenue(
    months: int = 6,
    membership: dict = Depends(get_current_company),
    db=Depends(get_db),
):
    now = datetime.now(timezone.utc)
    out = []
    for i in range(months - 1, -1, -1):
        ref = (now.replace(day=1) - timedelta(days=30 * i))
        month_start = ref.replace(day=1)
        next_month = (month_start + timedelta(days=32)).replace(day=1)

        won = 0.0
        forecast = 0.0
        async for d in db.deals.find(
            {
                "company_id": membership["company_id"],
                "deleted_at": None,
                "created_at": {"$gte": month_start.isoformat(), "$lt": next_month.isoformat()},
            },
            {"_id": 0, "value": 1, "won_at": 1},
        ):
            v = float(d.get("value") or 0)
            forecast += v
            if d.get("won_at"):
                won += v
        out.append({
            "month": month_start.strftime("%Y-%m"),
            "label": month_start.strftime("%b/%y"),
            "won": round(won, 2),
            "forecast": round(forecast, 2),
        })
    return {"items": out}


@router.get("/leaderboard")
async def leaderboard(
    membership: dict = Depends(get_current_company), db=Depends(get_db),
):
    pipeline = [
        {"$match": {"company_id": membership["company_id"], "deleted_at": None, "won_at": {"$ne": None}}},
        {"$group": {"_id": "$assigned_to", "deals_won": {"$sum": 1}, "value": {"$sum": "$value"}}},
        {"$sort": {"value": -1}},
        {"$limit": 10},
    ]
    rows = await db.deals.aggregate(pipeline).to_list(10)
    user_ids = [r["_id"] for r in rows if r.get("_id")]
    users = await db.users.find({"id": {"$in": user_ids}}, {"_id": 0, "id": 1, "name": 1, "avatar_url": 1}).to_list(10)
    by_id = {u["id"]: u for u in users}
    out = []
    for r in rows:
        u = by_id.get(r["_id"], {"id": r["_id"], "name": "—"})
        out.append({"user": u, "deals_won": r["deals_won"], "value": round(float(r["value"] or 0), 2)})
    return {"items": out}


@router.get("/activities")
async def activities_volume(
    days: int = 30,
    membership: dict = Depends(get_current_company), db=Depends(get_db),
):
    rows = await db.contact_activities.aggregate([
        {"$match": {"company_id": membership["company_id"]}},
        {"$group": {"_id": "$type", "count": {"$sum": 1}}},
    ]).to_list(20)
    return {"items": [{"type": r["_id"], "count": r["count"]} for r in rows]}


@router.get("/lead-sources")
async def lead_sources(
    membership: dict = Depends(get_current_company), db=Depends(get_db),
):
    rows = await db.contacts.aggregate([
        {"$match": {"company_id": membership["company_id"], "deleted_at": None}},
        {"$group": {"_id": "$origin", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
    ]).to_list(20)
    return {"items": [{"origin": r["_id"] or "Direto", "count": r["count"]} for r in rows]}
