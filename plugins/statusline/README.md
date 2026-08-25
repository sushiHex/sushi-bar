# statusline

A richer Claude Code status line, in one row:

```
⎇ master  Opus 4.8 high  128k ▒▒░░░░░░ 1M  ⧗ 7% 4h · 86% 2d  ~/repos/fonts
```

| Segment | Shows |
|---|---|
| `⎇ master` | git branch (preceded by the session name only when it differs from the dir) |
| `Opus 4.8 high` | current model + reasoning effort (`low`/`medium`/`high`/`xhigh`/`max`), shown as purple `ultracode` when that is active, plus `⚡fast` while fast mode is on |
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
- **`ultracode` is shown in purple in place of `xhigh`**, matching the colour Claude Code gives
  it in its own top-right indicator. Ultracode *is* xhigh plus standing workflow orchestration,
  so it arrives here only as `xhigh` — the status-line input carries no field for it, and
  `/effort ultracode` is session-only and writes nothing to settings.

  It is read from the **session transcript** instead. `/effort` prints its result, and that
  output is persisted as a plain user record:

  ```
  {"type":"user","message":{"role":"user",
   "content":"<local-command-stdout>Set effort level to ultracode ..."}}
  ```

  The last such record is what the session is running, so an interactive toggle is tracked —
  the case that matters, since it is how ultracode actually gets turned on. A record counts
  only when it is a `user` record whose `content` is a **string**: a tool result carries a
  *list* of blocks, and without that check the bar reads its own output back the moment
  anything greps the transcript for this marker.

  The transcript can reach tens of megabytes and this runs on every render, so the byte offset
  and last value are cached in `~/.claude/sushi-bar-effort.json` and only appended bytes are
  scanned — about 0.1s once, then ~2ms. A file that shrank is re-read from the start, since it
  is a different session or a rewritten one.

  Falls back to `CLAUDE_CODE_EFFORT_LEVEL=ultracode` in the environment, then `"ultracode": true`
  in the settings files in force (local → project → user), for sessions where `/effort` was
  never used. All three are gated on the reported effort being `xhigh`, since ultracode forces
  that.
- A plugin can't contribute a main status line directly, so `/statusline:install` is how it gets
  wired in. After you **update** the plugin, re-run `/statusline:install` to refresh the path.
- Git branch is read straight from `.git/HEAD` — no `git` process spawned per render.

**Requirements:** Python 3.9+ (`python` or `python3` on PATH). Cross-platform.
