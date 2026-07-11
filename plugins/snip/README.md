# snip

Capture a screenshot straight into your Claude Code session, on **native Windows**.

Four namespaced commands (installed via the marketplace):

| Command | Captures |
|---|---|
| `/snip:box` | drag a rectangle |
| `/snip:screen` | the monitor under your cursor (`snip.py --all` = every monitor) |
| `/snip:window` | click a window → just that window |
| `/snip:clipboard` | the image already on your clipboard |

**Modifiers** — the first word after the command: `3s` = wait 3 seconds first (grab a menu/tooltip); `3` = take 3 shots in a row; anything else is treated as your question. Example: `/snip:box 3s why is this misaligned?`.

Each command **runs on Sonnet at low effort** (set in the command frontmatter) so the read-and-answer turn stays fast, without changing your session's model/effort.

The bundled `snip.py` is also a standalone CLI:

| Flag | Does |
|---|---|
| `--mode box\|screen\|window\|clipboard` | what to capture (default `box`) |
| `--delay N` | wait N seconds before each capture |
| `--count N` | N captures in a row (max 10) |
| `--copy-path` | copy the file path(s) instead of the image |
| `--print-path` | print only the path(s) (used by the commands) |
| `--launch` | start a new `claude` with the image |

Default (no output flag) copies the image to the clipboard → press **Alt+V** to stage `[Image #N]`.

**Requirements:** Windows 10/11 · Python 3.9+ · Pillow (`python -m pip install pillow`).
