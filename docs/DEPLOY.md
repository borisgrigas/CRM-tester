# Guia de Deploy — CRM SaaS Multi-Tenant

> Host padrão documentado: **Railway**. Adaptações para outros hosts na seção [Outros hosts](#outros-hosts).

---

## Visão geral da arquitetura

```
Internet
   │
   ├─► Frontend  (React SPA, servido como build estático via `serve`)
   │       └── chama ──► Backend API  (FastAPI + uvicorn, 2 workers)
   │                          └── conecta ──► PostgreSQL  (gerenciado)
   │
   └─► Webhooks públicos  (POST /api/webhooks/{slug}/{source})
                          (POST /api/whatsapp/inbound/{slug})
```

O Railway executa **cada serviço pelo seu próprio Dockerfile**, não pelo `docker-compose.yml`.  
O `docker-compose.yml` existe apenas para desenvolvimento local.

---

## Pré-requisitos

- Conta no [Railway](https://railway.app) (plano Hobby mínimo para uso real)
- Repositório no GitHub com o código do projeto
- `openssl` instalado localmente (para gerar `JWT_SECRET`)

---

## Passo a passo — Railway

### 1. Gerar segredos antes de começar

Antes de abrir o Railway, gere os valores que serão usados nas variáveis:

```bash
# JWT_SECRET — copie a saída completa
openssl rand -hex 64

# Exemplo de saída (não use este):
# a3f8c2d1e4b7a9f0c3e6d2b5a8f1c4e7d0b3a6f9c2e5d8b1a4f7c0e3d6b9a2f5
```

Escolha também uma `ADMIN_PASSWORD` forte (mínimo 16 caracteres, com letras, números e símbolos).

---

### 2. Criar o projeto no Railway

1. Acesse [railway.app](https://railway.app) → **New Project**
2. Escolha **Deploy from GitHub repo**
3. Autorize o Railway a acessar o repositório
4. Selecione o repositório `CRM-tester`
5. Railway detectará o projeto. **Não faça deploy ainda** — continue para configurar os serviços

---

### 3. Provisionar o banco de dados PostgreSQL

1. No projeto Railway, clique em **+ New Service** → **Database** → **PostgreSQL**
2. Railway cria o banco e disponibiliza a variável `DATABASE_URL` automaticamente
3. Anote o valor de `DATABASE_URL` na aba **Variables** do serviço Postgres — será referenciado nos próximos passos
4. (Opcional, plano pago) Ative backups automáticos: aba **Settings** → **Backups**

---

### 4. Configurar o serviço Backend

1. **+ New Service** → **GitHub Repo** → selecione o mesmo repositório
2. Railway detectará o Dockerfile automaticamente. Configure:
   - **Root Directory**: `backend`
   - **Dockerfile Path**: `Dockerfile` (relativo ao root directory)
3. Na aba **Variables** do serviço backend, adicione:

| Variável | Valor |
|---|---|
| `DATABASE_URL` | Cole o valor do serviço Postgres (ou use `${{Postgres.DATABASE_URL}}` para referência automática) |
| `JWT_SECRET` | Valor gerado com `openssl rand -hex 64` |
| `CORS_ORIGINS` | URL do frontend (preencha depois do passo 5, ex: `https://crm-frontend.up.railway.app`) |
| `APP_ENV` | `production` |
| `ADMIN_EMAIL` | E-mail do administrador master inicial |
| `ADMIN_PASSWORD` | Senha forte (mínimo 16 caracteres) |

4. Clique em **Deploy**
5. Aguarde o build concluir. Verifique nos logs que aparece:
   ```
   INFO:     Application startup complete.
   ```
   > **Importante:** `seed.py` NÃO roda em produção — o Dockerfile usa diretamente `uvicorn`. Os dados de demonstração não são inseridos automaticamente.

6. Na aba **Settings** → **Networking**, clique em **Generate Domain** para obter a URL pública do backend (ex: `https://crm-backend-production.up.railway.app`)

---

### 5. Configurar o serviço Frontend

1. **+ New Service** → **GitHub Repo** → mesmo repositório
2. Configure:
   - **Root Directory**: `frontend`
   - **Dockerfile Path**: `Dockerfile`
3. Na aba **Variables**, adicione a variável de **build**:

| Variável | Tipo | Valor |
|---|---|---|
| `REACT_APP_BACKEND_URL` | **Build Variable** | URL pública do backend (do passo 4.6), ex: `https://crm-backend-production.up.railway.app` |

> ⚠️ `REACT_APP_BACKEND_URL` é um **Build ARG**, não uma env var de runtime.  
> No Railway, configure-a como **Build Variable** (não como "Variable" comum).  
> O React embute esse valor no bundle JavaScript durante o build — não pode ser alterado sem rebuild.

4. Clique em **Deploy**
5. Gere o domínio do frontend (aba **Settings** → **Networking** → **Generate Domain**)

---

### 6. Finalizar a configuração de CORS

Após ter a URL do frontend:

1. Volte ao serviço **backend** → aba **Variables**
2. Atualize `CORS_ORIGINS` com a URL real do frontend:
   ```
   CORS_ORIGINS=https://crm-frontend-production.up.railway.app
   ```
3. Railway irá redeploy o backend automaticamente

---

### 7. Verificar o deploy

Acesse a URL do frontend no browser e confirme:

- [ ] Página de login carrega
- [ ] Login funciona com `ADMIN_EMAIL` / `ADMIN_PASSWORD` configurados
- [ ] Dashboard exibe dados (vazios é esperado — sem seed em produção)
- [ ] Aba **Network** do browser não mostra erros de CORS
- [ ] A URL da API nas requisições bate com `REACT_APP_BACKEND_URL`

Para testar o backend diretamente:
```bash
curl https://crm-backend-production.up.railway.app/api/
# Esperado: {"message":"CRM SaaS API","version":"1.0.0"}
```

---

### Bootstrap do usuário master em produção

O endpoint `/api/auth/register` não existe. O CRM usa o modelo de convite (invite-only).
Para criar o usuário master em produção, conecte ao banco via Railway CLI ou psql e execute
o script `backend/bootstrap_prod.py` (a ser criado na Fase 2), ou use as credenciais
padrão definidas nas variáveis de ambiente `ADMIN_EMAIL` e `ADMIN_PASSWORD` que são
inseridas automaticamente pelo `seed.py` na primeira execução.

```bash
# Conexão ao banco via Railway CLI
railway connect Postgres
# Em seguida use o psql para verificar/inserir o usuário master se necessário
```

---

## Atualizar o deploy

O Railway faz **redeploy automático** a cada push para a branch configurada.  
Para mudar variáveis de ambiente, edite na aba **Variables** — o Railway irá redeploy automaticamente.

Para forçar um redeploy manual:
- Aba **Deployments** → clique em **Redeploy** no último deploy

---

## Domínio próprio

Para usar `app.seudominio.com` em vez de `.up.railway.app`:

1. Serviço frontend → **Settings** → **Networking** → **Custom Domain**
2. Adicione `app.seudominio.com`
3. Railway fornece os registros DNS (CNAME) — configure no seu provedor de domínio
4. Atualize `CORS_ORIGINS` no backend para incluir o domínio próprio
5. Atualize `REACT_APP_BACKEND_URL` no frontend e faça rebuild (se o backend também ganhar domínio próprio)

---

## Outros hosts

### Render

Processo idêntico ao Railway. Diferenças:
- Serviços criados como **Web Service** (backend) e **Static Site** ou **Web Service** (frontend)
- `REACT_APP_BACKEND_URL` é configurado como **Environment Variable** na aba de build
- PostgreSQL: **New** → **PostgreSQL** (gerenciado)

### Fly.io

```bash
# Instalar flyctl
curl -L https://fly.io/install.sh | sh

# Backend
cd backend
fly launch --name crm-backend --dockerfile Dockerfile
fly secrets set JWT_SECRET="..." CORS_ORIGINS="..." DATABASE_URL="..."
fly deploy

# Frontend
cd ../frontend
fly launch --name crm-frontend --dockerfile Dockerfile \
  --build-arg REACT_APP_BACKEND_URL=https://crm-backend.fly.dev
fly deploy
```

### VPS com Docker (self-hosted)

```bash
# Clone o repositório
git clone https://github.com/seu-usuario/CRM-tester.git
cd CRM-tester

# Configure as variáveis
cp .env.production.example .env
# Edite .env com os valores reais

# Build e subida (sem seed)
docker build -t crm-backend ./backend
docker build -t crm-frontend \
  --build-arg REACT_APP_BACKEND_URL=https://api.seudominio.com \
  ./frontend

# Use um docker-compose.prod.yml sem o serviço postgres local
# e com DATABASE_URL apontando para seu Postgres externo
```

Configure **nginx** como reverse proxy na frente do frontend e backend para terminar TLS.

---

## Checklist de segurança pré-produção

Revise cada item antes de tornar o sistema público:

### Segredos
- [ ] `JWT_SECRET` gerado com `openssl rand -hex 64` — **nunca** o valor padrão
- [ ] `ADMIN_PASSWORD` tem no mínimo 16 caracteres com letras, números e símbolos
- [ ] Nenhum arquivo `.env` foi commitado no git (`git log --all -- '*.env'` não mostra nada)
- [ ] `DATABASE_URL` usa credenciais únicas para este ambiente (não reutilizadas de dev)
- [ ] Nenhuma senha ou token hardcoded no código (`grep -r "master123" backend/` retorna vazio)

### Rede e acesso
- [ ] `CORS_ORIGINS` contém apenas o(s) domínio(s) do frontend — sem `*`
- [ ] Porta 5432 do Postgres não está exposta publicamente (Railway isola por padrão)
- [ ] HTTPS ativo: Railway fornece certificado TLS automático em `.up.railway.app`
- [ ] Domínio próprio (se usado) com HTTPS válido e redirect HTTP → HTTPS configurado

### Dados e banco
- [ ] `seed.py` **não** está sendo chamado no startup de produção (confirme nos logs do primeiro deploy)
- [ ] Backups automáticos do banco habilitados (Railway: aba Storage → Backups — requer plano pago)
- [ ] Testado o restore de backup antes de ir ao ar (Railway: **Restore** a partir de um snapshot)
- [ ] Índices criados (o `db.py` já cria `CREATE INDEX IF NOT EXISTS` no startup — confirme nos logs)

### Aplicação
- [ ] Login de admin funciona com as credenciais configuradas
- [ ] CORS não bloqueia requisições do frontend para o backend
- [ ] Logs do backend não expõem senhas ou tokens (observe os primeiros 100 linhas de log)
- [ ] `ADMIN_PASSWORD` trocado após o primeiro login bem-sucedido
- [ ] Flag `franchise` e `whatsapp` habilitadas apenas para as empresas que devem ter acesso

### Operação contínua
- [ ] Alertas de uso/falha configurados (Railway: aba **Observability**)
- [ ] Pelo menos um contato de suporte com acesso ao painel Railway
- [ ] Documentado onde ficam as variáveis de ambiente (Railway dashboard — não no repo)
- [ ] Processo de atualização definido: push para branch → Railway redeploy automático

---

## Referências

- [Railway Docs — Services](https://docs.railway.app/guides/services)
- [Railway Docs — Variables](https://docs.railway.app/guides/variables)
- [Railway Docs — PostgreSQL](https://docs.railway.app/databases/postgresql)
- [Railway Docs — Custom Domains](https://docs.railway.app/guides/custom-domains)
- [FastAPI Deployment](https://fastapi.tiangolo.com/deployment/)
- [Create React App — Environment Variables](https://create-react-app.dev/docs/adding-custom-environment-variables/)
