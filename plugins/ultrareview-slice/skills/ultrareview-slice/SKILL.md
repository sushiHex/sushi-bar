---
name: ultrareview-slice
description: Prepare `/code-review ultra` runs on an existing codebase (not just a branch diff): one slice of the highest-risk files, or the whole codebase partitioned into slices run in parallel, each under ultrareview's 500-file / 8,000-line cap, with their --fix edits collected onto one branch afterwards; or the same slices reviewed by `claude --cloud` sessions on cloud-session credit, findings pushed to branches and fetched back. Use when the user asks for a repo-wide, whole-codebase or "largest possible" ultrareview, when ultrareview reports "No changes to review" on a fresh branch, or when it refuses a diff as too large.
---

# Ultrareview slice

`/code-review ultra` with no argument reviews the current branch's diff against the
default branch. A branch freshly cut from main has no diff ("No changes to review"),
and a whole repository is far over the cap: 500 changed files and 8,000 changed lines
per branch review. Its whole-repo fallbacks are bound by the same caps. So a
"repo-wide" review is a sequence of slices, each a local branch whose diff against a
chosen base is exactly the slice.

The mechanism: in a dedicated worktree, commit 1 removes the slice files from the
index (the base); commit 2 restores them. `/code-review ultra <base-commit>` then
reviews "the changes on your branch since that commit", which is the whole slice as
additions. Both commits are local scaffolding and are never pushed.

Two scripts: `build_slices.py` partitions the whole codebase into slices, one
worktree each; `build_slice.py` packs one slice of chosen paths. Prefer the first for
"the whole codebase"; use the second for a single targeted run. Both sit beside this
file: `<skill dir>` below is the base directory Claude Code names when it loads this
skill. They need Python 3.9+ and git 2.31+; nothing else.

## Whole codebase (many slices)

1. **Draft a plan, then edit it.** `build_slices.py plan --repo <repo> [--out
   plan.json]` pairs each source file with the tests named after it (`test_x.py`,
   `x_test.go`, `x.test.ts`, `x.spec.ts`), orders groups largest first, and starts
   from default exclusions (lockfiles, images, fixtures, snapshots, vendor, dist). It
   names the test files that match no source file. Then edit by hand: add the
   repo's own data to `exclude` (mutation catalogs, generated code), merge modules
   that call into each other into one group, put the riskiest groups first, and place
   orphan tests with what they test. The plan is JSON, kept outside the repo (e.g. the
   scratchpad):

   ```json
   {"base_ref": "origin/main", "max_lines": 8000, "max_files": 500, "margin": 400,
    "exclude": ["tests/mutations/*", "tests/fixtures/*", "*.lock"],
    "groups": [["src/server.py", "tests/test_server.py"], ["src/auth/", "tests/auth/"]]}
   ```

   - A group is a module with its tests, so one run sees both. List groups in risk
     order; every file in no group follows, one by one, so docs and leftovers are still
     covered.
   - Exclude data the reviewer can't usefully read (generated files, lockfiles,
     fixtures, catalogs of test cases) and frozen code `--fix` must not edit. The build
     prints each exclusion pattern with its file count; nothing is dropped silently.
   - `margin` (default 400) is headroom under the line cap. Ultra counts raw lines,
     blank ones included, as the script does.
2. **Check the partition:** `python -I -B <skill dir>/build_slices.py
   build --repo <repo> --plan <plan> --dry-run`. Groups pack whole, in order; a group
   over the budget is split file by file, with a warning; a single file over it stops
   the build. Reorder or regroup until the slices make sense.
3. **Build:** the same command without `--dry-run`. It creates `<repo>-ultra-N` on
   `ultra/slice-N` (base `ultra/base-N`) per slice, checks that every slice's tree equals
   the base ref, writes a manifest to `<git-common-dir>/ultra-slices.json`, and prints
   one command per slice.
4. **Hand the user the launch.** Ultrareview bills usage credits (3 free runs per
   account, then roughly $5-25 a review), so state the count and the cost. The user
   runs it; Claude never does, not even through this script:

   ```
   ! python -I -B <skill dir>/build_slices.py launch --repo <repo>
   ```

   It runs `claude ultrareview <base-N> --json --trust-workspace` in every slice
   worktree at once (`--jobs N` to limit, `--slices 1,3` to choose, `--dry-run` to
   print the commands), waits for each (45 minutes by default), and saves the findings
   to `<git-common-dir>/ultra-findings/slice-N.json`, with stderr beside them as `.log`.
   Slices that already have findings are skipped unless `--rerun`. With the free runs
   used and usage credits off, every run refuses within seconds ("Free ultrareviews
   used. Turn on usage credits to continue."), bills nothing, and leaves only a log:
   turn credits on at https://claude.ai/settings/usage and launch again. Not
   documented: whether this form asks before billing once credits are on, and how
   many runs may go at once. Watch the first billed launch.
5. **Fix from the findings (default).** Read every slice's findings, verify each
   against source (reviews are claims), and fix the confirmed ones on one branch off
   the base ref, with tests. Record what you reject and why. One branch, one PR, and
   nothing fixed unverified.

   *Alternative:* the user runs each slice interactively with `--fix` (the commands
   `build` printed; each shows a cost dialog), then `collect`: Every slice tree equals the
   base, so each worktree's `--fix` edits (uncommitted or committed, new files
   included) are a patch against the base. It saves them to
   `<git-common-dir>/ultra-patches/`, names any file two slices edited, and applies
   them onto `ultra/fixes` in `<repo>-ultra-fixes`, one commit per slice, without the
   scaffolding commits. A patch that doesn't apply stops it: resolve there, commit,
   rerun.
6. **Verify, then PR.** Treat every fix as a claim: check it against source, run the
   tests, mutation-test what the project requires, and open a normal PR.
7. **Clean:** `build_slices.py clean --repo <repo>` removes the slice worktrees and
   branches and the manifest; it refuses a slice with uncollected edits unless
   `--force`. The fixes worktree is kept.

## Whole codebase on cloud-session credit (no ultrareview)

Ultrareview bills usage credits only. A cloud-session bonus credit (or plan usage)
pays for ordinary `claude --cloud` sessions instead, so this mode runs the review
itself as cloud sessions, one per slice, using the same plan and partition. The
8,000-line cap belongs to ultrareview, but slices still keep each session focused.
Measured on hardline-mcp: $2 for a 1,000-line slice, $4 for a 5,700-line one
(about 6 minutes), and about $21 for the whole codebase in 7 slices (40,800 lines,
all done within about 20 minutes): roughly $0.50 per 1,000 lines, plus a dollar or
two fixed per session. Fewer, larger slices are cheaper. Estimate it and tell the
user before launching. Get their go: it spends
their credit.

1. **Write a brief**: the review instructions every slice gets. The format and the
   push are added by the script, so the brief is only about what to look for. For
   a new codebase:
   - **Where the rules live:** point at the repo's CLAUDE.md, architecture docs and
     invariants, and say docs and comments are claims to verify against code.
   - **Its bug classes, by name:** what has actually broken in this codebase (from
     git log `fix:` commits and CLAUDE.md gotchas), not generic categories. For
     hardline that was shared-store races, transactions, process identity and
     liveness, Windows boundaries, and tests that pass against broken code.
   - **Its accepted limits:** name the documented trade-offs, and say to report one
     only if its stated reasoning is shown wrong.
   - **Proof:** the repo's install and test commands, and its mutation or probe
     method, so findings are demonstrated, not asserted.
   - Attack, don't validate; skip style; edit nothing but the findings file.
2. **Dry run:** `build_slices.py cloud --repo <repo> --plan <plan> --brief <brief>
   --cwd <clean checkout at the base ref> --dry-run` prints slice 1's full prompt.
   `--cwd` must be clean and at the base commit, since a session may upload it.
3. **Launch:** the same without `--dry-run` (`--slices 1` to test one first). Each
   session gets its own hidden console (through `conhost.exe`, since Windows Terminal
   ignores "hidden"), because `--cloud` needs a terminal, not a visible one. The
   console exits once the session exists, and the session runs in the cloud.
   `--visible` shows the consoles, to read a launch error. Each is told to
   commit only `research/<run>/slice-N.jsonl` on `review/<run>/slice-N` and push.
   Pushing needs the Claude GitHub App with write access on the repo. The script, not
   the brief, fixes the JSONL format: `{"kind": "finding", "severity", "file", "line",
   "summary", "failure_scenario", "evidence", "verified"}` or `{"kind": "checked",
   "summary"}`. The CLI's own JSON options (`--output-format`, `--json-schema`) work
   only with `--print`, which runs locally and ignores `--cloud`.
4. **Fetch:** `build_slices.py cloud-fetch --repo <repo> --run <run>` fetches the
   `review/<run>/*` branches, checks every line against the format (naming malformed
   ones by slice and line), and writes the per-slice files plus one merged
   `findings.jsonl`, sorted by severity and tagged with each record's slice, to
   `<git-common-dir>/ultra-cloud/<run>/`. `--wait N` polls every minute for up to N
   minutes until every slice has pushed (run it in the background); it names the slices
   still missing. The sessions themselves are at claude.ai/code. A run grows: launch
   one slice to measure, then `--run <same run> --slices 2-7` adds the rest to the
   same run and the same `findings.jsonl`. It refuses a slice the run already
   launched, and refuses a different base commit.
5. **Verify** every finding against source before reporting or fixing. Then delete
   the `review/<run>/*` branches on origin, once the user agrees.

Non-Windows: the launch can't open consoles. Run each prompt (`--dry-run` shows
them) with `claude --cloud` in a terminal.

## One slice

1. **Confirm the caps in effect.** The defaults are 500 files and 8,000 lines, but a
   refusal names the actual values. Use the user's stated values if given.
2. **Rank by risk, don't pack by size.** The line cap binds long before the file cap,
   so fill the slice with the code that matters most:
   - authority/security boundaries, protocol parsers, process/sandbox launchers;
   - code that recently failed or changed;
   - modules with known debt.

   Exclude generated files, lockfiles, vendored code, fixtures and frozen modules,
   i.e. anything a project marks as frozen, which `--fix` must not edit.
   Measure first: `git ls-files <dir> | xargs cat | wc -l` per directory/file.
3. **Build the slice** with the script. It creates the worktree and branch, packs paths
   in the order given until the cap, makes the two commits, verifies the diff stat, and
   prints the exact command:

   ```bash
   python -I -B <skill dir>/build_slice.py \
     --repo <repo> --worktree <repo>-ultra-audit --branch audit/ultra-<date> \
     [--base-ref origin/main] [--max-lines 8000] [--max-files 500] [--margin 0] \
     <path-or-dir> [<path-or-dir> ...]
   ```

   Paths are tried in order. Directories expand to their tracked files in sorted order.
   A file that would exceed the cap is skipped, and later smaller files can still fill
   the remainder. `--rebuild` resets an existing audit branch to the base ref and
   rebuilds it in place. Use it to change the slice; the base commit id changes each
   time.
4. **Hand the user the command.** The user runs it; it is billed and user-triggered, and
   Claude must never launch ultrareview itself:

   ```
   cd <worktree>; claude "/code-review ultra --fix --max-findings all <base-commit>"
   ```

## Cautions to state

- `--fix` edits only the audit worktree(s). Bring fixes to main through a normal PR,
  *without* the scaffolding commits (`build_slices.py collect` does this). Coordinate
  with whoever owns the files.
- On native Windows, uncommitted edits to tracked files upload as they are, so the
  worktree must be clean. The script refuses a dirty one.
- `--max-findings` behaviour under ultra isn't documented; findings still get verified
  against source before acting.
- `claude -p '/code-review ultra'` launches and exits without waiting, and stops
  without launching a run that would bill usage credits: script with
  `claude ultrareview`, never `-p`.
- Running ultra from inside a cloud session (`claude --cloud`) isn't documented, nor
  where its `--fix` lands there. Nothing documents different caps there either, so
  don't count on a cloud session to avoid slicing.
- If ultrareview refuses by a few lines, its counting differs. Drop the last packed
  file (`--margin N` reserves headroom) and rebuild.
- With `build_slice.py`, each later slice (B, C, …) is a separate run: rebuild with the
  next ranked paths, after taking the previous slice's fixes out. `build_slices.py`
  avoids this by giving every slice its own worktree.
- A worktree can't be removed while a session runs in it (Windows holds its folder).
  Have the user exit those sessions before `clean`.
- Slices see the whole checkout but review only their own files, so a finding that
  spans two slices (a caller in one, its callee in another) can be missed. Group code
  that calls into each other.
