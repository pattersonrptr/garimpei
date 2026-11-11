"""SessionStart hook: a short brief so a new session starts with the facts.

Prints (as context for Claude): current branch and uncommitted files, open
pull requests, and the phases of the main plan that are not done yet. Each
step is optional: a missing ``gh`` or network just leaves its line out.

Always exits 0: a brief must never stop a session from starting.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(os.environ.get("CLAUDE_PROJECT_DIR") or Path(__file__).resolve().parents[2])
PLAN = ROOT / "docs" / "plan" / "README.md"
PHASE_ROW = re.compile(r"^\|\s*([^|]+?)\s*\|\s*\*\*(.+?)\*\*(.*?)\|")


def run(*args: str, timeout: int = 8) -> str | None:
    try:
        result = subprocess.run(
            args,
            cwd=ROOT,
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    return result.stdout.strip() if result.returncode == 0 else None


def open_phases() -> list[str]:
    if not PLAN.exists():
        return []
    phases = []
    in_section = False
    for line in PLAN.read_text(encoding="utf-8").splitlines():
        if line.startswith("## "):
            in_section = line.startswith("## 6. Phases")
            continue
        match = PHASE_ROW.match(line) if in_section else None
        if match and "(done" not in match.group(3):
            phases.append(f"{match.group(1)} {match.group(2)}")
    return phases


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")  # Windows defaults to cp1252
    lines = ["Garimpei session brief (from .claude/hooks/session_brief.py):"]
    branch = run("git", "branch", "--show-current")
    if branch is not None:
        changed = run("git", "status", "--short", "--untracked-files=no")
        count = len(changed.splitlines()) if changed else 0
        lines.append(
            f"- Branch: {branch or '(detached)'}; {count} uncommitted tracked file(s)"
        )
    prs = run(
        "gh",
        "pr",
        "list",
        "--state",
        "open",
        "--limit",
        "10",
        "--json",
        "number,title,headRefName",
        "--template",
        '{{range .}}#{{.number}} {{.title}} ({{.headRefName}}){{"\\n"}}{{end}}',
    )
    if prs is not None:
        lines.append("- Open PRs: " + ("; ".join(prs.splitlines()) or "none"))
    phases = open_phases()
    if phases:
        lines.append("- Plan phases not done: " + "; ".join(phases))
    lines.append(
        "- Read docs/plan/README.md and the current phase doc before planning."
    )
    print("\n".join(lines))


if __name__ == "__main__":
    try:
        main()
    except Exception:  # never block a session start
        pass
