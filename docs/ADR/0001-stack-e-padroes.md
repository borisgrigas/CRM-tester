# ADR 0001: Stack e Padrões do CRM-tester

**Status:** Accepted
**Data:** 2026-05-28
**Contexto:** O sistema é um CRM SaaS multi-tenant no modelo franqueadora/franqueados, inspirado em RD Station e HubSpot. Uma franqueadora (tenant master) gerencia múltiplas unidades (sub-tenants). Cada unidade opera de forma isolada; a franqueadora tem visibilidade consolidada de todas. As decisões de stack foram tomadas para privilegiar velocidade de desenvolvimento, operação simples em containers e ausência de dependências de serviços gerenciados externos além do banco.

---

## Decisões

### Backend

- **Runtime:** Python 3.11
- **Framework:** FastAPI com ASGI (uvicorn, 2 workers em produção)
- **Driver de banco:** asyncpg (driver PostgreSQL nativo e assíncrono — sem ORM)
- **Auth:** PyJWT (HS256) + bcrypt (rounds=12); dois tokens: access (15 min) + refresh (7 dias); entregues via cookies httpOnly e no corpo da resposta
- **Esquema de params SQL:** Posicional `$1, $2, ...` (padrão asyncpg/PostgreSQL)
- **Validação de entrada:** Pydantic v2 (modelos em `models.py`)
- **Gerenciamento de conexões:** Pool asyncpg (`min_size=2`, `max_size=10`) criado no lifespan do FastAPI
- **Inicialização do schema:** DDL executado no startup via `init_pool()` (tabelas base) e `apply_schema_extra()` (schema_extra.sql); todos idempotentes
- **Codec JSONB:** Registrado globalmente no pool (`json.dumps`/`json.loads`)

### Frontend

- **Framework:** React 19 + Create React App (CRA)
- **Roteamento:** React Router v7 (`BrowserRouter`, rotas declarativas em App.js)
- **Estado global (sessão):** Zustand (`stores/authStore.js`) — user, companies, activeCompanyId, activeRole, flags, permissions
- **Estado de servidor:** React Query v5 (`@tanstack/react-query`; staleTime 30s; retry 1; sem refetch on window focus)
- **HTTP client:** axios com interceptor de auto-refresh em 401; `withCredentials: true` em todas as requisições
- **Componentes UI:** shadcn/ui (30+ componentes em `components/ui/`)
- **Drag-and-drop (Kanban):** @dnd-kit
- **Gráficos:** Recharts
- **Ícones:** @phosphor-icons/react
- **Notificações toast:** sonner
- **URL do backend:** `REACT_APP_BACKEND_URL` — variável de build-time (ARG do Dockerfile); embutida no bundle JS

### Banco de Dados

- **SGBD:** PostgreSQL 16
- **Versão:** 16 (imagem `postgres:16` no docker-compose)
- **Estratégia multi-tenant:** Single database, shared schema — campo `company_id` em todas as tabelas de dados; isolamento garantido exclusivamente pela aplicação (sem Row-Level Security, sem schemas separados)
- **Formato de IDs:** TEXT contendo UUID gerado pela aplicação via `str(uuid.uuid4())`; não há uso de `gen_random_uuid()` ou serial/sequence do banco
- **Timestamps:** Strings ISO 8601 em TEXT (não colunas `TIMESTAMP WITH TIME ZONE`); gerados com `datetime.now(timezone.utc).isoformat()` — timezone UTC
- **Foreign keys:** Não declaradas formalmente no banco; relações mantidas apenas pela lógica da aplicação
- **Soft delete:** Coluna `deleted_at TEXT` (NULL = ativo; valor ISO 8601 = deletado) nas tabelas: `users`, `companies`, `contacts`, `pipelines`, `pipeline_stages`, `deals`
- **Hard delete:** Usado em `tasks` (DELETE FROM) e na tabela `user_companies` (remoção de membership)
- **JSONB:** Usado para `custom_fields`, `tags`, `modules`, `settings`, `metadata`, `value` (feature_flags)

### Infraestrutura

- **Orquestração local:** Docker Compose (`docker-compose.yml`) com 3 serviços: `postgres`, `backend`, `frontend`; apenas para desenvolvimento
- **Produção:** Cada serviço tem seu próprio Dockerfile; deploy recomendado no Railway; sem docker-compose em produção
- **Build de produção (frontend):** Multi-stage Dockerfile: `yarn build` (CRA) → imagem final com `serve@14` servindo o diretório `build/`
- **Backend produção:** `uvicorn server:app --host 0.0.0.0 --port 8001 --workers 2` (seed nunca roda)
- **Banco em produção:** PostgreSQL gerenciado (Railway, Render) acessado via `DATABASE_URL`

---

## Consequências

### Pontos fortes
- Stack totalmente assíncrono (FastAPI + asyncpg): alta eficiência em I/O concorrente
- Schema inicializado automaticamente no startup: zero passos manuais de migração para deploy inicial
- Sem ORM: queries SQL explícitas facilitam auditoria e otimização; sem "magia" de mapeamento
- Isolamento multi-tenant simples: um campo `company_id` em todas as tabelas, sem complexidade de schemas separados
- Frontend com React Query: cache de servidor gerenciado automaticamente; sem duplicação de estado

### Limitações e o que contribuidores devem saber
- **Sem migrations formais:** O schema é recriado via DDL idempotente a cada startup. Mudanças destrutivas (DROP COLUMN, remoção de tabelas) não são gerenciadas — precisam ser aplicadas manualmente no banco de produção antes do deploy
- **Sem foreign keys no banco:** A integridade referencial depende 100% da aplicação. Registros órfãos são possíveis se a aplicação falhar entre operações compostas
- **IDs como TEXT:** UUIDs em colunas TEXT não têm validação de formato pelo banco. Joins e índices funcionam, mas sem o tipo `UUID` nativo do PostgreSQL
- **Timestamps como TEXT:** Não há garantia de formato no banco. Comparações de data usam comparação de strings (que funciona com ISO 8601 mas é frágil)
- **`REACT_APP_BACKEND_URL` é build-time:** Qualquer mudança de URL do backend exige rebuild e redeploy do frontend
- **Sem migrations:** Adicionar colunas é feito via `ALTER TABLE ... ADD COLUMN IF NOT EXISTS` no `schema_extra.sql`; esta abordagem não suporta rollback

---

## Padrões Estabelecidos

- **Nomenclatura de variáveis SQL:** Posicional `$1, $2, ...` (asyncpg)
- **Roles (hierarquia decrescente):** `MASTER > ADMIN > COMMERCIAL > ANALYST`
- **Scoping multi-tenant:** Toda query que acessa dados de negócio deve incluir `company_id = $n` no WHERE
- **Soft delete:** Coluna `deleted_at TEXT`; queries de leitura sempre filtram `deleted_at IS NULL`
- **Hard delete:** Apenas em `tasks` e na membership `user_companies`
- **Timestamps:** UTC, formato ISO 8601, tipo TEXT, gerado via `datetime.now(timezone.utc).isoformat()`
- **IDs de entidades:** TEXT contendo UUID v4 gerado pela aplicação; variável local `xid = str(uuid.uuid4())`
- **Geração de `_now_iso()`:** Função local repetida em cada router — não centralizada em módulo utilitário
- **Resposta de lista:** `{"items": [...], "total": N, "page": N, "limit": N}` (contatos, deals) ou `{"items": [...]}` (sem paginação) — não há padrão único
- **Autorização:** Dois mecanismos em uso simultâneo: (1) `require_roles()` como dependência FastAPI e (2) checks `if membership["role"] == "X": raise 403` no corpo das funções
- **Feature flags:** Registros na tabela `feature_flags` por empresa; verificação no frontend via `ModuleGuard` e `visibleModules()`; não verificadas no backend por rotas específicas
- **Permissões granulares:** Tabela `permissions` com entradas `"module:action"`; retornadas na autenticação; verificação apenas no frontend — sem enforcement no backend
- **Reset de senha / convite:** Tokens gerados e gravados no banco; e-mails não são enviados (links impressos no console)
- **Webhook sem autenticação de origem:** Endpoints públicos identificam o tenant pelo slug na URL; sem HMAC ou token de verificação
