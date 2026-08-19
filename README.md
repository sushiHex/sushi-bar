# 🍣 sushi-bar

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
![Platform](https://img.shields.io/badge/platform-Windows%20%C2%B7%20cross--platform-blue)
![Claude Code](https://img.shields.io/badge/Claude%20Code-plugin%20marketplace-8A63D2)

Small, bite-sized Claude Code tools, by [sushiHex](https://github.com/sushiHex). A third-party [plugin marketplace](https://code.claude.com/docs/en/plugin-marketplaces) — add it once, install the plates you want.

## Install

```
/plugin marketplace add sushiHex/sushi-bar
/plugin install snip@sushi-bar
/plugin install statusline@sushi-bar
/plugin install prose@sushi-bar
```

Update later with `/plugin marketplace update sushi-bar`.

## Plugins

| Plugin | Platform | What it does |
|--------|----------|--------------|
| **[snip](plugins/snip)** | Windows | Capture a screenshot straight into your Claude Code session — box, screen, window, or clipboard. |
| **[statusline](plugins/statusline)** | cross-platform | A richer status line — session · dir · git branch, model + reasoning effort, context bar, and 5h/7d usage-limit trackers. |
| **[prose](plugins/prose)** | cross-platform | Three selectable output styles — ELI5 plain language, ASD-STE100 Simplified Technical English, and STELI5 (both at once). |

### 🖼️ snip

Capture a shot and have Claude *read it in the same turn*. Four modes:

| Command | Captures |
|---|---|
| `/snip:box` | drag a rectangle |
| `/snip:screen` | the monitor under your cursor |
| `/snip:window` | click a window → just that window |
| `/snip:clipboard` | whatever image is already on your clipboard |

**Modifiers** — the first word after the command:

| Type | Effect |
|---|---|
| `/snip:box 3s` | wait **3 seconds**, then capture (line up a menu/tooltip first) |
| `/snip:box 3` | take **3 shots** in a row → Claude reads all of them |
| `/snip:box 3s what's broken?` | wait 3s, capture, then address your question |

- **Runs on Sonnet at low effort by default** (set per-command) so the read-and-answer turn stays fast — it never changes your session's model or effort.
- **Multi-monitor & DPI-correct.**
- The bundled `snip.py` also works standalone (`python snip.py` → image on clipboard → **Alt+V**), with `--mode`, `--delay`, `--count`, `--copy-path`, `--launch`, `--print-path`.

> **Honest note:** Claude Code's native **Win+Shift+S → Alt+V** already covers basic screenshot paste. `snip` adds the mode set, the timer/burst modifiers, and the one-step capture-and-analyze.

**Requirements:** Windows 10/11 · Python 3.9+ · Pillow (`python -m pip install pillow`).

### 📊 statusline

A richer status line, in one row:

```
⎇ master  Opus 4.8 high  128k ▒▒░░░░░░ 1M  ⧗ 7% 4h · 86% 2d  ~/repos/fonts
```

In order: **git branch** (with session name when it differs from the dir) · **model + reasoning effort** (plus `⚡fast` while fast mode is on) · **context** (tokens used · a dithered gray gauge · window capacity, derived per model) · **5h & 7d usage-limit trackers** (% used + time-to-reset, green→yellow→red) · **working dir**. Elements are separated by spacing (no dividers); it also keeps the terminal/tab title set.

```
/plugin install statusline@sushi-bar
/statusline:install          # wires it into settings.json (backs up any existing one)
/statusline:install ascii    # glyph-free variant for bare terminals
/statusline:uninstall        # restores your previous status line
```

- A plugin can't set a main status line directly, so `/statusline:install` writes the `statusLine` block for you. Re-run it after updating the plugin.
- The **5h/7d trackers show only on Pro/Max, after the session's first API response** — every segment is optional and degrades cleanly.

**Requirements:** Python 3.9+ (`python` or `python3`). Cross-platform.

### ✍️ prose

Three selectable **output styles**. They change how Claude writes *to you*, not what it builds.

| Style | Reads like |
|---|---|
| `prose:ELI5` | Plain language, everyday analogies, every technical term defined on first use |
| `prose:ASD-STE100` | [Simplified Technical English](https://www.asd-ste100.org/) — short sentences, active voice, one instruction per sentence |
| `prose:STELI5` | Both: ELI5's explaining, under STE's sentence discipline. Measured at **zero** sentences over 35 words where ELI5 had three. |

```
/plugin install prose@sushi-bar
```

Then pick one in **`/config` → Output style**, or set `"outputStyle": "prose:ELI5"` in `settings.json`.

- Both keep Claude Code's normal engineering behaviour (`keep-coding-instructions: true`) — only the prose changes.
- Code, commands, paths and error text are copied **verbatim**; a caveat is never dropped for being "advanced"; bad news stays blunt.
- Commit messages, code comments and in-repo docs keep **their project's** conventions.

> **Honest limit:** the ASD-STE100 style applies the *writing rules*. The ~900-word approved dictionary is licensed by the ASD and isn't bundled, so output isn't verified against it — and the style forbids Claude from claiming otherwise.

**Requirements:** none. No dependencies, no scripts.

## License

[MIT](LICENSE) © 2026 sushiHex
