"""Map / geolocation router."""
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from db import get_db
from deps import get_current_company

router = APIRouter(prefix="/map", tags=["map"])

_DEFAULTS = {
    "center_lat": -14.235,
    "center_lng": -51.925,
    "zoom": 4,
    "provider": "osm",
    "store_color": "#e11d48",
    "lead_color": "#2563eb",
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _settings_with_defaults(row: dict | None) -> dict:
    base = dict(_DEFAULTS)
    if row:
        base.update({k: v for k, v in row.items() if v is not None})
    return base


class MapSettingsInput(BaseModel):
    center_lat: Optional[float] = None
    center_lng: Optional[float] = None
    zoom: Optional[int] = None
    store_color: Optional[str] = None
    lead_color: Optional[str] = None


@router.get("/settings")
async def get_settings(membership: dict = Depends(get_current_company), conn=Depends(get_db)):
    row = await conn.fetchrow(
        "SELECT * FROM map_settings WHERE company_id = $1", membership["company_id"]
    )
    return _settings_with_defaults(dict(row) if row else None)


@router.put("/settings")
async def update_settings(
    payload: MapSettingsInput,
    membership: dict = Depends(get_current_company),
    conn=Depends(get_db),
):
    existing = await conn.fetchrow(
        "SELECT id FROM map_settings WHERE company_id = $1", membership["company_id"]
    )
    rid = existing["id"] if existing else str(uuid.uuid4())
    now = _now_iso()

    current = await get_settings(membership, conn)
    center_lat   = payload.center_lat   if payload.center_lat   is not None else current["center_lat"]
    center_lng   = payload.center_lng   if payload.center_lng   is not None else current["center_lng"]
    zoom         = payload.zoom         if payload.zoom         is not None else current["zoom"]
    store_color  = payload.store_color  if payload.store_color  is not None else current["store_color"]
    lead_color   = payload.lead_color   if payload.lead_color   is not None else current["lead_color"]

    await conn.execute(
        """INSERT INTO map_settings
               (id, company_id, center_lat, center_lng, zoom, store_color, lead_color, created_at, updated_at)
           VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $8)
           ON CONFLICT (company_id) DO UPDATE SET
               center_lat  = EXCLUDED.center_lat,
               center_lng  = EXCLUDED.center_lng,
               zoom        = EXCLUDED.zoom,
               store_color = EXCLUDED.store_color,
               lead_color  = EXCLUDED.lead_color,
               updated_at  = EXCLUDED.updated_at""",
        rid, membership["company_id"], center_lat, center_lng, zoom, store_color, lead_color, now,
    )
    return _settings_with_defaults({
        "center_lat": center_lat, "center_lng": center_lng, "zoom": zoom,
        "store_color": store_color, "lead_color": lead_color,
    })


@router.get("/pins")
async def get_pins(
    pin_filter: str = Query("all", alias="filter", pattern="^(all|stores|leads)$"),
    membership: dict = Depends(get_current_company),
    conn=Depends(get_db),
):
    sql = """SELECT id, name, email, phone, company_name,
                    latitude, longitude,
                    street, street_number, neighborhood, city, state, cep,
                    is_sold_store, region_interest, type
             FROM contacts
             WHERE company_id = $1 AND deleted_at IS NULL
               AND latitude IS NOT NULL AND longitude IS NOT NULL"""

    if pin_filter == "stores":
        sql += " AND is_sold_store = TRUE"
    elif pin_filter == "leads":
        sql += " AND region_interest IS NOT NULL"

    rows = await conn.fetch(sql, membership["company_id"])
    return {"pins": [dict(r) for r in rows]}


@router.get("/heatmap")
async def get_heatmap(membership: dict = Depends(get_current_company), conn=Depends(get_db)):
    rows = await conn.fetch(
        """SELECT latitude, longitude FROM contacts
           WHERE company_id = $1 AND deleted_at IS NULL
             AND latitude IS NOT NULL AND longitude IS NOT NULL""",
        membership["company_id"],
    )
    return {"points": [[r["latitude"], r["longitude"], 1.0] for r in rows]}
