#!/usr/bin/env python
"""snip.py - draw-box crop a screenshot and stage it for Claude Code (Windows).

ALWAYS opens a draw-a-box region selector (full virtual desktop, multi-monitor,
DPI-correct), captures exactly the rectangle you drag, saves it to a PNG, and by
default copies the IMAGE to the clipboard so you can press Alt+V in Claude Code
to stage it as [Image #N] (repeat to attach several images, then type text and
send them together). Optionally copies the path instead, or launches `claude`.

The selection is drawn by this script (stdlib tkinter overlay), so it does NOT
depend on the OS Snipping-Tool's last-used mode - it is always a rectangular
draw-box.

Requires Pillow:  python -m pip install pillow

Examples:
  python snip.py                  # draw box -> image on clipboard -> Alt+V stages [Image #N]
  python snip.py --copy-path      # draw box -> copy the file PATH instead (for @path)
  python snip.py --launch         # draw box -> start a NEW `claude` with the image
  python snip.py --out C:/x.png   # custom output path
"""
from __future__ import annotations

import argparse
import ctypes
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

MIN_DRAG_PX = 3             # ignore accidental clicks / near-zero drags
SELECT_TIMEOUT_MS = 60_000  # auto-cancel the overlay if left idle this long (avoid a hang)


def _set_dpi_aware() -> None:
    """Per-monitor DPI awareness so selector coords match physical screen pixels."""
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)  # PER_MONITOR_AWARE_V2
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass


def _virtual_screen() -> tuple[int, int, int, int]:
    """(x, y, w, h) of the whole virtual desktop across all monitors."""
    u = ctypes.windll.user32
    return (u.GetSystemMetrics(76), u.GetSystemMetrics(77),   # SM_X/Y_VIRTUALSCREEN
            u.GetSystemMetrics(78), u.GetSystemMetrics(79))   # SM_CX/CY_VIRTUALSCREEN


def select_region() -> tuple[int, int, int, int] | None:
    """Draw-box overlay; return absolute (x1, y1, x2, y2) or None if cancelled."""
    import tkinter as tk

    _set_dpi_aware()
    vx, vy, vw, vh = _virtual_screen()

    root = tk.Tk()
    root.overrideredirect(True)
    # "+{vx}+{vy}" is intentional: a negative origin renders as "+-1920", which Tk
    # reads as -1920 from the LEFT. Do NOT "simplify" to f"{vx:+d}" - "-1920" means
    # "from the right" in Tk geometry and would mis-place the overlay on a left/top monitor.
    root.geometry(f"{vw}x{vh}+{vx}+{vy}")
    root.attributes("-topmost", True)
    root.attributes("-alpha", 0.3)
    root.configure(bg="black", cursor="crosshair")

    canvas = tk.Canvas(root, bg="black", highlightthickness=0)
    canvas.pack(fill="both", expand=True)
    canvas.create_text(vw // 2, 24, fill="white",
                       text="Drag to select  ·  Esc to cancel", font=("Segoe UI", 12))

    st: dict = {"x0": 0, "y0": 0, "rect": None, "bbox": None}

    def press(e):
        st["x0"], st["y0"] = e.x, e.y
        st["rect"] = canvas.create_rectangle(e.x, e.y, e.x, e.y, outline="red", width=2)

    def drag(e):
        if st["rect"] is not None:
            canvas.coords(st["rect"], st["x0"], st["y0"], e.x, e.y)

    def release(e):
        x1, x2 = sorted((st["x0"], e.x))
        y1, y2 = sorted((st["y0"], e.y))
        st["bbox"] = (x1 + vx, y1 + vy, x2 + vx, y2 + vy)  # -> absolute screen coords
        root.withdraw()          # hide the overlay BEFORE the grab so it isn't captured
        root.update_idletasks()  # flush the un-map now, not "eventually"
        root.destroy()

    canvas.bind("<ButtonPress-1>", press)
    canvas.bind("<B1-Motion>", drag)
    canvas.bind("<ButtonRelease-1>", release)
    root.bind("<Escape>", lambda e: root.destroy())
    root.after(SELECT_TIMEOUT_MS, root.destroy)  # never hang if the user walks away
    root.focus_force()
    root.mainloop()
    return st["bbox"]


def set_clipboard_text(text: str) -> bool:
    """Put text on the clipboard via PowerShell Set-Clipboard; return success.

    Uses Set-Clipboard (not clip.exe) so Unicode paths survive - clip.exe reads
    stdin in the OEM code page and garbles non-ASCII. The value is passed out of
    band via an env var, and the bool lets callers avoid a false 'copied' message.
    """
    try:
        r = subprocess.run(
            ["powershell.exe", "-NoProfile", "-Command", "Set-Clipboard -Value $env:SNIP_TXT"],
            capture_output=True, text=True,
            env={**os.environ, "SNIP_TXT": text},
        )
        return r.returncode == 0
    except OSError:
        return False


def set_clipboard_image(path: Path) -> bool:
    """Put an image on the clipboard so Claude Code's Alt+V can stage it as [Image #N].

    Uses Windows PowerShell (powershell.exe) in -STA mode: the WinForms clipboard
    requires STA, and pwsh 7 runs MTA by default. The path is passed out of band
    via an env var so it never has to be quoted into the command string (a path
    like C:\\Users\\O'Brien\\... would otherwise break the literal).
    """
    ps = (
        "Add-Type -AssemblyName System.Windows.Forms;"
        "Add-Type -AssemblyName System.Drawing;"
        "$i=[System.Drawing.Image]::FromFile($env:SNIP_IMG);"
        "[System.Windows.Forms.Clipboard]::SetImage($i);$i.Dispose()"
    )
    try:
        r = subprocess.run(
            ["powershell.exe", "-STA", "-NoProfile", "-Command", ps],
            capture_output=True, text=True,
            env={**os.environ, "SNIP_IMG": str(path)},
        )
        return r.returncode == 0
    except Exception:
        return False


def main() -> int:
    ap = argparse.ArgumentParser(description="Draw-box screenshot for Claude Code.")
    ap.add_argument("--out",
                    default=str(Path(tempfile.gettempdir()) / "claude_capture.png"),
                    help="where to save the PNG")
    ap.add_argument("--launch", action="store_true",
                    help="start a NEW `claude` session with the image instead of copying it")
    ap.add_argument("--copy-path", action="store_true",
                    help="copy the file PATH instead of the image (for @path or plain paste)")
    ap.add_argument("--print-path", action="store_true",
                    help="print only the saved path to stdout (for the /snip command); no clipboard, no chatter")
    args = ap.parse_args()

    try:
        from PIL import ImageGrab
    except ImportError:
        print("Pillow is required:  python -m pip install pillow", file=sys.stderr)
        return 1

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.unlink(missing_ok=True)  # clear any stale capture so a cancel leaves no file

    abort = 0 if args.print_path else 1  # clean exit so the /snip !-command doesn't error
    box = select_region()
    if box is None:
        print("X Cancelled.", file=sys.stderr)
        return abort
    x1, y1, x2, y2 = box
    if x2 - x1 < MIN_DRAG_PX or y2 - y1 < MIN_DRAG_PX:
        print("X Selection too small.", file=sys.stderr)
        return abort

    time.sleep(0.1)  # compositor-settle margin; overlay is already hidden in release()
    try:
        ImageGrab.grab(bbox=(x1, y1, x2, y2), all_screens=True).save(out, "PNG")
    except Exception as exc:
        print(f"X Capture failed: {exc}", file=sys.stderr)
        return abort

    s = str(out)
    saved = f"-> Saved {out}."
    if args.print_path:
        print(s)                       # stdout: path only (for the /snip command)
    elif args.launch:
        try:
            subprocess.run(["claude", s])  # NEW session, image path as prompt
        except OSError as exc:
            print(f"{saved} (Couldn't launch 'claude': {exc}. Image is at {out}.)", file=sys.stderr)
    elif args.copy_path:
        if set_clipboard_text(s):
            print(f"{saved} Path copied - paste it (or @{out}) into your prompt.", flush=True)
        else:
            print(f"{saved} (Couldn't copy to clipboard; the file is at {out}.)", file=sys.stderr)
    else:                              # default: image on the clipboard for Alt+V
        if set_clipboard_image(out):
            print(f"{saved} Image copied - press Alt+V in Claude Code to stage it as "
                  "[Image #N]. Snip again + Alt+V for more, then type your text and send.", flush=True)
        elif set_clipboard_text(s):
            print(f"{saved} (Couldn't copy the image; copied the path instead - use @{out}.)", flush=True)
        else:
            print(f"{saved} (Couldn't copy to clipboard; the file is at {out}.)", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
