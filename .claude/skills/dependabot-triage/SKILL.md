---
name: dependabot-triage
description: Triage Garimpei's open Dependabot PRs - collect CI status and failure logs with a script, merge the green ones, fix small breakages on the PR branch, and bring the rest to the author as a numbered list with a recommendation each (merge, fix, or close and add an ignore rule). Use when the author asks to "olhar os PRs do Dependabot", "triar as dependências" or when the session brief lists Dependabot PRs.
---

# Dependabot triage

Run from the repository root. The script does the mechanical part; you read
its output, decide, and act.

## 1. Collect

```bash
bash .claude/skills/dependabot-triage/status.sh --watch
```

One block per open Dependabot PR: mergeability, CI states and, for a red
job, the log lines that usually explain it. No lines under a failed job
means the run was still going: run the script again.

## 2. Sort each PR

| Situation | Action |
|---|---|
| Green, minor/patch | Squash-merge (standing OK: merge on green CI) |
| Green, **major** (any package, test tools included) | **Do not merge.** Show it to the author first (decided Nov 12, 2026), with your reading: for a runtime library, whether its consumers support it (e.g. kombu's `redis` range in the lock) |
| Red, small and mechanical (ruff import order or format, a type that narrowed, a sibling package that must move with it) | Fix on the PR branch, verify the module, push |
| Red because an approved test now fails | **Stop**: never change an approved test without the author's OK |
| Red on a peer conflict (`ERESOLVE`) or an upstream cap | Recommend closing and adding an `ignore` rule |
| Needs a migration (driver, enum, library swap) | Recommend an ignore now and its own PR later, tests first |

Pairs that move together (e.g. `eslint` + `@eslint/js`, `vitest` +
`@vitest/coverage-v8`): once the author approves the major, bump both in
one PR and close the other.

## 3. Fixing a PR branch

- **Never rebase** a PR branch (that needs a force push, which the hook
  blocks): `git merge origin/main` into it instead.
- Lock conflict in `poetry.lock`: take `main`'s lock, then
  `uvx poetry@2 update --lock <the packages the PR bumped>`.
- Ruff at the version in the module's `poetry.lock`:
  `uvx ruff@<version> check src --fix` and `format src`. Keep
  `.pre-commit-config.yaml`'s ruff `rev` equal to it.
- Verify the module with the commands in `AGENTS.md` (*Verify*) before
  pushing. Check line endings (`git ls-files --eol <file>`) after scripted
  edits.
- If a push is rejected, Dependabot rebased the branch meanwhile: reset to
  the remote branch and cherry-pick your commit.

## 4. Merge order

Several PRs on the same lock file conflict once one lands. Merge one per
folder, then `@dependabot rebase` the others and run the script again.
After a merge, Dependabot opens the next PRs in its queue; expect waves.

## 5. Ignore rules

Add them to `.github/dependabot.yml` under the folder's entry, in a
`chore/` branch, with a comment saying why and when to remove it (link the
closed PR). Close the PR with a one-line reason. Use the narrowest range
that excludes the breakage (`redis >=6.5`, not every major).

## 6. Report to the author

Short summary: merged, fixed, closed. Then the open decisions as **one
numbered list**, one line of reason and a recommendation each, so the
author can answer "segue tudo" or name numbers. Record follow-up work
(migrations behind an ignore rule) in memory.
