# ultrareview-slice

Review a whole codebase with `/code-review ultra`, which reviews only a diff of at most 500 files and 8,000 lines. This skill makes a whole repository reviewable:

- It partitions the repo into slices.
- Each slice gets a worktree of its own, on a branch whose diff against a base is exactly that slice.
- Each run reviews its own slice, with the whole checkout there for context.

Ask Claude for a "whole-codebase ultrareview" and the skill takes over. You can also invoke it as `ultrareview-slice:ultrareview-slice`.

## Two ways to run the slices

**Ultrareview**, billed to usage credits: 3 free runs per account, then roughly $5–25 a review. `launch` runs `claude ultrareview <base> --json` in every slice at once and saves each slice's findings. You start the launch yourself; Claude never does, because it's billed. Or run each slice interactively with `--fix`, and `collect` gathers the edits onto one branch.

**Cloud sessions**, billed to cloud-session credit or plan usage:

- `cloud` starts one `claude --cloud` review session per slice.
- Each session commits its findings as JSONL to a branch and pushes it. The Claude GitHub App needs write access to the repo.
- `cloud-fetch` pulls those branches, validates every line, and merges them into one `findings.jsonl`.

Measured on a 40,800-line Python codebase: about $21 for all 7 slices, done within about 20 minutes.

## Commands

All in `skills/ultrareview-slice/build_slices.py`, which needs Python 3.9+ and git 2.31+:

| Command | Does |
|---|---|
| `plan` | Drafts a plan file: each source file paired with the tests named after it, with default exclusions |
| `build` | Partitions the repo per the plan, with one worktree and two scaffolding commits per slice |
| `launch` | Runs `claude ultrareview` on every slice, in parallel; you run this |
| `collect` | Applies each slice's `--fix` edits onto one `ultra/fixes` branch, without the scaffolding |
| `cloud` | Starts one `claude --cloud` review session per slice, in hidden consoles on Windows |
| `cloud-fetch` | Fetches the findings branches, validates them, and merges them into `findings.jsonl` |
| `clean` | Removes the slice worktrees and branches; refuses while edits are uncollected |

`build_slice.py` builds a single slice of hand-picked, highest-risk paths.

Every finding is a claim: the skill tells Claude to verify each against source before fixing it. `SKILL.md` has the full procedure and its cautions.
