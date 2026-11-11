"""PreToolUse hook: keep Claude's git commands away from ``main``.

Blocks, in Bash or PowerShell commands:

- ``git commit`` while the current branch is ``main``;
- ``git push`` to ``main`` (explicit refspec, or a bare push from ``main``);
- force pushes (``--force``, ``-f``, ``--force-with-lease``, ``+refspec``);
- ``--no-verify``, which would skip the pre-commit checks;
- ``gh pr merge --admin``, which would bypass the branch protection.

GitHub branch protection on ``main`` is the real lock (it applies to people
too); this hook stops Claude earlier, with a clear message.

Exit code 2 blocks the call and shows stderr to Claude. Any unexpected error
lets the call through (exit 0) so a broken hook never stops work.
"""

from __future__ import annotations

import json
import re
import shlex
import subprocess
import sys

MAIN = "main"
SEGMENT_SPLIT = re.compile(r"&&|\|\||[;|\n]")
# git options that take a value as the next word (git -C path commit ...)
GIT_OPTS_WITH_VALUE = {"-C", "-c", "--git-dir", "--work-tree", "--namespace"}


def words(segment: str) -> list[str]:
    try:
        return shlex.split(segment, posix=True)
    except ValueError:
        return segment.split()


def git_subcommand(tokens: list[str]) -> tuple[str, list[str]] | None:
    """Return (subcommand, its arguments) for a git call, else None."""
    if not tokens or tokens[0] not in ("git", "git.exe"):
        return None
    i = 1
    while i < len(tokens) and tokens[i].startswith("-"):
        i += 2 if tokens[i] in GIT_OPTS_WITH_VALUE else 1
    if i >= len(tokens):
        return None
    return tokens[i], tokens[i + 1 :]


def current_branch(cwd: str | None) -> str | None:
    result = subprocess.run(
        ["git", "branch", "--show-current"],
        cwd=cwd or None,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip() if result.returncode == 0 else None


def targets_main(refspec: str) -> bool:
    dest = refspec.lstrip("+").split(":")[-1]
    return dest in (MAIN, f"refs/heads/{MAIN}")


def check_push(args: list[str], branch: str | None) -> str | None:
    if any(a in ("--force", "-f") or a.startswith("--force-with-lease") for a in args):
        return "force push is not allowed"
    positional = [a for a in args if not a.startswith("-")]
    refspecs = positional[1:]  # first positional is the remote
    if any(r.startswith("+") for r in refspecs):
        return "force push (+refspec) is not allowed"
    if any(targets_main(r) for r in refspecs):
        return f"pushing to {MAIN} is not allowed; open a pull request"
    if not refspecs and branch == MAIN:
        return f"you are on {MAIN}; push a feature branch instead"
    return None


def reason(command: str, cwd: str | None) -> str | None:
    branch: str | None = None
    branch_known = False
    for segment in SEGMENT_SPLIT.split(command):
        tokens = words(segment.strip())
        if tokens[:3] == ["gh", "pr", "merge"] and "--admin" in tokens:
            return "gh pr merge --admin bypasses the branch protection"
        call = git_subcommand(tokens)
        if call is None:
            continue  # not a git call (e.g. a line of a commit message)
        sub, args = call
        if "--no-verify" in args:
            return "--no-verify skips the pre-commit checks"
        if sub in ("switch", "checkout"):
            # the branch changes mid-command: stop judging by the current one
            branch, branch_known = None, True
            continue
        if sub not in ("commit", "push"):
            continue
        if not branch_known:
            branch, branch_known = current_branch(cwd), True
        if sub == "commit" and branch == MAIN:
            return f"you are on {MAIN}; create a branch first"
        if sub == "push":
            why = check_push(args, branch)
            if why:
                return why
    return None


def main() -> int:
    try:
        call = json.load(sys.stdin)
        command = (call.get("tool_input") or {}).get("command")
        if not command:
            return 0
        why = reason(command, call.get("cwd"))
    except Exception:  # never let a hook bug block work
        return 0
    if why:
        print(f"Blocked by .claude/hooks/guard_git.py: {why}.", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
