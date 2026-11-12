#!/usr/bin/env bash
# Status of every open Dependabot PR: title, mergeability, CI result and,
# for a red check, the log lines that usually explain it.
# Usage: bash .claude/skills/dependabot-triage/status.sh [--watch]
#   --watch  wait for running checks to finish before reporting
set -uo pipefail

WATCH=0
[ "${1:-}" = "--watch" ] && WATCH=1

# Lines worth showing from a failed job: npm peer conflicts, pytest
# failures, ruff codes, TypeScript errors, import errors.
FILTER='ERESOLVE|While resolving|Found: |Could not resolve|Conflicting peer|FAILED|^E  |Error:|error TS|ModuleNotFoundError|ValueError|= [0-9]+ (failed|passed)|Found [0-9]+ error|^[A-Z]+[0-9]{3,4} |-->'

prs=$(gh pr list --author "app/dependabot" --state open --json number --jq '.[].number')
if [ -z "$prs" ]; then
  echo "No open Dependabot PRs."
  exit 0
fi

for n in $prs; do
  [ "$WATCH" = 1 ] && gh pr checks "$n" --watch --interval 20 >/dev/null 2>&1

  mergeable=UNKNOWN
  for _ in 1 2 3 4 5 6; do
    mergeable=$(gh pr view "$n" --json mergeable --jq .mergeable)
    [ "$mergeable" != UNKNOWN ] && break
    sleep 5
  done

  title=$(gh pr view "$n" --json title --jq .title)
  states=$(gh pr checks "$n" --json state --jq '[.[].state] | unique | join(",")')
  echo "=== #$n  $title"
  echo "    mergeable=$mergeable  ci=$states"

  failed=$(gh pr checks "$n" --json name,state,link \
    --jq '[.[] | select(.state=="FAILURE")] | unique_by(.name) | .[] | .name + "\t" + .link')
  [ -z "$failed" ] && continue

  while IFS=$'\t' read -r name link; do
    run=$(echo "$link" | sed -E 's#.*/runs/([0-9]+)/.*#\1#')
    echo "    --- failed: $name"
    gh run view "$run" --log-failed 2>/dev/null \
      | sed -E 's/^[^\t]*\t[^\t]*\t[0-9TZ:.-]+ //' \
      | grep -E "$FILTER" | grep -v 'DeprecationWarning' | sort -u | head -15 \
      | sed 's/^/      /'
  done <<< "$failed"
done
