"""Feature flags helpers."""


async def get_company_flags(conn, company_id: str) -> dict:
    rows = await conn.fetch(
        "SELECT name, value FROM feature_flags WHERE company_id = $1 AND is_active = TRUE",
        company_id,
    )
    return {r["name"]: r["value"] for r in rows}
