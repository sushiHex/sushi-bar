#!/usr/bin/env python
"""Validate the sushi-bar plugin marketplace before it can break installs.

A malformed ``marketplace.json`` / ``plugin.json`` — bad JSON, a missing
required field, a dangling ``source`` path, or a version that drifts between
the marketplace entry and the plugin's own manifest — silently breaks
``/plugin marketplace add`` for anyone who adds this marketplace. This script
catches all of those, plus Python syntax errors, so CI can gate them.

Run from anywhere:  python scripts/validate_manifests.py
Exit 0 if everything is valid; 1 with a list of problems otherwise.
"""
from __future__ import annotations

import json
import py_compile
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def _load_json(path: Path, errors: list[str]) -> dict | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        errors.append(f"missing manifest: {_rel(path)}")
    except json.JSONDecodeError as e:
        errors.append(f"invalid JSON in {_rel(path)}: {e}")
    return None


def _require(cond: object, msg: str, errors: list[str]) -> None:
    if not cond:
        errors.append(msg)


def validate_manifests(errors: list[str]) -> None:
    mkt_path = ROOT / ".claude-plugin" / "marketplace.json"
    mkt = _load_json(mkt_path, errors)
    if mkt is None:
        return

    _require(isinstance(mkt.get("name"), str) and mkt.get("name"),
             "marketplace.json: missing non-empty 'name'", errors)
    plugins = mkt.get("plugins")
    _require(isinstance(plugins, list) and plugins,
             "marketplace.json: 'plugins' must be a non-empty list", errors)

    for i, entry in enumerate(plugins or []):
        tag = f"marketplace.json plugins[{i}]"
        if not isinstance(entry, dict):
            errors.append(f"{tag}: not an object")
            continue
        name = entry.get("name")
        source = entry.get("source")
        _require(isinstance(name, str) and name, f"{tag}: missing 'name'", errors)
        _require(isinstance(source, str) and source, f"{tag}: missing 'source'", errors)
        if not isinstance(source, str) or not source:
            continue

        src_dir = (ROOT / source).resolve()
        if not src_dir.is_dir():
            errors.append(f"{tag}: source path does not exist: {source}")
            continue

        pj = _load_json(src_dir / ".claude-plugin" / "plugin.json", errors)
        if pj is None:
            continue
        _require(isinstance(pj.get("name"), str) and pj.get("name"),
                 f"{source}/.claude-plugin/plugin.json: missing 'name'", errors)
        _require(isinstance(pj.get("version"), str) and pj.get("version"),
                 f"{source}/.claude-plugin/plugin.json: missing 'version'", errors)

        # marketplace entry and the plugin's own manifest must agree
        if name and pj.get("name"):
            _require(name == pj["name"],
                     f"{tag}: name '{name}' != plugin.json name '{pj['name']}'", errors)
        mkt_ver = entry.get("version")
        if mkt_ver and pj.get("version"):
            _require(mkt_ver == pj["version"],
                     f"{tag}: version '{mkt_ver}' != plugin.json version '{pj['version']}'",
                     errors)


def validate_python(errors: list[str]) -> None:
    for py in sorted(ROOT.rglob("*.py")):
        if ".git" in py.parts:
            continue
        try:
            py_compile.compile(str(py), doraise=True)
        except py_compile.PyCompileError as e:
            errors.append(f"python syntax error in {_rel(py)}: {e.msg}")


def main() -> None:
    errors: list[str] = []
    validate_manifests(errors)
    validate_python(errors)
    if errors:
        print("VALIDATION FAILED:")
        for e in errors:
            print(f"  - {e}")
        sys.exit(1)
    print("All manifests valid and Python compiles cleanly.")


if __name__ == "__main__":
    main()
