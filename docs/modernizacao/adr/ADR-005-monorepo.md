# ADR-005 — Monorepo com frontend, backend e infraestrutura

- **Status:** Proposto · **Data:** 2026-11-13

## Contexto

Front (React), back (Python) e infra (Terraform) mudam juntos com frequência, especialmente o contrato da API.
O projeto tem 1–2 desenvolvedores.

## Decisão

Um único repositório (`FunctionalAgent`) com `frontend/`, `backend/`, `infra/`, `docs/` e configuração Firebase
na raiz. Workflows do GitHub Actions filtrados por caminho. O código Streamlit vai para `legacy/` até o go-live
(F12) e depois é removido (fica no histórico do git e numa tag `legacy-streamlit-final`).

## Consequências

- ✅ Uma mudança de contrato (back + cliente gerado + front) é um único PR, validado pelo CI de contrato.
- ✅ Specs, ADRs e código lado a lado.
- ⚠️ CI precisa de filtros por caminho para continuar rápido.
- 🔁 Revisitar se o time crescer e front/back tiverem ciclos de release independentes.
