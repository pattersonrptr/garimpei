#!/usr/bin/env bash
# Wait until the local API, site and admin answer (used by the e2e-local skill).
set -u

declare -A URLS=(
  [api]="http://localhost:8000/docs"
  [site]="http://localhost:3000/"
  [admin]="http://localhost/"
)
deadline=$((SECONDS + ${WAIT_SECONDS:-180}))

for name in api site admin; do
  url=${URLS[$name]}
  until curl -fsS -o /dev/null --max-time 5 "$url"; do
    if ((SECONDS >= deadline)); then
      echo "TIMEOUT: $name ($url) is not answering. Check: docker compose ps; docker compose logs --tail 50"
      exit 1
    fi
    sleep 3
  done
  echo "ok: $name ($url)"
done
