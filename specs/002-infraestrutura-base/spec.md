# F02 — Infraestrutura base GCP/Firebase (Terraform) e pipeline de deploy

| Campo | Valor |
|---|---|
| **Status** | Em implementação |
| **Fase** | 0 — Fundação |
| **Dependências** | F01 |
| **ADRs** | ADR-001, ADR-002 |
| **Estimativa** | 7 dias |
| **Gates** | Gate 0 e Gate 1 aprovados pelo dono do produto em 2026-11-14 |

> [Spec](spec.md) · [Plano](plan.md) · [Tarefas](tasks.md) · [Roadmap](../ROADMAP.md)

---

## Parte A — Especificação

### 1. Contexto e objetivo
- **Problema:** não há ambiente hospedado nem processo de deploy.
- **Objetivo:** recursos do app criados por Terraform no projeto compartilhado do portfólio, com deploy
  automatizado (Cloud Run + Hosting) sem chaves.
- **Indicador:** merge → produção (após aprovação) em ≤ 30 min; rollback em ≤ 5 min (medido em ensaio).

### 2. Escopo
- **Inclui:** módulos Terraform de `05-infraestrutura.md §2`, WIF, `deploy.yml`, `infra.yml`, `firebase.json`
  (headers de segurança), banco Firestore próprio com regras "nega tudo", runbook de rollback.
- **Fora de escopo:** domínio próprio (opcional, fim da Fase 3), App Check (F11), dashboards detalhados (F11),
  ambientes `dev`/`stg`, provedor Google no Auth (F03), montagem do segredo do LLM no Cloud Run (F05),
  Google Analytics (F16), orçamento (é do projeto compartilhado, não do app).
- **Decisões do PO (2026-11-14):** o app vive no projeto compartilhado do portfólio `pcb-inspect`;
  **um ambiente só (produção) + previews por PR**; URL `https://specsflow-ai.web.app` (site criado no
  console); recursos com prefixo `specflow` e banco Firestore próprio `specflow`; região `us-central1`;
  sem domínio próprio; `min-instances=0`; Terraform enxuto (Constituição VIII mantida).

### 3. Requisitos funcionais
| ID | Requisito | Prio. |
|---|---|---|
| F02-RF-01 | Um merge em `master` dispara automaticamente o pipeline de publicação (build, revisão candidata sem tráfego, smoke test) | Must |
| F02-RF-02 | A publicação em produção exige aprovação manual e usa canário com promoção ou rollback | Must |
| F02-RF-03 | O frontend publicado exibe o status e a versão do backend publicado | Must |
| F02-RF-04 | Um PR com label `preview` recebe URLs de preview (front + back) em comentário | Should |

### 4. Requisitos técnicos
| ID | Requisito | Verificação |
|---|---|---|
| F02-RT-01 | 100% dos recursos em Terraform; `terraform plan` sem diffs após `apply` | CI `infra.yml` |
| F02-RT-02 | Nenhuma chave JSON de service account existe (WIF somente) | `gcloud iam service-accounts keys list` vazio |
| F02-RT-03 | SA de runtime com papéis de `05-infraestrutura.md §3` e nada além | teste de política (script) |
| F02-RT-04 | Firestore (banco `specflow`): regras negam acesso de cliente; PITR + backup diário | teste com emulador de regras + `gcloud` |
| F02-RT-05 | Cloud Run: timeout 300 s, concorrência 40, imagem por digest, startup probe | `gcloud run services describe` |
| F02-RT-06 | Hosting com CSP, HSTS, `X-Content-Type-Options`, `Referrer-Policy` | teste E2E lê headers |
| F02-RT-07 | ~~Budget alert em 50/90/100%~~ — **removido em 2026-11-14**: o orçamento é do projeto compartilhado, gerido fora do app | — |
| F02-RT-08 | Estado do Terraform em GCS com versionamento | Terraform |
| F02-RT-09 | O Terraform só gerencia recursos do app (prefixo `specflow`, site `specsflow-ai`); não altera o banco `(default)`, a configuração de Auth, o orçamento nem recursos de outros apps do projeto | revisão do `plan` + checklist do bootstrap |

### 5. Teste final de aceitação
```gherkin
Funcionalidade: Infraestrutura e deploy

  Cenário: AT-F02-01 Merge publica o app                     # F02-RF-01, F02-RF-03
    Dado um commit mergeado em master que altera a versão exibida
    Quando o workflow "deploy" termina, após a aprovação
    Então https://specsflow-ai.web.app exibe "API: ok" e a nova versão

  Cenário: AT-F02-02 Produção exige aprovação e faz canário  # F02-RF-02
    Dado o build da imagem concluído
    Então o job "deploy-prd" aguarda aprovação no GitHub Environment "prd"
    Quando aprovo
    Então uma nova revisão recebe 10% do tráfego e, após 15 min saudável, 100%

  Cenário: AT-F02-03 Rollback em menos de 5 minutos           # F02-RF-02
    Dado uma revisão nova com /healthz retornando 500 (ensaio controlado)
    Quando o canário detecta erro
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
| III Segredos | Secret Manager; WIF; nenhum segredo no estado do Terraform |
| VII Simplicidade | Somente serviços serverless; sem LB; um ambiente só |
| VIII IaC | Tudo em Terraform, deploy só via pipeline, rollback < 5 min |

---

## Parte C — Validação
### 10. Rastreabilidade
| Requisito | Teste(s) | Status |
|---|---|---|
| F02-RF-01 | AT-F02-01 (`frontend/e2e/f02-deploy.spec.ts`) | ⬜ |
| F02-RF-02 | AT-F02-02, AT-F02-03, `scripts/test_canary.py` | ⬜ |
| F02-RF-03 | AT-F02-01 (`frontend/e2e/f02-deploy.spec.ts`) | ⬜ |
| F02-RF-04 | PR de prova com label `preview`, `backend/tests/unit/test_cors.py` | ⬜ |
| F02-RT-04 | AT-F02-04 (`infra/firestore-rules/firestore-rules.test.ts`, emulador) | ⬜ |

### 11. Evidências
| Data | Commit | Ambiente | Execução | Resultado | Aceito por |
|---|---|---|---|---|---|
| 2026-11-14 | (este PR) | local | `terraform validate`/`tflint`, `actionlint`, pytest (`scripts/`, backend), Playwright local, emulador de regras | Terraform válido; workflows válidos; canário 10 testes; CORS de preview; AT-F02-01 passa contra stack local; AT-F02-04 passa no emulador (e falha com regras abertas). Nada aplicado no GCP ainda | — |
