---
name: refactor-slice-pr
description: Run one Garimpei refactor or tests-first slice end to end - branch, tests for the author's review, red and green captured by a script, architecture review, PR from the template, CI, merge, phase doc and memory. Use for each slice of docs/plan/refactor-remaining-modules.md, or when the author says "segue com o próximo item da fila" or "abre o PR da fatia".
---

# Refactor slice → PR

One slice per PR. The script does the mechanical parts (Haiku-level work);
you write the tests, the code and the PR text.

## 1. Pick and propose

- Read the queue in `docs/plan/refactor-remaining-modules.md`. Propose one
  item with a recommendation; start only after the author says yes.
- Name the smell and the refactoring in Fowler's vocabulary.
- Untested code: characterization tests first, **in their own PR**
  (they pass on today's code; prove them with one mutation that fails).

## 2. Tests first, then stop

- Branch: `refactor/<slice>` (or `test/<slice>` for characterization).
- Write only the tests (or the test diff when a port or signature
  changes: mock setup only, assertions untouched when possible). Commit
  locally, do not push (CI would fail on missing code).
- Show the author what changes and why, as a short table or list, and
  **stop** for approval. Never change an approved test afterwards.
- Anything that changes behavior (even a tie-break) is a question to the
  author, with a recommendation.

## 3. Red, code, green

```bash
bash .claude/skills/refactor-slice-pr/slice.sh red   <pytest args>
# implement the least code
bash .claude/skills/refactor-slice-pr/slice.sh green <pytest args>
```

Prefer a red on an assertion: a skeleton that returns empty values gives
one. When the red can only be a `TypeError`/`ValueError` (a use case moving
to another port), say so in the PR. Then run the module's full checks from
`AGENTS.md` (*Verify*), including the blocking mypy paths in `ci.yml`.

## 4. Review, doc, PR

- Run the `architecture-reviewer` subagent on `git diff main...HEAD`; fix
  what is in scope, queue the rest.
- Phase doc: add a row to *Done* (PR column `(this PR)` until merged) and
  update the *Queue*. Use a Python script with `newline="\n"` (or Edit);
  keep each file's line endings.
- PR body from `.github/pull_request_template.md`: *What and why*, *Tests
  first* (approval date, red and green from `$OUT/red.txt` and
  `$OUT/green.txt`), *Refactoring*, *Verification* (counts, reviewer
  result). End with the Claude Code line.

## 5. CI and merge

```bash
bash .claude/skills/refactor-slice-pr/slice.sh merge <pr>
```

It waits for CI and merges only when every check passes; when one is red,
fix the cause first. Then update the memory (`xp-tdd-adoption.md` and its
line in `MEMORY.md`) with the PR number and the next step.
