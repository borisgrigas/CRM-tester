# Time de agentes full-stack para o Claude no VS Code

Este pacote contém um time de subagentes do **Claude Code** prontos para
desenvolver sistemas full-stack de forma organizada e consistente.

## O que está incluído

```
.claude/
  agents/
    architect.md           -> planeja a feature (não escreve código)
    database-engineer.md   -> schema, migrações, queries
    backend-developer.md   -> API, serviços, regra de negócio
    frontend-developer.md  -> componentes de UI, estado, formulários
    test-engineer.md       -> testes unitários, integração e E2E
    code-reviewer.md        -> revisa o código (não edita)
    debugger.md            -> encontra a causa raiz de bugs
CLAUDE.md                  -> convenções do projeto (a fonte da consistência)
```

## Como funciona

Um **subagente** é uma instância do Claude com prompt próprio, conjunto de
ferramentas próprio e uma janela de contexto isolada. O Claude principal
delega tarefas a eles automaticamente, lendo o campo `description` de cada
agente para decidir quando usá-lo. O resultado: o trabalho fica especializado,
o contexto principal não polui, e o código sai padronizado.

A **consistência** vem de dois lugares:
1. O `CLAUDE.md`, que todo agente lê antes de começar.
2. Cada agente lê código parecido que já existe e segue o mesmo estilo.

## Instalação

### 1. Tenha o Claude Code

No terminal:

```bash
npm install -g @anthropic-ai/claude-code
```

Requer Node.js 18+. Depois rode `claude` uma vez para autenticar.

### 2. Instale a extensão no VS Code

Procure por **Claude Code** na aba de extensões do VS Code e instale.
Ela usa o mesmo `claude` e os mesmos arquivos de configuração do terminal.

### 3. Coloque os agentes no projeto

Copie a pasta `.claude/` e o `CLAUDE.md` para a **raiz do seu projeto**:

```
seu-projeto/
  .claude/
    agents/...
  CLAUDE.md
  src/
  ...
```

- `.claude/agents/` na raiz do projeto = agentes válidos só neste projeto
  (recomendado: versione no Git para o time todo usar).
- Se quiser os agentes em **todos** os seus projetos, copie a pasta `agents/`
  para `~/.claude/agents/` no seu computador.

### 4. Preencha o CLAUDE.md

Abra o `CLAUDE.md` e substitua tudo entre `[colchetes]` pela realidade do seu
projeto: stack, estrutura de pastas, comandos e convenções. **Este passo é o
mais importante** — é ele que faz o código sair consistente.

### 5. Carregue os agentes

Reinicie a sessão do Claude Code. Para conferir, rode dentro do Claude:

```
/agents
```

Você verá os sete agentes na aba Library. Pelo `/agents` você também pode
editar, testar ou criar novos agentes pela interface guiada.

## Como usar

### Delegação automática

Basta pedir normalmente. O Claude escolhe o agente certo sozinho:

```
Implemente o cadastro de usuários com validação de e-mail.
```

O Claude tende a acionar o `architect` para planejar, depois o
`database-engineer`, o `backend-developer`, o `frontend-developer`, o
`test-engineer` e por fim o `code-reviewer`.

### Acionar um agente explicitamente

```
Use o architect para planejar o sistema de notificações.
@architect revise a modelagem do módulo de pagamentos.
```

### Encadear agentes (workflow recomendado)

Para uma feature nova, peça o pipeline inteiro:

```
Quero adicionar [feature]. Use o architect para planejar; depois
database-engineer, backend-developer e frontend-developer para implementar;
test-engineer para os testes; e code-reviewer para revisar no fim.
```

Fluxo típico de uma feature:

```
architect  ->  database-engineer  ->  backend-developer
   |                                        |
   v                                        v
frontend-developer  ->  test-engineer  ->  code-reviewer
```

Para um bug:

```
debugger  ->  test-engineer  ->  code-reviewer
```

## Dicas

- Comece pequeno: se sete agentes parecer demais, use só `architect`,
  `backend-developer`, `frontend-developer` e `code-reviewer`.
- Quanto mais completo o `CLAUDE.md`, mais consistente o resultado.
- Os agentes têm memória de projeto (`memory: project`): com o tempo eles
  acumulam conhecimento sobre o seu código. Esses arquivos ficam em
  `.claude/agent-memory/` — versione no Git se quiser compartilhar com o time.
- Ajuste o campo `model` no topo de cada agente se quiser (`opus`, `sonnet`,
  `haiku` ou `inherit`). `inherit` usa o mesmo modelo da sua sessão.
- Edite os prompts dos agentes à vontade — eles são só arquivos Markdown.

## Referência

Documentação oficial de subagentes do Claude Code:
https://code.claude.com/docs/en/sub-agents
