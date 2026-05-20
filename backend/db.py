"""Shared PostgreSQL connection pool via asyncpg."""
import json
import os

import asyncpg

_pool: asyncpg.Pool | None = None

_CREATE_TABLES = """
CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    avatar_url TEXT,
    created_at TEXT NOT NULL,
    deleted_at TEXT
);

CREATE TABLE IF NOT EXISTS companies (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    slug TEXT NOT NULL UNIQUE,
    plan TEXT DEFAULT 'free',
    logo_url TEXT,
    settings JSONB DEFAULT '{}',
    is_active BOOLEAN DEFAULT TRUE,
    is_franchisor BOOLEAN DEFAULT FALSE,
    created_at TEXT NOT NULL,
    deleted_at TEXT
);

CREATE TABLE IF NOT EXISTS user_companies (
    user_id TEXT NOT NULL,
    company_id TEXT NOT NULL,
    role TEXT NOT NULL,
    modules JSONB DEFAULT '[]',
    is_active BOOLEAN DEFAULT TRUE,
    invited_at TEXT,
    accepted_at TEXT,
    PRIMARY KEY (user_id, company_id)
);

CREATE TABLE IF NOT EXISTS contacts (
    id TEXT PRIMARY KEY,
    company_id TEXT NOT NULL,
    type TEXT NOT NULL DEFAULT 'lead',
    name TEXT NOT NULL,
    email TEXT,
    phone TEXT,
    company_name TEXT,
    position TEXT,
    origin TEXT,
    assigned_to TEXT,
    custom_fields JSONB DEFAULT '{}',
    tags JSONB DEFAULT '[]',
    score INTEGER DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT
);

CREATE TABLE IF NOT EXISTS contact_activities (
    id TEXT PRIMARY KEY,
    company_id TEXT NOT NULL,
    contact_id TEXT NOT NULL,
    user_id TEXT,
    type TEXT NOT NULL,
    description TEXT NOT NULL,
    metadata JSONB DEFAULT '{}',
    occurred_at TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS pipelines (
    id TEXT PRIMARY KEY,
    company_id TEXT NOT NULL,
    name TEXT NOT NULL,
    is_default BOOLEAN DEFAULT FALSE,
    created_at TEXT NOT NULL,
    deleted_at TEXT
);

CREATE TABLE IF NOT EXISTS pipeline_stages (
    id TEXT PRIMARY KEY,
    pipeline_id TEXT NOT NULL,
    company_id TEXT NOT NULL,
    name TEXT NOT NULL,
    position INTEGER DEFAULT 0,
    conversion_probability FLOAT DEFAULT 0.5,
    color TEXT DEFAULT '#3b82f6',
    sla_hours INTEGER DEFAULT 72,
    created_at TEXT NOT NULL,
    deleted_at TEXT
);

CREATE TABLE IF NOT EXISTS deals (
    id TEXT PRIMARY KEY,
    company_id TEXT NOT NULL,
    contact_id TEXT,
    pipeline_id TEXT,
    stage_id TEXT,
    title TEXT NOT NULL,
    value FLOAT DEFAULT 0,
    expected_close_date TEXT,
    assigned_to TEXT,
    custom_fields JSONB DEFAULT '{}',
    won_at TEXT,
    lost_at TEXT,
    lost_reason TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT
);

CREATE TABLE IF NOT EXISTS tasks (
    id TEXT PRIMARY KEY,
    company_id TEXT NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    contact_id TEXT,
    deal_id TEXT,
    assigned_to TEXT,
    created_by TEXT,
    due_date TEXT,
    priority TEXT DEFAULT 'medium',
    status TEXT DEFAULT 'pending',
    completed_at TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS notifications (
    id TEXT PRIMARY KEY,
    company_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    title TEXT NOT NULL,
    body TEXT,
    type TEXT,
    entity_type TEXT,
    entity_id TEXT,
    read_at TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS password_reset_tokens (
    id TEXT PRIMARY KEY,
    token TEXT NOT NULL UNIQUE,
    user_id TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    used BOOLEAN DEFAULT FALSE
);

CREATE INDEX IF NOT EXISTS idx_contacts_company_type ON contacts(company_id, type);
CREATE INDEX IF NOT EXISTS idx_deals_company_pipeline_stage ON deals(company_id, pipeline_id, stage_id);
CREATE INDEX IF NOT EXISTS idx_activities_contact ON contact_activities(contact_id, occurred_at DESC);
CREATE INDEX IF NOT EXISTS idx_uc_user ON user_companies(user_id);
CREATE INDEX IF NOT EXISTS idx_uc_company ON user_companies(company_id);
"""


async def _init_conn(conn: asyncpg.Connection) -> None:
    await conn.set_type_codec("jsonb", encoder=json.dumps, decoder=json.loads, schema="pg_catalog")


async def init_pool() -> None:
    global _pool
    _pool = await asyncpg.create_pool(
        os.environ["DATABASE_URL"],
        min_size=2,
        max_size=10,
        init=_init_conn,
    )
    async with _pool.acquire() as conn:
        await conn.execute(_CREATE_TABLES)


async def close_pool() -> None:
    global _pool
    if _pool:
        await _pool.close()
        _pool = None


async def get_db():
    async with _pool.acquire() as conn:
        yield conn
