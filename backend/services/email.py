"""Email service — Fase 1: log estruturado. Fase 2: integrar SMTP/SendGrid."""
import logging
import os

logger = logging.getLogger(__name__)

_FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:3000")


async def send_password_reset(email: str, token: str) -> None:
    reset_url = f"{_FRONTEND_URL}/reset-password?token={token}"
    logger.info("password_reset_requested", extra={"email": email})
    logger.debug("password_reset_url", extra={"reset_url": reset_url})


async def send_invite(email: str, company_name: str) -> None:
    logger.info(
        "user_invited",
        extra={"email": email, "company_name": company_name},
    )
