"""FastAPI dependencies for auth + multi-tenant context."""
from typing import Optional

import jwt
from fastapi import Depends, HTTPException, Request, status

from auth_utils import decode_token
from db import get_db


async def get_current_user(request: Request, db=Depends(get_db)) -> dict:
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

    user = await db.users.find_one({"id": payload["sub"]}, {"_id": 0, "password_hash": 0})
    if not user:
        raise HTTPException(status_code=401, detail="Usuário não encontrado")

    user["_jwt_company_id"] = payload.get("company_id")
    user["_jwt_role"] = payload.get("role")
    return user


async def get_current_company(user: dict = Depends(get_current_user), db=Depends(get_db)) -> dict:
    """Returns membership dict {user_id, company_id, role, ...}. Raises if user has no active company."""
    company_id = user.get("_jwt_company_id")
    if not company_id:
        raise HTTPException(status_code=400, detail="Nenhuma empresa selecionada")

    membership = await db.user_companies.find_one(
        {"user_id": user["id"], "company_id": company_id, "is_active": True},
        {"_id": 0},
    )
    if not membership:
        raise HTTPException(status_code=403, detail="Acesso negado a esta empresa")

    company = await db.companies.find_one({"id": company_id}, {"_id": 0})
    if not company or company.get("deleted_at") is not None:
        raise HTTPException(status_code=404, detail="Empresa não encontrada")
    if company.get("is_active") is False:
        raise HTTPException(status_code=403, detail="Empresa inativa")
    return membership


def require_roles(*allowed_roles: str):
    """Dependency factory: only allows users whose membership.role is in allowed_roles."""

    async def checker(membership: dict = Depends(get_current_company)) -> dict:
        if membership["role"] not in allowed_roles:
            raise HTTPException(status_code=403, detail="Permissão insuficiente")
        return membership

    return checker


async def require_master(user: dict = Depends(get_current_user), db=Depends(get_db)) -> dict:
    """For routes only a MASTER user can access."""
    membership = await db.user_companies.find_one(
        {"user_id": user["id"], "role": "MASTER", "is_active": True}, {"_id": 0}
    )
    if not membership:
        raise HTTPException(status_code=403, detail="Apenas MASTER")
    return user
