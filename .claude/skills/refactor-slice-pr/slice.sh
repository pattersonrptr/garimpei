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
  (cd "$ROOT/backend" && ${POETRY:-poetry} run python -m pytest "$@" -q 2>&1) \
    | summarize >"$OUT/$kind.txt"
  cat "$OUT/$kind.txt"
  if [ "$kind" = red ] && ! grep -q 'failed' "$OUT/red.txt"; then
    echo "WARNING: nothing failed; this is not a red run." >&2
    return 1
  fi
  if [ "$kind" = red ] && ! grep -q 'AssertionError' "$OUT/red.txt"; then
    echo "NOTE: no AssertionError; say in the PR why the red is not an assertion." >&2
  fi
  echo "saved: $OUT/$kind.txt"
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
    gh pr checks "$pr" --watch --interval 30 >/dev/null 2>&1
    if checks "$pr" | grep -vq ': pass$'; then
      checks "$pr"
      echo "Not merging: some check is not green." >&2
      exit 1
    fi
    gh pr merge "$pr" --squash --delete-branch
    git -C "$ROOT" switch -q main && git -C "$ROOT" pull -q
    git -C "$ROOT" log --oneline -1
    ;;
  *)
    sed -n '2,11p' "$0"
    exit 2
    ;;
esac
