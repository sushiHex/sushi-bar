---
allowed-tools: Bash(python:*), Read
description: Full-screen screenshot (monitor under cursor) into Claude
argument-hint: [Ns delay | N shots] [what to do with them]
model: sonnet
effort: low
---
Captured screenshot path(s), one per line (empty if cancelled):
!`python "${CLAUDE_PLUGIN_ROOT}/snip.py" --mode screen --print-path --spec "$1"`

Read each path shown above with the Read tool (there may be several). If it's empty or an error, tell the user the capture failed and stop — do NOT read stale files. The first word may be a timer (`3s`, e.g. to open a menu first) or a count (`3`) — ignore that leading token; then address the rest of: $ARGUMENTS
