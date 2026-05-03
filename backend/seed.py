"""Seed demo data: 1 master + 3 sub-tenants with users, leads, deals."""
import asyncio
import os
import random
import uuid
from datetime import datetime, timezone, timedelta

from dotenv import load_dotenv

load_dotenv()

from auth_utils import hash_password  # noqa: E402
from db import get_client, get_db  # noqa: E402


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _iso_offset(days: int = 0) -> str:
    return (datetime.now(timezone.utc) + timedelta(days=days)).isoformat()


FIRST_NAMES = ["Ana", "Carlos", "Bruno", "Fernanda", "Lucas", "Mariana", "Rafael", "Juliana", "Pedro", "Camila",
               "Thiago", "Larissa", "Ricardo", "Beatriz", "Gabriel", "Patrícia", "Diego", "Vanessa", "Henrique", "Renata"]
LAST_NAMES = ["Silva", "Souza", "Oliveira", "Costa", "Pereira", "Rodrigues", "Almeida", "Nascimento", "Lima", "Araújo",
              "Carvalho", "Gomes", "Martins", "Rocha", "Ribeiro", "Mendes", "Barbosa", "Cardoso", "Teixeira", "Cavalcanti"]
COMPANIES_DEMO = ["TechBR", "InovaCorp", "DataLab", "Green Solutions", "Mercado Plus", "Indústria Forte", "AgroTech",
                  "Construct Pro", "FinSolutions", "EduMaster", "HealthPlus", "Logistic Now", "RetailX", "MediaWave",
                  "AutoShop", "FoodCorp", "TravelFlex", "Smart Energy", "Bio Pharma", "FashionLine"]
ORIGINS = ["Site", "Indicação", "Google Ads", "Facebook", "Instagram", "Evento", "LinkedIn", "Direto"]
TAGS = ["VIP", "Quente", "Recorrente", "Premium", "Frio", "Re-engajar", "Estratégico"]


async def seed():
    db = get_db()

    # Drop existing demo data so script is re-runnable
    print("Cleaning demo data...")
    for col in ["companies", "users", "user_companies", "contacts", "contact_activities",
                "pipelines", "pipeline_stages", "deals", "tasks", "notifications", "audit_logs",
                "password_reset_tokens"]:
        await db[col].delete_many({})

    # Indexes
    await db.users.create_index("email", unique=True)
    await db.contacts.create_index([("company_id", 1), ("type", 1)])
    await db.deals.create_index([("company_id", 1), ("pipeline_id", 1), ("stage_id", 1)])

    # ---------- Companies ----------
    franqueadora = {
        "id": str(uuid.uuid4()),
        "name": "Franqueadora ACME",
        "slug": "acme",
        "plan": "enterprise",
        "logo_url": "https://images.unsplash.com/photo-1572533717789-543da73adb20?crop=entropy&cs=srgb&fm=jpg&ixid=M3w4NjA1ODR8MHwxfHNlYXJjaHwxfHxjb3Jwb3JhdGUlMjBjb21wYW55JTIwbG9nbyUyMG1pbmltYWx8ZW58MHx8fHwxNzc3ODE0NTIyfDA&ixlib=rb-4.1.0&q=85",
        "settings": {}, "created_at": _now_iso(), "deleted_at": None,
    }
    units = []
    for unit_name in ["Unidade São Paulo", "Unidade Rio de Janeiro", "Unidade Belo Horizonte"]:
        units.append({
            "id": str(uuid.uuid4()),
            "name": unit_name,
            "slug": unit_name.lower().replace(" ", "-").replace("ã", "a"),
            "plan": "pro",
            "logo_url": "https://images.unsplash.com/photo-1699511051588-94ee6509de71?crop=entropy&cs=srgb&fm=jpg&ixid=M3w4NjA1ODR8MHwxfHNlYXJjaHwzfHxjb3Jwb3JhdGUlMjBjb21wYW55JTIwbG9nbyUyMG1pbmltYWx8ZW58MHx8fHwxNzc3ODE0NTIyfDA&ixlib=rb-4.1.0&q=85",
            "settings": {}, "created_at": _now_iso(), "deleted_at": None,
        })

    all_companies = [franqueadora, *units]
    await db.companies.insert_many([dict(c) for c in all_companies])

    # ---------- Master user ----------
    master_email = os.environ.get("ADMIN_EMAIL", "master@franqueadora.com")
    master_pwd = os.environ.get("ADMIN_PASSWORD", "master123")
    master_user = {
        "id": str(uuid.uuid4()),
        "name": "Master Admin",
        "email": master_email,
        "password_hash": hash_password(master_pwd),
        "avatar_url": "https://images.unsplash.com/photo-1758691737605-69a0e78bd193?crop=entropy&cs=srgb&fm=jpg&ixid=M3w4NTYxODd8MHwxfHNlYXJjaHw0fHxtb2Rlcm4lMjBvZmZpY2UlMjB3b3JrZXIlMjBwb3J0cmFpdHxlbnwwfHx8fDE3Nzc4MTQ1MjJ8MA&ixlib=rb-4.1.0&q=85",
        "created_at": _now_iso(), "deleted_at": None,
    }
    await db.users.insert_one(dict(master_user))
    # Master is MASTER in franqueadora and has access to all units
    memberships = [{
        "user_id": master_user["id"], "company_id": franqueadora["id"], "role": "MASTER",
        "is_active": True, "invited_at": _now_iso(), "accepted_at": _now_iso(),
    }]
    for u in units:
        memberships.append({
            "user_id": master_user["id"], "company_id": u["id"], "role": "MASTER",
            "is_active": True, "invited_at": _now_iso(), "accepted_at": _now_iso(),
        })

    # ---------- Per-unit users ----------
    unit_user_pool: dict[str, list[dict]] = {}  # company_id -> [user]
    for unit in units:
        slug = unit["slug"]
        unit_users = []
        for role, suffix in [("ADMIN", "admin"), ("COMMERCIAL", "vendas"), ("COMMERCIAL", "vendas2"), ("ANALYST", "analista")]:
            email = f"{suffix}@{slug}.com"
            u = {
                "id": str(uuid.uuid4()),
                "name": f"{suffix.capitalize()} {unit['name'].split()[-1]}",
                "email": email,
                "password_hash": hash_password("senha123"),
                "avatar_url": "https://images.unsplash.com/photo-1752856408620-2e6fc6ac072f?crop=entropy&cs=srgb&fm=jpg&ixid=M3w4NTYxODd8MHwxfHNlYXJjaHwyfHxtb2Rlcm4lMjBvZmZpY2UlMjB3b3JrZXIlMjBwb3J0cmFpdHxlbnwwfHx8fDE3Nzc4MTQ1MjJ8MA&ixlib=rb-4.1.0&q=85",
                "created_at": _now_iso(), "deleted_at": None,
            }
            await db.users.insert_one(dict(u))
            unit_users.append({**u, "role": role})
            memberships.append({
                "user_id": u["id"], "company_id": unit["id"], "role": role,
                "is_active": True, "invited_at": _now_iso(), "accepted_at": _now_iso(),
            })
        unit_user_pool[unit["id"]] = unit_users

    await db.user_companies.insert_many(memberships)

    # ---------- Pipelines + Stages per company ----------
    stage_template = [
        {"name": "Novo Lead", "position": 0, "conversion_probability": 0.15, "color": "#94a3b8", "sla_hours": 24},
        {"name": "Contato Feito", "position": 1, "conversion_probability": 0.30, "color": "#3b82f6", "sla_hours": 48},
        {"name": "Proposta Enviada", "position": 2, "conversion_probability": 0.55, "color": "#8b5cf6", "sla_hours": 96},
        {"name": "Negociação", "position": 3, "conversion_probability": 0.75, "color": "#f59e0b", "sla_hours": 120},
        {"name": "Fechado Ganho", "position": 4, "conversion_probability": 1.0, "color": "#10b981", "sla_hours": 0},
        {"name": "Fechado Perdido", "position": 5, "conversion_probability": 0.0, "color": "#ef4444", "sla_hours": 0},
    ]
    pipelines_map = {}
    for company in all_companies:
        pid = str(uuid.uuid4())
        await db.pipelines.insert_one({
            "id": pid, "company_id": company["id"], "name": "Pipeline Comercial",
            "is_default": True, "created_at": _now_iso(), "deleted_at": None,
        })
        stages = []
        for s in stage_template:
            sid = str(uuid.uuid4())
            stage = {"id": sid, "pipeline_id": pid, "company_id": company["id"], **s,
                     "created_at": _now_iso(), "deleted_at": None}
            stages.append(stage)
        await db.pipeline_stages.insert_many([dict(x) for x in stages])
        pipelines_map[company["id"]] = {"pipeline_id": pid, "stages": stages}

    # ---------- Contacts (50 across units) + 20 deals ----------
    random.seed(42)
    total_contacts = 0
    total_deals = 0
    for unit in units:
        commercials = [u for u in unit_user_pool[unit["id"]] if u["role"] == "COMMERCIAL"]
        pipe = pipelines_map[unit["id"]]
        # split 50 contacts proportionally - ~17 per unit
        contacts_for_unit = []
        for _ in range(17):
            fn = random.choice(FIRST_NAMES)
            ln = random.choice(LAST_NAMES)
            owner = random.choice(commercials)
            contact_doc = {
                "id": str(uuid.uuid4()),
                "company_id": unit["id"],
                "type": random.choices(["lead", "client"], weights=[0.75, 0.25])[0],
                "name": f"{fn} {ln}",
                "email": f"{fn.lower()}.{ln.lower()}@{random.choice(COMPANIES_DEMO).lower().replace(' ', '')}.com",
                "phone": f"+55 11 9{random.randint(1000,9999)}-{random.randint(1000,9999)}",
                "company_name": random.choice(COMPANIES_DEMO),
                "position": random.choice(["CEO", "Diretor", "Gerente", "Coordenador", "Analista"]),
                "origin": random.choice(ORIGINS),
                "score": random.randint(10, 90),
                "assigned_to": owner["id"],
                "custom_fields": {},
                "tags": random.sample(TAGS, k=random.randint(0, 2)),
                "created_at": _iso_offset(-random.randint(1, 60)),
                "updated_at": _now_iso(),
                "deleted_at": None,
            }
            contacts_for_unit.append(contact_doc)
        await db.contacts.insert_many([dict(c) for c in contacts_for_unit])
        total_contacts += len(contacts_for_unit)

        # 7 deals per unit (~21 total, close to 20)
        stages = [s for s in pipe["stages"] if s["name"] not in ("Fechado Perdido",)]
        for i in range(7):
            contact = random.choice(contacts_for_unit)
            owner_id = contact["assigned_to"]
            stage = random.choice(stages)
            value = round(random.uniform(2000, 80000), 2)
            won = stage["name"] == "Fechado Ganho"
            deal_doc = {
                "id": str(uuid.uuid4()),
                "company_id": unit["id"],
                "contact_id": contact["id"],
                "pipeline_id": pipe["pipeline_id"],
                "stage_id": stage["id"],
                "title": f"Proposta {contact['company_name']} #{i+1}",
                "value": value,
                "expected_close_date": _iso_offset(random.randint(5, 30))[:10],
                "assigned_to": owner_id,
                "won_at": _iso_offset(-random.randint(1, 10)) if won else None,
                "lost_at": None,
                "lost_reason": None,
                "custom_fields": {},
                "created_at": _iso_offset(-random.randint(1, 30)),
                "updated_at": _now_iso(),
                "deleted_at": None,
            }
            await db.deals.insert_one(dict(deal_doc))
            total_deals += 1

        # A few sample tasks per unit
        for i in range(3):
            owner = random.choice(commercials)
            await db.tasks.insert_one({
                "id": str(uuid.uuid4()),
                "company_id": unit["id"],
                "contact_id": random.choice(contacts_for_unit)["id"],
                "deal_id": None,
                "assigned_to": owner["id"],
                "created_by": owner["id"],
                "title": random.choice(["Ligar para o cliente", "Enviar proposta", "Agendar reunião", "Follow-up por email"]),
                "description": "Tarefa gerada automaticamente pelo seed.",
                "due_date": _iso_offset(random.randint(1, 7))[:10],
                "priority": random.choice(["low", "medium", "high"]),
                "status": "pending",
                "completed_at": None,
                "created_at": _now_iso(),
                "updated_at": _now_iso(),
            })

        # Notifications for first commercial
        first_comm = commercials[0]
        await db.notifications.insert_one({
            "id": str(uuid.uuid4()),
            "company_id": unit["id"],
            "user_id": first_comm["id"],
            "title": "Novo lead atribuído",
            "body": "Você recebeu um novo lead para qualificação.",
            "type": "lead",
            "entity_type": "contact",
            "entity_id": contacts_for_unit[0]["id"],
            "read_at": None,
            "created_at": _now_iso(),
        })

    print(f"Done. Companies: {len(all_companies)}, Contacts: {total_contacts}, Deals: {total_deals}")
    print(f"\nCredentials:\n  MASTER:  {master_email} / {master_pwd}")
    print("  ADMIN:   admin@unidade-sao-paulo.com / senha123")
    print("  VENDAS:  vendas@unidade-sao-paulo.com / senha123")
    print("  ANALISTA: analista@unidade-sao-paulo.com / senha123")


if __name__ == "__main__":
    asyncio.run(seed())
    get_client().close()
