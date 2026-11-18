# Runbook — credencial vazada

O app não tem chave de LLM (o Gemini é chamado pela conta de serviço do Cloud Run, ADR-008) nem chave
de conta de serviço. O que pode vazar:

## Token do Jira de um usuário

O token fica cifrado com KMS no Firestore e nunca é devolvido nem logado (ADR-004). Se ele aparecer
em algum lugar (log, print, commit):

1. O dono revoga o token em https://id.atlassian.com/manage-profile/security/api-tokens.
2. Cria um novo e troca em Settings → Jira connection → Replace token.
3. Se veio de um log do app, abra um incidente: é bug (F04-RT-03). Apague as entradas com
   `gcloud logging` só se a política do projeto permitir; senão restrinja o acesso ao bucket de logs.

## Token do sandbox do Jira (testes de aceitação)

Fica só no `.env.local` do PO (`JIRA_SANDBOX_API_TOKEN`). Revogue e gere outro como acima e
atualize o `.env.local`. Nunca commitar; o gitleaks do CI barra o padrão conhecido.

## Credenciais do GCP do PO (gcloud/ADC)

`gcloud auth revoke --all` na máquina afetada, troque a senha da conta Google e revise o IAM do
projeto (`gcloud projects get-iam-policy pcb-inspect`). Não há chave de conta de serviço para
revogar; se uma for criada por engano: `gcloud iam service-accounts keys list/delete`.
