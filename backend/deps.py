"""FastAPI dependencies for auth + multi-tenant context."""
from typing import Optional

import jwt
from fastapi import Depends, HTTPException, Request, status

from auth_utils import decode_token
from db import get_db


async def get_current_user(request: Request, conn=Depends(get_db)) -> dict:
    token = request.cookies.get("access_token")
    if not token:
        auth = request.headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            token = auth[7:]
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Não autenticado")
    try:
        payload = decode_token(token)
        if payload.get("type") != "access":
            raise HTTPException(status_code=401, detail="Token inválido")
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expirado")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Token inválido")

    row = await conn.fetchrow(
        "SELECT id, name, email, avatar_url, created_at, deleted_at FROM users WHERE id = $1",
        payload["sub"],
    )
    if not row:
        raise HTTPException(status_code=401, detail="Usuário não encontrado")

    user = dict(row)
    user["_jwt_company_id"] = payload.get("company_id")
    user["_jwt_role"] = payload.get("role")
    return user


async def get_current_company(user: dict = Depends(get_current_user), conn=Depends(get_db)) -> dict:
    """Returns membership dict. Raises if user has no active company or company is inactive/deleted."""
    company_id = user.get("_jwt_company_id")
    if not company_id:
        raise HTTPException(status_code=400, detail="Nenhuma empresa selecionada")

    membership_row = await conn.fetchrow(
        "SELECT * FROM user_companies WHERE user_id = $1 AND company_id = $2 AND is_active = TRUE",
        user["id"], company_id,
    )
    if not membership_row:
        raise HTTPException(status_code=403, detail="Acesso negado a esta empresa")

    company_row = await conn.fetchrow("SELECT * FROM companies WHERE id = $1", company_id)
    if not company_row or company_row["deleted_at"] is not None:
        raise HTTPException(status_code=404, detail="Empresa não encontrada")
    if not company_row["is_active"]:
        raise HTTPException(status_code=403, detail="Empresa inativa")

    membership = dict(membership_row)
    membership.setdefault("modules", [])
    membership["_company"] = dict(company_row)
    return membership


def require_roles(*allowed_roles: str):
    """Dependency factory: only allows users whose membership.role is in allowed_roles."""

    async def checker(membership: dict = Depends(get_current_company)) -> dict:
        if membership["role"] not in allowed_roles:
            raise HTTPException(status_code=403, detail="Permissão insuficiente")
        return membership

    return checker


def require_module(module: str):
    """Blocks if the membership has a modules list that does not include the requested module.
    Empty/absent list = full access."""

    async def checker(membership: dict = Depends(get_current_company)) -> dict:
        modules = membership.get("modules") or []
        if modules and module not in modules:
            raise HTTPException(status_code=403, detail=f"Módulo '{module}' não permitido")
        return membership

    return checker


async def require_franchisor_master(user: dict = Depends(get_current_user), conn=Depends(get_db)) -> dict:
    """Only MASTER users of the franchisor company may use this resource."""
    active_company_id = user.get("_jwt_company_id")
    if not active_company_id:
        raise HTTPException(status_code=400, detail="Nenhuma empresa selecionada")

    company_row = await conn.fetchrow(
        "SELECT * FROM companies WHERE id = $1 AND deleted_at IS NULL", active_company_id
    )
    if not company_row or not company_row["is_franchisor"]:
        raise HTTPException(status_code=403, detail="Apenas a franqueadora pode realizar esta ação")

    membership_row = await conn.fetchrow(
        "SELECT * FROM user_companies WHERE user_id = $1 AND company_id = $2 AND role = 'MASTER' AND is_active = TRUE",
        user["id"], active_company_id,
    )
    if not membership_row:
        raise HTTPException(status_code=403, detail="Apenas MASTER da franqueadora")
    return user


async def get_franchisor(conn) -> Optional[dict]:
    row = await conn.fetchrow("SELECT * FROM companies WHERE is_franchisor = TRUE AND deleted_at IS NULL")
    return dict(row) if row else None
