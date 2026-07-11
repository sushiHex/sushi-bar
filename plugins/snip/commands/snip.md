---
allowed-tools: Bash(python:*), Read
description: Capture a draw-box screenshot and load it into this conversation
argument-hint: [optional: what to do with the screenshot]
model: sonnet
effort: low
---
Captured screenshot path (empty if the user cancelled or the selection was too small):
!`python "${CLAUDE_PLUGIN_ROOT}/snip.py" --print-path`

If a valid path is shown above, use the Read tool on that exact path to view the PNG. If it is empty or an error, tell the user the capture was cancelled and stop — do NOT read a stale file. Then address the following about the screenshot (may be empty): $ARGUMENTS
