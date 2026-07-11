#!/usr/bin/env python
"""snip.py - screenshot capture for Claude Code (native Windows).

Modes (--mode):
  box        draw a rectangle and capture it (default)
  screen     capture the monitor under the cursor (--all = every monitor)
  window     click a window to capture just that window
  clipboard  load an image already on the clipboard (no capture)

--delay N waits N seconds before capturing (box/screen/window) - handy for
opening a menu/tooltip first. By default the captured PNG is copied to the
clipboard so you can press Alt+V to stage it as [Image #N]; --copy-path copies
the path instead, --print-path prints only the path (for the /snip commands),
--launch starts a new `claude` with it.

Requires Pillow:  python -m pip install pillow

Examples:
  python snip.py                          # draw box -> image on clipboard -> Alt+V
  python snip.py --mode screen --delay 3  # 3s, then grab the screen under the cursor
  python snip.py --mode window --print-path
"""
from __future__ import annotations

import argparse
import ctypes
import os
import re
import subprocess
import sys
import tempfile
import time
from ctypes import c_void_p, wintypes
from pathlib import Path

MIN_DRAG_PX = 3             # ignore accidental clicks / near-zero drags/windows
SELECT_TIMEOUT_MS = 60_000  # auto-cancel an overlay if left idle this long


def _set_dpi_aware() -> None:
    """Per-monitor DPI awareness so coords match physical screen pixels."""
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


def _overlay(alpha: float, hint: str):
    """A full-virtual-desktop transparent tk overlay. Returns (root, canvas, vx, vy)."""
    import tkinter as tk

    _set_dpi_aware()
    vx, vy, vw, vh = _virtual_screen()
    root = tk.Tk()
    root.overrideredirect(True)
    # "+{vx}+{vy}" is intentional: a negative origin renders as "+-1920", which Tk
    # reads as -1920 from the LEFT. Do NOT switch to f"{vx:+d}" - "-1920" means
    # "from the right" and would mis-place the overlay on a left/top monitor.
    root.geometry(f"{vw}x{vh}+{vx}+{vy}")
    root.attributes("-topmost", True)
    root.attributes("-alpha", alpha)
    root.configure(bg="black", cursor="crosshair")
    canvas = tk.Canvas(root, bg="black", highlightthickness=0)
    canvas.pack(fill="both", expand=True)
    canvas.create_text(vw // 2, 24, fill="white", text=hint, font=("Segoe UI", 12))
    return root, canvas, vx, vy


def select_region() -> tuple[int, int, int, int] | None:
    """Draw-box overlay; return absolute (x1, y1, x2, y2) or None if cancelled."""
    root, canvas, vx, vy = _overlay(0.3, "Drag to select  ·  Esc to cancel")
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


def click_point() -> tuple[int, int] | None:
    """Single-click overlay (for window mode); return absolute (x, y) or None."""
    root, _canvas, vx, vy = _overlay(0.25, "Click a window to capture it  ·  Esc to cancel")
    st: dict = {"pt": None}

    def click(e):
        st["pt"] = (e.x + vx, e.y + vy)
        root.withdraw()
        root.update_idletasks()
        root.destroy()

    root.bind("<Button-1>", click)
    root.bind("<Escape>", lambda e: root.destroy())
    root.after(SELECT_TIMEOUT_MS, root.destroy)
    root.focus_force()
    root.mainloop()
    return st["pt"]


def monitor_rect_under_cursor() -> tuple[int, int, int, int]:
    """Absolute rect of the monitor the cursor is on."""
    u = ctypes.windll.user32
    u.MonitorFromPoint.restype = c_void_p
    u.MonitorFromPoint.argtypes = [wintypes.POINT, wintypes.DWORD]
    u.GetCursorPos.argtypes = [ctypes.POINTER(wintypes.POINT)]

    class MONITORINFO(ctypes.Structure):
        _fields_ = [("cbSize", wintypes.DWORD), ("rcMonitor", wintypes.RECT),
                    ("rcWork", wintypes.RECT), ("dwFlags", wintypes.DWORD)]

    u.GetMonitorInfoW.argtypes = [c_void_p, ctypes.POINTER(MONITORINFO)]
    pt = wintypes.POINT()
    u.GetCursorPos(ctypes.byref(pt))
    hmon = u.MonitorFromPoint(pt, 2)  # MONITOR_DEFAULTTONEAREST
    mi = MONITORINFO()
    mi.cbSize = ctypes.sizeof(MONITORINFO)
    u.GetMonitorInfoW(hmon, ctypes.byref(mi))
    r = mi.rcMonitor
    return (r.left, r.top, r.right, r.bottom)


def window_rect_at(x: int, y: int) -> tuple[int, int, int, int] | None:
    """Absolute rect of the top-level window under (x, y), via DWM visible bounds."""
    u = ctypes.windll.user32
    u.WindowFromPoint.restype = c_void_p
    u.WindowFromPoint.argtypes = [wintypes.POINT]
    u.GetAncestor.restype = c_void_p
    u.GetAncestor.argtypes = [c_void_p, wintypes.UINT]
    u.GetWindowRect.argtypes = [c_void_p, ctypes.POINTER(wintypes.RECT)]

    hwnd = u.WindowFromPoint(wintypes.POINT(x, y))
    if not hwnd:
        return None
    root_hwnd = u.GetAncestor(hwnd, 2)  # GA_ROOT
    rect = wintypes.RECT()
    res = 1
    try:  # DWMWA_EXTENDED_FRAME_BOUNDS (9) = true visible bounds (no invisible border)
        dwm = ctypes.windll.dwmapi
        dwm.DwmGetWindowAttribute.argtypes = [c_void_p, wintypes.DWORD,
                                              ctypes.POINTER(wintypes.RECT), wintypes.DWORD]
        res = dwm.DwmGetWindowAttribute(root_hwnd, 9, ctypes.byref(rect), ctypes.sizeof(rect))
    except Exception:
        res = 1
    if res != 0:  # DWM unavailable -> fall back to the raw window rect
        u.GetWindowRect(root_hwnd, ctypes.byref(rect))
    return (rect.left, rect.top, rect.right, rect.bottom)


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


def _countdown(seconds: int) -> None:
    for s in range(seconds, 0, -1):
        print(f"-> capturing in {s}...", file=sys.stderr, flush=True)
        time.sleep(1)


def capture(mode: str, delay: int, all_screens: bool):
    """Return a PIL Image for the chosen mode, or None if cancelled/empty."""
    from PIL import Image, ImageGrab

    if mode == "clipboard":  # nothing to wait for; delay is ignored
        data = ImageGrab.grabclipboard()
        if isinstance(data, Image.Image):
            return data
        if isinstance(data, list):
            for p in data:
                if Path(p).is_file():
                    return Image.open(p)
        return None

    if delay > 0:
        _countdown(delay)

    if mode == "screen":
        if all_screens:
            return ImageGrab.grab(all_screens=True)
        return ImageGrab.grab(bbox=monitor_rect_under_cursor(), all_screens=True)

    if mode == "window":
        pt = click_point()
        if pt is None:
            return None
        time.sleep(0.08)  # let the overlay clear before querying the window under it
        rect = window_rect_at(*pt)
        if not rect or rect[2] - rect[0] < MIN_DRAG_PX or rect[3] - rect[1] < MIN_DRAG_PX:
            return None
        time.sleep(0.1)
        return ImageGrab.grab(bbox=rect, all_screens=True)

    # default: box
    box = select_region()
    if box is None:
        return None
    x1, y1, x2, y2 = box
    if x2 - x1 < MIN_DRAG_PX or y2 - y1 < MIN_DRAG_PX:
        return None
    time.sleep(0.1)  # compositor-settle margin; overlay already hidden in release()
    return ImageGrab.grab(bbox=(x1, y1, x2, y2), all_screens=True)


def _parse_spec(raw: str) -> tuple[int, int]:
    """Parse the first /snip arg into (delay_seconds, count).

    '3s' -> wait 3 seconds, one shot.   '3' -> three shots in a row, no wait.
    Anything else (e.g. the start of a question) -> (0, 1). Count is capped at 10.
    """
    raw = (raw or "").strip().lower()
    m = re.fullmatch(r"(\d+)s", raw)
    if m:
        return int(m.group(1)), 1
    if raw.isdigit():
        return 0, max(1, min(10, int(raw)))
    return 0, 1


def main() -> int:
    ap = argparse.ArgumentParser(description="Screenshot capture for Claude Code.")
    ap.add_argument("--mode", choices=["box", "screen", "window", "clipboard"], default="box",
                    help="what to capture (default: box)")
    ap.add_argument("--delay", type=int, default=0,
                    help="seconds to wait before each capture (box/screen/window)")
    ap.add_argument("--count", type=int, default=1, help="number of captures in a row (max 10)")
    ap.add_argument("--spec", default="",
                    help="first /snip arg: 'Ns' = wait N seconds, 'N' = N shots (overrides --delay/--count)")
    ap.add_argument("--all", action="store_true", help="with --mode screen: every monitor")
    ap.add_argument("--out", default=str(Path(tempfile.gettempdir()) / "claude_capture.png"),
                    help="where to save the PNG")
    ap.add_argument("--launch", action="store_true",
                    help="start a NEW `claude` session with the image instead of copying it")
    ap.add_argument("--copy-path", action="store_true",
                    help="copy the file PATH instead of the image (for @path or plain paste)")
    ap.add_argument("--print-path", action="store_true",
                    help="print only the saved path to stdout (for the /snip commands)")
    args = ap.parse_args()

    try:
        import PIL  # noqa: F401
    except ImportError:
        print("Pillow is required:  python -m pip install pillow", file=sys.stderr)
        return 1

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.unlink(missing_ok=True)  # clear any stale capture so a cancel leaves no file

    delay, count = args.delay, args.count
    if args.spec:
        delay, count = _parse_spec(args.spec)
    abort = 0 if args.print_path else 1  # clean exit so the /snip !-command doesn't error

    paths: list[Path] = []
    for i in range(count):
        try:
            img = capture(args.mode, delay, args.all)
        except Exception as exc:
            print(f"X Capture failed: {exc}", file=sys.stderr)
            break
        if img is None:  # cancelled -> stop the series, keep what we already have
            break
        p = out if count == 1 else out.with_stem(f"{out.stem}_{i + 1}")
        p.unlink(missing_ok=True)
        try:
            img.save(p, "PNG")
        except Exception as exc:
            print(f"X Save failed: {exc}", file=sys.stderr)
            break
        paths.append(p)

    if not paths:
        print("X Cancelled or nothing captured.", file=sys.stderr)
        return abort

    last = paths[-1]
    n = len(paths)
    saved = f"-> Saved {n} images." if n > 1 else f"-> Saved {last}."
    if args.print_path:
        for p in paths:
            print(str(p))              # stdout: one path per line (for the /snip commands)
    elif args.launch:
        try:
            subprocess.run(["claude", str(last)])
        except OSError as exc:
            print(f"{saved} (Couldn't launch 'claude': {exc}. Image is at {last}.)", file=sys.stderr)
    elif args.copy_path:
        if set_clipboard_text("\n".join(str(p) for p in paths)):
            print(f"{saved} Path(s) copied to the clipboard.", flush=True)
        else:
            print(f"{saved} (Couldn't copy to clipboard; files are in {last.parent}.)", file=sys.stderr)
    else:                              # default: image on the clipboard for Alt+V
        extra = " (last of the set; clipboard holds one)" if n > 1 else ""
        if set_clipboard_image(last):
            print(f"{saved} Image copied{extra} - press Alt+V in Claude Code to stage it as "
                  "[Image #N]. Snip again + Alt+V for more, then type your text and send.", flush=True)
        elif set_clipboard_text(str(last)):
            print(f"{saved} (Couldn't copy the image; copied the path instead - use @{last}.)", flush=True)
        else:
            print(f"{saved} (Couldn't copy to clipboard; files are in {last.parent}.)", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
