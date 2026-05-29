# Inventário de Dívida Técnica — CRM SaaS

> Fase 0 — Auditoria (2026-05-28)
> Fontes: code-reviewer (DEBT-001–020) + database-engineer (DB-001–018)
> Ordenado por: Severidade DESC, Esforço ASC

---

## Legenda

| Campo | Valores |
|---|---|
| Severidade | CRITICAL / HIGH / MEDIUM / LOW |
| Esforço | XS (<1h) / S (<4h) / M (<1d) / L (<3d) / XL (1sem+) |
| Categoria | Security / Authorization / Data Integrity / Schema / Query / Transaction / Code Quality / Observability / Connection / Multi-tenancy |

---

## CRITICAL

---

### DEBT-001 — Usuários soft-deleted conseguem se autenticar
| Campo | Valor |
|---|---|
| ID | DEBT-001 |
| Categoria | Security |
| Severidade | CRITICAL |
| Esforço | XS |
| Arquivo | `backend/deps.py:28–33` |

**Descrição:** `get_current_user` busca o registro do usuário mas nunca verifica se `deleted_at IS NOT NULL`. Um usuário com conta desativada mantém tokens JWT válidos e pode fazer requisições autenticadas indefinidamente até o token expirar.

**Recomendação:** Após o `fetchrow`, adicionar verificação explícita: se `user["deleted_at"] is not None`, lançar HTTP 401. Deve estar em `get_current_user`, não nas rotas downstream.

---

### DEBT-002 — Tokens sensíveis escritos em stdout via print()
| Campo | Valor |
|---|---|
| ID | DEBT-002 |
| Categoria | Security |
| Severidade | CRITICAL |
| Esforço | S |
| Arquivo | `backend/routers/auth_router.py:221`, `backend/routers/users_router.py:157` |

**Descrição:** Tokens de reset de senha e convite de usuário são emitidos com `print()` em vez de um mecanismo de entrega real. Em produção aparecem nos logs da aplicação (stdout/stderr), visíveis a ferramentas de log aggregation e staff de operações. O token de reset concede capacidade total de troca de senha; o token de convite concede acesso à conta.

**Recomendação:** Remover ambos os `print()`. Substituir por serviço de e-mail transacional (SMTP, SendGrid, etc.) por trás de uma abstração. Até que o e-mail esteja pronto, logar em nível DEBUG com logger estruturado para que o token nunca apareça em logs INFO/WARNING.

---

### DB-002 — Read-back pós-update sem filtro de tenant (9 endpoints)
| Campo | Valor |
|---|---|
| ID | DB-002 |
| Categoria | Multi-tenancy |
| Severidade | CRITICAL |
| Esforço | S |
| Arquivo | `backend/routers/contacts_router.py:178`, `deals_router.py:157`, `tasks_router.py:105`, e outros 6 |

**Descrição:** Após executar UPDATE com `company_id` no WHERE, o SELECT de confirmação faz `SELECT * FROM tabela WHERE id = $1` — sem `company_id`. Um atacante que descubra um UUID de outro tenant pode ler dados alheios pelo read-back. Afeta 9 endpoints: `update_contact`, `update_deal`, `add_tags`, `remove_tags`, `move_stage`, `mark_won`, `mark_lost`, `complete_task`, `update_task`, `add_activity`.

**Recomendação:** Sempre incluir `AND company_id = $n` no SELECT de read-back pós-escrita. Revisar todos os `fetchrow` sem `company_id` que ocorrem após uma mutação.

---

### DB-003 — Ausência de RLS — isolamento de tenant depende exclusivamente da aplicação
| Campo | Valor |
|---|---|
| ID | DB-003 |
| Categoria | Multi-tenancy |
| Severidade | CRITICAL |
| Esforço | M |
| Arquivo | `backend/db.py:34–43` |

**Descrição:** Nenhuma política de Row-Level Security está configurada em nenhuma tabela. Toda a separação de tenant é feita por `WHERE company_id = $1` no código Python. Um bug em qualquer endpoint (como DB-002) vaza dados cross-tenant imediatamente e sem barreiras de segurança no banco.

**Recomendação:** Habilitar RLS em todas as tabelas de dados de tenant. Criar policy que compare `company_id` com `current_setting('app.current_company_id')`. Pode ser feita incrementalmente como defesa em profundidade, sem bloquear outras entregas.

---

### DB-004 — Ausência de FK constraints em todas as relações inter-tabelas
| Campo | Valor |
|---|---|
| ID | DB-004 |
| Categoria | Schema |
| Severidade | CRITICAL |
| Esforço | S |
| Arquivo | `backend/db.py:34–160` |

**Descrição:** Nenhuma das relações entre tabelas possui `FOREIGN KEY` declarada no DDL. Isso inclui `user_companies → users/companies`, `contacts → companies`, `deals → pipeline_stages`, `tasks → contacts/deals`, `notifications → users`, entre outros. Dados órfãos se acumulam silenciosamente. O `TRUNCATE ... CASCADE` do seed.py passa sem erro pois não há FKs reais para cascatear.

**Recomendação:** Adicionar `FOREIGN KEY` com `ON DELETE RESTRICT` (relações com soft-delete) ou `ON DELETE CASCADE` (registros filhos). Verificar dados órfãos existentes antes de aplicar. Iniciar pelas relações de maior risco: `user_companies → users/companies`, `deals → pipeline_stages`.

---

## HIGH

---

### DEBT-003 — Senha padrão "changeme123" hardcoded no modelo UserInvite
| Campo | Valor |
|---|---|
| ID | DEBT-003 |
| Categoria | Security |
| Severidade | HIGH |
| Esforço | S |
| Arquivo | `backend/models.py:63` |

**Descrição:** `UserInvite.password` tem valor padrão `"changeme123"`. Se um admin omitir o campo senha ao convidar um usuário, a conta é criada com credencial bem conhecida. Sem mecanismo de "troca obrigatória no primeiro login", contas podem permanecer permanentemente expostas.

**Recomendação:** Remover o default. Tornar `password Optional[str] = None` e gerar senha temporária criptograficamente aleatória no servidor (entregue com segurança) ou exigir o campo. Adicionar flag `password_must_change` à tabela `users`.

---

### DEBT-004 — Sem rate limiting nos endpoints de autenticação
| Campo | Valor |
|---|---|
| ID | DEBT-004 |
| Categoria | Security |
| Severidade | HIGH |
| Esforço | S |
| Arquivo | `backend/routers/auth_router.py` (login + forgot-password) |

**Descrição:** `/auth/login` e `/auth/forgot-password` aceitam requisições ilimitadas por IP e por conta. Sem throttling, sem bloqueio temporário, sem CAPTCHA. Ataques de credential stuffing e brute-force de senha são trivialmente viáveis em produção.

**Recomendação:** Adicionar `slowapi` (ou equivalente): ex. 5 tentativas/min por IP no `/login`, 3/hora por e-mail no `/forgot-password`. Considerar bloqueio temporário com back-off exponencial após falhas repetidas na mesma conta.

---

### DEBT-005 — _ensure_master_anywhere permite escalonamento de privilégio cross-tenant
| Campo | Valor |
|---|---|
| ID | DEBT-005 |
| Categoria | Authorization |
| Severidade | HIGH |
| Esforço | M |
| Arquivo | `backend/routers/companies_router.py:24–44` |

**Descrição:** `list_companies`, `get_company` e `company_users` usam `_ensure_master_anywhere`, que apenas verifica que o usuário possui MASTER em *qualquer* empresa. Um usuário MASTER na Empresa A pode listar todas as empresas e ler todos os seus usuários — incluindo empresas em que não tem membership. Violação de isolamento de tenant na API inteira de companies.

**Recomendação:** Substituir `_ensure_master_anywhere` por `require_franchisor_master` (que já existe em `deps.py` e verifica MASTER especificamente na franqueadora). Esta dependência já está implementada e pronta para uso.

---

### DEBT-006 — update_task e delete_task sem verificação de role
| Campo | Valor |
|---|---|
| ID | DEBT-006 |
| Categoria | Authorization |
| Severidade | HIGH |
| Esforço | XS |
| Arquivo | `backend/routers/tasks_router.py:83–106, 120–125` |

**Descrição:** `PUT /tasks/{task_id}` permite que qualquer usuário autenticado — incluindo ANALYST — atualize campos da tarefa (título, descrição, assigned_to, priority, status). `DELETE /tasks/{task_id}` também não tem restrição de role. ANALYST deveria ser somente-leitura.

**Recomendação:** Adicionar bloqueio de ANALYST em `update_task` (consistente com contacts e deals). Para delete, restringir a MASTER/ADMIN como feito em `contacts_router` e `deals_router`.

---

### DEBT-007 — add_tags e remove_tags sem verificação de role
| Campo | Valor |
|---|---|
| ID | DEBT-007 |
| Categoria | Authorization |
| Severidade | HIGH |
| Esforço | XS |
| Arquivo | `backend/routers/contacts_router.py:207–222, 225–240` |

**Descrição:** `POST /{contact_id}/tags` e `DELETE /{contact_id}/tags` realizam mutações mas nenhum dos dois verifica o role do usuário. ANALYST pode adicionar ou remover tags de qualquer contato da empresa.

**Recomendação:** Adicionar o mesmo guard de ANALYST usado em `update_contact`: `if membership["role"] == "ANALYST": raise HTTP 403`.

---

### DEBT-008 — COMMERCIAL pode atualizar registros de outros usuários via update_contact/update_deal
| Campo | Valor |
|---|---|
| ID | DEBT-008 |
| Categoria | Authorization |
| Severidade | HIGH |
| Esforço | S |
| Arquivo | `backend/routers/contacts_router.py:158–179`, `deals_router.py:137–158` |

**Descrição:** `list_contacts` e `list_deals` corretamente filtram COMMERCIAL para seus próprios registros. Porém, `update_contact` e `update_deal` não repetem esse escopo — o WHERE verifica apenas `id AND company_id`. Um usuário COMMERCIAL que descubra um UUID alheio (via feed de atividades, deal compartilhado, etc.) pode fazer PUT nele.

**Recomendação:** Em `update_contact` e `update_deal`, adicionar condição `AND assigned_to = $x` quando o role for COMMERCIAL, espelhando a lógica de listagem. Ou buscar o registro primeiro e verificar ownership antes de prosseguir.

---

### DB-005 — Tabela tasks sem deleted_at — deleção física sem auditoria
| Campo | Valor |
|---|---|
| ID | DB-005 |
| Categoria | Schema |
| Severidade | HIGH |
| Esforço | S |
| Arquivo | `backend/db.py:117–132` |

**Descrição:** `tasks` usa `DELETE` físico (`tasks_router.py:122`). Todos os outros recursos principais (contacts, deals, pipelines) usam soft delete com `deleted_at`. Tasks deletadas não aparecem em auditorias, relatórios históricos ou logs de atividade.

**Recomendação:** Adicionar `deleted_at TEXT` (futuro TIMESTAMPTZ) à tabela `tasks` e converter o DELETE para `UPDATE SET deleted_at = now()`. Filtrar `deleted_at IS NULL` nas queries de listagem.

---

### DB-006 — N+1 no endpoint /analytics/funnel
| Campo | Valor |
|---|---|
| ID | DB-006 |
| Categoria | Query |
| Severidade | HIGH |
| Esforço | S |
| Arquivo | `backend/routers/analytics_router.py:113–123` |

**Descrição:** O endpoint `funnel` itera sobre stages e, para cada um, executa dois SELECTs separados (COUNT e SELECT value). Com pipeline de 6 stages são 12 queries individuais. O padrão N+1 também ocorre em `companies_router.py` — 3 COUNT queries por empresa em loop.

**Recomendação:** Substituir o loop por query única: `SELECT stage_id, COUNT(*), SUM(value) FROM deals WHERE … GROUP BY stage_id`. Para companies, usar lateral join ou CTE para calcular contagens de todas as empresas em uma query.

---

### DB-007 — N+1 no endpoint /analytics/revenue
| Campo | Valor |
|---|---|
| ID | DB-007 |
| Categoria | Query |
| Severidade | HIGH |
| Esforço | S |
| Arquivo | `backend/routers/analytics_router.py:144–158` |

**Descrição:** O endpoint `revenue` executa uma query por mês em loop Python (padrão 6 iterações). Cada iteração faz SELECT com range de datas. São 6+ queries sequenciais por request.

**Recomendação:** Substituir por query única com `DATE_TRUNC('month', created_at::timestamptz) GROUP BY mês`. Requer a conversão de `created_at` para TIMESTAMPTZ (DB-001).

---

### DB-008 — Agregações de valor calculadas em memória Python em vez de SUM no banco
| Campo | Valor |
|---|---|
| ID | DB-008 |
| Categoria | Query |
| Severidade | HIGH |
| Esforço | S |
| Arquivo | `backend/routers/analytics_router.py:51–53` |

**Descrição:** Em `/analytics/overview`, a query `SELECT value, won_at FROM deals WHERE …` retorna todas as linhas para o Python somar com `sum(float(r["value"]))`. Em produção com milhares de deals, trafega e processa dados desnecessários. Mesmo padrão em `revenue` e `funnel`.

**Recomendação:** Substituir por `SELECT SUM(value), SUM(CASE WHEN won_at IS NOT NULL THEN value ELSE 0 END) FROM deals WHERE …` diretamente no banco.

---

### DB-009 — Índices ausentes em colunas de filtro de alta frequência
| Campo | Valor |
|---|---|
| ID | DB-009 |
| Categoria | Index |
| Severidade | HIGH |
| Esforço | S |
| Arquivo | `backend/db.py:155–159` |

**Descrição:** Colunas usadas em WHERE com alta frequência sem índice: `contacts.assigned_to` (filtrado em todo `list_contacts` para role COMMERCIAL), `contacts.deleted_at`, `deals.assigned_to`, `deals.deleted_at`, `tasks.company_id + status + due_date`, `deals.won_at`, `contact_activities.company_id`, `notifications.company_id + user_id`.

**Recomendação:** Criar índices parciais e compostos: `idx_contacts_assigned ON contacts(company_id, assigned_to) WHERE deleted_at IS NULL`; `idx_deals_assigned ON deals(company_id, assigned_to) WHERE deleted_at IS NULL`; `idx_tasks_company_status ON tasks(company_id, status, due_date)`; `idx_deals_won ON deals(company_id, won_at) WHERE won_at IS NOT NULL`; `idx_notifications_user ON notifications(company_id, user_id)`.

---

### DB-010 — Ausência de CHECK constraints em colunas de domínio fixo
| Campo | Valor |
|---|---|
| ID | DB-010 |
| Categoria | Schema |
| Severidade | HIGH |
| Esforço | XS |
| Arquivo | `backend/db.py:34–43` |

**Descrição:** Colunas com domínio fixo sem restrição: `user_companies.role` (deveria aceitar apenas MASTER/ADMIN/COMMERCIAL/ANALYST), `contacts.type` (lead/client), `tasks.priority` (low/medium/high), `tasks.status` (pending/in_progress/done), `whatsapp_messages.direction` (inbound/outbound). Dados inválidos são inseridos silenciosamente e quebram a lógica de negócio (ex: role='comercial' em minúsculo nunca matcha nenhuma condição).

**Recomendação:** Adicionar CHECK constraints via `ALTER TABLE … ADD CONSTRAINT`. Começar pelas mais críticas: `user_companies.role` e `contacts.type`. Verificar dados existentes antes de aplicar.

---

### DB-011 — Valores monetários armazenados como FLOAT
| Campo | Valor |
|---|---|
| ID | DB-011 |
| Categoria | Schema |
| Severidade | HIGH |
| Esforço | S |
| Arquivo | `backend/db.py:98–115` |

**Descrição:** `deals.value` armazenado como FLOAT está sujeito a erros de ponto flutuante. `SUM(value)` em muitos registros acumula erros. `pipeline_stages.conversion_probability` também é FLOAT sem CHECK de intervalo [0,1].

**Recomendação:** Migrar `deals.value` para `NUMERIC(15,2)` e `conversion_probability` para `NUMERIC(5,4)` com `CHECK (value >= 0 AND value <= 1)`. Migração de tipo requer `USING` cast explícito e teste de rollback.

---

### DB-012 — Multi-step writes sem transação explícita
| Campo | Valor |
|---|---|
| ID | DB-012 |
| Categoria | Transaction |
| Severidade | HIGH |
| Esforço | S |
| Arquivo | `backend/routers/deals_router.py:94–116, 172–196, 199–215, 218–234` |

**Descrição:** Múltiplos endpoints executam escritas relacionadas sem `BEGIN/COMMIT`: `create_deal` (INSERT deals + UPDATE contacts.score), `move_stage` (UPDATE deals + UPDATE contacts.score), `mark_won` (UPDATE deals + UPDATE contacts), `mark_lost` (UPDATE deals + UPDATE contacts.score), `add_activity` (INSERT contact_activities + UPDATE contacts.score). Se qualquer etapa falhar, o estado fica inconsistente.

**Recomendação:** Envolver cada grupo de escritas relacionadas em `async with conn.transaction():`. Auditar todos os endpoints com mais de um `execute()` que assumem consistência.

---

## MEDIUM

---

### DEBT-009 — Ausência de FK constraints (code quality perspective)
| Campo | Valor |
|---|---|
| ID | DEBT-009 |
| Categoria | Data Integrity |
| Severidade | MEDIUM |
| Esforço | L |
| Arquivo | `backend/db.py` (todo o bloco `_CREATE_TABLES`) |

**Descrição:** (Perspectiva de qualidade de código.) Todas as relações (contacts→companies, deals→contacts, deals→pipeline_stages, tasks→contacts, tasks→deals, notifications→users) são garantidas apenas na camada de aplicação. Linhas órfãs se acumulam silenciosamente.

**Recomendação:** Ver DB-004 (CRITICAL) para a solução completa. Priorizar as relações de maior risco de negócio.

---

### DEBT-010 — Colunas de timestamp como TEXT em vez de TIMESTAMPTZ
| Campo | Valor |
|---|---|
| ID | DEBT-010 |
| Categoria | Data Integrity |
| Severidade | MEDIUM |
| Esforço | M |
| Arquivo | `backend/db.py` (todas as colunas de timestamp) |

**Descrição:** (Perspectiva de código.) Cada coluna de data/hora é `TEXT NOT NULL`. Impede aritmética nativa de datas no PostgreSQL, torna índices em ranges ineficazes, e é incompatível com ORMs e ferramentas de BI que esperam tipos reais. Ver DB-001 para análise completa do banco.

**Recomendação:** Migrar para `TIMESTAMPTZ`. O driver asyncpg faz a conversão `datetime ↔ TIMESTAMPTZ` nativamente; remover todos os `_now_iso()` / `.isoformat()`.

---

### DEBT-011 — Transições de estado won/lost sem guard — deal pode ter won_at e lost_at simultaneamente
| Campo | Valor |
|---|---|
| ID | DEBT-011 |
| Categoria | Data Integrity |
| Severidade | MEDIUM |
| Esforço | S |
| Arquivo | `backend/routers/deals_router.py:199–234` |

**Descrição:** `mark_won` e `mark_lost` fazem UPDATE sem verificar o estado atual. Chamar `/won` e depois `/lost` no mesmo deal resulta em `won_at` e `lost_at` ambos preenchidos, corrompendo os cálculos de taxa de conversão.

**Recomendação:** Em `mark_won`, adicionar `WHERE lost_at IS NULL` no UPDATE. Em `mark_lost`, adicionar `WHERE won_at IS NULL`. Retornar HTTP 409 se a transição de estado for inválida.

---

### DEBT-012 — update_* retorna dados sem company_id no fallback de payload vazio
| Campo | Valor |
|---|---|
| ID | DEBT-012 |
| Categoria | Data Integrity |
| Severidade | MEDIUM |
| Esforço | S |
| Arquivo | `backend/routers/contacts_router.py:158–162`, `deals_router.py:137–141`, `tasks_router.py:85–88` |

**Descrição:** Quando `payload.model_dump()` resulta em dict vazio (todos os campos opcionais omitidos), o código faz `fetchrow("SELECT * FROM ... WHERE id = $1")` sem `company_id`. Um COMMERCIAL que conheça um `contact_id` alheio pode enviar PUT com body vazio e receber os dados completos.

**Recomendação:** Incluir `company_id` no SELECT do fallback para garantir scoping de tenant. Considerar retornar HTTP 422 para body de update completamente vazio.

---

### DEBT-013 — F-string SQL dinâmica com nomes de coluna interpolados
| Campo | Valor |
|---|---|
| ID | DEBT-013 |
| Categoria | Code Quality |
| Severidade | MEDIUM |
| Esforço | S |
| Arquivo | `contacts_router.py`, `deals_router.py`, `tasks_router.py`, `users_router.py`, `pipelines_router.py`, `companies_router.py` |

**Descrição:** Todos os endpoints UPDATE constroem o SET clause iterando sobre as chaves do `model_dump()` e inserindo nomes de coluna diretamente em f-string: `f"{k} = ${n}"`. Hoje é seguro pois as chaves vêm de modelos Pydantic confiáveis, mas o padrão é uma refatoração longe de ser injetável se as chaves forem derivadas de input do usuário no futuro.

**Recomendação:** Definir allowlist explícita de colunas atualizáveis por entidade (`frozenset`) e validar `k` contra ela antes da interpolação. Ou usar cláusulas SET explícitas por campo com inclusão condicional.

---

### DEBT-014 — _now_iso() duplicado em 12 arquivos
| Campo | Valor |
|---|---|
| ID | DEBT-014 |
| Categoria | Code Quality |
| Severidade | MEDIUM |
| Esforço | S |
| Arquivo | Todos os routers, integrations e seed.py |

**Descrição:** A helper `def _now_iso() -> str: return datetime.now(timezone.utc).isoformat()` está copiada identicamente em cada router, nos arquivos de integração e em seed.py. Sem módulo de utils compartilhado. Qualquer mudança de formato precisa sincronizar 12 arquivos.

**Recomendação:** Criar `backend/utils.py` com uma única `now_iso()` e importar de lá. Esse módulo seria também o lugar para request-ID helper e log formatter estruturado.

---

### DEBT-015 — LIMIT 500 hardcoded sem paginação em list_tasks
| Campo | Valor |
|---|---|
| ID | DEBT-015 |
| Categoria | Code Quality |
| Severidade | MEDIUM |
| Esforço | XS |
| Arquivo | `backend/routers/tasks_router.py:52` |

**Descrição:** `list_tasks` retorna até 500 linhas em resposta única sem parâmetros `page/limit` e sem `total` na resposta. O padrão de paginação já existe em `list_contacts` e `list_deals` e deveria ser consistente.

**Recomendação:** Adicionar `page` e `limit` (com máximo configurável, ex.: 100) ao endpoint. Retornar `{"items": ..., "total": ..., "page": ..., "limit": ...}`.

---

### DEBT-016 — N+1 no endpoint /analytics/funnel e companies/consolidated
| Campo | Valor |
|---|---|
| ID | DEBT-016 |
| Categoria | Code Quality |
| Severidade | MEDIUM |
| Esforço | S |
| Arquivo | `backend/routers/analytics_router.py:113–124`, `companies_router.py` |

**Descrição:** Ver DB-006 para análise detalhada. Do ponto de vista de código, o padrão de loop-com-queries é um antipadrão que se repete em dois arquivos diferentes, sugerindo ausência de revisão de query patterns.

**Recomendação:** Ver DB-006. Consolidar em GROUP BY queries.

---

### DEBT-017 — /analytics/activities ignora o parâmetro "days"
| Campo | Valor |
|---|---|
| ID | DEBT-017 |
| Categoria | Code Quality |
| Severidade | MEDIUM |
| Esforço | XS |
| Arquivo | `backend/routers/analytics_router.py:187–197` |

**Descrição:** O endpoint declara `days: int = 30` como query parameter mas nunca o usa na query SQL. Sempre retorna contagens de atividades de todos os tempos, não dos últimos N dias. Violação silenciosa de contrato de API.

**Recomendação:** Aplicar o filtro: `WHERE company_id = $1 AND occurred_at >= NOW() - INTERVAL '$days days'`. Após migração para TIMESTAMPTZ (DEBT-010), é uma correção de uma linha.

---

### DB-001 — Todos os timestamps armazenados como TEXT em vez de TIMESTAMPTZ
| Campo | Valor |
|---|---|
| ID | DB-001 |
| Categoria | Schema |
| Severidade | MEDIUM |
| Esforço | M |
| Arquivo | `backend/db.py:10–160` |

**Descrição:** Todas as colunas de data/hora são `TEXT`. O banco não impõe formato, não executa comparações de intervalo com índice B-tree nativo, não converte fuso horário e não valida entrada. As queries em `analytics_router.py` comparam `created_at >= $n` com strings ISO — funciona enquanto o formato permanecer consistente, mas falha silenciosamente com qualquer variação. `ORDER BY due_date ASC` em `tasks_router.py` ordena lexicograficamente (correto por coincidência com ISO-8601, porém frágil).

**Recomendação:** Migrar para `TIMESTAMPTZ`. Colunas de data pura (`due_date`, `expected_close_date`) para `DATE`. É migração destrutiva de tipo: exige `USING` e conversão coluna por coluna com rollback testado.

---

### DB-013 — LIMIT 500 sem paginação em list_tasks
| Campo | Valor |
|---|---|
| ID | DB-013 |
| Categoria | Query |
| Severidade | MEDIUM |
| Esforço | XS |
| Arquivo | `backend/routers/tasks_router.py:51–54` |

**Descrição:** Ver DEBT-015. Do ponto de vista de banco, 500 linhas serializadas em JSON por request sem cursor/keyset pagination é ineficiente para clientes com volume alto de tarefas.

**Recomendação:** Ver DEBT-015. Implementar paginação por cursor com `(due_date, id)` como tiebreaker para a ordenação existente.

---

### DB-014 — Sem filtro de soft-delete em queries de users
| Campo | Valor |
|---|---|
| ID | DB-014 |
| Categoria | Schema |
| Severidade | MEDIUM |
| Esforço | S |
| Arquivo | `backend/db.py:11–19` |

**Descrição:** A tabela `users` tem `deleted_at` mas queries que buscam usuários (`leaderboard` em `analytics_router.py`, seed.py) não filtram `deleted_at IS NULL`. Usuário desativado continuaria aparecendo no leaderboard. Sem índice em `users.deleted_at`.

**Recomendação:** Adicionar índice parcial `users(id) WHERE deleted_at IS NULL` e revisar todas as queries de lookup em `users` para incluir `AND deleted_at IS NULL`.

---

### DB-015 — Colunas de endereço esparsas adicionadas via ALTER TABLE
| Campo | Valor |
|---|---|
| ID | DB-015 |
| Categoria | Schema |
| Severidade | MEDIUM |
| Esforço | M |
| Arquivo | `backend/core/schema_extra.sql:55–67` |

**Descrição:** 9 colunas de endereço adicionadas diretamente em `contacts` (cep, street, street_number, neighborhood, city, state, latitude, longitude, address). A maioria null para leads sem endereço completo. `latitude`/`longitude` como FLOAT têm problemas de precisão — deveriam ser `NUMERIC(10,7)` ou tipo `GEOGRAPHY` do PostGIS.

**Recomendação:** Avaliar se endereço exige histórico ou múltiplos registros. Se sim, criar tabela `contact_addresses` com FK. Se sempre one-to-one, migrar lat/lng para `NUMERIC(10,7)`.

---

### DB-016 — Pool sem timeout configurado
| Campo | Valor |
|---|---|
| ID | DB-016 |
| Categoria | Connection |
| Severidade | MEDIUM |
| Esforço | XS |
| Arquivo | `backend/db.py:167–176` |

**Descrição:** `asyncpg.create_pool` é chamado com `min_size=2` e `max_size=10` mas sem `command_timeout` nem `timeout` (tempo máximo para adquirir conexão do pool). Sob carga alta, requests que não conseguem conexão ficam bloqueados sem limite de tempo, causando acúmulo de coroutines e eventual esgotamento de memória.

**Recomendação:** Adicionar `timeout=30.0` e `command_timeout=60.0` ao `create_pool`. Avaliar `max_size=20` dependendo do hardware.

---

### DB-017 — Índices ausentes em schema_extra.sql
| Campo | Valor |
|---|---|
| ID | DB-017 |
| Categoria | Schema |
| Severidade | MEDIUM |
| Esforço | XS |
| Arquivo | `backend/core/schema_extra.sql` |

**Descrição:** `password_reset_tokens` sem índice em `user_id` ou `expires_at` (campos usados em validação de token). `permissions` sem índice cobrindo `(company_id, user_id, permission)` — o padrão de lookup mais comum.

**Recomendação:** Criar `idx_password_tokens_user ON password_reset_tokens(user_id)`, `idx_password_tokens_expires ON password_reset_tokens(expires_at) WHERE used = FALSE`, `idx_permissions_lookup ON permissions(company_id, user_id, permission)`.

---

## LOW

---

### DEBT-018 — get_deal busca contato sem scoping de company_id
| Campo | Valor |
|---|---|
| ID | DEBT-018 |
| Categoria | Code Quality |
| Severidade | LOW |
| Esforço | XS |
| Arquivo | `backend/routers/deals_router.py:128–129` |

**Descrição:** No detalhe de deal, o contato é buscado com `SELECT * FROM contacts WHERE id = $1` — sem filtro de `company_id`. Na prática é seguro pois o deal já é company-scoped, mas contorna a fronteira de tenant na query e poderia retornar dados de tenant diferente se o `contact_id` fosse adulterado.

**Recomendação:** Adicionar `AND company_id = $2` ao lookup de contato, usando o `company_id` do próprio deal já verificado.

---

### DEBT-019 — CORS padrão wildcard quando CORS_ORIGINS não está setado
| Campo | Valor |
|---|---|
| ID | DEBT-019 |
| Categoria | Security |
| Severidade | LOW |
| Esforço | XS |
| Arquivo | `backend/server.py:63` |

**Descrição:** `cors_origins = os.environ.get("CORS_ORIGINS", "*").split(",")`. Se `CORS_ORIGINS` não estiver definido (novo deploy), a API aceita requests cross-origin de qualquer domínio. Com `allow_credentials=True`, browsers enviarão cookies à API a partir de origens controladas por atacantes.

**Recomendação:** Remover o default `"*"`. Se a variável de ambiente estiver ausente, lançar erro na inicialização ou default para lista vazia. Documentar `CORS_ORIGINS` como variável obrigatória no guia de deploy.

---

### DEBT-020 — Sem logging estruturado, sem request IDs, sem health endpoint real
| Campo | Valor |
|---|---|
| ID | DEBT-020 |
| Categoria | Observability |
| Severidade | LOW |
| Esforço | M |
| Arquivo | `backend/server.py` + todos os routers |

**Descrição:** Três gaps relacionados: (1) `logging.basicConfig` com formatter de texto plano — sem JSON logs estruturados para log aggregation. (2) Sem middleware de request-ID — rastreamento correlacionado entre requests assíncronos impossível. (3) Sem endpoint `/health` ou `/healthz` real — o único acessível é `GET /api/` que não é uma probe de saúde adequada (não verifica conectividade com o banco).

**Recomendação:** Adicionar `RequestIDMiddleware` que gera UUID por request e o injeta no contexto de log. Trocar para `structlog` ou `python-json-logger`. Adicionar `GET /health` que verifica conectividade do pool e retorna `{"status": "ok", "db": "connected"}`.

---

### DB-018 — PKs como TEXT em vez de UUID nativo
| Campo | Valor |
|---|---|
| ID | DB-018 |
| Categoria | Schema |
| Severidade | LOW |
| Esforço | S |
| Arquivo | `backend/db.py:10–160` (todos os PKs) |

**Descrição:** Todas as PKs são `TEXT PRIMARY KEY` geradas com `str(uuid.uuid4())` no Python. O banco não impõe que o valor seja UUID válido. O tipo nativo `UUID` do PostgreSQL usa 16 bytes vs 36 bytes para TEXT com hífens, e oferece validação de formato.

**Recomendação:** Avaliar migração apenas se o crescimento de dados justificar — o ganho é marginal para volumes típicos de CRM. Se decidir migrar, fazê-lo em migração única com `USING id::uuid` antes de adicionar as FKs do DB-004.

---

## Resumo Executivo

| Severidade | Qtd | IDs |
|---|---|---|
| CRITICAL | 5 | DEBT-001, DEBT-002, DB-002, DB-003, DB-004 |
| HIGH | 12 | DEBT-003–008, DB-005–012 |
| MEDIUM | 14 | DEBT-009–017, DB-001, DB-013–017 |
| LOW | 7 | DEBT-018–020, DB-018 (+ variações) |
| **Total** | **38** | |

---

*Auditoria: 2026-05-28 — Diagnóstico apenas. Nenhuma implementação neste documento.*
