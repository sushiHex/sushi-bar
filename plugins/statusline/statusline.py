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
# Ultracode's own colour in Claude Code's dark themes, rgb(175,135,255) — the
# nearest 256-colour cell. It reads as a mode, not another dim attribute, which
# is the point: ultracode is the one effort setting that changes what the
# session does rather than only how hard it thinks.
ULTRA = "38;5;141"
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


# Where the last-seen effort level and transcript offset are remembered, so a
# transcript that reaches tens of megabytes is read once and then only appended
# to. Beside the status line's own plugin data rather than in the project.
_EFFORT_CACHE = os.path.join(
    os.path.expanduser("~"), ".claude", "sushi-bar-effort.json"
)

_EFFORT_MARK = "<local-command-stdout>Set effort level to "
_EFFORT_MARK_B = _EFFORT_MARK.encode("utf-8")


def _scan_effort(raw: bytes, offset: int, fallback: str) -> tuple[str, int]:
    """Scan appended bytes, returning (level, new_offset).

    Bytes rather than text: the offset is a byte position, and reading in text
    mode on Windows collapses CRLF to LF, so len(text) is short of the real
    offset and the next read starts mid-record.

    A record counts only when it is a `user` record whose `message.content` is
    a STRING. `/effort` writes its output that way; a tool result carries a
    LIST of blocks and an assistant turn is not a user record. Without both
    checks the bar reads its own output back - grepping a transcript for this
    marker puts the marker in that transcript.
    """
    level = fallback
    lines = raw.split(b"\n")
    # A final line with no newline is a record still being written; leave it
    # for the next pass rather than parsing half of it.
    remainder = lines.pop() if lines else b""
    for line in lines:
        if _EFFORT_MARK_B not in line:
            continue
        try:
            rec = json.loads(line.decode("utf-8", "replace"))
        except Exception:
            continue
        if rec.get("type") != "user":
            continue
        message = rec.get("message") or {}
        content = message.get("content")
        if isinstance(content, str) and content.startswith(_EFFORT_MARK):
            level = content[len(_EFFORT_MARK):].split()[0].strip(":,.")
    return level, offset + len(raw) - len(remainder)


def transcript_effort(path: str) -> str:
    """The effort level last chosen with `/effort` in this session, or "".

    This is the only observable that tracks an interactive toggle. Claude Code
    sends no ultracode field to a status line and never writes the setting to
    disk, but the command's own output is persisted to the transcript, and the
    last one is what the session is running.
    """
    if not path:
        return ""
    try:
        size = os.path.getsize(path)
    except OSError:
        return ""

    cached = {}
    try:
        with open(_EFFORT_CACHE, encoding="utf-8") as fh:
            cached = json.load(fh)
    except Exception:
        pass

    offset, level = 0, ""
    if cached.get("path") == path and isinstance(cached.get("offset"), int):
        # A file that shrank is a different session or a rewritten one; reading
        # from the old offset would return whatever bytes now sit there.
        if cached["offset"] <= size:
            offset = cached["offset"]
            level = str(cached.get("level") or "")

    if offset == size and level:
        return level

    try:
        with open(path, "rb") as fh:
            fh.seek(offset)
            level, offset = _scan_effort(fh.read(), offset, level)
    except OSError:
        return level

    try:
        with open(_EFFORT_CACHE, "w", encoding="utf-8") as fh:
            json.dump({"path": path, "offset": offset, "level": level}, fh)
    except OSError:
        pass  # the read still stands; only the next one pays for it again
    return level


def settings_ultracode(cwd: str) -> bool:
    """Whether a settings file in force for `cwd` enables ultracode.

    Claude Code's own precedence: project-local overrides project, which
    overrides user. The first file that *mentions* the key decides — absent is
    not the same as false, or an unrelated project settings.json would veto the
    user's setting.
    """
    candidates = (
        os.path.join(cwd, ".claude", "settings.local.json"),
        os.path.join(cwd, ".claude", "settings.json"),
        os.path.join(os.path.expanduser("~"), ".claude", "settings.json"),
    )
    for path in candidates:
        try:
            with open(path, encoding="utf-8") as fh:
                value = json.load(fh).get("ultracode")
        except Exception:
            # Unreadable or malformed settings must not take the whole line
            # down; a status line that raises leaves no bar at all.
            continue
        if isinstance(value, bool):
            return value
    return False


def ultracode_active(effort: str, cwd: str, transcript: str = "") -> bool:
    """Whether this session is running ultracode rather than plain xhigh.

    Claude Code sends no ultracode field to a status line, and an interactive
    toggle is never written to disk, so this is inference from what *is*
    reachable. Two things make it honest rather than a guess:

    Ultracode forces effort to xhigh, so any other level rules it out outright
    — which is what catches a settings file left saying `true` after the
    session was switched to a lower level.

    CLAUDE_CODE_EFFORT_LEVEL overrides effort for the whole session and is
    inherited by this process, so when it is set it is the answer, and a
    settings file disagreeing with it is not in force.

    The gap that remains: switching from ultracode to plain xhigh with a
    settings file still saying true reads as ultracode. Nothing observable
    distinguishes those two.
    """
    if effort != "xhigh":
        return False
    # The transcript first: `/effort` is how ultracode actually gets turned on,
    # and its output is the only trace that toggle leaves anywhere. A settings
    # file can therefore only ever be staler than this.
    chosen = transcript_effort(transcript)
    if chosen:
        return chosen == "ultracode"
    env = (os.environ.get("CLAUDE_CODE_EFFORT_LEVEL") or "").strip().lower()
    if env:
        return env == "ultracode"
    return settings_ultracode(cwd)


def main() -> None:
    render(read_json())


def render(d: dict) -> None:
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
    # Ultracode is xhigh plus standing workflow orchestration, and it reaches
    # here only as "xhigh" — there is no field for it. See ultracode_active for
    # what the name is inferred from and where that inference stops.
    ultra = ultracode_active(effort, cwd, str(d.get("transcript_path") or ""))
    if ultra:
        effort = "ultracode"
    # Fast mode is a toggle (/fast) — shown only while it's on, never as "off".
    fast = bool(d.get("fast_mode"))
    # Output style reshapes every reply, so it belongs next to effort. "default"
    # is the stock behaviour and earns no slot. A plugin style arrives namespaced
    # ("prose:STELI5"); the prefix is install detail rather than session state, so
    # only the leaf is shown.
    style = str((d.get("output_style") or {}).get("name") or "").strip()
    style = "" if style.lower() == "default" else style.rsplit(":", 1)[-1].strip()
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

    if model or style:
        # Effort, fast mode and output style ride with the model as one unit
        # (single space, not SEP) and sit a shade dimmer, so the model name stays
        # the primary read. Each drops out independently when unset, so a default
        # session still renders just the model.
        seg = c(MODEL_GRAY, model) if model else ""
        for extra in (effort, FAST if fast else "", style):
            if not extra:
                continue
            # Ultracode reports itself as xhigh, since it *is* xhigh plus
            # standing workflow orchestration. Naming it takes its own colour:
            # the same one Claude Code gives it in its top-right indicator.
            colour = ULTRA if extra is effort and ultra else GREY
            seg = f"{seg} {c(colour, extra)}" if seg else c(colour, extra)
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
