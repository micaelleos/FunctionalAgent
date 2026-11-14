# ADR-006 — Deploy manual com `make deploy`, sem pipeline de CD

- **Status:** Aceito · **Data:** 2026-11-14 · **Decisor:** dono do produto

## Contexto

O SpecFlow AI é um projeto de portfólio com uma pessoa só, hospedado no projeto GCP compartilhado
`pcb-inspect`, com um único ambiente (produção). A F02 tinha sido implementada com CD completo no GitHub
Actions: `deploy.yml` com aprovação, canário de 10% por 15 min e rollback automático, `preview.yml` com
previews por PR, `infra.yml` com apply aprovado, e Workload Identity Federation com duas service accounts,
uma delas Owner do projeto compartilhado.

Para esse contexto, isso custa mais do que entrega:
- exige administrar environments, variáveis e proteções no GitHub;
- mantém uma SA com papel Owner num projeto que hospeda outros apps;
- e um canário de 15 min não tem tráfego real para observar.

## Decisão

- **Deploy da aplicação:** `make deploy` (`scripts/deploy.sh`), rodado pelo dono do produto com o próprio
  login do gcloud:
  1. cria a imagem e envia ao Artifact Registry;
  2. cria uma revisão do Cloud Run sem tráfego;
  3. faz um smoke test em `/health`, que precisa responder `ok` com a versão do commit;
  4. passa 100% do tráfego para a revisão nova;
  5. publica o SPA no Firebase Hosting.
- **Infraestrutura:** continua 100% em Terraform (Art. VIII.1), aplicada localmente com
  `terraform apply`, com o estado em `gs://pcb-inspect-tfstate`.
- **CI no GitHub Actions continua** (`ci.yml`): lint, testes, regras, imagem e Terraform estático.
  É o Gate 2.
- **Removidos:**
  - os workflows `deploy.yml`, `preview.yml` e `infra.yml`;
  - as ações compostas e o `scripts/canary.py`;
  - o módulo Terraform `wif` (pool, provider e as SAs `specflow-deployer` e `specflow-terraform`);
  - o CORS de canais de preview.

## Consequências

- ✅ Nenhuma credencial do GCP fica com o GitHub e nenhuma SA tem papel Owner. Continua sem chaves JSON
  (o login é de usuário).
- ✅ Bootstrap menor: não há environments, variáveis nem WIF para configurar.
- ✅ O rollback continua abaixo de 5 min (Art. VIII.3): o smoke falho não move tráfego, e o
  `docs/runbooks/rollback.md` troca o tráfego para a revisão anterior.
- ⚠️ O deploy depende de quem roda o comando. Commit sujo sai com a versão `<sha>-dirty`, que fica
  visível no app.
- ⚠️ Sem canário e sem preview: a validação antes de produção é o CI mais o smoke da revisão sem tráfego.
- ↩️ Reverter: recuperar os arquivos removidos no histórico do git (PR da F02) e emendar a Constituição.
