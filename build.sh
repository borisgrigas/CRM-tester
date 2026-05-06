#!/usr/bin/env bash
# build.sh — setup completo do CRM SaaS Multi-Tenant
# Uso:  ./build.sh           (instala + seed)
#       ./build.sh --no-seed (apenas instala dependências)

set -e

NO_SEED=0
for arg in "$@"; do
  if [[ "$arg" == "--no-seed" ]]; then NO_SEED=1; fi
done

ROOT="$(cd "$(dirname "$0")" && pwd)"

echo "==> [1/4] Verificando pré-requisitos"
command -v python3 >/dev/null || { echo "python3 não encontrado"; exit 1; }
command -v yarn >/dev/null    || { echo "yarn não encontrado (npm install -g yarn)"; exit 1; }
command -v mongod >/dev/null  || echo "  (aviso: mongod local não encontrado — assumindo MongoDB remoto via MONGO_URL)"

echo "==> [2/4] Configurando .env (se ausente)"
if [[ ! -f "$ROOT/backend/.env" ]]; then
  cp "$ROOT/.env.example" "$ROOT/backend/.env"
  echo "  ✓ backend/.env criado a partir do .env.example — REVISE-O antes de subir em produção"
fi
if [[ ! -f "$ROOT/frontend/.env" ]]; then
  cat > "$ROOT/frontend/.env" <<EOF
REACT_APP_BACKEND_URL=http://localhost:8001
WDS_SOCKET_PORT=0
EOF
  echo "  ✓ frontend/.env criado"
fi

echo "==> [3/4] Instalando dependências"
echo "  • backend (pip)"
cd "$ROOT/backend"
python3 -m pip install --quiet --upgrade pip
python3 -m pip install --quiet -r requirements.txt

echo "  • frontend (yarn)"
cd "$ROOT/frontend"
yarn install --silent

if [[ $NO_SEED -eq 1 ]]; then
  echo "==> [4/4] Seed pulado (--no-seed)"
  echo
  echo "✅ Setup concluído sem seed."
  exit 0
fi

echo "==> [4/4] Rodando seed (cria índices + dados de demonstração)"
cd "$ROOT/backend"
python3 seed.py

echo
echo "✅ Setup completo!"
echo
echo "Para iniciar:"
echo "  • Backend:  cd backend && uvicorn server:app --host 0.0.0.0 --port 8001 --reload"
echo "  • Frontend: cd frontend && yarn start"
echo
echo "Ou com Docker:"
echo "  • docker-compose up --build"
echo
echo "Credenciais demo:"
echo "  MASTER:     master@franqueadora.com / master123"
echo "  ADMIN:      admin@unidade-sao-paulo.com / senha123"
echo "  COMMERCIAL: vendas@unidade-sao-paulo.com / senha123"
echo "  ANALYST:    analista@unidade-sao-paulo.com / senha123"
