---
allowed-tools: Bash(python:*), Read
description: Click-a-window screenshot into Claude
argument-hint: [Ns delay | N shots] [what to do with them]
model: sonnet
effort: low
---
Captured screenshot path(s), one per line (empty if cancelled):
!`python "${CLAUDE_PLUGIN_ROOT}/snip.py" --mode window --print-path --spec "$1"`

An overlay appears; the user clicks the window to capture. Read each path shown above with the Read tool. If it's empty or an error, tell the user the capture was cancelled and stop — do NOT read stale files. The first word may be a timer (`3s`) or a count (`3`) — ignore that leading token; then address the rest of: $ARGUMENTS
