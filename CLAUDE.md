@AGENTS.md

## Claude Code only

- Shared settings, permissions and hooks live in `.claude/` (versioned);
  personal ones go in `.claude/settings.local.json` (gitignored).
- Hooks: `guard_files.py` blocks edits to `.env*` and to migrations on
  `main`, and asks the author before any change to `.claude/settings*.json`
  or `.claude/hooks/`; `guard_git.py` blocks commits on `main`, pushes to
  `main`, force pushes, skipping pre-commit and admin merges;
  `ruff_on_edit.py` fixes and formats edited Python files.
- Instructions (`AGENTS.md`) can be ignored; hooks and permissions are
  enforced by Claude Code. GitHub branch protection on `main` applies to
  everyone.
