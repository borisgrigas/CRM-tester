"""Analytics: dashboards and KPIs."""
from datetime import datetime, timezone, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, Query

from db import get_db
from deps import get_current_company

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/overview")
async def overview(
    frm: Optional[str] = Query(None, alias="from"),
    to: Optional[str] = None,
    pipeline_id: Optional[str] = None,
    membership: dict = Depends(get_current_company),
    conn=Depends(get_db),
):
    company_id = membership["company_id"]

    total_leads = await conn.fetchval(
        "SELECT COUNT(*) FROM contacts WHERE company_id = $1 AND type = 'lead' AND deleted_at IS NULL", company_id
    )
    total_clients = await conn.fetchval(
        "SELECT COUNT(*) FROM contacts WHERE company_id = $1 AND type = 'client' AND deleted_at IS NULL", company_id
    )

    deal_cond = ["company_id = $1", "deleted_at IS NULL"]
    deal_params: list = [company_id]
    n = 2
    if pipeline_id:
        deal_cond.append(f"pipeline_id = ${n}")
        deal_params.append(pipeline_id)
        n += 1
    if frm:
        deal_cond.append(f"created_at >= ${n}")
        deal_params.append(frm)
        n += 1
    if to:
        deal_cond.append(f"created_at <= ${n}")
        deal_params.append(to)
        n += 1
    deal_where = " AND ".join(deal_cond)

    deals_total = await conn.fetchval(f"SELECT COUNT(*) FROM deals WHERE {deal_where}", *deal_params)
    deals_won = await conn.fetchval(f"SELECT COUNT(*) FROM deals WHERE {deal_where} AND won_at IS NOT NULL", *deal_params)
    deals_lost = await conn.fetchval(f"SELECT COUNT(*) FROM deals WHERE {deal_where} AND lost_at IS NOT NULL", *deal_params)

    value_rows = await conn.fetch(f"SELECT value, won_at FROM deals WHERE {deal_where}", *deal_params)
    pipeline_value = sum(float(r["value"] or 0) for r in value_rows)
    won_value = sum(float(r["value"] or 0) for r in value_rows if r["won_at"])

    act_cond = ["company_id = $1"]
    act_params: list = [company_id]
    m = 2
    if frm:
        act_cond.append(f"occurred_at >= ${m}")
        act_params.append(frm)
        m += 1
    if to:
        act_cond.append(f"occurred_at <= ${m}")
        act_params.append(to)
        m += 1
    activities_count = await conn.fetchval(
        f"SELECT COUNT(*) FROM contact_activities WHERE {' AND '.join(act_cond)}", *act_params
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
    conn=Depends(get_db),
):
    company_id = membership["company_id"]
    if pipeline_id:
        p_row = await conn.fetchrow(
            "SELECT * FROM pipelines WHERE company_id = $1 AND id = $2 AND deleted_at IS NULL",
            company_id, pipeline_id,
        )
    else:
        p_row = await conn.fetchrow(
            "SELECT * FROM pipelines WHERE company_id = $1 AND deleted_at IS NULL ORDER BY is_default DESC LIMIT 1",
            company_id,
        )
    if not p_row:
        return {"stages": []}

    pipeline = dict(p_row)
    s_rows = await conn.fetch(
        "SELECT * FROM pipeline_stages WHERE pipeline_id = $1 AND deleted_at IS NULL ORDER BY position ASC",
        pipeline["id"],
    )
    out = []
    for s in s_rows:
        count = await conn.fetchval(
            "SELECT COUNT(*) FROM deals WHERE company_id = $1 AND pipeline_id = $2 AND stage_id = $3 AND deleted_at IS NULL",
            company_id, pipeline["id"], s["id"],
        )
        v_rows = await conn.fetch(
            "SELECT value FROM deals WHERE company_id = $1 AND pipeline_id = $2 AND stage_id = $3 AND deleted_at IS NULL",
            company_id, pipeline["id"], s["id"],
        )
        value = sum(float(r["value"] or 0) for r in v_rows)
        out.append({"stage_id": s["id"], "name": s["name"], "color": s["color"], "count": count, "value": round(value, 2)})
    return {"pipeline": pipeline, "stages": out}


@router.get("/revenue")
async def revenue(
    months: int = 6,
    membership: dict = Depends(get_current_company),
    conn=Depends(get_db),
):
    company_id = membership["company_id"]
    now = datetime.now(timezone.utc)
    cur = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    month_starts = []
    for _ in range(months):
        month_starts.append(cur)
        prev_last = cur - timedelta(days=1)
        cur = prev_last.replace(day=1)
    month_starts.reverse()

    out = []
    for month_start in month_starts:
        next_month = (month_start + timedelta(days=32)).replace(day=1)
        rows = await conn.fetch(
            """SELECT value, won_at FROM deals
               WHERE company_id = $1 AND deleted_at IS NULL
               AND created_at >= $2 AND created_at < $3""",
            company_id, month_start.isoformat(), next_month.isoformat(),
        )
        won = sum(float(r["value"] or 0) for r in rows if r["won_at"])
        forecast = sum(float(r["value"] or 0) for r in rows)
        out.append({
            "month": month_start.strftime("%Y-%m"),
            "label": month_start.strftime("%b/%y"),
            "won": round(won, 2),
            "forecast": round(forecast, 2),
        })
    return {"items": out}


@router.get("/leaderboard")
async def leaderboard(membership: dict = Depends(get_current_company), conn=Depends(get_db)):
    company_id = membership["company_id"]
    rows = await conn.fetch(
        """SELECT assigned_to, COUNT(*) AS deals_won, SUM(value) AS value
           FROM deals
           WHERE company_id = $1 AND deleted_at IS NULL AND won_at IS NOT NULL
           GROUP BY assigned_to
           ORDER BY SUM(value) DESC
           LIMIT 10""",
        company_id,
    )
    user_ids = [r["assigned_to"] for r in rows if r["assigned_to"]]
    users_rows = await conn.fetch(
        "SELECT id, name, avatar_url FROM users WHERE id = ANY($1)", user_ids
    ) if user_ids else []
    by_id = {u["id"]: dict(u) for u in users_rows}
    out = []
    for r in rows:
        u = by_id.get(r["assigned_to"], {"id": r["assigned_to"], "name": "—"})
        out.append({"user": u, "deals_won": r["deals_won"], "value": round(float(r["value"] or 0), 2)})
    return {"items": out}


@router.get("/activities")
async def activities_volume(
    days: int = 30,
    membership: dict = Depends(get_current_company),
    conn=Depends(get_db),
):
    rows = await conn.fetch(
        "SELECT type, COUNT(*) AS count FROM contact_activities WHERE company_id = $1 GROUP BY type",
        membership["company_id"],
    )
    return {"items": [{"type": r["type"], "count": r["count"]} for r in rows]}


@router.get("/lead-sources")
async def lead_sources(membership: dict = Depends(get_current_company), conn=Depends(get_db)):
    rows = await conn.fetch(
        """SELECT origin, COUNT(*) AS count FROM contacts
           WHERE company_id = $1 AND deleted_at IS NULL
           GROUP BY origin ORDER BY COUNT(*) DESC LIMIT 20""",
        membership["company_id"],
    )
    return {"items": [{"origin": r["origin"] or "Direto", "count": r["count"]} for r in rows]}
