"""Hand-written mutation run for characterization tests.

Usage (slice.sh mutate calls it):
    python mutate.py <spec.json> <out_dir> <launcher> [--only M1,M2] -- <pytest args>

The spec is a JSON list of mutations, each one exact text to replace once:
    [{"id": "M1", "name": "create open to any user",
      "file": "src/app/.../controller.py", "old": "...", "new": "..."}]
"file" is relative to backend/. "old" must occur exactly once (line endings
are compared as LF; a CRLF file is written back as CRLF).

Before mutating, the tests run once on the code as it is and must pass.
Each mutated file is restored from a copy held in memory, and also saved
to <out_dir>/mutate-backup/ so an interrupted run can be put back by hand;
the run refuses to start while that folder has files. Never git checkout
to restore (the file may hold uncommitted work).

Prints one line per mutation (KILLED / SURVIVED / SKIPPED) and writes a
Markdown table to <out_dir>/mutations.md for the PR body.
"""

import json
import os
import shlex
import subprocess
import sys
from pathlib import Path

ROOT = Path(subprocess.check_output(["git", "rev-parse", "--show-toplevel"], text=True).strip())
BACKEND = ROOT / "backend"


def run_pytest(launcher: str, args: list[str]) -> subprocess.CompletedProcess:
    cmd = [*shlex.split(launcher), "run", "python", "-m", "pytest", "-x", "-q", "-p", "no:cacheprovider", *args]
    # This script runs on the backend virtualenv's Python; its variables
    # would make the launcher (uvx, poetry) load the wrong standard library.
    leaked = {"__PYVENV_LAUNCHER__", "VIRTUAL_ENV", "PYTHONHOME", "PYTHONPATH"}
    env = {k: v for k, v in os.environ.items() if k not in leaked}
    return subprocess.run(cmd, cwd=BACKEND, capture_output=True, text=True, env=env)


def apply(path: Path, original: bytes, old: str, new: str) -> str | None:
    text = original.decode("utf-8")
    crlf = "\r\n" in text
    lf = text.replace("\r\n", "\n")
    count = lf.count(old)
    if count != 1:
        return f"'old' found {count} times"
    mutated = lf.replace(old, new)
    if crlf:
        mutated = mutated.replace("\n", "\r\n")
    path.write_bytes(mutated.encode("utf-8"))
    return None


def main() -> int:
    argv = sys.argv[1:]
    if "--" not in argv or len(argv) < 4:
        print(__doc__, file=sys.stderr)
        return 2
    sep = argv.index("--")
    head, pytest_args = argv[:sep], argv[sep + 1 :]
    spec_path, out_dir, launcher, *rest = head
    only: set[str] = set()
    if rest[:1] == ["--only"] and len(rest) == 2:
        only = set(rest[1].split(","))
    elif rest:
        print(f"unknown options: {rest}", file=sys.stderr)
        return 2
    if not pytest_args:
        print("pytest args required after --", file=sys.stderr)
        return 2

    mutations = json.loads(Path(spec_path).read_text(encoding="utf-8"))
    if only:
        mutations = [m for m in mutations if m["id"] in only]

    backup = Path(out_dir) / "mutate-backup"
    if backup.exists() and any(backup.iterdir()):
        print(f"{backup} has files from an interrupted run; put them back and empty it first.", file=sys.stderr)
        return 2
    backup.mkdir(parents=True, exist_ok=True)

    print("Baseline: running the tests on the code as it is...", flush=True)
    baseline = run_pytest(launcher, pytest_args)
    if baseline.returncode != 0:
        tail = (baseline.stdout + baseline.stderr).strip().splitlines()[-15:]
        print("\n".join(tail), file=sys.stderr)
        print("Baseline failed: the tests must pass before mutating.", file=sys.stderr)
        return 1

    rows = []
    for m in mutations:
        path = BACKEND / m["file"]
        original = path.read_bytes()
        saved = backup / (m["file"].replace("/", "__"))
        saved.write_bytes(original)
        try:
            problem = apply(path, original, m["old"], m["new"])
            if problem:
                verdict = f"SKIPPED ({problem})"
            else:
                verdict = "KILLED" if run_pytest(launcher, pytest_args).returncode != 0 else "SURVIVED"
        finally:
            path.write_bytes(original)
            saved.unlink()
        rows.append((m["id"], m["name"], verdict))
        print(f"{m['id']} {m['name']}: {verdict}", flush=True)

    killed = sum(1 for r in rows if r[2] == "KILLED")
    survived = sum(1 for r in rows if r[2] == "SURVIVED")
    table = ["| Mutation | What it breaks | Result |", "|---|---|---|"]
    table += [f"| {i} | {n} | {v} |" for i, n, v in rows]
    table.append("")
    table.append(f"{killed} killed, {survived} survived, {len(rows) - killed - survived} skipped.")
    report = Path(out_dir) / "mutations.md"
    report.write_text("\n".join(table) + "\n", encoding="utf-8")
    print(f"{killed} killed, {survived} survived. saved: {report}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
