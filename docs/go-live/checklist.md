# Checklist de prontidão do go-live (F12-RT-01)

Cada item só é marcado com a evidência ao lado (link, comando, data). O go-live (Dia D) acontece com
todos marcados. Revisão final: PO.

| # | Item | Status | Evidência |
|---|---|---|---|
| 1 | SLO de disponibilidade e alertas ativos | ✅ | F11: `terraform apply` 2026-11-18; AT-F11-03 (e-mail do alerta recebido pelo PO) |
| 2 | Restauração do Firestore ensaiada (PITR → banco temporário) | ⬜ | `docs/runbooks/firestore-restauracao.md`; registrar horário, documento conferido e a limpeza |
| 3 | Runbooks revisados | ⬜ | `docs/runbooks/` lidos pelo PO depois do ensaio de restauração |
| 4 | Evals ≥ baseline | ⬜ | `uv run --project backend python evals/run.py --compare evals/results/<baseline>.json evals/results/<novo>.json` |
| 5 | ZAP baseline sem achados altos | ✅ | F11-RT-10, run 44282497680 (0 altos) |
| 6 | Custo estimado por mês aprovado pelo PO | ⬜ | tabela abaixo |
| 7 | Privacidade publicada | ⬜ | https://specsflow-ai.web.app/privacy (F12-RF-04) |
| 8 | App Check em `enforce` | ⬜ | F11-T008 (a partir de 2026-11-25); AT-F11-04 |
| 9 | HTTPS | ✅ | Firebase Hosting e Cloud Run só servem HTTPS; sem domínio próprio (decisão do PO) |
| 10 | Contato de suporte no About | ⬜ | https://specsflow-ai.web.app/about → "Open an issue on GitHub" (F12-RF-03) |
| 11 | AT-F12-01 verde em prd | ⬜ | `e2e/f12-golive.spec.ts` com `E2E_PRD=1` |
| 12 | Beta concluído, sem Sev1 aberto | ⬜ | `docs/go-live/beta.md` → resumo do feedback |

## Custo estimado (item 6)

Recursos do app no projeto compartilhado `pcb-inspect`. As faixas gratuitas são do projeto inteiro.

| Item | Base | Estimativa/mês |
|---|---|---|
| Gemini (Vertex AI) | cota de 200 mil tokens/usuário/dia; custo real no dashboard (`cost_usd`) | ≈ US$ 0,01–0,05 por usuário ativo/dia |
| Cloud Run | `min_instances = 0`, 1 vCPU, 1 GiB | faixa gratuita na escala do beta |
| Firestore, Hosting, Logging, Trace, uptime | uso baixo | faixa gratuita |
| reCAPTCHA Enterprise (App Check) | 10 mil avaliações/mês grátis | US$ 0 |
| Alertas do Monitoring (6 condições) | se a cobrança por condição estiver valendo | ≈ US$ 9 |
| KMS (1 chave) | US$ 0,06/versão + operações | < US$ 0,10 |

O alerta "custo estimado de LLM > US$ 2/dia" avisa antes de qualquer surpresa (`docs/runbooks/custo.md`).
