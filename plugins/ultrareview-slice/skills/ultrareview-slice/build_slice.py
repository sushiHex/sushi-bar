"""Build one local ultrareview slice: base commit withholds the files, next commit restores them.

Run with `python -I -B build_slice.py --repo R --worktree W --branch B paths...`.
Never pushes. Prints the base commit and the exact /code-review ultra command.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import tempfile
from pathlib import Path


_NO_HOOKS = tempfile.mkdtemp(prefix="ultra-no-hooks-")


def git(cwd: Path, *args: str, capture: bool = True) -> str:
    # No hooks (they would run on the synthetic checkout and commits), literal
    # pathspecs (file names are names, not patterns), UTF-8 whatever the locale.
    result = subprocess.run(["git", "-c", f"core.hooksPath={_NO_HOOKS}", "--literal-pathspecs", *args],
                            cwd=cwd, stdin=subprocess.DEVNULL, capture_output=capture,
                            text=True, encoding="utf-8", check=False)
    if result.returncode != 0:
        sys.exit(f"git {' '.join(args)} failed: {(result.stderr or '').strip()}")
    return result.stdout if capture else ""


def line_count(path: Path) -> int:
    data = path.read_bytes()
    return data.count(b"\n") + (1 if data and not data.endswith(b"\n") else 0)


def expand(worktree: Path, specs: list[str]) -> list[str]:
    seen: dict[str, None] = {}
    for spec in specs:
        files = git(worktree, "ls-files", "-z", "--", spec).split("\0")
        found = sorted(name for name in files if name)
        if not found:
            print(f"warning: no tracked files match {spec!r}", file=sys.stderr)
        for name in found:
            seen.setdefault(name, None)
    return list(seen)


def main() -> None:
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--worktree", type=Path, required=True)
    parser.add_argument("--branch", required=True)
    parser.add_argument("--base-ref", default="origin/main")
    parser.add_argument("--max-lines", type=int, default=8000)
    parser.add_argument("--max-files", type=int, default=500)
    parser.add_argument("--margin", type=int, default=0,
                        help="lines of headroom to keep under --max-lines")
    parser.add_argument("--rebuild", action="store_true",
                        help="reset an existing audit worktree/branch to --base-ref")
    parser.add_argument("paths", nargs="+")
    options = parser.parse_args()
    repo, worktree = options.repo.resolve(), options.worktree.resolve()

    if worktree.exists():
        if not options.rebuild:
            sys.exit(f"{worktree} exists; pass --rebuild to reuse it")
        if git(worktree, "status", "--porcelain").strip():
            sys.exit(f"{worktree} has uncommitted changes; refusing to reset it")
        if git(worktree, "rev-parse", "--abbrev-ref", "HEAD").strip() != options.branch:
            sys.exit(f"{worktree} is not on branch {options.branch}")
        git(worktree, "reset", "-q", "--hard", options.base_ref)
    else:
        git(repo, "worktree", "add", "-q", "-b", options.branch, str(worktree),
            options.base_ref)

    budget = options.max_lines - options.margin
    chosen: list[str] = []
    lines = 0
    for name in expand(worktree, options.paths):
        size = line_count(worktree / name)
        if len(chosen) < options.max_files and lines + size <= budget:
            chosen.append(name)
            lines += size
        else:
            print(f"skipped (cap): {name} ({size} lines)", file=sys.stderr)
    if not chosen:
        sys.exit("no file fits under the cap")

    original = git(worktree, "rev-parse", "HEAD").strip()
    with tempfile.NamedTemporaryFile("wb", suffix=".nul", delete=False) as spec:
        spec.write(b"\0".join(p.encode("utf-8") for p in chosen) + b"\0")
    try:
        git(worktree, "rm", "-q", "--cached", f"--pathspec-from-file={spec.name}", "--pathspec-file-nul")
        git(worktree, "commit", "-q", "--no-verify", "-m",
            "audit base: slice withheld (local review scaffolding, never push)")
        base = git(worktree, "rev-parse", "HEAD").strip()
        # The original index entries, straight from the commit: no filters, and
        # tracked-but-ignored files come back too.
        git(worktree, "restore", f"--source={original}", "--staged",
            f"--pathspec-from-file={spec.name}", "--pathspec-file-nul")
        git(worktree, "commit", "-q", "--no-verify", "-m", f"audit slice: {len(chosen)} files, {lines} lines")
    finally:
        Path(spec.name).unlink(missing_ok=True)

    stat = git(worktree, "diff", "--shortstat", base, "HEAD").strip()
    if git(worktree, "status", "--porcelain").strip():
        sys.exit("worktree is not clean after building the slice")
    print(f"slice: {len(chosen)} files, {lines} lines (cap {options.max_files} files, "
          f"{options.max_lines} lines)")
    print(f"diff: {stat}")
    print(f"base: {base}")
    for name in chosen:
        print(f"  {name}")
    print(f'\ncd "{worktree}"; claude "/code-review ultra --fix --max-findings all {base}"')


if __name__ == "__main__":
    main()
