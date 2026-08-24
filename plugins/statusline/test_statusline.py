"""Tests for the sushi-bar status line.

Run with:  python -m pytest plugins/statusline/test_statusline.py
"""
from __future__ import annotations

import json
import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).parent))

import statusline as sl  # noqa: E402


@pytest.fixture(autouse=True)
def _no_env_override(monkeypatch):
    monkeypatch.delenv("CLAUDE_CODE_EFFORT_LEVEL", raising=False)


@pytest.fixture
def project(tmp_path, monkeypatch):
    """A project dir with a .claude/, and HOME pointed somewhere empty."""
    home = tmp_path / "home"
    (home / ".claude").mkdir(parents=True)
    monkeypatch.setattr(sl.os.path, "expanduser", lambda p: str(home) if p == "~" else p)
    proj = tmp_path / "proj"
    (proj / ".claude").mkdir(parents=True)

    def write(where: str, **keys):
        target = {
            "user": home / ".claude" / "settings.json",
            "project": proj / ".claude" / "settings.json",
            "local": proj / ".claude" / "settings.local.json",
        }[where]
        target.write_text(json.dumps(keys), encoding="utf-8")

    return proj, write


# ── the guard that keeps the claim honest ────────────────────────────────


def test_a_non_xhigh_effort_rules_ultracode_out(project):
    """Ultracode forces effort to xhigh. Anything else means it is not on -
    including a settings file that still says otherwise, which is exactly what
    an interactive switch away from ultracode leaves behind."""
    proj, write = project
    write("user", ultracode=True)

    assert sl.ultracode_active("high", str(proj)) is False


def test_a_missing_effort_rules_ultracode_out(project):
    """Models without reasoning effort send no level at all."""
    proj, write = project
    write("user", ultracode=True)

    assert sl.ultracode_active("", str(proj)) is False


# ── the env override, which is definitive when present ───────────────────


def test_the_env_override_reports_ultracode(project, monkeypatch):
    proj, _write = project
    monkeypatch.setenv("CLAUDE_CODE_EFFORT_LEVEL", "ultracode")

    assert sl.ultracode_active("xhigh", str(proj)) is True


def test_the_env_override_wins_over_a_settings_file(project, monkeypatch):
    """CLAUDE_CODE_EFFORT_LEVEL overrides effort for the whole session, so a
    settings file saying otherwise is not in force."""
    proj, write = project
    write("user", ultracode=True)
    monkeypatch.setenv("CLAUDE_CODE_EFFORT_LEVEL", "xhigh")

    assert sl.ultracode_active("xhigh", str(proj)) is False


def test_the_env_override_is_case_insensitive(project, monkeypatch):
    proj, _write = project
    monkeypatch.setenv("CLAUDE_CODE_EFFORT_LEVEL", "  UltraCode ")

    assert sl.ultracode_active("xhigh", str(proj)) is True


# ── settings precedence ──────────────────────────────────────────────────


def test_user_settings_enable_it(project):
    proj, write = project
    write("user", ultracode=True)

    assert sl.ultracode_active("xhigh", str(proj)) is True


def test_project_settings_beat_user_settings(project):
    proj, write = project
    write("user", ultracode=True)
    write("project", ultracode=False)

    assert sl.ultracode_active("xhigh", str(proj)) is False


def test_local_settings_beat_project_settings(project):
    proj, write = project
    write("project", ultracode=False)
    write("local", ultracode=True)

    assert sl.ultracode_active("xhigh", str(proj)) is True


def test_a_file_without_the_key_defers_to_the_next(project):
    """Absent is not false. A project settings.json that says nothing about
    ultracode must not veto the user's setting."""
    proj, write = project
    write("user", ultracode=True)
    write("project", model="opus")

    assert sl.ultracode_active("xhigh", str(proj)) is True


def test_no_settings_anywhere_means_no(project):
    proj, _write = project

    assert sl.ultracode_active("xhigh", str(proj)) is False


def test_unreadable_settings_do_not_raise(project):
    """A statusline that throws leaves the user with no bar at all."""
    proj, _write = project
    (proj / ".claude" / "settings.json").write_text("{not json", encoding="utf-8")

    assert sl.ultracode_active("xhigh", str(proj)) is False


def test_a_non_boolean_value_is_ignored(project):
    proj, write = project
    write("user", ultracode="yes")

    assert sl.ultracode_active("xhigh", str(proj)) is False


# ── rendering ────────────────────────────────────────────────────────────


def _render(payload) -> str:
    import io

    buf = io.StringIO()
    old = sys.stdout
    sys.stdout = buf
    try:
        sl.render(payload)
    finally:
        sys.stdout = old
    return buf.getvalue()


def test_ultracode_replaces_xhigh_in_the_line(project, monkeypatch):
    proj, _w = project
    monkeypatch.setenv("CLAUDE_CODE_EFFORT_LEVEL", "ultracode")
    out = _render({
        "model": {"display_name": "Opus 5"},
        "workspace": {"current_dir": str(proj)},
        "effort": {"level": "xhigh"},
    })

    assert "ultracode" in out
    # Asserted on the rendered effort token, not the raw line: pytest's tmp dir
    # is named after the test, so "xhigh" also appears in the path segment.
    assert f"\033[{sl.GREY}mxhigh" not in out


def test_ultracode_is_rendered_in_purple(project, monkeypatch):
    """Matching Claude Code's own effortUltra colour, rgb(175,135,255)."""
    proj, _w = project
    monkeypatch.setenv("CLAUDE_CODE_EFFORT_LEVEL", "ultracode")
    out = _render({
        "model": {"display_name": "Opus 5"},
        "workspace": {"current_dir": str(proj)},
        "effort": {"level": "xhigh"},
    })

    assert f"\033[{sl.ULTRA}multracode" in out


def test_plain_xhigh_is_unchanged(project):
    proj, _w = project
    out = _render({
        "model": {"display_name": "Opus 5"},
        "workspace": {"current_dir": str(proj)},
        "effort": {"level": "xhigh"},
    })

    assert "xhigh" in out
    assert "ultracode" not in out
    assert f"\033[{sl.ULTRA}m" not in out
