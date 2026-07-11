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
| **[snip](plugins/snip)** | Draw a box anywhere on screen → the shot loads straight into your Claude Code session. |

### 🖼️ snip

Run **`/snip:snip`** → drag a box → Claude reads the shot in the same turn. Pass a question to act on it: `/snip:snip what's wrong with this error?`.

- **Always a rectangular draw-box** (its own overlay, not the OS Snip's remembered mode) — multi-monitor and DPI-correct.
- **Auto-read:** captures *and* loads the image for Claude in one step.
- Tuned to run on **Sonnet at low effort** so the read-and-answer turn stays fast.
- The bundled `snip.py` also works standalone (`python snip.py` → image on clipboard → **Alt+V**), with `--copy-path`, `--launch`, and `--print-path` modes.

> **Honest note:** Claude Code's native **Win+Shift+S → Alt+V** already covers basic screenshot paste. `snip` adds the guaranteed draw-box and the one-step capture-and-analyze.

**Requirements:** Windows 10/11 · Python 3.9+ · Pillow (`python -m pip install pillow`).

## License

[MIT](LICENSE) © 2026 sushiHex
