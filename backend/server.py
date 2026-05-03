"""Main FastAPI app — multi-tenant CRM SaaS."""
import logging
import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv

load_dotenv()

from fastapi import APIRouter, Depends, FastAPI  # noqa: E402
from starlette.middleware.cors import CORSMiddleware  # noqa: E402

from db import get_client, get_db  # noqa: E402
from routers import (  # noqa: E402
    analytics_router,
    auth_router,
    companies_router,
    contacts_router,
    deals_router,
    notifications_router,
    pipelines_router,
    tasks_router,
    users_router,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    db = get_db()
    try:
        await db.users.create_index("email", unique=True)
    except Exception:
        pass
    try:
        await db.contacts.create_index([("company_id", 1), ("type", 1)])
        await db.deals.create_index([("company_id", 1), ("pipeline_id", 1), ("stage_id", 1)])
        await db.contact_activities.create_index([("contact_id", 1), ("occurred_at", -1)])
        await db.user_companies.create_index([("user_id", 1), ("company_id", 1)], unique=True)
    except Exception:
        pass
    yield
    get_client().close()


app = FastAPI(title="CRM SaaS Multi-Tenant", version="1.0.0", lifespan=lifespan)

api_router = APIRouter(prefix="/api")
api_router.include_router(auth_router.router)
api_router.include_router(contacts_router.router)
api_router.include_router(pipelines_router.router)
api_router.include_router(deals_router.router)
api_router.include_router(analytics_router.router)
api_router.include_router(companies_router.router)
api_router.include_router(users_router.router)
api_router.include_router(tasks_router.router)
api_router.include_router(notifications_router.router)


@api_router.get("/")
async def root():
    return {"message": "CRM SaaS API", "version": "1.0.0"}


app.include_router(api_router)

cors_origins = os.environ.get("CORS_ORIGINS", "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)
