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
- `git push` is allowed without asking: `guard_git.py` and the branch
  protection already stop pushes to `main` and force pushes. Merges still ask.
- **Automate what repeats.** When a task is done by hand again and again
  (same commands, same lookups, same checklist), propose turning it into a
  skill, hook, subagent or permission, and say which model fits (Haiku for
  mechanical steps, Sonnet for reviews, the main model for design). Only
  for something already repeated here (YAGNI); propose, don't just add it.
