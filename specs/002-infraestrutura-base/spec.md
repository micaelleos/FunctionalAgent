# F02 — Infraestrutura base GCP/Firebase (Terraform) e deploy por `make deploy`

| Campo | Valor |
|---|---|
| **Status** | Em implementação |
| **Fase** | 0 — Fundação |
| **Dependências** | F01 |
| **ADRs** | ADR-001, ADR-002, ADR-006 |
| **Estimativa** | 5 dias |
| **Gates** | Gate 0 e Gate 1 aprovados pelo dono do produto em 2026-11-14; escopo revisado no mesmo dia (sem CI/CD, ADR-006) |

> [Spec](spec.md) · [Plano](plan.md) · [Tarefas](tasks.md) · [Roadmap](../ROADMAP.md)

---

## Parte A — Especificação

### 1. Contexto e objetivo
- **Problema:** não há ambiente hospedado nem processo de deploy.
- **Objetivo:** recursos do app criados por Terraform no projeto compartilhado do portfólio e um deploy
  de um comando (`make deploy`) que publica API e SPA com segurança.
- **Indicador:** `make deploy` publica em ≤ 10 min; rollback em ≤ 5 min (medido em ensaio).

### 2. Escopo
- **Inclui:** módulos Terraform de `05-infraestrutura.md §2` (sem WIF), `make deploy`
  (`scripts/deploy.sh`), `firebase.json` (headers de segurança), banco Firestore próprio com regras
  "nega tudo", runbook de rollback, checagem estática do Terraform no CI.
- **Fora de escopo:** pipeline de CD (deploy/infra pelo GitHub Actions, aprovação, canário, previews por
  PR, WIF), removido em 2026-11-14 (ADR-006); domínio próprio; App Check (F11); dashboards detalhados
  (F11); ambientes `dev`/`stg`; provedor Google no Auth (F03); montagem do segredo do LLM no Cloud Run
  (F05); Google Analytics (F16); orçamento (é do projeto compartilhado, não do app).
- **Decisões do PO (2026-11-14):**
  - o app vive no projeto compartilhado do portfólio `pcb-inspect`;
  - **um ambiente só (produção)**;
  - URL `https://specsflow-ai.web.app` (site criado no console);
  - recursos com prefixo `specflow` e banco Firestore próprio `specflow`;
  - região `us-central1`; `min-instances=0`;
  - Terraform enxuto;
  - **deploy manual por `make deploy`, sem CI/CD**, por ser projeto de portfólio (ADR-006,
    Constituição v2.0.0).

### 3. Requisitos funcionais
| ID | Requisito | Prio. |
|---|---|---|
| F02-RF-01 | `make deploy` publica a API (imagem por digest, revisão sem tráfego, smoke em `/health` com a versão do commit, 100% do tráfego) e depois o SPA no Hosting | Must |
| F02-RF-02 | Se o smoke falhar, o tráfego continua na revisão anterior; um rollback manual leva < 5 min (`docs/runbooks/rollback.md`) | Must |
| F02-RF-03 | O frontend publicado exibe o status e a versão do backend publicado | Must |

> F02-RF-04 (previews por PR) foi removido em 2026-11-14 (ADR-006).

### 4. Requisitos técnicos
| ID | Requisito | Verificação |
|---|---|---|
| F02-RT-01 | 100% dos recursos em Terraform; `terraform plan` sem diffs após `apply` | `terraform plan -detailed-exitcode` |
| F02-RT-02 | Nenhuma chave JSON de service account existe; o deploy usa o login de usuário do gcloud | `gcloud iam service-accounts keys list` vazio |
| F02-RT-03 | SA de runtime com papéis de `05-infraestrutura.md §3` e nada além | `gcloud projects get-iam-policy` |
| F02-RT-04 | Firestore (banco `specflow`): regras negam acesso de cliente; PITR + backup diário | teste com emulador de regras + `gcloud` |
| F02-RT-05 | Cloud Run: timeout 300 s, concorrência 40, imagem por digest, startup probe | `gcloud run services describe` |
| F02-RT-06 | Hosting com CSP, HSTS, `X-Content-Type-Options`, `Referrer-Policy` | teste E2E lê headers |
| F02-RT-07 | ~~Budget alert em 50/90/100%~~ — **removido em 2026-11-14**: o orçamento é do projeto compartilhado, gerido fora do app | — |
| F02-RT-08 | Estado do Terraform em GCS com versionamento | `gcloud storage buckets describe` |
| F02-RT-09 | O Terraform só gerencia recursos do app (prefixo `specflow`, site `specsflow-ai`); não altera o banco `(default)`, a configuração de Auth, o orçamento nem recursos de outros apps do projeto | revisão do `plan` + checklist do bootstrap |

### 5. Teste final de aceitação
```gherkin
Funcionalidade: Infraestrutura e deploy

  Cenário: AT-F02-01 make deploy publica o app               # F02-RF-01, F02-RF-03
    Dado um commit com uma nova versão
    Quando rodo "make deploy"
    Então https://specsflow-ai.web.app exibe "API: ok" e a nova versão

  Cenário: AT-F02-02 Smoke falho não move tráfego            # F02-RF-02
    Dado uma revisão nova cujo /health não responde ok com a versão esperada
    Quando "make deploy-api" faz o smoke test
    Então o comando falha e 100% do tráfego continua na revisão anterior

  Cenário: AT-F02-03 Rollback em menos de 5 minutos          # F02-RF-02
    Dado uma revisão nova recebendo 100% do tráfego
    Quando sigo docs/runbooks/rollback.md
    Então o tráfego volta 100% para a revisão anterior em até 5 minutos

  Cenário: AT-F02-04 Cliente não acessa Firestore diretamente # F02-RT-04
    Dado um usuário autenticado no Firebase
    Quando tenta ler "users/{uid}" via SDK do cliente
    Então recebe "permission-denied"
```

### 6. Conformidade com a Constituição
| Artigo | Cumprimento |
|---|---|
| II Privacidade | Regras do Firestore negam cliente; banco próprio, isolado dos outros apps do projeto |
| III Segredos | Secret Manager; nenhuma chave de SA; nenhum segredo no estado do Terraform |
| VII Simplicidade | Somente serviços serverless; sem LB; um ambiente só; sem pipeline de CD |
| VIII IaC | Tudo em Terraform; deploy só por `make deploy` com smoke antes do tráfego; rollback < 5 min (v2.0.0, ADR-006) |

---

## Parte C — Validação
### 10. Rastreabilidade
| Requisito | Teste(s) | Status |
|---|---|---|
| F02-RF-01 | AT-F02-01 (`frontend/e2e/f02-deploy.spec.ts`, contra produção) | ✅ |
| F02-RF-02 | AT-F02-02, AT-F02-03 (ensaio de `docs/runbooks/rollback.md`) | ⬜ |
| F02-RF-03 | AT-F02-01 (`frontend/e2e/f02-deploy.spec.ts`) | ✅ |
| F02-RT-04 | AT-F02-04 (`infra/firestore-rules/firestore-rules.test.ts`, emulador) | ✅ |

### 11. Evidências
| Data | Commit | Ambiente | Execução | Resultado | Aceito por |
|---|---|---|---|---|---|
| 2026-11-14 | (este PR) | local | `terraform validate`/`tflint`, `actionlint`, pytest (`scripts/`, backend), Playwright local, emulador de regras | Terraform válido; workflows válidos; canário 10 testes; CORS de preview; AT-F02-01 passa contra stack local; AT-F02-04 passa no emulador (e falha com regras abertas). Nada aplicado no GCP ainda | — |
| 2026-11-14 | (este PR) | prd (`pcb-inspect`) | Bootstrap §1–2: bucket `pcb-inspect-tfstate`, primeiro apply local, verificação §5 | RT-01 plan sem diferenças; RT-02 0 chaves nas 3 SAs; RT-03 4 papéis (`datastore.user` com condição `specflow-database-only`); RT-04 PITR e proteção contra exclusão ativos, backup diário 14 d; RT-05 timeout 300 s, concorrência 40 (imagem ainda é a provisória, até o 1º deploy); RT-08 versionamento ativo; RT-09 só recursos `specflow-*`/`specsflow-ai`, `pcb-defect-api` e banco `(default)` intocados. Pendentes: GitHub (§3), RT-06 (depende do 1º deploy do frontend), AT-F02-01..03 | — |
| 2026-11-14 | `2918a76ff8dd-dirty` | prd | Deploy manual (`make deploy`, sem CI/CD por decisão do PO) + `E2E_BASE_URL=https://specsflow-ai.web.app npx playwright test` | API na revisão `specflow-api-00004-zet` (smoke em `/health` antes do tráfego); SPA em https://specsflow-ai.web.app; AT-F02-01 passa; RT-06 passa (CSP, HSTS 1 ano, nosniff, Referrer-Policy, X-Frame-Options). `/healthz` dá 404 na URL `*.run.app` (caminho reservado pelo Google), então os clientes externos usam `/health` | — |
| 2026-11-14 | `2918a76ff8dd-dirty` | prd | Revisão de escopo (ADR-006): `terraform apply` que remove o WIF e ajusta o Cloud Run e o Artifact Registry; `make deploy-api` pela API v2 | 13 recursos do WIF destruídos (inclusive o papel Owner da SA `specflow-terraform`); limpeza do Artifact Registry mantém 3 imagens; o Cloud Run sem `CORS_ORIGIN_REGEX` deu 409 (nome de revisão fixado pelo `gcloud`), corrigido no Terraform e no deploy; revisão `specflow-api-00005-vgm` com 100% em "latest"; `terraform plan` sem diferenças (RT-01) | — |
