# Runbook — restauração do Firestore

O banco `specflow` tem PITR (7 dias, F02-RT-04) e backup diário (`google_firestore_backup_schedule`).
Restaurar **sempre para um banco novo** e copiar o que for preciso: nunca sobrescrever `specflow` nem
tocar o `(default)` do projeto.

## Dados de um usuário apagados por engano (PITR, até 7 dias)

```bash
# 1. Bucket temporário (prefixo do app) e exportação do banco num instante (minuto cheio, ≤ 7 dias)
gcloud storage buckets create gs://pcb-inspect-specflow-restore --location="$REGION" --project "$PROJECT"
gcloud firestore export gs://pcb-inspect-specflow-restore/$(date +%Y%m%d-%H%M) \
  --project "$PROJECT" --database "$DB" --snapshot-time=2026-11-18T10:00:00Z
# 2. Importa num banco temporário e confere
gcloud firestore databases create --database=specflow-restore --location="$REGION" --project "$PROJECT"
gcloud firestore import gs://pcb-inspect-specflow-restore/<pasta> --database=specflow-restore --project "$PROJECT"
# 3. Copia os documentos de users/{uid}/… do banco temporário para o specflow (script ou console)
# 4. Apaga o banco temporário e o bucket da exportação
gcloud firestore databases delete --database=specflow-restore --project "$PROJECT"
gcloud storage rm --recursive gs://pcb-inspect-specflow-restore
```

## Banco inteiro perdido (backup diário)

```bash
gcloud firestore backups list --project "$PROJECT" --location "$REGION"
gcloud firestore databases restore --project "$PROJECT" \
  --source-backup=projects/$PROJECT/locations/$REGION/backups/<id> --destination-database=specflow-restore
```

Depois aponte a API para o banco restaurado (variável `FIRESTORE_DATABASE` no Terraform do Cloud Run)
ou copie de volta. O bucket de exportação, se criado, também tem o prefixo `specflow`.
