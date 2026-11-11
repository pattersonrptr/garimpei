"""PostToolUse hook: format and lint a Python file right after Claude edits it.

Runs ``ruff check --fix`` and then ``ruff format`` on the edited file, inside its
module (``backend/`` or ``scrapers/``) so that module's ruff settings apply.
Problems ruff cannot fix are reported back to Claude (exit code 2) so they
are fixed now, not in CI. No ruff available: does nothing.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

MODULES = ("backend", "scrapers")


def repo_root() -> Path:
    return Path(
        os.environ.get("CLAUDE_PROJECT_DIR") or Path(__file__).resolve().parents[2]
    )


def find_ruff(root: Path, module: str) -> str | None:
    for base in (root / module, root / "backend"):
        for candidate in (base / ".venv/Scripts/ruff.exe", base / ".venv/bin/ruff"):
            if candidate.exists():
                return str(candidate)
    return shutil.which("ruff")


def main() -> int:
    try:
        call = json.load(sys.stdin)
        file_path = (call.get("tool_input") or {}).get("file_path") or ""
        if not file_path.endswith(".py"):
            return 0
        root = repo_root()
        rel = Path(file_path).resolve().relative_to(root.resolve())
        module = rel.parts[0] if rel.parts else ""
        if module not in MODULES:
            return 0
        ruff = find_ruff(root, module)
        if not ruff:
            return 0
        cwd = root / module
        target = str(Path(file_path).resolve())
        check = subprocess.run(
            [ruff, "check", "--fix", "--quiet", target],
            cwd=cwd,
            capture_output=True,
            text=True,
        )
        # Format after fixing: a removed import must not leave a blank line.
        subprocess.run(
            [ruff, "format", "--quiet", target], cwd=cwd, capture_output=True
        )
    except Exception:  # never let a hook bug block work
        return 0
    if check.returncode != 0:
        print(
            f"ruff found problems it could not fix in {rel.as_posix()}:\n"
            f"{check.stdout}{check.stderr}",
            file=sys.stderr,
        )
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
