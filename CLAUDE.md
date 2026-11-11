@AGENTS.md

## Claude Code only

- Shared settings, permissions and hooks live in `.claude/` (versioned);
  personal ones go in `.claude/settings.local.json` (gitignored).
- Hooks: `guard_files.py` blocks edits to `.env*` and to migrations on
  `main`; `ruff_on_edit.py` fixes and formats edited Python files.
