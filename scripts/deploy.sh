#!/usr/bin/env bash
# Deploy manual de produção a partir da máquina local (sem CI/CD).
#   scripts/deploy.sh api   # build + push da imagem, revisão sem tráfego, smoke, 100% do tráfego
#   scripts/deploy.sh web   # build do SPA apontando para a API e publicação no Firebase Hosting
# Requer gcloud autenticado (Owner no projeto) e Docker (ADR-006). O deploy do Hosting também usa as
# credenciais padrão do gcloud (`gcloud auth application-default login`).
set -euo pipefail

PROJECT=${PROJECT:-pcb-inspect}
REGION=${REGION:-us-central1}
SERVICE=${SERVICE:-specflow-api}
SITE=${SITE:-specsflow-ai}
REPOSITORY=${REPOSITORY:-$REGION-docker.pkg.dev/$PROJECT/specflow/api}
FIREBASE_TOOLS=firebase-tools@13.35.1
GCLOUD=${GCLOUD:-$(command -v gcloud || echo "$HOME/google-cloud-sdk/bin/gcloud")}

ROOT=$(cd "$(dirname "$0")/.." && pwd)
VERSION=${VERSION:-$(git -C "$ROOT" rev-parse --short=12 HEAD)$(git -C "$ROOT" diff --quiet HEAD || echo -dirty)}
# Versão que o smoke exige em /health. Só muda no ensaio do AT-F02-02 (docs/runbooks/rollback.md).
EXPECTED_VERSION=${EXPECTED_VERSION:-$VERSION}

log() { printf '\n==> %s\n' "$*"; }
service_json() { "$GCLOUD" run services describe "$SERVICE" --project "$PROJECT" --region "$REGION" --format=json; }

# Cloud Run Admin API v2. O deploy não usa `gcloud run deploy` porque ele dá nome às revisões
# (template.revision); com o nome fixado, qualquer mudança de configuração feita depois pelo
# Terraform falha com 409 ("revision ... with different configuration already exists").
RUN_API="https://run.googleapis.com/v2/projects/$PROJECT/locations/$REGION/services/$SERVICE"
run_api() { curl -sS --fail-with-body -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" "$@"; }
run_get() { run_api "$RUN_API"; }
# PATCH do serviço inteiro (campos só de saída são ignorados) e espera a operação terminar.
run_patch() {
  local op
  op=$(run_api -X PATCH "$RUN_API" -d @- | jq -r '.name')
  for _ in $(seq 1 120); do
    local st; st=$(run_api "https://run.googleapis.com/v2/$op")
    if jq -e '.done' <<<"$st" >/dev/null; then
      if jq -e '.error' <<<"$st" >/dev/null; then jq -r '.error.message' <<<"$st" >&2; return 1; fi
      return 0
    fi
    sleep 3
  done
  echo "Tempo esgotado esperando $op" >&2; return 1
}

# Smoke do modelo (F05-RT-09): chama o Gemini configurado no serviço (LLM_MODEL/LLM_LOCATION) com
# uma pergunta curta. Confirma que a API do Vertex está ativa e que o ID do modelo existe; a
# permissão da SA do Cloud Run é do Terraform (roles/aiplatform.user).
smoke_llm() {
  local svc=$1 model location host
  model=$(jq -r '[.template.containers[0].env[]? | select(.name == "LLM_MODEL") | .value][0] // empty' <<<"$svc")
  location=$(jq -r '[.template.containers[0].env[]? | select(.name == "LLM_LOCATION") | .value][0] // "global"' <<<"$svc")
  if [ -z "$model" ]; then echo "LLM_MODEL não configurado no serviço (terraform apply)" >&2; return 1; fi
  host=$([ "$location" = global ] && echo aiplatform.googleapis.com || echo "$location-aiplatform.googleapis.com")
  log "Smoke do modelo $model ($location)"
  curl -sS --fail-with-body -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
    "https://$host/v1/projects/$PROJECT/locations/$location/publishers/google/models/$model:generateContent" \
    -d '{"contents":[{"role":"user","parts":[{"text":"Responda só: ok"}]}],"generationConfig":{"maxOutputTokens":16}}' \
    | jq -e '.candidates | length > 0' >/dev/null
}

deploy_api() {
  local tag="rc-${VERSION//[^a-z0-9]/-}" image svc previous revision tag_url url ok=""
  TOKEN=$("$GCLOUD" auth print-access-token)

  log "Build da imagem (versão $VERSION)"
  docker build --provenance=false --sbom=false --build-arg APP_VERSION="$VERSION" \
    -t "$REPOSITORY:$VERSION" "$ROOT/backend"

  log "Push para o Artifact Registry"
  docker login -u oauth2accesstoken --password-stdin "https://${REPOSITORY%%/*}" <<<"$TOKEN" >/dev/null
  docker push "$REPOSITORY:$VERSION" >/dev/null
  image=$(docker inspect --format '{{index .RepoDigests 0}}' "$REPOSITORY:$VERSION")
  echo "$image"

  svc=$(run_get)
  smoke_llm "$svc" || { echo "Smoke do modelo falhou; nada foi publicado." >&2; exit 1; }
  previous=$(jq -r '([.trafficStatuses[]? | select(.percent == 100) | .revision // empty][0])
    // (.latestReadyRevision | split("/") | last)' <<<"$svc")

  log "Revisão nova sem tráfego (tag $tag); tráfego fixo em $previous"
  jq --arg img "$image" --arg prev "$previous" --arg tag "$tag" '
    .template.containers[0].image = $img
    | del(.template.revision)
    | .traffic = [
        {type: "TRAFFIC_TARGET_ALLOCATION_TYPE_REVISION", revision: $prev, percent: 100},
        {type: "TRAFFIC_TARGET_ALLOCATION_TYPE_LATEST", tag: $tag, percent: 0}
      ]' <<<"$svc" | run_patch
  svc=$(run_get)
  revision=$(jq -r '.latestCreatedRevision | split("/") | last' <<<"$svc")
  tag_url=$(jq -r --arg t "$tag" '.trafficStatuses[] | select(.tag == $t) | .uri' <<<"$svc")
  url=$(jq -r '.uri' <<<"$svc")

  log "Smoke test de $revision em $tag_url/health"
  for _ in $(seq 1 10); do
    if curl -fsS "$tag_url/health" | jq -e --arg v "$EXPECTED_VERSION" '.status == "ok" and .version == $v'; then
      ok=1; break
    fi
    sleep 3
  done

  if [ -z "$ok" ]; then
    echo "Smoke falhou; o tráfego continua em $previous." >&2
    jq --arg prev "$previous" '.traffic = [{type: "TRAFFIC_TARGET_ALLOCATION_TYPE_REVISION", revision: $prev, percent: 100}]' \
      <<<"$svc" | run_patch
    exit 1
  fi

  # "latest": revisões criadas depois pelo Terraform (mudança de configuração) também passam a servir.
  log "100% do tráfego para a última revisão ($revision)"
  jq '.traffic = [{type: "TRAFFIC_TARGET_ALLOCATION_TYPE_LATEST", percent: 100}]' <<<"$svc" | run_patch
  echo "API: $url (rollback: revisão $previous)"
}

deploy_web() {
  local api_url adc="${GOOGLE_APPLICATION_CREDENTIALS:-$HOME/.config/gcloud/application_default_credentials.json}"
  if [ ! -f "$adc" ]; then
    echo "O firebase-tools usa as credenciais padrão do gcloud. Rode antes:" >&2
    echo "  $GCLOUD auth application-default login" >&2
    exit 1
  fi
  api_url=$(service_json | jq -r '.status.url')

  # Config pública do web app (F03-RT-08): lida da API do Firebase, nunca commitada. O ID do web
  # app vem do Terraform (fonte única).
  local app_id config token
  app_id=$(sed -n 's/^firebase_web_app_id *= *"\([^"]*\)".*/\1/p' "$ROOT/infra/terraform/envs/prd.tfvars")
  token=$("$GCLOUD" auth print-access-token)
  config=$(curl -sS --fail-with-body -H "Authorization: Bearer $token" -H "x-goog-user-project: $PROJECT" \
    "https://firebase.googleapis.com/v1beta1/projects/$PROJECT/webApps/$app_id/config")

  log "Build do SPA (VITE_API_BASE_URL=$api_url, Firebase $(jq -r '.projectId' <<<"$config"))"
  (
    cd "$ROOT/frontend"
    VITE_API_BASE_URL="$api_url" \
      VITE_FIREBASE_API_KEY=$(jq -r '.apiKey' <<<"$config") \
      VITE_FIREBASE_AUTH_DOMAIN=$(jq -r '.authDomain' <<<"$config") \
      VITE_FIREBASE_PROJECT_ID=$(jq -r '.projectId' <<<"$config") \
      VITE_FIREBASE_APP_ID=$(jq -r '.appId' <<<"$config") \
      npm run build
  )

  log "Publicação no Firebase Hosting (site $SITE)"
  (cd "$ROOT" && npx --yes "$FIREBASE_TOOLS" deploy --only hosting --project "$PROJECT" --non-interactive)
  echo "Frontend: https://$SITE.web.app"
}

case "${1:-}" in
  api) deploy_api ;;
  web) deploy_web ;;
  *) echo "uso: $0 api|web" >&2; exit 2 ;;
esac
