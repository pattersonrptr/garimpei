@AGENTS.md

## Claude Code only

- Shared settings, permissions and hooks live in `.claude/` (versioned);
  personal ones go in `.claude/settings.local.json` (gitignored).
- Hooks: `guard_files.py` blocks edits to `.env*` and to migrations on
  `main`, and asks the author before any change to `.claude/settings*.json`
  or `.claude/hooks/`; `guard_git.py` blocks commits on `main`, pushes to
  `main`, force pushes, skipping pre-commit and admin merges;
  `ruff_on_edit.py` fixes and formats edited Python files;
  `session_brief.py` (SessionStart) prints the branch, open PRs and the plan
  phases not done yet, so a session does not have to look them up.
- Skill `e2e-local` (`.claude/skills/`): the local end-to-end check with
  screenshots. Skill `dependabot-triage`: CI status and failure logs of the
  open Dependabot PRs (script), then merge, fix or propose ignore rules.
  Subagent `architecture-reviewer` (`.claude/agents/`): reviews
  a diff against the architecture rules; run it before merging
  backend or scrapers changes.
- Permissions deny `WebFetch` on Amazon domains (no Amazon scraping). Shell
  commands like `curl` are not covered by that rule.
- Instructions (`AGENTS.md`) can be ignored; hooks and permissions are
  enforced by Claude Code. GitHub branch protection on `main` applies to
  everyone.
- `git push` is allowed without asking: `guard_git.py` and the branch
  protection already stop pushes to `main` and force pushes. `gh pr merge`
  is allowed too: branch protection requires the four CI checks (admins
  included) and `guard_git.py` blocks admin merges. Merge only when CI is
  green (and, for a feature or bug fix, once the author approved its
  tests); fix CI first when it is red.
- **Tests first:** after writing the tests of a slice, stop and wait for the
  author's review before writing production code (`AGENTS.md`, *Tests
  first*). For a review after the fact, use `/code-review` with a focus on
  whether the tests check behavior or just mirror the implementation.
- **Automate what repeats.** When a task is done by hand again and again
  (same commands, same lookups, same checklist), propose turning it into a
  skill, hook, subagent or permission, and say which model fits (Haiku for
  mechanical steps, Sonnet for reviews, the main model for design). Only
  for something already repeated here (YAGNI); propose, don't just add it.
