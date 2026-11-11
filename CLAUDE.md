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
  screenshots. Subagent `architecture-reviewer` (`.claude/agents/`): reviews
  a diff against the architecture rules; run it before asking for a merge of
  backend or scrapers changes.
- Permissions deny `WebFetch` on Amazon domains (no Amazon scraping). Shell
  commands like `curl` are not covered by that rule.
- Instructions (`AGENTS.md`) can be ignored; hooks and permissions are
  enforced by Claude Code. GitHub branch protection on `main` applies to
  everyone.
