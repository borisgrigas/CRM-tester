# ADR 0002: Sem endpoint público de registro de usuários

**Status:** Accepted  
**Data:** 2026-05-28  
**Contexto:** O arquivo `docs/DEPLOY.md` (seção "Criar o primeiro admin manualmente") referencia um endpoint `POST /api/auth/register` para bootstrap do sistema em produção. Este endpoint **não existe** em nenhum router registrado da aplicação. A referência é incorreta e pode induzir operadores a erro.

---

## Decisão

**Não existe e não será criado um endpoint público de registro de usuários.**

O CRM é um sistema SaaS multi-tenant operado por franquias. O acesso ao sistema é **por convite** — gerenciado exclusivamente por usuários MASTER ou ADMIN via `POST /api/users/invite`. Não faz sentido existir um endpoint que qualquer pessoa na internet possa usar para criar uma conta.

---

## Motivação

### Modelo de negócio exige acesso controlado

O sistema serve redes de franquias. A franqueadora (tenant master) controla quais unidades existem e quem tem acesso a cada uma. Um endpoint `/register` público quebraria este modelo ao permitir que qualquer pessoa criasse um usuário não vinculado a nenhuma empresa.

### Vetor de ataque desnecessário

Um `/register` público seria um vetor para:
- Criação de contas de spam.
- Enumeração de e-mails cadastrados via respostas de erro.
- Ataques de força bruta em massa.

### Bootstrap de produção não precisa de endpoint HTTP

A criação do primeiro usuário MASTER em produção pode e deve ser feita diretamente no banco de dados, sem expor uma rota HTTP que depois precisaria ser desabilitada ou protegida.

---

## Alternativas consideradas

### Alternativa 1: Criar /register mas protegido por um token de bootstrap

**Rejeitada.** Adiciona complexidade (geração, armazenamento e revogação do token de bootstrap) para um caso de uso que acontece uma única vez por implantação.

### Alternativa 2: Criar /register mas desabilitado por feature flag

**Rejeitada.** Uma flag em banco não é suficientemente seguro — o endpoint ainda estaria no código e poderia ser habilitado acidentalmente.

### Alternativa 3: Manter o status quo (sem /register) e corrigir a documentação

**Aceita.**

---

## Consequências

### Positivas
- Superfície de ataque menor.
- Modelo de acesso por convite preservado.
- Sem dead code no codebase.

### Negativas / mitigações

**Criação do primeiro usuário MASTER em produção é um passo manual.**

O operador deve seguir um dos dois fluxos abaixo na primeira implantação:

#### Opção A — via Railway CLI (recomendado)

```bash
# 1. Instale o Railway CLI
npm install -g @railway/cli

# 2. Autentique
railway login

# 3. Conecte ao banco do projeto
railway connect Postgres

# 4. No prompt psql, crie a empresa franqueadora e o usuário master:
INSERT INTO companies (id, name, slug, plan, is_active, is_franchisor, created_at)
VALUES (gen_random_uuid()::text, 'Franqueadora', 'franqueadora', 'enterprise', true, true, now()::text);

-- Anote o id da empresa acima.
-- Substitua os valores abaixo pelos dados reais.
INSERT INTO users (id, name, email, password_hash, created_at)
VALUES (
  gen_random_uuid()::text,
  'Admin Master',
  'admin@seudominio.com',
  -- bcrypt hash de 'SuaSenhaForte123!' com rounds=12
  -- Use: python3 -c "import bcrypt; print(bcrypt.hashpw(b'SuaSenhaForte123!', bcrypt.gensalt(12)).decode())"
  '$2b$12$INSIRA_O_HASH_AQUI',
  now()::text
);

-- Vincule o usuário à empresa como MASTER:
INSERT INTO user_companies (user_id, company_id, role, modules, is_active, invited_at, accepted_at)
VALUES (
  (SELECT id FROM users WHERE email = 'admin@seudominio.com'),
  (SELECT id FROM companies WHERE slug = 'franqueadora'),
  'MASTER',
  '[]',
  true,
  now()::text,
  now()::text
);
```

#### Opção B — via script de bootstrap (alternativa)

Criar um script `backend/scripts/bootstrap_master.py` que aceita parâmetros via CLI e insere o usuário diretamente via asyncpg. Este script **não faz parte do startup do servidor** — é executado manualmente uma única vez:

```bash
# Exemplo de uso futuro (script a ser criado)
DATABASE_URL="..." python backend/scripts/bootstrap_master.py \
  --name "Admin Master" \
  --email "admin@seudominio.com" \
  --password "SuaSenhaForte123!" \
  --company-name "Franqueadora"
```

---

## Referências

- `docs/DEPLOY.md` — seção "8. Criar o primeiro admin manualmente" foi atualizada para remover a referência ao endpoint inexistente.
- `backend/routers/auth_router.py` — nenhum endpoint `/register` existe.
- `backend/routers/users_router.py` — `POST /users/invite` é o único mecanismo de criação de usuários em runtime.
