"""User permissions helpers."""


async def get_user_permissions(conn, user_id: str, company_id: str) -> list[str]:
    rows = await conn.fetch(
        "SELECT permission FROM permissions WHERE user_id = $1 AND company_id = $2",
        user_id, company_id,
    )
    return [r["permission"] for r in rows]
