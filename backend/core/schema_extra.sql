-- Extra schema: applied after base tables in db.py
-- All statements are idempotent (IF NOT EXISTS / IF NOT EXISTS on columns).

-- Feature flags per company
CREATE TABLE IF NOT EXISTS feature_flags (
    id         TEXT PRIMARY KEY,
    company_id TEXT NOT NULL,
    name       TEXT NOT NULL,
    value      JSONB DEFAULT 'true',
    is_active  BOOLEAN DEFAULT TRUE,
    created_at TEXT NOT NULL,
    UNIQUE (company_id, name)
);

-- Granular per-user permissions inside a company
CREATE TABLE IF NOT EXISTS permissions (
    id         TEXT PRIMARY KEY,
    company_id TEXT NOT NULL,
    user_id    TEXT NOT NULL,
    permission TEXT NOT NULL,
    granted_by TEXT,
    created_at TEXT NOT NULL,
    UNIQUE (company_id, user_id, permission)
);

-- Map / geolocation settings per company
CREATE TABLE IF NOT EXISTS map_settings (
    id         TEXT PRIMARY KEY,
    company_id TEXT NOT NULL UNIQUE,
    center_lat FLOAT   DEFAULT -14.235,
    center_lng FLOAT   DEFAULT -51.925,
    zoom       INTEGER DEFAULT 4,
    provider   TEXT    DEFAULT 'google',
    api_key    TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

-- WhatsApp messages log
CREATE TABLE IF NOT EXISTS whatsapp_messages (
    id          TEXT PRIMARY KEY,
    company_id  TEXT NOT NULL,
    contact_id  TEXT,
    direction   TEXT NOT NULL,
    from_number TEXT,
    to_number   TEXT,
    body        TEXT,
    media_url   TEXT,
    status      TEXT DEFAULT 'sent',
    external_id TEXT,
    created_at  TEXT NOT NULL
);

-- Additional columns for contacts
ALTER TABLE contacts ADD COLUMN IF NOT EXISTS address         TEXT;
ALTER TABLE contacts ADD COLUMN IF NOT EXISTS latitude        FLOAT;
ALTER TABLE contacts ADD COLUMN IF NOT EXISTS longitude       FLOAT;
ALTER TABLE contacts ADD COLUMN IF NOT EXISTS whatsapp_phone  TEXT;
ALTER TABLE contacts ADD COLUMN IF NOT EXISTS cep             TEXT;
ALTER TABLE contacts ADD COLUMN IF NOT EXISTS street          TEXT;
ALTER TABLE contacts ADD COLUMN IF NOT EXISTS street_number   TEXT;
ALTER TABLE contacts ADD COLUMN IF NOT EXISTS neighborhood    TEXT;
ALTER TABLE contacts ADD COLUMN IF NOT EXISTS city            TEXT;
ALTER TABLE contacts ADD COLUMN IF NOT EXISTS state           TEXT;
ALTER TABLE contacts ADD COLUMN IF NOT EXISTS notes           TEXT;
ALTER TABLE contacts ADD COLUMN IF NOT EXISTS region_interest TEXT;
ALTER TABLE contacts ADD COLUMN IF NOT EXISTS is_sold_store   BOOLEAN DEFAULT FALSE;

-- Additional columns for users
ALTER TABLE users ADD COLUMN IF NOT EXISTS phone TEXT;
ALTER TABLE users ADD COLUMN IF NOT EXISTS cpf   TEXT;

-- Indexes for new tables
CREATE INDEX IF NOT EXISTS idx_feature_flags_company  ON feature_flags(company_id)  WHERE is_active;
CREATE INDEX IF NOT EXISTS idx_permissions_user       ON permissions(company_id, user_id);
CREATE INDEX IF NOT EXISTS idx_whatsapp_contact       ON whatsapp_messages(company_id, contact_id);

-- CPF is the universal identity: unique where not null
CREATE UNIQUE INDEX IF NOT EXISTS idx_users_cpf ON users (cpf) WHERE cpf IS NOT NULL;

-- Pin color customization per company
ALTER TABLE map_settings ADD COLUMN IF NOT EXISTS store_color TEXT DEFAULT '#e11d48';
ALTER TABLE map_settings ADD COLUMN IF NOT EXISTS lead_color  TEXT DEFAULT '#2563eb';
