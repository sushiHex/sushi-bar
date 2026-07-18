---
allowed-tools: Bash(python:*), Bash(python3:*), Bash(command:*), Read
description: Remove the sushi-bar status line (restores your previous one if any)
model: sonnet
effort: low
---
!`PY=$(command -v python || command -v python3); "$PY" "${CLAUDE_PLUGIN_ROOT}/install.py" --uninstall`

Report the result above. If a previous status line was restored from backup, say so; otherwise confirm the sushi-bar status line was removed. Tell the user to restart the session (or wait for the next render) for the change to take effect.
