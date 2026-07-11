---
allowed-tools: Bash(python:*), Read
description: Draw-box screenshot into Claude (opt "Ns" delay or "N" shots)
argument-hint: [Ns delay | N shots] [what to do with them]
model: sonnet
effort: low
---
Captured screenshot path(s), one per line (empty if cancelled):
!`python "${CLAUDE_PLUGIN_ROOT}/snip.py" --mode box --print-path --spec "$1"`

Read each path shown above with the Read tool (there may be several). If it's empty or an error, tell the user the capture was cancelled and stop — do NOT read stale files. The first word may be a timer (`3s`) or a count (`3`) — ignore that leading token; then address the rest of: $ARGUMENTS
