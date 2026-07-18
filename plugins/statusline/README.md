# statusline

A richer Claude Code status line, in one row:

```
⎇ master   Opus 4.8 (1M)   ███░░░░░ 34%   ⧗ 7% (4h) · 86% (2d)   ~/repos/fonts
```

| Segment | Shows |
|---|---|
| `⎇ master` | git branch (preceded by the session name only when it differs from the dir) |
| `Opus 4.8 (1M)` | current model |
| `███░░░░░ 34%` | context-window usage — a quiet flat gray gauge |
| `⧗ 7% (4h) · 86% (2d)` | subscription usage limits: 5-hour & 7-day, each % used + time-to-reset (green → yellow → red) |
| `~/repos/fonts` | working directory (at the end) |

It also keeps the terminal/tab **title** set to the session name.

## Install

```
/plugin marketplace add sushiHex/sushi-bar
/plugin install statusline@sushi-bar
/statusline:install
```

`/statusline:install` writes the `statusLine` block into your `~/.claude/settings.json`
(pointing at the bundled script) and backs up any status line you already had. Restart the
session — or wait for the next render — to see it.

Pure-ASCII variant (glyph-free) for terminals/fonts without the box/branch glyphs:
```
/statusline:install ascii
```

Remove it (restores your previous status line if there was one):
```
/statusline:uninstall
```

## Notes

- **The 5h/7d usage trackers appear only on Claude.ai Pro/Max, and only after the session's
  first API response** — that data isn't in the status-line input until then. Every segment is
  optional, so it renders cleanly without it.
- A plugin can't contribute a main status line directly, so `/statusline:install` is how it gets
  wired in. After you **update** the plugin, re-run `/statusline:install` to refresh the path.
- Git branch is read straight from `.git/HEAD` — no `git` process spawned per render.

**Requirements:** Python 3.9+ (`python` or `python3` on PATH). Cross-platform.
