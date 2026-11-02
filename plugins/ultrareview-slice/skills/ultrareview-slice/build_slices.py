"""Review a whole codebase with /code-review ultra: partition it into slices, one worktree each.

    python -I -B build_slices.py plan    --repo R [--base-ref origin/main] [--out PLAN.json]
    python -I -B build_slices.py build   --repo R --plan PLAN.json [--prefix P] [--dry-run]
    python -I -B build_slices.py launch  --repo R [--slices 1,3] [--jobs N] [--rerun] [--dry-run]
    python -I -B build_slices.py collect --repo R [--branch ultra/fixes]
    python -I -B build_slices.py clean   --repo R [--force]

build: every tracked file not excluded lands in exactly one slice. Groups (a
module with its tests) are packed whole, in plan order; files in no group
follow one by one. Slice N is worktree P-N on branch ultra/slice-N, whose base
ultra/base-N withholds the slice's files, so `/code-review ultra <base>` there
reviews exactly the slice while the checkout holds the whole repo. A manifest
in the repo's git dir records each slice for collect and clean.

launch: runs `claude ultrareview <base> --json --trust-workspace` in every
slice worktree at once and saves each findings payload to
<git-common-dir>/ultra-findings/slice-N.json (stderr beside it as .log). It is
billed per run: the user runs it, never Claude. Slices that already have
findings are skipped unless --rerun.

collect: each slice tree equals the base ref, so whatever --fix left in a
worktree is a patch that applies to the base. Saves one patch per slice, names
files two slices touched, and applies them onto one branch off the base ref
(worktree P-fixes), a commit per slice, without the scaffolding commits.

clean: removes the slice worktrees and branches; refuses a slice whose edits
were not collected unless --force. Never pushes anything.

PLAN.json: {"base_ref": "origin/main", "max_lines": 8000, "max_files": 500,
"margin": 400, "exclude": ["tests/mutations/*"], "groups": [["src/a.py",
"tests/test_a.py"], ["src/b/"]]}. Specs are git pathspecs; excludes are
fnmatch globs on repo paths.
"""

from __future__ import annotations

import argparse
import fnmatch
import json
import subprocess
import sys
import tempfile
from pathlib import Path


def git(cwd: Path, *args: str, check: bool = True) -> str:
    result = subprocess.run(["git", *args], cwd=cwd, stdin=subprocess.DEVNULL,
                            capture_output=True, text=True, encoding="utf-8")
    if check and result.returncode != 0:
        sys.exit(f"git {' '.join(args)} failed in {cwd}: {result.stderr.strip()}")
    return result.stdout


def lines_at(repo: Path, commit: str, paths) -> dict[str, int]:
    """Line counts of ``paths`` at ``commit``, in one `git cat-file --batch` read."""
    paths = list(paths)
    request = "".join(f"{commit}:{p}\n" for p in paths).encode("utf-8")
    out = subprocess.run(["git", "cat-file", "--batch"], cwd=repo, input=request,
                         capture_output=True, check=True).stdout
    sizes, at = {}, 0
    for path in paths:
        header_end = out.index(b"\n", at)
        size = int(out[at:header_end].split()[2])
        data = out[header_end + 1: header_end + 1 + size]
        sizes[path] = data.count(b"\n") + (1 if data and not data.endswith(b"\n") else 0)
        at = header_end + 1 + size + 1  # the blob, then its trailing newline
    return sizes


def manifest_path(repo: Path) -> Path:
    return Path(git(repo, "rev-parse", "--path-format=absolute", "--git-common-dir").strip()) / "ultra-slices.json"


def plan_slices(repo: Path, plan: dict, commit: str) -> tuple[list[dict], list[tuple[str, str]]]:
    budget = plan.get("max_lines", 8000) - plan.get("margin", 400)
    max_files = plan.get("max_files", 500)
    tracked = [p for p in git(repo, "ls-tree", "-r", "-z", "--name-only", commit).split("\0") if p]
    excluded = []
    for path in tracked:
        hit = next((g for g in plan.get("exclude", []) if fnmatch.fnmatch(path, g)), None)
        if hit:
            excluded.append((path, hit))
    reviewable = [p for p in tracked if p not in {e[0] for e in excluded}]
    placed: set[str] = set()
    groups: list[list[str]] = []
    for specs in plan.get("groups", []):
        files = []
        for spec in specs:
            found = [p for p in git(repo, "ls-tree", "-r", "-z", "--name-only", commit, "--", spec).split("\0") if p]
            if not found:
                sys.exit(f"plan names {spec!r}, which matches no tracked file at {commit[:7]}")
            files += [p for p in sorted(found) if p in reviewable and p not in placed and p not in files]
        placed.update(files)
        if files:
            groups.append(files)
    groups += [[p] for p in reviewable if p not in placed]  # the rest, one file each

    sizes = lines_at(repo, commit, reviewable)
    slices: list[dict] = []
    current: dict = {"files": [], "lines": 0}

    def close() -> None:
        nonlocal current
        if current["files"]:
            slices.append(current)
        current = {"files": [], "lines": 0}

    for group in groups:
        total = sum(sizes[p] for p in group)
        if total > budget:  # too big for any slice: split it, file by file
            print(f"warning: group starting {group[0]} is {total} lines; split across slices", file=sys.stderr)
            parts = [[p] for p in group]
        else:
            parts = [group]
        for part in parts:
            size = sum(sizes[p] for p in part)
            if size > budget:
                sys.exit(f"{part[0]} alone is {size} lines, over the {budget}-line budget")
            if current["lines"] + size > budget or len(current["files"]) + len(part) > max_files:
                close()
            current["files"] += part
            current["lines"] += size
    close()
    assert sorted(p for s in slices for p in s["files"]) == sorted(reviewable), "coverage broken"
    return slices, excluded


# Draft-plan defaults: what a reviewer can't usefully read. The user edits them.
DEFAULT_EXCLUDES = [
    "*.lock", "*-lock.json", "*-lock.yaml", "go.sum", "LICENSE*", "*.min.js", "*.map",
    "*.png", "*.jpg", "*.jpeg", "*.gif", "*.ico", "*.svg", "*.pdf", "*.zip", "*.woff*",
    "*/fixtures/*", "*/__snapshots__/*", "*/vendor/*", "dist/*", "build/*",
]


def _test_stem(path: str) -> str | None:
    """The source stem a test file names, or None if it is not a test."""
    name = Path(path).name
    stem, _, _ = name.partition(".")
    for prefix in ("test_",):
        if stem.startswith(prefix):
            return stem[len(prefix):]
    for suffix in ("_test", "_spec"):
        if stem.endswith(suffix):
            return stem[: -len(suffix)]
    if any(f".{tag}." in name for tag in ("test", "spec")):
        return stem
    return None


def draft_plan(args) -> None:
    """Pair each source file with the tests named after it; order by size."""
    repo = args.repo.resolve()
    commit = git(repo, "rev-parse", "--verify", f"{args.base_ref}^{{commit}}").strip()
    tracked = [p for p in git(repo, "ls-tree", "-r", "-z", "--name-only", commit).split("\0") if p]
    kept = [p for p in tracked if not any(fnmatch.fnmatch(p, g) for g in DEFAULT_EXCLUDES)]
    tests: dict[str, list[str]] = {}
    for p in kept:
        stem = _test_stem(p)
        if stem:
            tests.setdefault(stem, []).append(p)
    groups = []
    for p in kept:
        if _test_stem(p) is None and Path(p).suffix in CODE_SUFFIXES:
            group = [p, *sorted(tests.pop(Path(p).name.partition(".")[0], []))]
            groups.append(group)
    sizes = lines_at(repo, commit, [p for g in groups for p in g])
    groups.sort(key=lambda g: -sum(sizes[p] for p in g))
    plan = {"base_ref": args.base_ref, "max_lines": 8000, "max_files": 500, "margin": 400,
            "exclude": DEFAULT_EXCLUDES, "groups": groups}
    text = json.dumps(plan, indent=2)
    if args.out:
        args.out.write_text(text + "\n", encoding="utf-8")
    else:
        print(text)
    unmatched = sorted(p for ps in tests.values() for p in ps)
    print(f"{len(groups)} groups; {len(unmatched)} test files named after no source file "
          f"(they follow as leftovers; group them by hand if they belong together)",
          file=sys.stderr)


CODE_SUFFIXES = {".py", ".js", ".jsx", ".ts", ".tsx", ".go", ".rs", ".java", ".kt", ".cs",
                 ".c", ".cc", ".cpp", ".h", ".hpp", ".rb", ".php", ".swift", ".scala", ".sh"}


def build(args) -> None:
    repo = args.repo.resolve()
    plan = json.loads(args.plan.read_text(encoding="utf-8"))
    base_ref = plan.get("base_ref", "origin/main")
    commit = git(repo, "rev-parse", "--verify", f"{base_ref}^{{commit}}").strip()
    if manifest_path(repo).exists() and not args.dry_run:
        sys.exit(f"{manifest_path(repo)} exists: collect and clean the previous run first")
    slices, excluded = plan_slices(repo, plan, commit)
    prefix = Path(args.prefix).resolve() if args.prefix else repo.parent / f"{repo.name}-ultra"
    for n, s in enumerate(slices, 1):
        print(f"slice {n}: {len(s['files'])} files, {s['lines']} lines")
    print(f"excluded: {len(excluded)} files")
    for pattern in sorted({e[1] for e in excluded}):
        print(f"  {pattern}: {sum(1 for e in excluded if e[1] == pattern)}")
    if args.dry_run:
        return

    records = []
    for n, s in enumerate(slices, 1):
        tree = Path(f"{prefix}-{n}")
        if tree.exists():
            sys.exit(f"{tree} exists; remove it or pass another --prefix")
        git(repo, "worktree", "add", "-q", "-b", f"ultra/slice-{n}", str(tree), commit)
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", newline="\n", suffix=".txt", delete=False) as spec:
            spec.write("\n".join(s["files"]) + "\n")
        try:
            git(tree, "rm", "-q", "--cached", f"--pathspec-from-file={spec.name}")
            git(tree, "commit", "-q", "-m", f"ultra base {n}: slice withheld (local scaffolding, never push)")
            base = git(tree, "rev-parse", "HEAD").strip()
            git(tree, "branch", f"ultra/base-{n}", base)
            git(tree, "add", f"--pathspec-from-file={spec.name}")
            git(tree, "commit", "-q", "-m", f"ultra slice {n}: {len(s['files'])} files, {s['lines']} lines")
        finally:
            Path(spec.name).unlink(missing_ok=True)
        head = git(tree, "rev-parse", "HEAD").strip()
        if subprocess.run(["git", "diff", "--quiet", commit, head], cwd=tree).returncode:
            sys.exit(f"slice {n}'s tree differs from {commit[:7]}")
        if git(tree, "status", "--porcelain").strip():
            sys.exit(f"{tree} is not clean after building")
        records.append({"n": n, "worktree": str(tree), "base": base, "head": head,
                        "files": s["files"], "lines": s["lines"], "collected": False})

    manifest_path(repo).write_text(json.dumps(
        {"repo": str(repo), "commit": commit, "base_ref": base_ref, "prefix": str(prefix),
         "excluded": [e[0] for e in excluded], "slices": records}, indent=2), encoding="utf-8")
    print(f"\nmanifest: {manifest_path(repo)}\nRun each (billed, user-triggered; never launched by Claude):")
    for r in records:
        print(f'  cd {r["worktree"]}; claude "/code-review ultra --fix --max-findings all {r["base"]}"')


def launch(args) -> None:
    """Run `claude ultrareview <base> --json` per slice, in parallel; save each findings
    payload. Billed: the user starts this, never Claude."""
    import os
    import shutil
    from concurrent.futures import ThreadPoolExecutor

    repo = args.repo.resolve()
    m = json.loads(manifest_path(repo).read_text(encoding="utf-8"))
    out = manifest_path(repo).parent / "ultra-findings"
    out.mkdir(exist_ok=True)
    wanted = parse_slices(args.slices) if args.slices else None
    todo = [r for r in m["slices"] if (wanted is None or r["n"] in wanted)
            and (args.rerun or not (out / f"slice-{r['n']}.json").exists())]
    exe = shutil.which("claude") or "claude"
    env = {k: v for k, v in os.environ.items() if k != "CLAUDECODE"}  # allow a nested launch

    def argv(r: dict) -> list[str]:
        return [exe, "ultrareview", r["base"], "--json", "--trust-workspace"]

    if args.dry_run or not todo:
        for r in todo:
            print(f"slice {r['n']}: cd {r['worktree']}; {subprocess.list2cmdline(argv(r))}")
        print(f"{len(todo)} slice(s) to run" + ("" if todo else " (all have findings; --rerun to redo)"))
        return

    def run(r: dict) -> tuple[int, int]:
        n = r["n"]
        with open(out / f"slice-{n}.json.part", "w", encoding="utf-8") as stdout, \
                open(out / f"slice-{n}.log", "w", encoding="utf-8") as stderr:
            code = subprocess.run(argv(r), cwd=r["worktree"], env=env, stdin=subprocess.DEVNULL,
                                  stdout=stdout, stderr=stderr, encoding="utf-8").returncode
        part = out / f"slice-{n}.json.part"
        if code == 0:
            part.replace(out / f"slice-{n}.json")
        else:
            part.unlink(missing_ok=True)  # the log says why; leave nothing that looks like findings
        print(f"slice {n}: exit {code}" + ("" if code == 0 else f", see {out / f'slice-{n}.log'}"),
              flush=True)
        return n, code

    print(f"launching {len(todo)} ultrareview run(s), {args.jobs or len(todo)} at a time (billed)")
    with ThreadPoolExecutor(max_workers=args.jobs or len(todo)) as pool:
        results = list(pool.map(run, todo))
    failed = [n for n, code in results if code]
    print(f"\nfindings in {out}" + (f"; failed: {failed}" if failed else ""))


def parse_slices(spec: str) -> set[int]:
    """`1,3,5-7` -> {1, 3, 5, 6, 7}."""
    wanted: set[int] = set()
    for part in spec.split(","):
        low, _, high = part.strip().partition("-")
        wanted.update(range(int(low), int(high or low) + 1))
    return wanted


def cloud_dir(repo: Path, run: str) -> Path:
    return manifest_path(repo).parent / "ultra-cloud" / run


# The findings format every cloud session writes, and cloud-fetch checks. Field
# names follow the review tools' own (file, line, summary, failure_scenario).
FINDINGS_FORMAT = (
    "Write it as JSON Lines: one JSON object per line, no other text. A finding: "
    '{"kind": "finding", "severity": "blocker" | "should-fix" | "nit", "file": "<repo path>", '
    '"line": <int>, "summary": "<one sentence>", "failure_scenario": "<inputs or state -> '
    'wrong outcome>", "evidence": "<what you checked or ran>", "verified": true | false}. '
    'Something you checked and found sound: {"kind": "checked", "summary": "<what>"}. '
    "Findings most severe first; at least one line even when there are no findings."
)
SEVERITIES = ("blocker", "should-fix", "nit")


def parse_findings(text: str, n: int) -> tuple[list[dict], list[str]]:
    """Each line's record, tagged with its slice; problems name the line."""
    records, problems = [], []
    for i, line in enumerate(text.splitlines(), 1):
        if not line.strip():
            continue
        try:
            rec = json.loads(line)
        except json.JSONDecodeError as exc:
            problems.append(f"slice {n} line {i}: not JSON ({exc.msg})")
            continue
        kind = rec.get("kind") if isinstance(rec, dict) else None
        if kind == "finding":
            missing = [k for k in ("severity", "file", "line", "summary", "failure_scenario")
                       if k not in rec]
            if missing or rec["severity"] not in SEVERITIES:
                problems.append(f"slice {n} line {i}: finding lacks {missing or 'a known severity'}")
        elif kind != "checked":
            problems.append(f"slice {n} line {i}: kind {kind!r} is neither finding nor checked")
            continue
        records.append({"slice": n, **rec})
    return records, problems


def cloud(args) -> None:
    """One `claude --cloud` review session per slice. Each pushes its findings to
    review/<run>/slice-N; cloud-fetch reads them. Spends cloud-session credit."""
    import datetime
    import os

    repo, cwd = args.repo.resolve(), (args.cwd or args.repo).resolve()
    plan = json.loads(args.plan.read_text(encoding="utf-8"))
    commit = git(repo, "rev-parse", "--verify", f"{plan.get('base_ref', 'origin/main')}^{{commit}}").strip()
    if git(cwd, "rev-parse", "HEAD").strip() != commit or git(cwd, "status", "--porcelain").strip():
        sys.exit(f"{cwd} must be a clean checkout at {commit[:7]}: a cloud session may "
                 "upload it, uncommitted changes included (pass --cwd)")
    run = args.run or datetime.datetime.now(datetime.timezone.utc).strftime("ultra-%Y%m%d-%H%M")
    existing = []
    if (cloud_dir(repo, run) / "run.json").exists():  # adding slices to a run
        earlier = json.loads((cloud_dir(repo, run) / "run.json").read_text(encoding="utf-8"))
        if earlier["commit"] != commit:
            sys.exit(f"run {run} reviews {earlier['commit'][:7]}, not {commit[:7]}")
        existing = earlier["slices"]
    brief = args.brief.read_text(encoding="utf-8").strip()
    slices, _ = plan_slices(repo, plan, commit)
    wanted = parse_slices(args.slices) if args.slices else None
    again = sorted({r["n"] for r in existing} & (wanted or set(range(1, len(slices) + 1))))
    if again:
        sys.exit(f"run {run} already launched slice(s) {again}; choose others with --slices")
    records = []
    for n, s in enumerate(slices, 1):
        if wanted and n not in wanted:
            continue
        branch, out = f"review/{run}/slice-{n}", f"research/{run}/slice-{n}.jsonl"
        prompt = (f"{brief}\n\nCommit: {commit}. Review only these files, reading anything else "
                  f"for context:\n" + "\n".join(f"- {p}" for p in s["files"]) +
                  f"\n\nWrite your findings to {out}. {FINDINGS_FORMAT} Commit only that file, on a new branch "
                  f"{branch} from {commit[:12]}, and push it to origin. Edit nothing else. If "
                  "the push fails, give the exact error in your final message.")
        records.append({"n": n, "branch": branch, "file": out, "lines": s["lines"],
                        "files": s["files"], "prompt": prompt})
    total = sum(r["lines"] for r in records)
    print(f"run {run}: {len(records)} cloud session(s), {total} lines, at {commit[:7]}")
    if args.dry_run:
        print(records[0]["prompt"] if records else "nothing selected")
        return
    exe = __import__("shutil").which("claude") or "claude"
    env = {k: v for k, v in os.environ.items() if k != "CLAUDECODE"}
    # --cloud needs a terminal, not a visible one: each gets a hidden console of its
    # own, which closes once the session exists; the session then runs in the cloud.
    # Through conhost.exe explicitly, because a new console is otherwise handed to
    # the default terminal (Windows Terminal), which ignores SW_HIDE.
    flags = getattr(subprocess, "CREATE_NEW_CONSOLE", 0)
    if not flags:
        sys.exit("cloud launch needs Windows consoles here; run each prompt with "
                 "`claude --cloud` in a terminal (see --dry-run)")
    info = subprocess.STARTUPINFO()
    info.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    info.wShowWindow = 0 if not args.visible else 1  # SW_HIDE / SW_SHOWNORMAL
    host = [] if args.visible else ["conhost.exe"]
    for r in records:
        subprocess.Popen([*host, exe, "--cloud", r["prompt"]], cwd=cwd, env=env,
                         creationflags=flags, startupinfo=info)
        print(f"slice {r['n']}: launched -> {r['branch']}")
    d = cloud_dir(repo, run)
    d.mkdir(parents=True, exist_ok=True)
    every = sorted(existing + records, key=lambda r: r["n"])
    (d / "run.json").write_text(json.dumps({"run": run, "commit": commit, "slices": every},
                                           indent=2), encoding="utf-8")
    print(f"\nthen: build_slices.py cloud-fetch --repo {repo} --run {run}")


def cloud_fetch(args) -> None:
    import time

    repo = args.repo.resolve()
    d = cloud_dir(repo, args.run)
    run = json.loads((d / "run.json").read_text(encoding="utf-8"))
    deadline = time.monotonic() + 60 * args.wait
    while True:
        git(repo, "fetch", "-q", "origin",
            f"+refs/heads/review/{args.run}/*:refs/remotes/origin/review/{args.run}/*")
        absent = [r["n"] for r in run["slices"] if subprocess.run(
            ["git", "rev-parse", "-q", "--verify", f"origin/{r['branch']}"], cwd=repo,
            capture_output=True).returncode]
        if not absent or time.monotonic() >= deadline:
            break
        print(f"waiting for slices {absent}", flush=True)
        time.sleep(60)
    missing, merged, problems = [], [], []
    for r in run["slices"]:
        ref = f"origin/{r['branch']}"
        found = subprocess.run(["git", "show", f"{ref}:{r['file']}"], cwd=repo,
                               capture_output=True, text=True, encoding="utf-8")
        if found.returncode:
            missing.append(r["n"])
            continue
        (d / Path(r["file"]).name).write_text(found.stdout, encoding="utf-8")
        records, bad = parse_findings(found.stdout, r["n"])
        merged += records
        problems += bad
        counts = {s: sum(1 for x in records if x.get("severity") == s) for s in SEVERITIES}
        print(f"slice {r['n']}: " + ", ".join(f"{v} {k}" for k, v in counts.items()))
    order = {s: i for i, s in enumerate(SEVERITIES)}
    findings = sorted((x for x in merged if x["kind"] == "finding"),
                      key=lambda x: (order.get(x.get("severity"), 9), x["slice"]))
    checked = [x for x in merged if x["kind"] == "checked"]
    (d / "findings.jsonl").write_text(
        "".join(json.dumps(x, ensure_ascii=False) + "\n" for x in findings + checked),
        encoding="utf-8")
    print(f"\n{len(findings)} findings, {len(checked)} checked-sound -> {d / 'findings.jsonl'}")
    for p in problems:
        print(f"malformed: {p}")
    print(f"missing (not pushed yet, or failed): {missing}" if missing else "all slices in")


def slice_patch(r: dict) -> str:
    tree = Path(r["worktree"])
    git(tree, "add", "-A", "--intent-to-add")  # new files a fix created
    return git(tree, "diff", "--binary", r["head"])


def collect(args) -> None:
    repo = args.repo.resolve()
    m = json.loads(manifest_path(repo).read_text(encoding="utf-8"))
    out = manifest_path(repo).parent / "ultra-patches"
    out.mkdir(exist_ok=True)
    patches, touched = {}, {}
    for r in m["slices"]:
        text = slice_patch(r)
        if not text.strip():
            continue
        path = out / f"slice-{r['n']}.patch"
        path.write_text(text, encoding="utf-8", newline="\n")
        patches[r["n"]] = path
        for line in text.splitlines():
            if line.startswith("diff --git a/"):
                touched.setdefault(line.split(" b/", 1)[1], []).append(r["n"])
    if not patches:
        print("no slice has edits to collect")
        return
    for f, ns in sorted(touched.items()):
        if len(ns) > 1:
            print(f"conflict risk: {f} edited by slices {ns}")
    fixes = Path(f"{m['prefix']}-fixes")
    if not fixes.exists():
        git(repo, "worktree", "add", "-q", "-b", args.branch, str(fixes), m["commit"])
    for n, path in sorted(patches.items()):
        result = subprocess.run(["git", "apply", "--3way", "--index", str(path)], cwd=fixes,
                                capture_output=True, text=True)
        if result.returncode:
            sys.exit(f"slice {n}'s patch did not apply cleanly in {fixes}:\n{result.stderr}"
                     f"Resolve there, commit, then rerun collect.")
        git(fixes, "commit", "-q", "-m", f"ultra slice {n}: review fixes")
        for r in m["slices"]:
            if r["n"] == n:
                r["collected"] = True
        print(f"slice {n}: applied ({path})")
    manifest_path(repo).write_text(json.dumps(m, indent=2), encoding="utf-8")
    print(f"\nfixes on {args.branch} in {fixes}; verify each finding, test, then open a PR")


def clean(args) -> None:
    repo = args.repo.resolve()
    m = json.loads(manifest_path(repo).read_text(encoding="utf-8"))
    for r in m["slices"]:
        tree = Path(r["worktree"])
        if tree.exists():
            edited = bool(slice_patch(r).strip())
            if edited and not r["collected"] and not args.force:
                sys.exit(f"slice {r['n']} has uncollected edits in {tree}; collect, or pass --force")
            git(repo, "worktree", "remove", "--force", str(tree))
        for branch in (f"ultra/slice-{r['n']}", f"ultra/base-{r['n']}"):
            git(repo, "branch", "-D", branch, check=False)
        print(f"slice {r['n']}: removed")
    manifest_path(repo).unlink()
    print("manifest removed; the fixes worktree and branch, if any, are kept")


def main() -> None:
    parser = argparse.ArgumentParser(allow_abbrev=False)
    sub = parser.add_subparsers(dest="command", required=True)
    pl = sub.add_parser("plan")
    pl.add_argument("--repo", type=Path, required=True)
    pl.add_argument("--base-ref", default="origin/main")
    pl.add_argument("--out", type=Path)
    b = sub.add_parser("build")
    b.add_argument("--repo", type=Path, required=True)
    b.add_argument("--plan", type=Path, required=True)
    b.add_argument("--prefix")
    b.add_argument("--dry-run", action="store_true")
    la = sub.add_parser("launch")
    la.add_argument("--repo", type=Path, required=True)
    la.add_argument("--slices", help="comma-separated slice numbers (default: all)")
    la.add_argument("--jobs", type=int, default=0, help="runs at once (default: all)")
    la.add_argument("--rerun", action="store_true", help="redo slices that have findings")
    la.add_argument("--dry-run", action="store_true")
    cl = sub.add_parser("cloud")
    cl.add_argument("--repo", type=Path, required=True)
    cl.add_argument("--plan", type=Path, required=True)
    cl.add_argument("--brief", type=Path, required=True, help="review instructions for every slice")
    cl.add_argument("--cwd", type=Path, help="clean checkout at the base ref (default: --repo)")
    cl.add_argument("--run", help="run name (default: ultra-<utc time>)")
    cl.add_argument("--slices", help="comma-separated slice numbers (default: all)")
    cl.add_argument("--dry-run", action="store_true")
    cl.add_argument("--visible", action="store_true", help="show the launch consoles (to see an error)")
    cf = sub.add_parser("cloud-fetch")
    cf.add_argument("--repo", type=Path, required=True)
    cf.add_argument("--run", required=True)
    cf.add_argument("--wait", type=float, default=0, help="minutes to keep polling for slices not yet pushed")
    c = sub.add_parser("collect")
    c.add_argument("--repo", type=Path, required=True)
    c.add_argument("--branch", default="ultra/fixes")
    k = sub.add_parser("clean")
    k.add_argument("--repo", type=Path, required=True)
    k.add_argument("--force", action="store_true")
    args = parser.parse_args()
    {"plan": draft_plan, "build": build, "launch": launch, "cloud": cloud, "cloud-fetch": cloud_fetch,
     "collect": collect, "clean": clean}[args.command](args)


if __name__ == "__main__":
    main()
