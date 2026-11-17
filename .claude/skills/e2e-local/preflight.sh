#!/usr/bin/env bash
# Get the local stack ready for the e2e suite (used by the e2e-local skill):
#   1. start the services the suite needs that are not running;
#   2. wait until the API, site, admin and Mailpit answer;
#   3. install the Chromium of the Playwright version in frontend/
#      (a no-op when it is already there; skipped with E2E_CHANNEL set).
# Run from the repository root.
set -u

NEEDED=(db redis web site frontend mailpit)
running=$(docker compose ps --status running --services)
missing=()
for svc in "${NEEDED[@]}"; do
  grep -qx "$svc" <<<"$running" || missing+=("$svc")
done
if ((${#missing[@]})); then
  echo "starting: ${missing[*]}"
  docker compose up -d "${missing[@]}" || exit 1
fi

declare -A URLS=(
  [api]="http://localhost:8000/docs"
  [site]="http://localhost:3000/"
  [admin]="http://localhost/"
  [mailpit]="http://localhost:8026/"
)
deadline=$((SECONDS + ${WAIT_SECONDS:-180}))

for name in api site admin mailpit; do
  url=${URLS[$name]}
  until curl -fsS -o /dev/null --max-time 5 "$url" 2>/dev/null; do
    if ((SECONDS >= deadline)); then
      echo "TIMEOUT: $name ($url) is not answering. Check: docker compose ps; docker compose logs --tail 50"
      exit 1
    fi
    sleep 3
  done
  echo "ok: $name ($url)"
done

if [[ -z "${E2E_CHANNEL:-}" ]]; then
  (cd frontend && npx playwright install chromium) || {
    echo "FAILED: npx playwright install chromium (from frontend/)"
    exit 1
  }
  echo "ok: Playwright Chromium"
fi
