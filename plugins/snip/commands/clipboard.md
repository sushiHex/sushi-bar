---
allowed-tools: Bash(python:*), Read
description: Load the image already on your clipboard into Claude
argument-hint: [what to do with it]
model: sonnet
effort: low
---
Image path from the clipboard (empty if there was no image):
!`python "${CLAUDE_PLUGIN_ROOT}/snip.py" --mode clipboard --print-path`

If a path is shown above, Read it with the Read tool. If it's empty or an error, tell the user there was no image on the clipboard (e.g. take one with Win+Shift+S first) and stop. Then address: $ARGUMENTS
