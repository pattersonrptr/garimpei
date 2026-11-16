#!/usr/bin/env bash
# Mechanical steps of a refactor or tests-first slice: capture the red and
# green pytest output for the PR body, wait for CI, merge when green.
# Usage (from the repository root):
#   bash .claude/skills/refactor-slice-pr/slice.sh red   <pytest args>
#   bash .claude/skills/refactor-slice-pr/slice.sh green <pytest args>
#   bash .claude/skills/refactor-slice-pr/slice.sh ci    [pr]
#   bash .claude/skills/refactor-slice-pr/slice.sh merge <pr>
# pytest args are paths and options relative to backend/ (e.g.
# "src/tests/unit/use_cases/test_x.py -k Foo"). red/green write a short
# summary to $OUT/red.txt or $OUT/green.txt and print it.
set -uo pipefail

ROOT=$(git rev-parse --show-toplevel)
OUT="${TMPDIR:-${TMP:-/tmp}}/garimpei-slice"
mkdir -p "$OUT"

# Failing test names, the first error line of each kind and the totals.
summarize() {
  grep -E '^FAILED|^E +[A-Za-z]+(Error|Exception)|[0-9]+ (failed|passed)' \
    | sed -E 's#^FAILED [^ ]*::#FAILED #; s/ - .*//' \
    | awk '!seen[$0]++' | head -40
}

run_tests() {
  local kind=$1
  shift
  # Poetry finds the virtualenv on any OS (.venv/bin or .venv/Scripts, or
  # its own cache); POETRY can point to another launcher, e.g. "uvx poetry@2".
  # Without either, fall back to uvx (AGENTS.md, Verify).
  local launcher=${POETRY:-}
  if [ -z "$launcher" ]; then
    if command -v poetry >/dev/null 2>&1; then
      launcher=poetry
    elif command -v uvx >/dev/null 2>&1; then
      launcher="uvx poetry@2"
    else
      echo "Neither poetry nor uvx found; set POETRY." >&2
      return 2
    fi
  fi
  (cd "$ROOT/backend" && $launcher run python -m pytest "$@" -q 2>&1) \
    | summarize >"$OUT/$kind.txt"
  cat "$OUT/$kind.txt"
  # No test totals means pytest never ran (wrong launcher, bad arguments).
  if ! grep -Eq '[0-9]+ (failed|passed)' "$OUT/$kind.txt"; then
    echo "ERROR: pytest did not run; check the launcher ($launcher) and arguments." >&2
    return 2
  fi
  if [ "$kind" = red ] && ! grep -q 'failed' "$OUT/red.txt"; then
    echo "WARNING: nothing failed; this is not a red run." >&2
    return 1
  fi
  if [ "$kind" = red ] && ! grep -q 'AssertionError' "$OUT/red.txt"; then
    echo "NOTE: no AssertionError; say in the PR why the red is not an assertion." >&2
  fi
  echo "saved: $OUT/$kind.txt"
}

# The phase docs say "(this PR)" until the number is known; on the PR's own
# branch, write the number in, commit and push (CI then runs on that commit).
number_phase_docs() {
  local pr=$1 head files
  head=$(gh pr view "$pr" --json headRefName -q .headRefName) || return 1
  files=$(git -C "$ROOT" grep -l '(this PR)' -- 'docs/plan/*.md' || true)
  [ -n "$files" ] || return 0
  if [ "$(git -C "$ROOT" branch --show-current)" != "$head" ]; then
    echo "NOTE: not on $head; left '(this PR)' in: $files" >&2
    return 0
  fi
  for f in $files; do
    sed -i "s/(this PR)/#$pr/g" "$ROOT/$f"
  done
  (cd "$ROOT" && git add -- $files &&
    git commit -q -m "docs(plan): number #$pr in the phase doc" &&
    git push -q) || return 1
  echo "Phase doc: (this PR) -> #$pr ($files)"
  # Wait until GitHub lists checks for the new commit before watching them.
  local sha
  sha=$(git -C "$ROOT" rev-parse HEAD)
  for _ in $(seq 1 24); do
    [ "$(gh pr view "$pr" --json headRefOid -q .headRefOid)" = "$sha" ] &&
      [ -n "$(gh pr view "$pr" --json statusCheckRollup -q '.statusCheckRollup[]')" ] &&
      return 0
    sleep 5
  done
  echo "WARNING: no checks listed for $sha after 2 min." >&2
}

# Windows bind mounts miss uvicorn's reload: restart the local API so it runs
# the merged code, and wait until it answers. Skipped when it is not running.
restart_api() {
  docker compose -f "$ROOT/docker-compose.yml" ps --status running --services 2>/dev/null |
    grep -qx web || { echo "Local API not running; no restart."; return 0; }
  docker compose -f "$ROOT/docker-compose.yml" restart web >/dev/null 2>&1
  for _ in $(seq 1 45); do
    if [ "$(curl -s -o /dev/null -w '%{http_code}' http://localhost:8000/docs)" = 200 ]; then
      echo "Local API restarted and answering."
      return 0
    fi
    sleep 2
  done
  echo "WARNING: local API did not answer within 90 s after the restart." >&2
}

checks() {
  gh pr checks "$@" 2>&1 | awk -F'\t' '{print $1 ": " $2}'
}

case "${1:-}" in
  red | green)
    kind=$1
    shift
    [ $# -gt 0 ] || { echo "pytest args required" >&2; exit 2; }
    run_tests "$kind" "$@"
    ;;
  ci)
    shift
    gh pr checks "$@" --watch --interval 30 >/dev/null 2>&1
    checks "$@"
    ;;
  merge)
    pr=${2:?pr number required}
    # Switching to main afterwards would carry uncommitted changes along.
    if [ -n "$(git -C "$ROOT" status --porcelain --untracked-files=no)" ]; then
      git -C "$ROOT" status --short --untracked-files=no
      echo "Not merging: commit or stash these changes first." >&2
      exit 1
    fi
    number_phase_docs "$pr" || exit 1
    gh pr checks "$pr" --watch --interval 30 >/dev/null 2>&1
    if checks "$pr" | grep -vq ': pass$'; then
      checks "$pr"
      echo "Not merging: some check is not green." >&2
      exit 1
    fi
    # Fails, for example, when the branch is behind main (gh pr update-branch).
    if ! gh pr merge "$pr" --squash --delete-branch; then
      echo "Merge failed; staying on $(git -C "$ROOT" branch --show-current)." >&2
      exit 1
    fi
    git -C "$ROOT" switch -q main && git -C "$ROOT" pull -q || exit 1
    git -C "$ROOT" log --oneline -1
    restart_api
    ;;
  *)
    sed -n '2,11p' "$0"
    exit 2
    ;;
esac
