"""Main FastAPI app — multi-tenant CRM SaaS."""
import logging
import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv

load_dotenv()

from fastapi import APIRouter, FastAPI  # noqa: E402
from starlette.middleware.cors import CORSMiddleware  # noqa: E402

from db import apply_schema_extra, close_pool, init_pool  # noqa: E402
from integrations import webhook_router, whatsapp_router  # noqa: E402
from routers import (  # noqa: E402
    admin_router,
    analytics_router,
    auth_router,
    companies_router,
    contacts_router,
    deals_router,
    map_router,
    notifications_router,
    pipelines_router,
    tasks_router,
    users_router,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_pool()
    await apply_schema_extra()
    yield
    await close_pool()


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
api_router.include_router(map_router.router)
api_router.include_router(admin_router.router)
api_router.include_router(webhook_router.router)
api_router.include_router(whatsapp_router.router)


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
