# CLAUDE.md

> Este arquivo é lido por TODOS os agentes no início de cada tarefa.
> É a fonte da consistência. Preencha os campos entre colchetes com a
> realidade do seu projeto e mantenha-o atualizado conforme o projeto evolui.

## Visão geral do projeto

[Uma ou duas frases sobre o que o sistema faz e quem usa.]

## Stack

- **Frontend:** [ex.: React + TypeScript + Vite + Tailwind]
- **Backend:** [ex.: Node.js + Express, ou Python + FastAPI]
- **Banco de dados:** [ex.: PostgreSQL]
- **ORM / acesso a dados:** [ex.: Prisma, ou SQLAlchemy]
- **Testes:** [ex.: Vitest no front, Jest no back, Playwright para E2E]
- **Gerenciador de pacotes:** [ex.: pnpm]

## Estrutura de pastas

```
[Cole aqui a árvore de pastas principal e diga o que vai em cada uma.
Ex.:
src/
  api/         -> rotas e controllers
  services/    -> regra de negócio
  repositories/-> acesso a dados
  components/  -> componentes de UI
  hooks/       -> hooks reutilizáveis
tests/         -> testes
migrations/    -> migrações de banco
]
```

## Comandos

- Instalar dependências: `[ex.: pnpm install]`
- Rodar em desenvolvimento: `[ex.: pnpm dev]`
- Build: `[ex.: pnpm build]`
- Lint: `[ex.: pnpm lint]`
- Checagem de tipos: `[ex.: pnpm typecheck]`
- Rodar testes: `[ex.: pnpm test]`
- Rodar migração: `[ex.: pnpm db:migrate]`

## Convenções de código

- **Nomenclatura:** [ex.: arquivos em kebab-case, componentes em PascalCase, variáveis em camelCase]
- **Imports:** [ex.: usar alias `@/` para `src/`; ordenar libs externas antes das internas]
- **Tratamento de erro:** [ex.: backend retorna `{ error: { code, message } }` com status HTTP correto]
- **Resposta de API:** [ex.: sempre `{ data }` em sucesso; paginação como `{ data, page, total }`]
- **Estado no frontend:** [ex.: React Query para dados de servidor; sem estado de servidor em useState]
- **Estilo:** [ex.: somente Tailwind; sem CSS inline; usar os tokens de `theme`]
- **Commits:** [ex.: Conventional Commits — feat:, fix:, chore:]

## Regras gerais

- Reaproveite o que já existe antes de criar algo novo.
- Não introduza bibliotecas novas sem necessidade clara.
- Nunca exponha segredos; tudo sensível vem de variáveis de ambiente.
- Toda feature precisa de testes antes de ser considerada pronta.
- [Outras regras específicas do seu time.]

## O que NÃO mexer

- [ex.: pasta `legacy/` está congelada; arquivos gerados automaticamente.]
