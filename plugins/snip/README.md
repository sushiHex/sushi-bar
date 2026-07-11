# snip

Draw-box screenshot capture for Claude Code on **native Windows**.

`/snip:snip` (from this plugin) opens a rectangular draw-box, captures exactly what you drag, and loads it into the session so Claude can see it. Pass a question to act on it: `/snip:snip why is this layout broken?`.

The bundled `snip.py` is also a standalone CLI:

| Command | Does |
|---|---|
| `python snip.py` | draw box → **image on clipboard** → press **Alt+V** to stage `[Image #N]` |
| `python snip.py --copy-path` | copy the file **path** instead (for `@path`) |
| `python snip.py --print-path` | print only the saved path (used by the `/snip` command) |
| `python snip.py --launch` | start a new `claude` with the image |

Handy shell alias (PowerShell `$PROFILE`):

```powershell
function snip { python "$HOME\.claude\plugins\cache\snip\snip.py" @args }
```

**Requirements:** Windows 10/11 · Python 3.9+ · Pillow (`python -m pip install pillow`).
