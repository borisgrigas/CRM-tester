---
name: recurring-issues-f1
description: Padrões de bug recorrentes encontrados na revisão da Fase 1 do CRM
metadata:
  type: project
---

**1. ALL_MODULES desincronizado com require_module**
`models.py:ALL_MODULES` não incluía `"whatsapp"`, `"franchise"`, `"admin"` — módulos usados em `require_module()`. Resultado: `_validate_modules()` rejeita esses módulos ao convidar usuários, tornando o controle inoperante.
**Why:** Lista foi criada antes de todos os módulos serem definidos e nunca atualizada.
**How to apply:** Ao revisar features de módulo, sempre verificar se o módulo está em `ALL_MODULES`.

**2. Fallback de payload vazio sem company_id (resolvido em F1)**
`update_*` com body vazio fazia `SELECT WHERE id = $1` sem `company_id`. Padrão corrigido na F1 — agora inclui `company_id`. Verificar em novos endpoints UPDATE se o branch de payload vazio também tem scoping de tenant.

**3. complete_task / ações de patch sem 404 explícito**
`complete_task` retornava `{}` com HTTP 200 quando tarefa não encontrada, em vez de 404. Padrão correto: checar `if not row: raise HTTPException(404)` após `fetchrow` de RETURNING *.

**4. Simetria de ownership COMMERCIAL**
`update_contact` e `update_deal` verificam `assigned_to` para COMMERCIAL; `update_task` não verificava. Regra: qualquer endpoint de mutação que tenha `list_*` com filtro de COMMERCIAL deve ter verificação de ownership equivalente no UPDATE/DELETE.

**5. reset_url em logger.info com extra**
`services/email.py` loga `reset_url` (contém token) em nível INFO via `extra={}`. Dependendo do formatter, tokens podem aparecer em logs de produção.
