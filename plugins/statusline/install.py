#!/usr/bin/env python
"""Install/uninstall the sushi-bar status line into ~/.claude/settings.json.

A Claude Code plugin cannot contribute a main status line directly (only the
`agent` and `subagentStatusLine` keys are accepted from plugin settings), so this
helper wires the bundled ``statusline.py`` into the user's own settings.json.

Install:   python install.py --plugin-root "<CLAUDE_PLUGIN_ROOT>" [--ascii]
Uninstall: python install.py --uninstall

Install backs up any pre-existing `statusLine` block (once) to a sidecar file so
uninstall can restore it. Re-running install after a plugin update just refreshes
the path; it never clobbers the original backup.
"""
from __future__ import annotations

import argparse
import json
import os
import sys

SETTINGS = os.path.join(os.path.expanduser("~"), ".claude", "settings.json")
BACKUP = os.path.join(os.path.expanduser("~"), ".claude", ".statusline-sushi-backup.json")


def _fwd(path: str) -> str:
    return path.replace("\\", "/")


def _load(path: str) -> dict:
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
            return data if isinstance(data, dict) else {}
    except FileNotFoundError:
        return {}
    except json.JSONDecodeError as e:
        print(f"ERROR: {path} is not valid JSON ({e}); refusing to touch it.")
        sys.exit(1)


def _save(path: str, data: dict) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2)
        fh.write("\n")


def install(plugin_root: str, ascii_mode: bool) -> None:
    script = _fwd(os.path.join(plugin_root, "statusline.py"))
    if not os.path.isfile(script):
        print(f"ERROR: bundled statusline.py not found at {script}")
        sys.exit(1)

    py = _fwd(sys.executable or "python")
    prefix = "SUSHI_STATUSLINE_ASCII=1 " if ascii_mode else ""
    command = f'{prefix}"{py}" "{script}"'

    settings = _load(SETTINGS)

    # Back up an existing, non-sushi status line exactly once.
    existing = settings.get("statusLine")
    if existing and not os.path.exists(BACKUP):
        cmd = existing.get("command", "") if isinstance(existing, dict) else ""
        if "statusline.py" not in cmd:  # don't back up a prior sushi install
            _save(BACKUP, existing)
            print(f"Backed up your previous status line to {_fwd(BACKUP)}")

    settings["statusLine"] = {"type": "command", "command": command}
    _save(SETTINGS, settings)
    print("Installed sushi-bar status line.")
    print(f"  settings.json statusLine.command = {command}")


def uninstall() -> None:
    settings = _load(SETTINGS)
    if os.path.exists(BACKUP):
        with open(BACKUP, "r", encoding="utf-8") as fh:
            settings["statusLine"] = json.load(fh)
        _save(SETTINGS, settings)
        os.remove(BACKUP)
        print("Restored your previous status line from backup.")
    else:
        if settings.pop("statusLine", None) is not None:
            _save(SETTINGS, settings)
            print("Removed the sushi-bar status line (no prior status line to restore).")
        else:
            print("No status line was set; nothing to do.")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--plugin-root")
    ap.add_argument("--ascii", action="store_true")
    ap.add_argument("--uninstall", action="store_true")
    args = ap.parse_args()

    if args.uninstall:
        uninstall()
        return
    if not args.plugin_root:
        print("ERROR: --plugin-root is required for install.")
        sys.exit(1)
    install(args.plugin_root, args.ascii)


if __name__ == "__main__":
    main()
