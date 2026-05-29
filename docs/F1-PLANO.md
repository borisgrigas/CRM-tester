# Plano F1 — Correções Críticas + Ativação da Fundação

> Elaborado por: Architect Agent  
> Data: 2026-05-28  
> Base: leitura completa de todos os routers, core/, tests/, frontend/ e AUDITORIA.md

---

## Resumo executivo

A Fase 1 resolve **8 dívidas técnicas de segurança e autorização** identificadas na auditoria F0.
As mudanças afetam **14 arquivos** no backend e **2 no frontend** (apenas lógica de guarda).
Não há mudanças de schema de banco de dados — todas as tabelas e colunas necessárias já existem.

**Riscos principais:**
1. A correção A1 (deleted_at em get_current_user) pode deslogar usuários que estiverem com tokens válidos mas `deleted_at` preenchido — comportamento correto e esperado.
2. As correções A5 e A6 (novos guards em tasks e contacts) podem quebrar os testes de integração existentes em `backend_test.py` e `test_admin_features.py` — mapeados seção a seção abaixo.
3. A substituição de `_ensure_master_anywhere` por `require_franchisor_master` (A4) muda a semântica de algumas rotas de companies — descrito detalhadamente.

**Número real de read-backs sem filtro de tenant:** 13 (não 9 como estimado). Detalhados em A2.

---

## PARTE A — Correções críticas

---

### A1. DEBT-001: filtrar deleted_at em get_current_user

**Arquivo:** `backend/deps.py` — função `get_current_user`, linhas 28–31

**Problema:** A query busca o usuário apenas por `id`, sem verificar `deleted_at IS NULL`. Um usuário soft-deletado (coluna `deleted_at` preenchida) continua conseguindo autenticar com um token JWT válido que ainda não expirou.

**Mudança na query SQL:**

```
Atual (linha 28–31):
  row = await conn.fetchrow(
      "SELECT id, name, email, avatar_url, created_at, deleted_at FROM users WHERE id = $1",
      payload["sub"],
  )
  if not row:
      raise HTTPException(status_code=401, detail="Usuário não encontrado")

Desejado:
  row = await conn.fetchrow(
      "SELECT id, name, email, avatar_url, created_at, deleted_at "
      "FROM users WHERE id = $1 AND deleted_at IS NULL",
      payload["sub"],
  )
  if not row:
      raise HTTPException(status_code=401, detail="Usuário não encontrado")
```

A coluna `deleted_at` não precisa mais ser retornada na query (seria sempre NULL), mas mantê-la não causa problema. Remover da seleção é opcional e pode ser feito na mesma iteração.

**Outros pontos que resolvem o usuário e NÃO filtram deleted_at:**

| Ponto | Arquivo | Linha | Query atual |
|-------|---------|-------|-------------|
| `POST /auth/refresh` | auth_router.py | 129–132 | `SELECT ... FROM users WHERE id = $1` — sem filtro |
| `PUT /auth/password` | auth_router.py | 249 | `SELECT password_hash FROM users WHERE id = $1` — sem filtro |
| `PUT /profile` | users_router.py | 301 | `SELECT ... FROM users WHERE id = $1` — sem filtro |

Os três pontos devem receber `AND deleted_at IS NULL` na mesma correção. O endpoint `/auth/refresh` é o mais crítico: um usuário deletado poderia renovar o token indefinidamente.

**Impacto em testes:**
- `TestAuth.test_login_master_returns_tokens_and_companies` — não é afetado (usuário ativo).
- `TestAuth.test_me_endpoint` — não é afetado.
- Nenhum teste atual cobre o cenário de usuário deletado tentando autenticar — este é um gap de teste que o test-engineer deve preencher.

---

### A2. DB-002: read-backs pós-UPDATE sem filtro de tenant

**Problema:** Após um UPDATE que filtra por `company_id`, o read-back subsequente usa apenas `WHERE id = $1`, sem repetir o filtro de tenant. Embora improvável em condições normais (o id foi gerado no contexto da empresa), esta inconsistência viola o princípio de defesa em profundidade e pode ser explorada se houver falha em outra camada (ex.: IDs previsíveis ou colisão de UUID, por mais remota que seja).

**Estratégia escolhida: RETURNING * no UPDATE**

asyncpg suporta `RETURNING *` em comandos UPDATE via `fetchrow()` (em vez de `execute()`). Esta é a abordagem preferida porque:
- Elimina a segunda round-trip ao banco.
- Garante que o objeto retornado seja exatamente o registro atualizado no contexto correto.
- Mantém o padrão de retornar o objeto completo ao caller.

**Sintaxe asyncpg:**
```python
# Troca execute() por fetchrow() e adiciona RETURNING *
row = await conn.fetchrow(
    f"UPDATE tabela SET ... WHERE id = $n AND company_id = $m RETURNING *",
    *params,
)
if not row:
    raise HTTPException(status_code=404, detail="...")
return dict(row)
```

**Endpoints afetados — 13 read-backs identificados:**

| # | Rota | Arquivo:linha | Padrão atual | Padrão desejado |
|---|------|---------------|--------------|-----------------|
| 1 | `POST /contacts` (create) | contacts_router.py:123 | INSERT + `SELECT * WHERE id = $1` | INSERT + `SELECT * WHERE id = $1 AND company_id = $2` (INSERT não tem RETURNING, mantenha SELECT mas adicione company_id) |
| 2 | `PUT /contacts/{id}` (update) | contacts_router.py:172–178 | UPDATE com company_id + `SELECT * WHERE id = $1` | UPDATE ... RETURNING * via fetchrow() |
| 3 | `POST /contacts/{id}/convert` | contacts_router.py:197–203 | UPDATE com company_id + `SELECT * WHERE id = $1` | UPDATE ... RETURNING * via fetchrow() |
| 4 | `POST /contacts/{id}/tags` (add) | contacts_router.py:217–221 | UPDATE sem company_id + `SELECT * WHERE id = $1` | UPDATE ... WHERE id = $n AND company_id = $m RETURNING * via fetchrow() |
| 5 | `DELETE /contacts/{id}/tags` (remove) | contacts_router.py:235–239 | UPDATE sem company_id + `SELECT * WHERE id = $1` | UPDATE ... WHERE id = $n AND company_id = $m RETURNING * via fetchrow() |
| 6 | `POST /contacts/{id}/activities` | contacts_router.py:284 | INSERT + `SELECT * FROM contact_activities WHERE id = $1` | INSERT + `SELECT * FROM contact_activities WHERE id = $1 AND company_id = $2` |
| 7 | `POST /deals` (create) | deals_router.py:115 | INSERT + `SELECT * FROM deals WHERE id = $1` | INSERT + `SELECT * FROM deals WHERE id = $1 AND company_id = $2` |
| 8 | `PUT /deals/{id}` (update) | deals_router.py:151–157 | UPDATE com company_id + `SELECT * WHERE id = $1` | UPDATE ... RETURNING * via fetchrow() |
| 9 | `PATCH /deals/{id}/stage` | deals_router.py:183–189 | UPDATE com company_id + `SELECT * WHERE id = $1` | UPDATE ... RETURNING * via fetchrow() |
| 10 | `POST /deals/{id}/won` | deals_router.py:204–208 | UPDATE com company_id + `SELECT * WHERE id = $1` | UPDATE ... RETURNING * via fetchrow() |
| 11 | `POST /deals/{id}/lost` | deals_router.py:222–227 | UPDATE com company_id + `SELECT * WHERE id = $1` | UPDATE ... RETURNING * via fetchrow() |
| 12 | `POST /tasks` (create) | tasks_router.py:79 | INSERT + `SELECT * FROM tasks WHERE id = $1` | INSERT + `SELECT * FROM tasks WHERE id = $1 AND company_id = $2` |
| 13 | `PUT /tasks/{id}` (update) | tasks_router.py:99–105 | UPDATE com company_id + `SELECT * WHERE id = $1` | UPDATE ... RETURNING * via fetchrow() |

**Nota sobre o item #4 e #5 (tags):** As linhas 217–219 (add_tags) e 234–236 (remove_tags) fazem o UPDATE sem company_id no WHERE — este é um bug adicional mais grave, pois o próprio UPDATE não tem escopo de tenant. O plano corrige os dois problemas de uma vez com RETURNING.

**Casos que mantêm SELECT separado (itens 1, 6, 7, 12):**
Para INSERTs, asyncpg suporta `INSERT ... RETURNING *` também. Pode-se usar a mesma abordagem `fetchrow()` com `INSERT ... RETURNING *` em vez de dois statements. Recomenda-se adotar esta forma para consistência, adicionando o filtro de company_id apenas como documentação — o INSERT já garante o company_id correto pelo valor inserido.

**Impacto em testes:**
- `TestContacts.test_create_contact_as_admin` — não deve quebrar; retorna o mesmo objeto.
- `TestPipelineAndDeals.test_move_deal_stage` — não deve quebrar.
- `TestPipelineAndDeals.test_won_and_lost_endpoints_exist` — não deve quebrar.
- `TestTasks.test_create_and_complete_task` — não deve quebrar.

---

### A3. DEBT-002: services/email.py — substituir print() por logger estruturado

**Localização dos print() atuais:**

| Print | Arquivo | Linha | Conteúdo |
|-------|---------|-------|----------|
| Reset de senha | auth_router.py | 221 | `print(f"[RESET LINK] /reset-password?token={token}")` |
| Convite de usuário | users_router.py | 157 | `print(f"[INVITE] activation link for {email}: /accept-invite?token={uuid.uuid4()}")` |

**Arquivo novo:** `backend/services/email.py`

**Interface planejada:**

```python
# backend/services/email.py

import logging

logger = logging.getLogger(__name__)

async def send_password_reset(email: str, token: str, reset_url: str) -> None:
    """
    Fase 1: log estruturado apenas.
    Fase 2: integrar com provider de e-mail (SendGrid, SES, etc.).
    """
    logger.info(
        "password_reset_requested",
        extra={"email": email, "reset_url": reset_url},
    )

async def send_invite(
    email: str,
    token: str,
    invite_url: str,
    company_name: str,
) -> None:
    """
    Fase 1: log estruturado apenas.
    """
    logger.info(
        "user_invited",
        extra={"email": email, "invite_url": invite_url, "company_name": company_name},
    )
```

**Callers que devem ser alterados:**

`auth_router.py` — função `forgot_password` (linha 221):
- Remover: `print(f"[RESET LINK] /reset-password?token={token}")`
- Adicionar import de `send_password_reset` de `services.email`
- Construir `reset_url` a partir de variável de ambiente `FRONTEND_URL` (ou hardcoded `/reset-password?token={token}` em dev)
- Chamar: `await send_password_reset(email=payload.email, token=token, reset_url=reset_url)`

`users_router.py` — função `invite_user` (linha 157):
- Remover: `print(f"[INVITE] activation link for {email}: /accept-invite?token={uuid.uuid4()}")`
- Adicionar import de `send_invite` de `services.email`
- O token de convite atual é gerado inline com `uuid.uuid4()` mas não é gravado no banco — isso significa que o link de convite não pode ser validado. Na Fase 1, gerar um token e gravá-lo ou simplesmente logar sem token real. Recomendação: gerar um token real, gravá-lo em uma tabela `invite_tokens`, e logar o URL. A tabela pode ser criada em `schema_extra.sql`.
- Chamar: `await send_invite(email=email, token=invite_token, invite_url=invite_url, company_name=membership["_company"]["name"])`

**Dependência de variável de ambiente nova:** `FRONTEND_URL` (ex: `https://crm-frontend.up.railway.app`). Deve ser adicionada à documentação de deploy.

**Impacto em testes:** Nenhum teste cobre `forgot_password` ou `invite_user` via e-mail. Os testes de invite existentes (`TestUserInvite`) testam apenas a criação do usuário e do membership, não o envio de e-mail. A mudança não quebra testes existentes.

---

### A4. DEBT-005: _ensure_master_anywhere → require_franchisor_master

**Localização de `_ensure_master_anywhere`:**
- **Definida em:** `backend/routers/companies_router.py`, linhas 24–30
- É uma função local ao módulo, não importada de deps.py

**O que cada função verifica:**

| Função | Onde está | O que verifica |
|--------|-----------|----------------|
| `_ensure_master_anywhere` | companies_router.py:24–30 | Se o usuário tem role MASTER em **qualquer** empresa (não necessariamente a ativa) |
| `require_franchisor_master` | deps.py:90–108 | Se o usuário é MASTER **e** a empresa **ativa** é a franqueadora |

As duas funções têm semânticas diferentes:
- `_ensure_master_anywhere` verifica a hierarquia global do usuário — é usada para dar acesso de leitura a dados de todas as empresas.
- `require_franchisor_master` verifica que a ação está sendo executada no contexto da franqueadora — é usada para mutações que afetam a rede.

**Rotas afetadas em companies_router.py:**

| Rota | Função atual | Análise | Dependência nova |
|------|-------------|---------|------------------|
| `GET /companies` (list_companies, linha 43–44) | `_ensure_master_anywhere` | Leitura de todas as empresas — qualquer MASTER deve poder ver. Manter `_ensure_master_anywhere`. | Manter como está |
| `POST /companies` (create_company, linha 67) | `require_franchisor_master` | Correto — mutação da rede | Manter |
| `GET /companies/consolidated` (linha 95) | `_ensure_master_or_admin_anywhere` | Leitura consolidada — MASTER ou ADMIN de qualquer empresa. Manter. | Manter como está |
| `GET /companies/{id}` (get_company, linha 141–142) | `_ensure_master_anywhere` | Leitura de empresa específica — qualquer MASTER deve poder ver. Manter. | Manter como está |
| `PUT /companies/{id}` (update_company, linha 152) | `require_franchisor_master` | Correto — mutação | Manter |
| `PATCH /companies/{id}/activate` (linha 181) | `require_franchisor_master` | Correto | Manter |
| `PATCH /companies/{id}/deactivate` (linha 191) | `require_franchisor_master` | Correto | Manter |
| `DELETE /companies/{id}` (linha 202) | `require_franchisor_master` | Correto | Manter |
| `GET /companies/{id}/users` (linha 216–217) | `_ensure_master_anywhere` | Leitura — manter. | Manter como está |

**Conclusão:** As rotas de leitura (`GET`) devem manter `_ensure_master_anywhere` porque um MASTER de uma unidade franqueada precisa ver outras unidades para gestão. As rotas de mutação já usam `require_franchisor_master` corretamente. **Não há substituição necessária** — a análise da auditoria confundiu os dois mecanismos como duplicatas quando na verdade são complementares.

**Ação real no A4:** Documentar esta distinção no código com comentários claros, e verificar se alguma rota de leitura deveria na verdade exigir `require_franchisor_master` (análise indica que não — o padrão atual é intencional).

**Impacto em testes:**
- `TestCompanies.test_companies_blocked_for_admin` — testa que admin_sp recebe 403 em `GET /companies`. Continuará passando pois `_ensure_master_anywhere` bloqueia ADMIN.
- `TestCompaniesCRUD.test_create_company_with_unique_slug` — usa master_session. Continuará passando.

---

### A5. DEBT-006/007: Guards faltando em tasks e tags

**tasks_router.py — rotas sem guard adequado:**

| Rota | Linha | Role atual | Problema | Role correto | Implementação |
|------|-------|------------|---------|--------------|---------------|
| `PUT /tasks/{task_id}` | 83–106 | Nenhum — qualquer autenticado pode atualizar qualquer tarefa da empresa | Sem restrição — ANALYST pode editar tarefas | COMMERCIAL, ADMIN, MASTER (não ANALYST) | Adicionar `if membership["role"] == "ANALYST": raise HTTPException(403, "ANALYST não pode editar tarefas")` — mesmo padrão inline usado em `update_contact` e `update_deal` |
| `PATCH /tasks/{task_id}/complete` | 109–117 | Nenhum | ANALYST pode completar tarefa | Todos exceto restrição de ownership para COMMERCIAL | COMMERCIAL pode completar apenas suas próprias tarefas; outros podem completar qualquer uma. Adicionar: `if membership["role"] == "COMMERCIAL": verificar assigned_to` |
| `DELETE /tasks/{task_id}` | 120–125 | Nenhum | ANALYST e COMMERCIAL podem deletar | ADMIN, MASTER | Adicionar `if membership["role"] not in ("MASTER", "ADMIN"): raise HTTPException(403, "Apenas ADMIN/MASTER")` — mesmo padrão de `delete_contact` e `delete_deal` |

**contacts_router.py — tags sem guard para mutações:**

| Rota | Linha | Role atual | Problema | Role correto | Implementação |
|------|-------|------------|---------|--------------|---------------|
| `POST /contacts/{id}/tags` | 207–222 | `get_current_company` — qualquer role | ANALYST pode adicionar tags (mutação) | COMMERCIAL, ADMIN, MASTER | Adicionar `if membership["role"] == "ANALYST": raise HTTPException(403, "ANALYST não pode alterar tags")` |
| `DELETE /contacts/{id}/tags` | 225–239 | `get_current_company` — qualquer role | ANALYST pode remover tags (mutação) | COMMERCIAL, ADMIN, MASTER | Idem |

**contacts_router.py — atividades sem guard para mutações:**

| Rota | Linha | Role atual | Problema |
|------|-------|------------|---------|
| `POST /contacts/{id}/activities` | 252 | `get_current_company` — qualquer role | ANALYST pode criar atividades (que alteram score do contato) |

A intenção do sistema (auditoria) lista esta rota como "Qualquer autenticado". Se ANALYST deve poder registrar atividades (ex: anotações de análise), manter assim. Se não deve, adicionar o guard. **Decisão pendente com o product owner** — o plano anota como ponto de atenção mas não impõe mudança.

**map_router.py — PUT settings sem guard:**

| Rota | Linha | Role atual | Role correto |
|------|-------|------------|--------------|
| `PUT /map/settings` | 51 | `get_current_company` — qualquer role | ADMIN, MASTER (configurações afetam todos os usuários da empresa) |

Adicionar: `if membership["role"] not in ("MASTER", "ADMIN"): raise HTTPException(403, "Apenas ADMIN/MASTER podem alterar configurações do mapa")`

**Impacto em testes:**
- `TestTasks.test_create_and_complete_task` — usa `admin_sp_session` (ADMIN). Não é afetado.
- Nenhum teste atual cobre cenários de ANALYST tentando mutar tasks. Gap de teste a ser preenchido.

---

### A6. DEBT-008: Ownership em updates COMMERCIAL

**Problema:** Um usuário COMMERCIAL pode editar contatos e deals atribuídos a outros COMMERCIAL da mesma empresa (basta saber o `id`). O filtro de ownership existe apenas nas listagens (GET), não nas mutações (PUT/PATCH).

**Estratégia recomendada: verificação inline após fetch**

Adicionar um SELECT de verificação antes do UPDATE para checar ownership:
- Buscar o registro com `id` e `company_id`.
- Se `membership["role"] == "COMMERCIAL"` e `row["assigned_to"] != membership["user_id"]`, retornar 403.
- ADMIN e MASTER podem editar qualquer registro.

Esta abordagem é preferível a adicionar `AND assigned_to = $n` no UPDATE porque:
- O UPDATE com `AND assigned_to` retornaria "UPDATE 0" tanto para "não encontrado" quanto para "não é dono" — ambíguo para o cliente.
- O SELECT separado permite diferenciar 404 (não existe) de 403 (não tem permissão), fornecendo feedback correto ao frontend.

**Rotas afetadas em contacts_router.py:**

| Rota | Linha da operação UPDATE | Verificação a adicionar |
|------|--------------------------|------------------------|
| `PUT /contacts/{contact_id}` | 172 | Antes do UPDATE dinâmico: `SELECT assigned_to FROM contacts WHERE id = $1 AND company_id = $2 AND deleted_at IS NULL`; se COMMERCIAL e `assigned_to != user_id`, raise 403 |
| `POST /contacts/{contact_id}/convert` | 197 | Mesma lógica antes do UPDATE |
| `POST /contacts/{contact_id}/tags` | 209 | O SELECT existente (linha 209) já busca a row. Aproveitar para adicionar verificação de ownership após o fetch |
| `DELETE /contacts/{contact_id}/tags` | 227 | O SELECT existente (linha 227) já busca a row. Aproveitar para adicionar verificação de ownership |

**Rotas afetadas em deals_router.py:**

| Rota | Linha | Verificação a adicionar |
|------|-------|------------------------|
| `PUT /deals/{deal_id}` | 133 | SELECT antes do UPDATE dinâmico: se COMMERCIAL e `assigned_to != user_id`, raise 403 |
| `PATCH /deals/{deal_id}/stage` | 172 | Idem |
| `POST /deals/{deal_id}/won` | 199 | Idem |
| `POST /deals/{deal_id}/lost` | 218 | Idem |

**Comportamento por role:**
- `MASTER` e `ADMIN`: podem editar qualquer registro da empresa (sem verificação de ownership).
- `COMMERCIAL`: pode editar apenas registros com `assigned_to = membership["user_id"]`.
- `ANALYST`: já bloqueado para mutações nas rotas relevantes.

**Nota:** Para as rotas de deals, será necessário também injetar `get_current_user` (ou usar `membership["user_id"]`) para obter o user_id. O dict `membership` já contém `user_id` (proveniente de `user_companies`), portanto não é necessário injetar `get_current_user` separadamente — `membership["user_id"]` é suficiente.

**Impacto em testes:**
- Nenhum teste atual testa cenário COMMERCIAL editando registro alheio. Não há risco de quebra.
- O test-engineer deve adicionar testes com `commercial_sp_session` tentando editar registro de outro COMMERCIAL.

---

## PARTE B — Ativação da fundação

---

### B1. require_module() nas rotas

**Leitura da assinatura em deps.py (linha 77–87):**

```python
def require_module(module: str):
    async def checker(membership: dict = Depends(get_current_company)) -> dict:
        modules = membership.get("modules") or []
        if modules and module not in modules:
            raise HTTPException(status_code=403, detail=f"Módulo '{module}' não permitido")
        return membership
    return checker
```

**Semântica importante:** `modules` vazio = acesso total. O guard só bloqueia quando a lista de módulos está explicitamente definida e o módulo não está nela. Isso significa que MASTER/ADMIN com `modules = []` têm acesso irrestrito — comportamento correto.

**require_module é adicional aos guards de role:** Sim. O fluxo correto é:
1. `get_current_company` valida o token e a membership.
2. `require_roles()` ou check inline valida a role.
3. `require_module()` valida se o usuário tem acesso ao módulo.

Para rotas que já têm `require_roles()`, adicionar `require_module()` como dependência extra na lista `dependencies=[...]`.

**Mapeamento de rotas por módulo:**

| Rota | Arquivo | Módulo | Nível | Como adicionar |
|------|---------|--------|-------|----------------|
| `GET /map/settings` | map_router.py | "map" | "view" | `dependencies=[Depends(require_module("map"))]` |
| `PUT /map/settings` | map_router.py | "map" | "edit" | `dependencies=[Depends(require_module("map"))]` |
| `GET /map/pins` | map_router.py | "map" | "view" | `dependencies=[Depends(require_module("map"))]` |
| `GET /map/heatmap` | map_router.py | "map" | "view" | `dependencies=[Depends(require_module("map"))]` |
| `GET /admin/flags` | admin_router.py | "admin" | "manage" | Já tem `require_roles("MASTER", "ADMIN")` — adicionar `require_module("admin")` |
| `PUT /admin/flags/{name}` | admin_router.py | "admin" | "manage" | Idem |
| `GET /admin/permissions` | admin_router.py | "admin" | "manage" | Idem |
| `PUT /admin/permissions/{user_id}` | admin_router.py | "admin" | "manage" | Idem |
| `DELETE /admin/permissions/{user_id}/{permission}` | admin_router.py | "admin" | "manage" | Idem |
| `GET /companies/consolidated` | companies_router.py | "franchise" | "view" | Adicionar `Depends(require_module("franchise"))` |
| `POST /whatsapp/send` | whatsapp_router.py | "whatsapp" | "edit" | Adicionar `Depends(require_module("whatsapp"))` |
| `GET /whatsapp/conversations` | whatsapp_router.py | "whatsapp" | "view" | Adicionar `Depends(require_module("whatsapp"))` |
| `GET /whatsapp/messages` | whatsapp_router.py | "whatsapp" | "view" | Adicionar `Depends(require_module("whatsapp"))` |

**Rotas que NÃO devem ter require_module:**
- `/auth/*`, `/webhooks/*`, `/whatsapp/inbound/*` — públicas ou de infraestrutura.
- Rotas de contatos, deals, tasks, pipelines, analytics, notifications, users — usam o sistema de roles, não de módulos. Módulos são restrições _opcionais_ configuradas por empresa, não substituem roles.

**Nota sobre o módulo "map":** O moduleRegistry.js define `flag: null` para o módulo "map", mas o ALL_MODULES do backend (`models.py`) não inclui "map" na lista. Isso significa que `require_module("map")` funcionará mesmo sem "map" estar em ALL_MODULES — a tabela `user_companies.modules` pode conter qualquer string. Para consistência, "map" deve ser adicionado ao `ALL_MODULES` em `models.py`.

---

### B2. login e /me: retornar flags + permissions

**Estado atual — SURPRESA POSITIVA:**

As rotas `POST /auth/login`, `GET /auth/me` e `POST /auth/switch-company` **já retornam `flags` e `permissions`** no payload de resposta. Isso foi implementado mas aparentemente não estava sendo consumido adequadamente pelo frontend.

Evidência:
- `auth_router.py:102–103`: `flags = await get_company_flags(conn, ...)` e `permissions = await get_user_permissions(conn, ...)`
- `auth_router.py:105–113`: ambos incluídos no retorno do login
- `auth_router.py:196–205`: `/me` também retorna ambos
- `auth_router.py:178–187`: `switch-company` também retorna ambos

**Estado do authStore.js — SURPRESA POSITIVA:**

O `authStore.js` **já tem campos `flags` e `permissions`** e já os lê corretamente das respostas do backend:
- `flags: data.flags || {}` no `setSession`, `login`, `refreshMe` e `switchCompany`
- `permissions: data.permissions || []` nos mesmos lugares
- Métodos `hasFlag(name)` e `hasPermission(perm)` já implementados

**O que ainda falta:**

1. O login não retorna `active_modules` no payload de `POST /auth/login` (linha 105–113 de auth_router.py). A rota `/auth/me` retorna `active_modules`, mas o login não. O authStore.js no método `login` faz `activeModules: data.active_modules || []` — que ficará vazio após o login inicial, só sendo preenchido no `refreshMe` ou `switchCompany`.

   **Correção:** Adicionar `active_modules` ao retorno do `POST /auth/login` em auth_router.py. A query já existe na função `_membership_modules`. Adicionar:
   ```python
   active_modules = await _membership_modules(conn, user["id"], default_company["id"])
   ```
   E incluir `"active_modules": active_modules` no dict retornado.

2. O endpoint `POST /auth/refresh` (linhas 117–146) não retorna flags, permissions ou active_modules. O refresh é usado pelo interceptor axios para renovar o token — o frontend usa o retorno apenas para atualizar o header de Authorization. Mas o authStore não é atualizado pelo refresh. Isso é aceitável porque o `refreshMe()` (chamado no Bootstrap no App.js) já faz essa atualização completa. **Não é necessário alterar o refresh.**

**Mudanças necessárias em auth_router.py:**
- Linha 81–114 (`login`): adicionar `active_modules` ao retorno.
- Sem outras mudanças — flags e permissions já funcionam.

**Impacto em testes:**
- `TestAuth.test_login_master_returns_tokens_and_companies` — passa a ter mais campos no retorno; o teste não verifica ausência de campos, portanto não quebra.

---

### B3. Frontend — ModuleGuard e moduleRegistry

**Estado atual — SURPRESA POSITIVA:**

O `ModuleGuard.jsx` já está corretamente integrado:
- Lê `activeRole` e `permissions` do `useAuthStore`.
- Usa `moduleLevel()` de `moduleRegistry.js`.
- `moduleLevel()` já implementa a lógica correta: MASTER/ADMIN recebem "manage" automaticamente; outros roles verificam as permissions granulares.

O `App.js` já aplica `ModuleGuard` nas rotas que precisam (`/whatsapp`, `/franchise`, `/map`, `/admin`).

**O que falta:**

1. **Rotas `/admin/users` e `/admin/companies` em App.js (linhas 176–193) não têm ModuleGuard.** Estas rotas usam apenas `ProtectedRoute` (qualquer usuário autenticado pode acessar a URL diretamente). COMMERCIAL e ANALYST conseguem abrir estas páginas se souberem a URL.

   Correção em App.js:
   - `/admin/users`: envolver com `<ModuleGuard module="admin" level="manage">`
   - `/admin/companies`: envolver com `<ModuleGuard module="admin" level="manage">`

2. **`moduleRegistry.js` não tem o módulo "franchise" apontando para flag "franchise" de forma consistente com o backend.** Na auditoria, o `consolidated` endpoint no backend não tem `require_module("franchise")` — após a correção B1, estará alinhado.

3. **Nenhuma verificação de role hardcoded no frontend para mover para ModuleGuard** — o frontend já usa o padrão correto de verificar pelo store. As páginas `AdminUsers.jsx` e `AdminCompanies.jsx` podem ter checks diretos de role — estes devem ser verificados pelo implementador mas não mudam a estrutura do ModuleGuard.

**Mudanças em App.js:**
- `/admin/users` (linha 175–183): adicionar `<ModuleGuard module="admin" level="manage">` envolvendo `<AdminUsers />`
- `/admin/companies` (linha 184–193): adicionar `<ModuleGuard module="admin" level="manage">` envolvendo `<AdminCompanies />`

---

### B4. Padrão único de autorização

**Estado atual — dois mecanismos em uso:**

1. `require_roles()` como `Depends()` na assinatura do decorador — usado em pipelines_router.py (todas as mutações), users_router.py (todas as mutações exceto GET), admin_router.py (todos os endpoints).

2. Check inline `if membership["role"] == "X": raise HTTPException(403, ...)` — usado em contacts_router.py, deals_router.py, tasks_router.py.

**Decisão arquitetural:**

Manter os **dois mecanismos**, mas com regras claras de quando usar cada um:

| Mecanismo | Quando usar |
|-----------|-------------|
| `require_roles()` como `Depends()` | Quando a decisão de acesso é binária e não depende do conteúdo da requisição. Ex: "somente MASTER/ADMIN pode criar pipeline". |
| Check inline | Quando a decisão depende de contexto que só existe dentro da função. Ex: "COMMERCIAL só vê seus próprios registros", "ANALYST bloqueado mas COMMERCIAL e ADMIN seguem caminhos diferentes". |

**Conversões necessárias — onde o inline deve ser convertido para Depends:**

Nenhuma conversão obrigatória nesta fase. As rotas que usam inline têm lógica diferenciada por role (não apenas um bloqueio binário), o que justifica o inline.

**Conversões OPCIONAIS para melhorar consistência:**

| Rota | Arquivo | Inline atual | Possível Depends |
|------|---------|-------------|-----------------|
| `POST /contacts` (create) | contacts_router.py:98 | `if role == "ANALYST": raise 403` | `dependencies=[Depends(require_roles("MASTER","ADMIN","COMMERCIAL"))]` |
| `POST /deals` (create) | deals_router.py:95 | `if role == "ANALYST": raise 403` | Idem |
| `POST /tasks` (create) | tasks_router.py:65 | `if role == "ANALYST": raise 403` | Idem |
| `DELETE /contacts/{id}` | contacts_router.py:184 | `if role not in ("MASTER","ADMIN"): raise 403` | `dependencies=[Depends(require_roles("MASTER","ADMIN"))]` |
| `DELETE /deals/{id}` | deals_router.py:163 | `if role not in ("MASTER","ADMIN"): raise 403` | Idem |

Estas conversões são de consistência estética — funcionalmente equivalentes. **Recomendação:** implementar junto com as correções A5/A6 para não criar mais divergência.

---

### B5. POST /api/auth/register — decisão

**Verificação:**
O endpoint `POST /api/auth/register` é referenciado no `docs/DEPLOY.md` (linhas 155–168) como forma de criar o primeiro admin em produção.

**Busca no código:** Nenhum router registra esta rota. O `auth_router.py` não tem uma função `register`. A rota não existe na aplicação.

**Decisão: REMOVER a referência do DEPLOY.md e documentar a alternativa correta.**

O fluxo de bootstrap correto é:
1. `seed.py` cria os dados iniciais em desenvolvimento (usuário master + empresas).
2. Em produção, o DEPLOY.md deve instruir o operador a conectar ao banco via Railway CLI e inserir o usuário master com `INSERT INTO users ... ` e `INSERT INTO user_companies ...` diretamente, ou usar um script de bootstrap (`bootstrap_prod.py`) que não seja parte do startup automático.

**ADR:** `docs/ADR/0002-sem-registro-publico.md` (criado separadamente abaixo).

**Mudança em docs/DEPLOY.md:**
- Remover o bloco do "Passo 8" (linhas 150–167) que referencia `POST /api/auth/register`.
- Substituir por instruções para usar Railway CLI + psql, ou um script de bootstrap manual.

---

## Riscos e ordem de implementação

### Ordem recomendada (menor risco para maior)

```
1. A3  — email.py (arquivo novo, zero risco de quebra)
2. B5  — remover /register de DEPLOY.md (apenas doc)
3. A1  — deleted_at em get_current_user + refresh + profile (segurança, baixo risco de quebra)
4. A2  — read-backs sem tenant filter (refactor interno, sem mudança de contrato)
5. A4  — documentar distinção _ensure_master_anywhere vs require_franchisor_master (sem mudança funcional)
6. B1  — require_module() nas rotas (novo guard, pode bloquear usuários com módulos restritos)
7. B2  — active_modules no login (adição de campo, retrocompatível)
8. B3  — ModuleGuard em /admin/users e /admin/companies (restrição, sem quebra para MASTER/ADMIN)
9. A5  — Guards em tasks e tags (novas restrições, pode quebrar fluxos de ANALYST/COMMERCIAL)
10. A6 — Ownership em updates COMMERCIAL (mais restritivo, requer testes de validação)
11. B4  — conversões inline → Depends (cosmético, baixo risco)
```

### Itens que podem quebrar testes existentes

| Correção | Teste em risco | Por quê |
|----------|---------------|---------|
| A5 (DELETE /tasks sem role) | `TestTasks.test_create_and_complete_task` | Não — usa ADMIN |
| A5 (PUT /tasks sem role) | Nenhum teste atual | Gap |
| A6 (ownership COMMERCIAL) | `commercial_sp_session` em TestContacts | Depende de qual contato o COMMERCIAL tenta editar |
| B1 (require_module) | Nenhum — fixtures usam MASTER/ADMIN com modules=[] | Acesso total quando modules vazio |
| B3 (/admin/users ModuleGuard) | Nenhum teste acessa /admin/users via frontend | Sem risco |

### Breaking changes

Nenhuma das mudanças altera o schema do banco ou o contrato dos endpoints (shape de request/response). Todas as mudanças são:
- Adições de campos no response (B2).
- Reforço de regras de autorização que resultam em mais respostas 403 (A5, A6, B1, B3).
- Refactoring de queries internas (A1, A2).
- Novo arquivo de serviço (A3).

---

## Arquivos que mudam

### Backend

| Arquivo | Tipo | Mudanças |
|---------|------|---------|
| `backend/deps.py` | Modificar | A1: query de `get_current_user` (linha 28–31); sem mudança nas funções require_ |
| `backend/routers/auth_router.py` | Modificar | A1: query de refresh (linha 129–132) e change_password (linha 249); A3: substituir print (linha 221) por call a email service; B2: adicionar active_modules ao retorno de login |
| `backend/routers/users_router.py` | Modificar | A1: query de update_profile (linha 301); A3: substituir print (linha 157) por call a email service |
| `backend/routers/contacts_router.py` | Modificar | A2: 6 read-backs (itens 1–6); A5: guards em add_tags e remove_tags; A6: verificações de ownership em update, convert, tags |
| `backend/routers/deals_router.py` | Modificar | A2: 5 read-backs (itens 7–11); A6: verificações de ownership em update, stage, won, lost |
| `backend/routers/tasks_router.py` | Modificar | A2: 1 read-back (item 12–13); A5: guards em update, complete, delete |
| `backend/routers/map_router.py` | Modificar | A5: guard em PUT /settings; B1: require_module("map") em todas as rotas |
| `backend/routers/admin_router.py` | Modificar | B1: require_module("admin") como dependência adicional |
| `backend/routers/companies_router.py` | Modificar | A4: adicionar comentários de documentação; sem mudança funcional |
| `backend/integrations/whatsapp_router.py` | Modificar | B1: require_module("whatsapp") em send, conversations, messages |
| `backend/models.py` | Modificar | B1: adicionar "map" ao ALL_MODULES |
| `backend/services/email.py` | Criar | A3: interface de envio de e-mail com logger estruturado |
| `docs/DEPLOY.md` | Modificar | B5: remover referência a /api/auth/register |
| `docs/ADR/0002-sem-registro-publico.md` | Criar | B5: ADR documentando a decisão |

### Frontend

| Arquivo | Tipo | Mudanças |
|---------|------|---------|
| `frontend/src/App.js` | Modificar | B3: envolver /admin/users e /admin/companies com ModuleGuard |

### Sem mudanças necessárias

| Arquivo | Motivo |
|---------|--------|
| `backend/core/feature_flags.py` | Já correto — `get_company_flags` funciona como esperado |
| `backend/core/permissions.py` | Já correto — `get_user_permissions` funciona como esperado |
| `backend/core/access_deps.py` | Apenas re-exports — sem mudança |
| `backend/deps.py` (funções require_*) | `require_roles`, `require_module`, `require_franchisor_master` estão corretos |
| `frontend/src/stores/authStore.js` | Já tem flags, permissions, hasFlag, hasPermission — não precisa de mudanças |
| `frontend/src/lib/moduleRegistry.js` | Já correto — moduleLevel() e visibleModules() funcionam |
| `frontend/src/components/ModuleGuard.jsx` | Já correto — lê do store e usa moduleLevel() |
| `frontend/src/components/ProtectedRoute.jsx` | Já correto |

---

## Divisão de trabalho

| Correção | Agente |
|----------|--------|
| A1 (deleted_at em queries de usuário) | backend-developer |
| A2 (read-backs sem tenant filter) | backend-developer |
| A3 (services/email.py) | backend-developer |
| A4 (documentar distinção _ensure_master_anywhere) | backend-developer |
| A5 (guards em tasks e tags) | backend-developer |
| A6 (ownership COMMERCIAL) | backend-developer |
| B1 (require_module nas rotas) | backend-developer |
| B2 (active_modules no login) | backend-developer |
| B3 (ModuleGuard em /admin/users e /admin/companies) | frontend-developer |
| B4 (padrão de autorização — conversões opcionais) | backend-developer |
| B5 (DEPLOY.md + ADR) | backend-developer |
| Testes de deleted_at user (gap A1) | test-engineer |
| Testes de ownership COMMERCIAL (gap A6) | test-engineer |
| Testes de ANALYST tentando mutar tasks (gap A5) | test-engineer |
| Schema para invite_tokens (dependência de A3 fase 2) | database-engineer |
