# F01 — Monorepo, tooling e CI base

| Campo | Valor |
|---|---|
| **Status** | Em implementação |
| **Fase** | 0 — Fundação |
| **Dependências** | — |
| **ADRs** | ADR-005 |
| **Estimativa** | 5 dias |

> [Spec](spec.md) · [Plano](plan.md) · [Tarefas](tasks.md) · [Roadmap](../ROADMAP.md)

---

## Parte A — Especificação

### 1. Contexto e objetivo
- **Problema:** sem estrutura para front/back/infra, dependências sem versão, `__pycache__` versionado, código morto,
  nenhum teste ou CI (D15, D16, D18).
- **Objetivo:** esqueleto do monorepo onde qualquer PR é validado automaticamente e o ambiente local sobe com um comando.
- **Indicador:** tempo do CI de PR ≤ 10 min; 100% dos PRs passam pelo CI.

### 2. Escopo
- **Inclui:** estrutura de pastas, `backend/` (FastAPI com `/healthz`), `frontend/` (Vite + React com página inicial),
  `legacy/` (Streamlit movido), tooling (uv, ruff, mypy, eslint, prettier, pre-commit), `docker-compose` com emuladores,
  `ci.yml`, template de PR, script de rastreabilidade de requisitos, limpeza de `__pycache__` e código morto.
- **Fora de escopo:** deploy (F02), autenticação (F03).

### 3. Requisitos funcionais
| ID | Requisito | Prio. |
|---|---|---|
| F01-RF-01 | Um dev com Docker consegue subir front + back + emuladores com `make dev` em uma máquina limpa | Must |
| F01-RF-02 | `GET /healthz` do backend responde `200 {"status":"ok","version":<sha>}` | Must |
| F01-RF-03 | A página inicial do React exibe o status retornado por `/healthz` | Must |
| F01-RF-04 | Todo PR executa lint, tipos, testes e build de front e back, e o resultado aparece no PR | Must |
| F01-RF-05 | O app Streamlit continua executável a partir de `legacy/` até o go-live | Must |

### 4. Requisitos técnicos
| ID | Requisito | Verificação |
|---|---|---|
| F01-RT-01 | Dependências travadas: `uv.lock` e `package-lock.json` versionados; CI usa `--frozen`/`npm ci` | CI |
| F01-RT-02 | `.gitignore` cobre `__pycache__`, `.env*`, `node_modules`, `dist`; nenhum `.pyc` no repo | `git ls-files` no CI |
| F01-RT-03 | mypy `strict` e TypeScript `strict` habilitados | config + CI |
| F01-RT-04 | `import-linter` com as regras de camadas da arquitetura | CI |
| F01-RT-05 | Imagem Docker do backend multi-stage, usuário não-root, < 300 MB | `docker inspect` no CI |
| F01-RT-06 | gitleaks em pre-commit e CI | CI |
| F01-RT-07 | `scripts/trace_requirements.py` falha se um RF de spec com status ≥ "Em validação" não tiver teste marcado | CI |

### 5. Teste final de aceitação
```gherkin
Funcionalidade: Esqueleto do monorepo

  Cenário: AT-F01-01 Ambiente local com um comando        # F01-RF-01, F01-RF-02, F01-RF-03
    Dado um clone limpo do repositório com Docker instalado
    Quando executo "make dev"
    Então "http://localhost:8000/healthz" responde 200 com status "ok"
    E "http://localhost:5173" exibe "API: ok"

  Cenário: AT-F01-02 PR com erro de lint é bloqueado       # F01-RF-04
    Dado um PR que introduz um import não utilizado no backend
    Então o check "ci / backend-lint" falha e o merge fica bloqueado

  Cenário: AT-F01-03 Streamlit legado continua rodando     # F01-RF-05
    Quando executo "make legacy"
    Então o app Streamlit abre a página "Agente Funcional"
```

### 6. Conformidade com a Constituição
| Artigo | Cumprimento |
|---|---|
| III Segredos | gitleaks; `.env*` ignorado |
| VI Testes | CI obrigatório desde o 1º dia; cobertura medida |
| VIII IaC | Ambiente local declarativo (compose) |

---

## Parte C — Validação
### 10. Rastreabilidade
| Requisito | Teste(s) | Status |
|---|---|---|
| F01-RF-01 | AT-F01-01 (com Docker: `make dev`) | ⬜ pendente — validado sem Docker, falta rodar o compose |
| F01-RF-02 | AT-F01-01, `backend/tests/unit/test_health.py` | ✅ |
| F01-RF-03 | AT-F01-01, `frontend/src/App.test.tsx` | ✅ |
| F01-RF-04 | AT-F01-02 (PR de prova com erro de lint) | ⬜ pendente — exige o CI rodando no GitHub e branch protection |
| F01-RF-05 | AT-F01-03 (`make legacy`) | ⬜ pendente |

### 11. Evidências
| Data | Commit | Ambiente | Execução | Resultado | Aceito por |
|---|---|---|---|---|---|
| 2026-11-13 | (este PR) | local, sem Docker | backend `uvicorn` + frontend `vite` + Chromium/Playwright | AT-F01-01 parcial: página exibe "API: ok" ([screenshot](evidencias/AT-F01-01.png)); `make lint` e `make test` verdes (back 100%, front 100% de linhas) | — |

**Pendências para o Gate 3 da F01**
- Rodar `make dev` numa máquina com Docker (o ambiente de desenvolvimento usado não tinha daemon Docker); o build da imagem também é verificado pelo job `backend` do CI.
- Ativar branch protection em `master` exigindo os checks `ci / backend`, `ci / frontend`, `ci / repo-hygiene` e 1 review; depois abrir o PR de prova do AT-F01-02.
- Executar AT-F01-03 (`make legacy`) com uma chave OpenAI válida.
- Aviso conhecido: `npm audit` acusa 1 vulnerabilidade moderada (minimatch dentro do `typescript-eslint` 8.72.2, só em desenvolvimento, sem correção publicada na 8.x). O CI audita dependências de produção em nível alto.
