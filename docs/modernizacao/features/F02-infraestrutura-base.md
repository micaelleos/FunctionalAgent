# F02 — Infraestrutura base GCP/Firebase (Terraform) e pipeline de deploy

| Campo | Valor |
|---|---|
| **Status** | Rascunho |
| **Fase** | 0 — Fundação |
| **Dependências** | F01 |
| **ADRs** | ADR-001, ADR-002 |
| **Estimativa** | 7 dias |

## Parte A — Especificação

### 1. Contexto e objetivo
- **Problema:** não há ambiente hospedado nem processo de deploy.
- **Objetivo:** projetos `dev` e `prd` criados por Terraform, com deploy automatizado (Cloud Run + Hosting) sem chaves.
- **Indicador:** merge → dev em ≤ 15 min; rollback em ≤ 5 min (medido em ensaio).

### 2. Escopo
- **Inclui:** módulos Terraform de `05-infraestrutura.md §2`, WIF, `deploy.yml`, `infra.yml`, `firebase.json`
  (headers de segurança), Firestore com regras "nega tudo" e índices, budget alerts, runbook de rollback.
- **Fora de escopo:** domínio próprio (opcional, fim da Fase 3), App Check (F11), dashboards detalhados (F11).

### 3. Requisitos funcionais
| ID | Requisito | Prio. |
|---|---|---|
| F02-RF-01 | Um merge em `master` publica automaticamente backend e frontend em dev | Must |
| F02-RF-02 | A publicação em prd exige aprovação manual e usa canário com promoção ou rollback | Must |
| F02-RF-03 | O frontend publicado em dev exibe o status do backend publicado em dev | Must |
| F02-RF-04 | Um PR com label `preview` recebe URLs de preview (front + back) em comentário | Should |

### 4. Requisitos técnicos
| ID | Requisito | Verificação |
|---|---|---|
| F02-RT-01 | 100% dos recursos em Terraform; `terraform plan` sem diffs após `apply` | CI `infra.yml` |
| F02-RT-02 | Nenhuma chave JSON de service account existe (WIF somente) | `gcloud iam service-accounts keys list` vazio |
| F02-RT-03 | SA de runtime com papéis de `05-infraestrutura.md §3` e nada além | teste de política (script) |
| F02-RT-04 | Firestore: regras negam acesso de cliente; PITR + backup diário em prd | teste com emulador de regras + `gcloud` |
| F02-RT-05 | Cloud Run: timeout 300 s, concorrência 40, imagem por digest, startup probe | `gcloud run services describe` |
| F02-RT-06 | Hosting com CSP, HSTS, `X-Content-Type-Options`, `Referrer-Policy` | teste E2E lê headers |
| F02-RT-07 | Budget alert em 50/90/100% do orçamento definido | Terraform |
| F02-RT-08 | Estado do Terraform em GCS com versionamento | Terraform |

### 5. Teste final de aceitação
```gherkin
Funcionalidade: Infraestrutura e deploy

  Cenário: AT-F02-01 Merge publica em dev                    # F02-RF-01, F02-RF-03
    Dado um commit mergeado em master que altera a versão exibida
    Quando o workflow "deploy" termina
    Então a URL de dev do Hosting exibe "API: ok" e a nova versão

  Cenário: AT-F02-02 Produção exige aprovação e faz canário  # F02-RF-02
    Dado o deploy em dev concluído
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
| II Privacidade | Regras do Firestore negam cliente |
| III Segredos | Secret Manager; WIF; nenhum segredo no estado do Terraform |
| VII Simplicidade | Somente serviços serverless; sem LB |
| VIII IaC | Tudo em Terraform, deploy só via pipeline, rollback < 5 min |

## Parte B — Plano técnico

### 7. Desenho
- Bootstrap manual **único e documentado** (criar projetos, bucket de estado, billing) em `infra/bootstrap/README.md`;
  todo o resto por Terraform.
- `deploy.yml` conforme `06-cicd-deploy.md`. Canário: script que consulta métricas do Cloud Monitoring
  (`run.googleapis.com/request_count` por `response_code_class`) da tag `rc-<sha>`.
- `firestore.rules`: `match /{document=**} { allow read, write: if false; }`.
- **Rollback:** `update-traffic` para revisão anterior; `firebase hosting:rollback`.

### 8. Tarefas
| # | Tarefa | Teste | Est. |
|---|---|---|---|
| 1 | Bootstrap: projetos, billing, bucket de estado | checklist | 0,5 d |
| 2 | Módulos: services, artifact_registry, firestore, secrets, kms | `terraform validate` + plan | 1,5 d |
| 3 | Módulos: cloud_run, firebase (hosting, auth), wif, budget | plan/apply dev | 1,5 d |
| 4 | `firebase.json` com headers, `firestore.rules`, índices | AT-F02-04, teste de headers | 0,5 d |
| 5 | `deploy.yml` (dev, prd com aprovação, canário, rollback) | AT-F02-01..03 | 2 d |
| 6 | `preview.yml` + `infra.yml` | PR de prova | 1 d |

### 9. Plano de testes
Terraform: `fmt`, `validate`, `tflint`, `plan` no PR. Regras Firestore: `@firebase/rules-unit-testing`. E2E: AT-F02-01..04.

## Parte C — Validação
### 10. Rastreabilidade
| Requisito | Teste(s) | Status |
|---|---|---|
| F02-RF-01 | AT-F02-01 | ⬜ |
| F02-RF-02 | AT-F02-02, AT-F02-03 | ⬜ |
| F02-RF-03 | AT-F02-01 | ⬜ |
| F02-RF-04 | PR de prova com label `preview` | ⬜ |
| F02-RT-04 | AT-F02-04, `firestore-rules.test.ts` | ⬜ |

### 11. Evidências
| Data | Commit | Ambiente | Execução | Resultado | Aceito por |
|---|---|---|---|---|---|
