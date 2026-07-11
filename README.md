# 🍣 sushi-bar

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
![Platform: Windows](https://img.shields.io/badge/platform-Windows-blue)
![Claude Code](https://img.shields.io/badge/Claude%20Code-plugin%20marketplace-8A63D2)

Small, bite-sized Claude Code tools for **native Windows**, by [sushiHex](https://github.com/sushiHex). A third-party [plugin marketplace](https://code.claude.com/docs/en/plugin-marketplaces) — add it once, install the plates you want.

## Install

```
/plugin marketplace add sushiHex/sushi-bar
/plugin install snip@sushi-bar
```

Update later with `/plugin marketplace update sushi-bar`.

## Plugins

| Plugin | What it does |
|--------|--------------|
| **[snip](plugins/snip)** | Capture a screenshot straight into your Claude Code session — box, screen, window, or clipboard. |

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

## License

[MIT](LICENSE) © 2026 sushiHex
