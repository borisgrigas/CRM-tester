"""Seed demo data: 1 master + 3 sub-tenants with users, leads, deals."""
import asyncio
import os
import random
import uuid
from datetime import datetime, timezone, timedelta

from dotenv import load_dotenv

load_dotenv()

from auth_utils import hash_password  # noqa: E402
import db as _db  # noqa: E402
from db import init_pool, close_pool  # noqa: E402


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
    async with _db._pool.acquire() as conn:
        print("Cleaning demo data...")
        await conn.execute("""
            TRUNCATE TABLE password_reset_tokens, notifications, tasks, deals,
                           contact_activities, contacts, pipeline_stages, pipelines,
                           user_companies, users, companies
            RESTART IDENTITY CASCADE
        """)

        # ---------- Companies ----------
        franqueadora_id = str(uuid.uuid4())
        now = _now_iso()
        await conn.execute(
            """INSERT INTO companies (id, name, slug, plan, logo_url, settings, is_active, is_franchisor, created_at, deleted_at)
               VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10)""",
            franqueadora_id, "Franqueadora ACME", "acme", "enterprise",
            "https://images.unsplash.com/photo-1572533717789-543da73adb20?crop=entropy&cs=srgb&fm=jpg&ixid=M3w4NjA1ODR8MHwxfHNlYXJjaHwxfHxjb3Jwb3JhdGUlMjBjb21wYW55JTIwbG9nbyUyMG1pbmltYWx8ZW58MHx8fHwxNzc3ODE0NTIyfDA&ixlib=rb-4.1.0&q=85",
            {}, True, True, now, None,
        )

        unit_names = ["Unidade São Paulo", "Unidade Rio de Janeiro", "Unidade Belo Horizonte"]
        unit_ids = []
        for unit_name in unit_names:
            uid = str(uuid.uuid4())
            slug = unit_name.lower().replace(" ", "-").replace("ã", "a").replace("é", "e")
            await conn.execute(
                """INSERT INTO companies (id, name, slug, plan, logo_url, settings, is_active, is_franchisor, created_at, deleted_at)
                   VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10)""",
                uid, unit_name, slug, "pro",
                "https://images.unsplash.com/photo-1699511051588-94ee6509de71?crop=entropy&cs=srgb&fm=jpg&ixid=M3w4NjA1ODR8MHwxfHNlYXJjaHwzfHxjb3Jwb3JhdGUlMjBjb21wYW55JTIwbG9nbyUyMG1pbmltYWx8ZW58MHx8fHwxNzc3ODE0NTIyfDA&ixlib=rb-4.1.0&q=85",
                {}, True, False, now, None,
            )
            unit_ids.append(uid)

        all_company_ids = [franqueadora_id] + unit_ids

        # ---------- Master user ----------
        master_email = os.environ.get("ADMIN_EMAIL", "master@franqueadora.com")
        master_pwd = os.environ.get("ADMIN_PASSWORD", "master123")
        master_id = str(uuid.uuid4())
        await conn.execute(
            "INSERT INTO users (id, name, email, password_hash, avatar_url, created_at, deleted_at) VALUES ($1,$2,$3,$4,$5,$6,$7)",
            master_id, "Master Admin", master_email, hash_password(master_pwd),
            "https://images.unsplash.com/photo-1758691737605-69a0e78bd193?crop=entropy&cs=srgb&fm=jpg&ixid=M3w4NTYxODd8MHwxfHNlYXJjaHw0fHxtb2Rlcm4lMjBvZmZpY2UlMjB3b3JrZXIlMjBwb3J0cmFpdHxlbnwwfHx8fDE3Nzc4MTQ1MjJ8MA&ixlib=rb-4.1.0&q=85",
            now, None,
        )
        for cid in all_company_ids:
            await conn.execute(
                "INSERT INTO user_companies (user_id, company_id, role, modules, is_active, invited_at, accepted_at) VALUES ($1,$2,$3,$4,$5,$6,$7)",
                master_id, cid, "MASTER", [], True, now, now,
            )

        # ---------- Per-unit users ----------
        unit_user_pool: dict[str, list[dict]] = {}
        for unit_id in unit_ids:
            slug_row = await conn.fetchrow("SELECT slug FROM companies WHERE id = $1", unit_id)
            slug = slug_row["slug"]
            unit_users = []
            for role, suffix in [("ADMIN", "admin"), ("COMMERCIAL", "vendas"), ("COMMERCIAL", "vendas2"), ("ANALYST", "analista")]:
                email = f"{suffix}@{slug}.com"
                uid = str(uuid.uuid4())
                await conn.execute(
                    "INSERT INTO users (id, name, email, password_hash, avatar_url, created_at, deleted_at) VALUES ($1,$2,$3,$4,$5,$6,$7)",
                    uid, f"{suffix.capitalize()} {slug.split('-')[-1].capitalize()}",
                    email, hash_password("senha123"),
                    "https://images.unsplash.com/photo-1752856408620-2e6fc6ac072f?crop=entropy&cs=srgb&fm=jpg&ixid=M3w4NTYxODd8MHwxfHNlYXJjaHwyfHxtb2Rlcm4lMjBvZmZpY2UlMjB3b3JrZXIlMjBwb3J0cmFpdHxlbnwwfHx8fDE3Nzc4MTQ1MjJ8MA&ixlib=rb-4.1.0&q=85",
                    now, None,
                )
                await conn.execute(
                    "INSERT INTO user_companies (user_id, company_id, role, modules, is_active, invited_at, accepted_at) VALUES ($1,$2,$3,$4,$5,$6,$7)",
                    uid, unit_id, role, [], True, now, now,
                )
                unit_users.append({"id": uid, "role": role, "email": email})
            unit_user_pool[unit_id] = unit_users

        # ---------- Pipelines + Stages ----------
        stage_template = [
            {"name": "Novo Lead", "position": 0, "conversion_probability": 0.15, "color": "#94a3b8", "sla_hours": 24},
            {"name": "Contato Feito", "position": 1, "conversion_probability": 0.30, "color": "#3b82f6", "sla_hours": 48},
            {"name": "Proposta Enviada", "position": 2, "conversion_probability": 0.55, "color": "#8b5cf6", "sla_hours": 96},
            {"name": "Negociação", "position": 3, "conversion_probability": 0.75, "color": "#f59e0b", "sla_hours": 120},
            {"name": "Fechado Ganho", "position": 4, "conversion_probability": 1.0, "color": "#10b981", "sla_hours": 0},
            {"name": "Fechado Perdido", "position": 5, "conversion_probability": 0.0, "color": "#ef4444", "sla_hours": 0},
        ]
        pipelines_map: dict[str, dict] = {}
        for cid in all_company_ids:
            pid = str(uuid.uuid4())
            await conn.execute(
                "INSERT INTO pipelines (id, company_id, name, is_default, created_at, deleted_at) VALUES ($1,$2,$3,$4,$5,$6)",
                pid, cid, "Pipeline Comercial", True, now, None,
            )
            stages = []
            for s in stage_template:
                sid = str(uuid.uuid4())
                await conn.execute(
                    """INSERT INTO pipeline_stages
                       (id, pipeline_id, company_id, name, position, conversion_probability, color, sla_hours, created_at, deleted_at)
                       VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10)""",
                    sid, pid, cid, s["name"], s["position"],
                    s["conversion_probability"], s["color"], s["sla_hours"], now, None,
                )
                stages.append({"id": sid, "name": s["name"]})
            pipelines_map[cid] = {"pipeline_id": pid, "stages": stages}

        # ---------- Contacts + Deals + Tasks + Notifications ----------
        random.seed(42)
        total_contacts = 0
        total_deals = 0

        for unit_id in unit_ids:
            commercials = [u for u in unit_user_pool[unit_id] if u["role"] == "COMMERCIAL"]
            pipe = pipelines_map[unit_id]
            contacts_for_unit = []

            for _ in range(17):
                fn = random.choice(FIRST_NAMES)
                ln = random.choice(LAST_NAMES)
                owner = random.choice(commercials)
                contact_id = str(uuid.uuid4())
                await conn.execute(
                    """INSERT INTO contacts
                       (id, company_id, type, name, email, phone, company_name, position,
                        origin, assigned_to, custom_fields, tags, score, created_at, updated_at, deleted_at)
                       VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,$16)""",
                    contact_id, unit_id,
                    random.choices(["lead", "client"], weights=[0.75, 0.25])[0],
                    f"{fn} {ln}",
                    f"{fn.lower()}.{ln.lower()}@{random.choice(COMPANIES_DEMO).lower().replace(' ', '')}.com",
                    f"+55 11 9{random.randint(1000, 9999)}-{random.randint(1000, 9999)}",
                    random.choice(COMPANIES_DEMO),
                    random.choice(["CEO", "Diretor", "Gerente", "Coordenador", "Analista"]),
                    random.choice(ORIGINS),
                    owner["id"],
                    {}, random.sample(TAGS, k=random.randint(0, 2)),
                    random.randint(10, 90),
                    _iso_offset(-random.randint(1, 60)), _now_iso(), None,
                )
                contacts_for_unit.append({"id": contact_id, "assigned_to": owner["id"]})

            total_contacts += len(contacts_for_unit)

            stages = [s for s in pipe["stages"] if s["name"] != "Fechado Perdido"]
            for i in range(7):
                contact = random.choice(contacts_for_unit)
                stage = random.choice(stages)
                value = round(random.uniform(2000, 80000), 2)
                won = stage["name"] == "Fechado Ganho"
                deal_id = str(uuid.uuid4())
                await conn.execute(
                    """INSERT INTO deals
                       (id, company_id, contact_id, pipeline_id, stage_id, title, value,
                        expected_close_date, assigned_to, custom_fields, won_at, lost_at,
                        lost_reason, created_at, updated_at, deleted_at)
                       VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,$16)""",
                    deal_id, unit_id, contact["id"],
                    pipe["pipeline_id"], stage["id"],
                    f"Proposta #{i + 1}",
                    value,
                    _iso_offset(random.randint(5, 30))[:10],
                    contact["assigned_to"],
                    {},
                    _iso_offset(-random.randint(1, 10)) if won else None,
                    None, None,
                    _iso_offset(-random.randint(1, 30)), _now_iso(), None,
                )
                total_deals += 1

            for i in range(3):
                owner = random.choice(commercials)
                contact = random.choice(contacts_for_unit)
                await conn.execute(
                    """INSERT INTO tasks
                       (id, company_id, title, description, contact_id, deal_id, assigned_to,
                        created_by, due_date, priority, status, completed_at, created_at, updated_at)
                       VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14)""",
                    str(uuid.uuid4()), unit_id,
                    random.choice(["Ligar para o cliente", "Enviar proposta", "Agendar reunião", "Follow-up por email"]),
                    "Tarefa gerada automaticamente pelo seed.",
                    contact["id"], None, owner["id"], owner["id"],
                    _iso_offset(random.randint(1, 7))[:10],
                    random.choice(["low", "medium", "high"]),
                    "pending", None, now, now,
                )

            first_comm = commercials[0]
            await conn.execute(
                """INSERT INTO notifications
                   (id, company_id, user_id, title, body, type, entity_type, entity_id, read_at, created_at)
                   VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10)""",
                str(uuid.uuid4()), unit_id, first_comm["id"],
                "Novo lead atribuído",
                "Você recebeu um novo lead para qualificação.",
                "lead", "contact", contacts_for_unit[0]["id"], None, now,
            )

        print(f"Done. Companies: {len(all_company_ids)}, Contacts: {total_contacts}, Deals: {total_deals}")
        print(f"\nCredentials:\n  MASTER:  {master_email} / {master_pwd}")
        print("  ADMIN:   admin@unidade-sao-paulo.com / senha123")
        print("  VENDAS:  vendas@unidade-sao-paulo.com / senha123")
        print("  ANALISTA: analista@unidade-sao-paulo.com / senha123")


async def main():
    await init_pool()
    try:
        await seed()
    finally:
        await close_pool()


if __name__ == "__main__":
    asyncio.run(main())
