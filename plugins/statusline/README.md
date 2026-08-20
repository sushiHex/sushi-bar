# statusline

A richer Claude Code status line, in one row:

```
⎇ master  Opus 4.8 high  128k ▒▒░░░░░░ 1M  ⧗ 7% 4h · 86% 2d  ~/repos/fonts
```

| Segment | Shows |
|---|---|
| `⎇ master` | git branch (preceded by the session name only when it differs from the dir) |
| `Opus 4.8 high` | current model + reasoning effort (`low`/`medium`/`high`/`xhigh`/`max`), plus `⚡fast` while fast mode is on |
| `Opus 4.8 high STELI5` | …and the active output style, when one is set. `default` earns no slot; a plugin style (`prose:STELI5`) shows just the leaf |
| `128k ▒▒░░░░░░ 1M` | context window: tokens used · a dithered gray gauge · capacity (derived from the window size for every model) |
| `⧗ 7% 4h · 86% 2d` | subscription usage limits: 5-hour & 7-day, each % used + time-to-reset (green → yellow → red) |
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
- **Reasoning effort shows only for models that have it.** Claude Code omits it for Opus 4.0/4.1,
  Sonnet 4.x, Haiku 4.5 and claude-3-*, so the segment drops out rather than showing a made-up
  default. **`⚡fast` appears only while fast mode is on** — nothing is added when it's off.
- A plugin can't contribute a main status line directly, so `/statusline:install` is how it gets
  wired in. After you **update** the plugin, re-run `/statusline:install` to refresh the path.
- Git branch is read straight from `.git/HEAD` — no `git` process spawned per render.

**Requirements:** Python 3.9+ (`python` or `python3` on PATH). Cross-platform.
