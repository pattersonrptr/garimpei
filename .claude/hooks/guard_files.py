"""PreToolUse hook: refuse edits to files that must not be changed by Claude.

- ``.env`` files (secrets). ``.env.example`` is fine.
- Alembic migrations already on ``main``: production may have applied them;
  a change needs a new migration instead.

Edits to Claude's own settings and hooks (``.claude/settings*.json``,
``.claude/hooks/``) are not blocked but always ask the author, so the agent
cannot quietly switch its guards off.

Claude Code sends the tool call as JSON on stdin. Exit code 2 blocks the call
and shows stderr to Claude. Any unexpected error lets the call through (exit
0) so a broken hook never stops work; the permission rules still apply.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path, PurePosixPath

MIGRATIONS = PurePosixPath("backend/alembic/versions")


def repo_root() -> Path:
    return Path(
        os.environ.get("CLAUDE_PROJECT_DIR") or Path(__file__).resolve().parents[2]
    )


def relative(path: str, root: Path) -> PurePosixPath | None:
    try:
        return PurePosixPath(
            Path(path).resolve().relative_to(root.resolve()).as_posix()
        )
    except ValueError:
        return None  # outside the repository: not ours to guard


def is_secret_env(rel: PurePosixPath) -> bool:
    name = rel.name
    return name.startswith(".env") and name != ".env.example"


def on_main(rel: PurePosixPath, root: Path) -> bool:
    result = subprocess.run(
        ["git", "cat-file", "-e", f"main:{rel}"],
        cwd=root,
        capture_output=True,
    )
    return result.returncode == 0


def reason(file_path: str) -> str | None:
    root = repo_root()
    rel = relative(file_path, root)
    if rel is None:
        return None
    if is_secret_env(rel):
        return (
            f"{rel} holds secrets and is not edited by Claude. "
            "Ask the author to change it, or edit .env.example."
        )
    if rel.parent == MIGRATIONS and rel.suffix == ".py" and on_main(rel, root):
        return (
            f"{rel} is already on main (it may be applied in production). "
            "Write a new Alembic migration instead of changing this one."
        )
    return None


def is_guard_config(rel: PurePosixPath) -> bool:
    """Claude's own settings and hooks: changing them can switch guards off."""
    return rel.parts[:1] == (".claude",) and (
        rel.name.startswith("settings") or rel.parts[1:2] == ("hooks",)
    )


def ask_author(rel: PurePosixPath) -> None:
    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "ask",
                    "permissionDecisionReason": (
                        f"{rel} configures Claude's own guards; "
                        "the author confirms every change."
                    ),
                }
            }
        )
    )


def main() -> int:
    try:
        call = json.load(sys.stdin)
        tool_input = call.get("tool_input") or {}
        file_path = tool_input.get("file_path") or tool_input.get("notebook_path")
        if not file_path:
            return 0
        why = reason(file_path)
        rel = relative(file_path, repo_root())
        if not why and rel is not None and is_guard_config(rel):
            ask_author(rel)
            return 0
    except Exception:  # never let a hook bug block work
        return 0
    if why:
        print(f"Blocked by .claude/hooks/guard_files.py: {why}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
