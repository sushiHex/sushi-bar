#!/usr/bin/env python
"""sushi-bar status line for Claude Code.

Renders one line:  session · dir · git branch │ model │ context bar │ 5h/7d usage.

Reads the status-line JSON on stdin (schema per the Claude Code 2.1.x binary) and
prints an ANSI-colored line. Also emits an OSC title escape so the terminal/tab title
stays set. Every field is optional and rendered defensively — a missing field just
drops its segment, so it degrades cleanly on any platform or Claude tier.

Cross-platform. No third-party deps. Set SUSHI_STATUSLINE_ASCII=1 for a glyph-free
(pure-ASCII) rendering on terminals/fonts that lack the box/branch glyphs.
"""
from __future__ import annotations

import json
import os
import sys
import time

# Claude Code runs this with stdout defaulting to the host console codepage
# (e.g. cp1252 on Windows), which can't encode the box/glyph characters below.
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

ASCII = bool(os.environ.get("SUSHI_STATUSLINE_ASCII"))
if ASCII:
    BAR_F, BAR_E, BR_PRE, CLK, FAST = "#", "-", "", "", "fast"
else:
    BAR_F, BAR_E, BR_PRE, CLK, FAST = "▒", "░", "⎇ ", "⧗ ", "⚡fast"

CYAN, GREY, WHITE, GREEN, YELLOW, RED, MAGENTA, BLUE = (
    "96", "90", "97", "92", "93", "91", "95", "94",
)
MODEL_GRAY = "38;5;245"  # medium gray, matching Claude Code's dim hint text (e.g. "(shift+tab to cycle)")
LGRAY = "37"  # light gray — the context %, one step below bright white


def c(code: str, text: str) -> str:
    return f"\033[{code}m{text}\033[0m"


SEP = "  "  # two spaces between elements — no divider; color already separates them


def sev_color(pct: float) -> str:
    """Green < 50, yellow < 80, red >= 80. Used for the usage-limit trackers."""
    if pct >= 80:
        return RED
    if pct >= 50:
        return YELLOW
    return GREEN


# Context-bar: a flat, quiet gauge. Fill uses the same medium gray as the model
# name (MODEL_GRAY); the empty track is a dimmer gray. No fullness-based shading.
GRAY_TRACK = "38;5;237"


def read_json() -> dict:
    try:
        return json.load(sys.stdin)
    except Exception:
        return {}


def git_branch(cwd: str) -> str:
    """Read the branch from .git/HEAD without spawning git. Handles worktrees (.git file)."""
    try:
        gitpath = os.path.join(cwd, ".git")
        if os.path.isfile(gitpath):  # worktree: '.git' is a file 'gitdir: <path>'
            with open(gitpath, "r", encoding="utf-8", errors="replace") as fh:
                line = fh.readline().strip()
            if not line.startswith("gitdir:"):
                return ""
            gitdir = line.split(":", 1)[1].strip()
            if not os.path.isabs(gitdir):
                gitdir = os.path.normpath(os.path.join(cwd, gitdir))
            head = os.path.join(gitdir, "HEAD")
        else:
            head = os.path.join(gitpath, "HEAD")
        with open(head, "r", encoding="utf-8", errors="replace") as fh:
            ref = fh.readline().strip()
        if ref.startswith("ref:"):
            return ref.rsplit("/", 1)[-1]
        return ref[:7] if ref else ""  # detached HEAD -> short sha
    except Exception:
        return ""


def short_dir(path: str) -> str:
    home = os.path.expanduser("~")
    try:
        if path and os.path.normcase(path).startswith(os.path.normcase(home)):
            path = "~" + path[len(home):]
    except Exception:
        pass
    return (path or "").replace("\\", "/")


def bar(pct: float, width: int = 8) -> str:
    pct = max(0.0, min(100.0, pct))
    filled = int(round(pct / 100 * width))
    return c(MODEL_GRAY, BAR_F * filled) + c(GRAY_TRACK, BAR_E * (width - filled))


def fmt_reset(resets_at) -> str:
    try:
        delta = float(resets_at) - time.time()
    except Exception:
        return ""
    if delta <= 0:
        return "now"
    mins = delta / 60
    if mins < 60:
        return f"{int(mins)}m"
    hours = mins / 60
    if hours < 24:
        return f"{int(round(hours))}h"
    return f"{int(round(hours / 24))}d"


def fmt_tokens(n: float) -> str:
    """Compact token count: 128000 -> '128k', 1200000 -> '1.2M'."""
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}".rstrip("0").rstrip(".") + "M"
    if n >= 1000:
        return f"{round(n / 1000)}k"
    return str(int(round(n)))


def quota_seg(window: dict) -> str:
    if not isinstance(window, dict):
        return ""
    pct = window.get("used_percentage")
    if pct is None:
        return ""
    reset = fmt_reset(window.get("resets_at"))
    tail = f" {reset}" if reset else ""
    # No 5h/7d label — the reset window (minutes/hours vs days) implies which is which.
    # No parens — the reset is dim gray, already visually distinct from the colored %.
    return c(sev_color(pct), f"{int(round(pct))}%") + c(GREY, tail)


def main() -> None:
    d = read_json()
    ws = d.get("workspace") or {}
    cwd = ws.get("current_dir") or d.get("cwd") or os.getcwd()

    base = os.path.basename(cwd.rstrip("/\\"))
    name = d.get("session_name") or base or "claude"
    # Strip any "(...)" suffix — the capacity is shown separately as the total-size
    # element next to the bar. "Opus 4.8 (1M context)" -> "Opus 4.8"; "Sonnet 5" -> "Sonnet 5".
    model = ((d.get("model") or {}).get("display_name") or "").split(" (")[0].strip()
    # Reasoning effort: low | medium | high | xhigh | max. Only present for models that
    # support it (absent on Opus 4.0/4.1, Sonnet 4.x, Haiku 4.5, claude-3-*), so it
    # simply drops out rather than rendering a misleading default.
    effort = str((d.get("effort") or {}).get("level") or "").strip()
    # Fast mode is a toggle (/fast) — shown only while it's on, never as "off".
    fast = bool(d.get("fast_mode"))
    cw = d.get("context_window") or {}
    ctx = cw.get("used_percentage")
    cw_size = cw.get("context_window_size")
    rl = d.get("rate_limits") or {}
    branch = git_branch(cwd)

    # OSC title (kept for tab identification) — written first, not part of the visible line.
    sys.stdout.write(f"\033]0;Claude: {name}\007")

    segs: list[str] = []

    # Identity first: session name (only when it differs from the dir's basename) + git branch.
    ident = []
    if name != base:
        ident.append(c(CYAN, name))
    if branch:
        ident.append(c(CYAN, f"{BR_PRE}{branch}"))
    if ident:
        segs.append(" ".join(ident))

    if model:
        # Effort rides with the model as one unit (single space, not SEP) and sits a
        # shade dimmer, so the model name stays the primary read.
        seg = c(MODEL_GRAY, model)
        if effort:
            seg += " " + c(GREY, effort)
        if fast:
            seg += " " + c(GREY, FAST)
        segs.append(seg)

    if ctx is not None:
        try:
            pct = float(ctx)
            if cw_size:
                # current size · bar · total size — usage on the left (where the bar fills), capacity on the right.
                total = c(LGRAY, fmt_tokens(float(cw_size)))
                current = c(LGRAY, fmt_tokens(pct / 100 * float(cw_size)))
                segs.append(f"{current} {bar(pct)} {total}")
            else:
                segs.append(f"{bar(pct)} {c(LGRAY, f'{int(round(pct))}%')}")
        except (TypeError, ValueError):
            pass

    quotas = [q for q in (quota_seg(rl.get("five_hour")),
                          quota_seg(rl.get("seven_day"))) if q]
    if quotas:
        segs.append((c(GREY, CLK) if CLK else "") + c(GREY, " · ").join(quotas))

    # Working directory, at the end.
    segs.append(c(GREY, short_dir(cwd)))

    sys.stdout.write(SEP.join(segs))


if __name__ == "__main__":
    main()
