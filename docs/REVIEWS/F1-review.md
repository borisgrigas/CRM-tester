# Code Review — Fase 1

**Revisor:** code-reviewer agent
**Data:** 2026-05-29
**Base:** leitura direta de todos os arquivos modificados na F1

---

## Resumo executivo

**Aprovado com ressalvas.**
As correções críticas de segurança (DEBT-001, DEBT-002, DB-002) foram implementadas corretamente e os guards de autorização (A5, A6) cobrem os casos mapeados. Dois problemas de atenção bloqueiam commit limpo: o fallback de payload vazio em `update_contact`, `update_deal` e `update_task` ainda omite `company_id` (DEBT-012 — não resolvido), e `complete_task` não levanta 404 quando a tarefa não existe.

---

## Cobertura das correções críticas

### A1 — `deleted_at IS NULL` em pontos que resolvem usuário

| Ponto | Status | Evidência |
|---|---|---|
| `get_current_user` (deps.py:28) | CORRETO | `WHERE id = $1 AND deleted_at IS NULL` |
| `refresh` (auth_router.py:133) | CORRETO | `WHERE id = $1 AND deleted_at IS NULL` |
| `change_password` (auth_router.py:252) | CORRETO | `WHERE id = $1 AND deleted_at IS NULL` |
| `update_profile` (users_router.py:302) | CORRETO | SELECT de read-back filtra `AND deleted_at IS NULL` |

**Resultado: CORRETO**

---

### A2 — Read-backs pós-mutação com `company_id` no WHERE ou `RETURNING *`

| Endpoint | Arquivo:linha | Status | Evidência |
|---|---|---|---|
| `create_contact` | contacts_router.py:123 | CORRETO | `SELECT * FROM contacts WHERE id = $1 AND company_id = $2` |
| `update_contact` (mutação) | contacts_router.py:189 | CORRETO | `RETURNING *` com `company_id` no WHERE do UPDATE |
| `add_tags` | contacts_router.py:236 | CORRETO | `RETURNING *` com `company_id` no WHERE |
| `remove_tags` | contacts_router.py:257 | CORRETO | `RETURNING *` com `company_id` no WHERE |
| `convert_to_client` | contacts_router.py:213 | CORRETO | `RETURNING *` com `company_id` no WHERE |
| `create_deal` | deals_router.py:115 | CORRETO | `SELECT * FROM deals WHERE id = $1 AND company_id = $2` |
| `update_deal` (mutação) | deals_router.py:168 | CORRETO | `RETURNING *` com `company_id` no WHERE do UPDATE |
| `move_stage` | deals_router.py:205/210 | CORRETO | `RETURNING *` com `company_id` no WHERE |
| `mark_won` | deals_router.py:241 | CORRETO | `RETURNING *` com `company_id` no WHERE |
| `mark_lost` | deals_router.py:272 | CORRETO | `RETURNING *` com `company_id` no WHERE |
| `create_task` | tasks_router.py:79 | CORRETO | `SELECT * FROM tasks WHERE id = $1 AND company_id = $2` |
| `update_task` (mutação) | tasks_router.py:109 | CORRETO | `RETURNING *` com `company_id` no WHERE |
| `complete_task` | tasks_router.py:123 | CORRETO | `RETURNING *` com `company_id` no WHERE |
| `add_activity` | contacts_router.py:304 | CORRETO | `SELECT * FROM contact_activities WHERE id = $1 AND company_id = $2` |

**Resultado: CORRETO**

---

### A3 — Remoção de `print()` com tokens sensíveis

| Ponto | Status | Evidência |
|---|---|---|
| `auth_router.py` | CORRETO | Nenhum `print()` encontrado no arquivo |
| `users_router.py` | CORRETO | Nenhum `print()` encontrado no arquivo |
| `services/email.py` criado | CORRETO | Usa `logger.info()` com nível INFO e `extra={}` estruturado |

Obs: `seed.py` ainda contém `print()` com credenciais demo, mas esse arquivo é explicitamente de seed local e não rota de produção — aceitável fora do escopo desta fase.

**Resultado: CORRETO**

---

### A4 — Distinção `_ensure_master_anywhere` vs `require_franchisor_master` documentada

| Ponto | Status | Evidência |
|---|---|---|
| Comentário em companies_router.py | CORRETO | Linhas 14–18: distingue claramente uso em GETs vs mutações |
| Mutações usam `require_franchisor_master` | CORRETO | POST, PUT, PATCH, DELETE todos usam `Depends(require_franchisor_master)` |
| GETs usam `_ensure_master_anywhere` | CORRETO | `list_companies`, `get_company`, `company_users` |

**Resultado: CORRETO** (nota: DEBT-005 — escalonamento cross-tenant via `_ensure_master_anywhere` é problema residual documentado, intencionalmente fora do escopo desta fase)

---

### A5 — Guards de role em `tasks_router.py` e `contacts_router.py` (tags)

| Endpoint | Status | Evidência |
|---|---|---|
| `PUT /tasks/{id}` | CORRETO | `if membership["role"] == "ANALYST": raise 403` em tasks_router.py:88 |
| `PATCH /tasks/{id}/complete` | CORRETO | Guard de ANALYST em tasks_router.py:119 |
| `DELETE /tasks/{id}` | CORRETO | `if membership["role"] not in ("MASTER", "ADMIN"): raise 403` em tasks_router.py:131 |
| `POST /contacts/{id}/tags` | CORRETO | Guard ANALYST + COMMERCIAL ownership em contacts_router.py:223 e 231 |
| `DELETE /contacts/{id}/tags` | CORRETO | Guard ANALYST + COMMERCIAL ownership em contacts_router.py:244 e 252 |

**Resultado: CORRETO**

---

### A6 — Ownership COMMERCIAL verificado antes de mutações em contacts e deals

| Endpoint | Status | Evidência |
|---|---|---|
| `PUT /contacts/{id}` | CORRETO | contacts_router.py:169–177: busca `assigned_to`, compara com `membership["user_id"]` |
| `PUT /deals/{id}` | CORRETO | deals_router.py:148–156: mesma lógica |
| `PATCH /deals/{id}/stage` | CORRETO | deals_router.py:193–200 |
| `POST /deals/{id}/won` | CORRETO | deals_router.py:229–237 |
| `POST /deals/{id}/lost` | CORRETO | deals_router.py:261–268 |

**Resultado: CORRETO**

---

### B1 — `require_module` ativo nos roteadores corretos

| Router | Módulo | Status | Evidência |
|---|---|---|---|
| `map_router.py` | `"map"` | CORRETO | Aplicado no `APIRouter(..., dependencies=[Depends(require_module("map"))])` |
| `admin_router.py` | `"admin"` | CORRETO | Aplicado por rota individual em cada endpoint (`/flags`, `/permissions`) |
| `companies_router.py` (consolidated) | `"franchise"` | CORRETO | `@router.get("/consolidated", dependencies=[Depends(require_module("franchise"))])` |
| `whatsapp_router.py` (/send, /conversations, /messages) | `"whatsapp"` | CORRETO | Cada rota autenticada tem `dependencies=[Depends(require_module("whatsapp"))]` |

**Resultado: CORRETO**

---

### B2 — `active_modules` no retorno de `POST /auth/login`

| Ponto | Status | Evidência |
|---|---|---|
| Login retorna `active_modules` | CORRETO | auth_router.py:116: `"active_modules": active_modules` |
| `/auth/me` retorna `active_modules` | CORRETO | auth_router.py:206 |
| `/auth/switch-company` retorna `active_modules` | CORRETO | auth_router.py:187 |

**Resultado: CORRETO**

---

### B3 — `ModuleGuard` em `/admin/users` e `/admin/companies` no frontend

| Rota | Status | Evidência |
|---|---|---|
| `/admin` | CORRETO | App.js:167: `<ModuleGuard module="admin" level="manage">` |
| `/admin/users` | CORRETO | App.js:179: `<ModuleGuard module="admin" level="manage">` |
| `/admin/companies` | CORRETO | App.js:191: `<ModuleGuard module="admin" level="manage">` |
| `/whatsapp` | CORRETO | App.js:131: `<ModuleGuard module="whatsapp" level="view">` |
| `/franchise` | CORRETO | App.js:143: `<ModuleGuard module="franchise" level="view">` |
| `/map` | CORRETO | App.js:155: `<ModuleGuard module="map">` |

**Resultado: CORRETO**

---

## Consistência do padrão de autorização

**O que está bem:**
- `require_roles()` como `Depends` é usado corretamente em todas as rotas de `users_router.py` que exigem MASTER/ADMIN.
- Os checks inline `if role == X: raise 403` são usados coerentemente para lógica diferenciada dentro de rotas (ANALYST bloqueado, COMMERCIAL verificado por ownership).
- `require_module` é aplicado no nível do router (map) quando todo o router requer o módulo, e no nível de rota individual (admin, whatsapp) quando apenas algumas rotas precisam — padrão consistente.
- `require_franchisor_master` está corretamente restrito a mutações em companies.

**O que ainda é inconsistente:**

1. `update_task` bloqueia ANALYST mas não verifica ownership de COMMERCIAL. Diferente de `update_contact` e `update_deal` que verificam `assigned_to` para COMMERCIAL. Um COMMERCIAL pode editar tarefas de outros membros da empresa se souber o UUID.

2. `complete_task` não retorna 404 quando a tarefa não é encontrada (linha 126): `return dict(row) if row else {}` retorna `{}` com HTTP 200. Todos os outros endpoints equivalentes (update_contact, update_deal) levantam `HTTPException(404)`.

3. O fallback de payload vazio em `update_contact` (linha 162–167), `update_deal` (linha 141–146) e `update_task` (linha 93–97) faz `SELECT ... WHERE id = $1 AND company_id = $2` — o `company_id` está presente nesses três casos. **DEBT-012 foi parcialmente resolvido**: as queries de fallback incluem `company_id`. Porém nenhum deles retorna 422 para body vazio — aceitam silenciosamente e retornam o registro atual. Não é erro, mas é contrato de API ambíguo.

---

## Problemas encontrados

| ID | Severidade | Arquivo:linha | Descrição | Recomendação |
|---|---|---|---|---|
| R1 | **Critico** | tasks_router.py:126 | `complete_task` retorna `{}` com HTTP 200 quando a tarefa não existe. Todos os outros endpoints similares levantam 404. Além de inconsistência, permite que um COMMERCIAL complete tarefas alheias silenciosamente (o UPDATE não afeta nenhuma linha, retorna `None`, e o código retorna sucesso). | Substituir `return dict(row) if row else {}` por `if not row: raise HTTPException(status_code=404, detail="Tarefa não encontrada")` seguido de `return dict(row)` |
| R2 | **Atenção** | tasks_router.py:87–113 | `update_task` bloqueia ANALYST mas não verifica ownership de COMMERCIAL. Quebra a simetria com `update_contact` e `update_deal` que têm verificação de `assigned_to` para COMMERCIAL. | Adicionar após o bloco de `if not update:`, antes do UPDATE SQL, a mesma lógica de ownership de COMMERCIAL presente em `update_contact` (linhas 169–177) |
| R3 | **Atenção** | models.py:47–57 | `ALL_MODULES` não inclui `"whatsapp"`, `"franchise"` e `"admin"` — módulos usados em `require_module()`. `_validate_modules()` em `users_router.py` rejeita qualquer módulo fora da lista. Um admin não consegue atribuir os módulos `whatsapp`, `franchise` ou `admin` a um usuário via API, tornando o controle de acesso por módulo inoperante nesses casos. | Adicionar `"whatsapp"`, `"franchise"` e `"admin"` a `ALL_MODULES` em `models.py` |
| R4 | **Sugestao** | services/email.py:11–15 | `reset_url` com o token é logada em nível INFO com `extra={"reset_url": reset_url}`. Dependendo do formatter do logger, `extra` pode aparecer na linha de log completa em produção, reintroduzindo o problema do DEBT-002 via log. | Logar apenas `email` no nível INFO; logar `reset_url` em DEBUG (`logger.debug(...)`) ou não logar a URL em produção. Verificar o formatter configurado em `server.py`. |

---

## Issues residuais (próxima fase)

Os três itens abaixo são os mais impactantes dentre os não endereçados na F1:

**1. DEBT-005 — `_ensure_master_anywhere` permite escalonamento de privilégio cross-tenant (HIGH)**
`list_companies`, `get_company` e `company_users` aceitam qualquer MASTER de qualquer empresa. Um MASTER da Empresa A lê dados de todas as empresas da rede. A dependência `require_franchisor_master` já existe e está pronta — é substituição direta, mas muda o comportamento intencional para GETs, exigindo alinhamento de produto.

**2. DEBT-012 — Fallback de payload vazio sem 422 (MEDIUM)**
`update_contact`, `update_deal` e `update_task` aceitam PUT com body completamente vazio e retornam o registro atual com HTTP 200. Embora o `company_id` esteja presente (isolamento OK), o contrato de API é ambíguo. Deveria retornar HTTP 422 com mensagem clara.

**3. DB-012 — Multi-step writes sem transação (HIGH)**
`create_deal`, `move_stage`, `mark_won`, `mark_lost` e `add_activity` executam múltiplas escritas relacionadas sem `BEGIN/COMMIT`. Uma falha entre os `execute()` deixa estado inconsistente (ex.: deal salvo, score do contato não atualizado). Correção: envolver em `async with conn.transaction():`.

---

## Veredicto

**Pode commitar com ressalvas.**

O problema R1 (`complete_task` retornando sucesso falso para tarefa inexistente) é um bug de comportamento que pode mascarar falhas de autorização silenciosas para COMMERCIAL — recomendo corrigir antes do commit. R3 (`ALL_MODULES` incompleto) é bloqueante para o funcionamento real do controle de módulos em produção, pois impede que `whatsapp`, `franchise` e `admin` sejam atribuídos a usuários via convite.

R2 e R4 podem ir como follow-up imediato mas não bloqueiam este commit se houver pressão de tempo.
