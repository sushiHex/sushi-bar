---
allowed-tools: Bash(python:*), Bash(python3:*), Bash(command:*), Read
description: Install the sushi-bar status line into your settings.json
argument-hint: [ascii]
model: sonnet
effort: low
---
!`PY=$(command -v python || command -v python3); "$PY" "${CLAUDE_PLUGIN_ROOT}/install.py" --plugin-root "${CLAUDE_PLUGIN_ROOT}" $([ "$1" = "ascii" ] && echo --ascii)`

Report the result above.

- If it succeeded: tell the user the status line is installed, and to **restart the session** (or wait for the next render) to see it — the **5h/7d usage-limit trackers only fill in after the session's first API response** and only on a Claude.ai Pro/Max plan, so a brand-new session shows everything except those until the first turn.
- If a previous status line was backed up, note that `/statusline:uninstall` will restore it.
- If it failed, show the error and stop.

Note: this points settings.json at the currently-installed plugin version. After you update the `statusline` plugin, re-run `/statusline:install` to refresh the path.
