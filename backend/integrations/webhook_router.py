"""Webhook ingestion router."""
from fastapi import APIRouter, Request

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.post("/{source}")
async def receive_webhook(source: str, request: Request):
    payload = await request.json()
    return {"source": source, "received": True, "keys": list(payload.keys())}
