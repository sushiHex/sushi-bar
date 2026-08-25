"""Reading the live effort level out of the session transcript.

Claude Code sends no ultracode field to a status line and an interactive
`/effort` toggle is never written to settings. But the command's own output is
persisted to the transcript as a plain user record:

    {"type":"user","message":{"role":"user",
     "content":"<local-command-stdout>Set effort level to ultracode ..."}}

The last such record is what the session is running. That covers `/effort`,
which is the way ultracode is actually turned on.

The trap: a tool result quoting that text would be a false positive. Real
records carry `content` as a STRING; tool results carry a LIST of blocks. The
reader requires the string form.
"""
from __future__ import annotations

import json
import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).parent))

import statusline as sl  # noqa: E402


def _cmd(level: str) -> str:
    return json.dumps({
        "type": "user",
        "message": {
            "role": "user",
            "content": f"<local-command-stdout>Set effort level to {level} "
                       f"(this session only): blah</local-command-stdout>",
        },
    })


def _tool_result_quoting(level: str) -> str:
    """What one of my own greps looks like — same text, list content."""
    return json.dumps({
        "type": "user",
        "message": {
            "role": "user",
            "content": [{
                "type": "tool_result",
                "tool_use_id": "toolu_x",
                "content": f"<local-command-stdout>Set effort level to {level}",
            }],
        },
    })


def _chat(text: str) -> str:
    return json.dumps({"type": "assistant",
                       "message": {"role": "assistant", "content": text}})


@pytest.fixture
def transcript(tmp_path):
    path = tmp_path / "session.jsonl"
    path.write_text("", encoding="utf-8")

    def append(*lines: str):
        with path.open("a", encoding="utf-8") as fh:
            for line in lines:
                fh.write(line + "\n")

    return path, append


@pytest.fixture(autouse=True)
def _fresh_cache(tmp_path, monkeypatch):
    monkeypatch.setattr(sl, "_EFFORT_CACHE", tmp_path / "effort-cache.json")


def test_no_effort_command_reads_as_unknown(transcript):
    path, append = transcript
    append(_chat("hello"))

    assert sl.transcript_effort(str(path)) == ""


def test_the_last_effort_command_wins(transcript):
    path, append = transcript
    append(_cmd("ultracode"), _chat("..."), _cmd("xhigh"))

    assert sl.transcript_effort(str(path)) == "xhigh"


def test_ultracode_is_read_when_it_is_last(transcript):
    path, append = transcript
    append(_cmd("xhigh"), _cmd("max"), _cmd("ultracode"))

    assert sl.transcript_effort(str(path)) == "ultracode"


def test_a_tool_result_quoting_the_text_is_ignored(transcript):
    """The trap. Grepping for this string puts it in the transcript; without
    the string/list distinction the bar would read its own output."""
    path, append = transcript
    append(_cmd("xhigh"), _tool_result_quoting("ultracode"))

    assert sl.transcript_effort(str(path)) == "xhigh"


def test_assistant_prose_quoting_the_text_is_ignored(transcript):
    path, append = transcript
    append(_cmd("xhigh"),
           _chat("<local-command-stdout>Set effort level to ultracode"))

    assert sl.transcript_effort(str(path)) == "xhigh"


def test_a_missing_transcript_reads_as_unknown(tmp_path):
    assert sl.transcript_effort(str(tmp_path / "gone.jsonl")) == ""


def test_a_malformed_line_does_not_break_the_read(transcript):
    path, append = transcript
    append(_cmd("ultracode"), "{not json at all")

    assert sl.transcript_effort(str(path)) == "ultracode"


# ── the incremental read ─────────────────────────────────────────────────


def test_only_new_bytes_are_scanned_on_a_second_call(transcript, monkeypatch):
    """A transcript reaches tens of megabytes and this runs on every render."""
    path, append = transcript
    append(_cmd("ultracode"))
    assert sl.transcript_effort(str(path)) == "ultracode"

    read_sizes = []
    real_read = sl.io.open if hasattr(sl, "io") else open

    append(_chat("more talk"))
    before = path.stat().st_size
    sl.transcript_effort(str(path))
    # The cache must have advanced to the end of the file.
    cached = json.loads(sl._EFFORT_CACHE.read_text(encoding="utf-8"))
    assert cached["offset"] == before


def test_a_later_change_is_picked_up_incrementally(transcript):
    path, append = transcript
    append(_cmd("xhigh"))
    assert sl.transcript_effort(str(path)) == "xhigh"

    append(_cmd("ultracode"))
    assert sl.transcript_effort(str(path)) == "ultracode"


def test_the_remembered_value_survives_when_nothing_new_arrives(transcript):
    path, append = transcript
    append(_cmd("ultracode"))
    assert sl.transcript_effort(str(path)) == "ultracode"

    assert sl.transcript_effort(str(path)) == "ultracode"


def test_a_shrunken_transcript_is_rescanned_from_the_start(transcript):
    """A different session, or a rewritten file. Reading from a stale offset
    would return whatever bytes happened to be there."""
    path, append = transcript
    append(_cmd("ultracode"), _chat("x" * 400))
    assert sl.transcript_effort(str(path)) == "ultracode"

    path.write_text(_cmd("high") + "\n", encoding="utf-8")

    assert sl.transcript_effort(str(path)) == "high"


def test_switching_transcripts_does_not_reuse_the_other_cache(transcript, tmp_path):
    path, append = transcript
    append(_cmd("ultracode"))
    assert sl.transcript_effort(str(path)) == "ultracode"

    other = tmp_path / "other.jsonl"
    other.write_text(_cmd("medium") + "\n", encoding="utf-8")

    assert sl.transcript_effort(str(other)) == "medium"


# ── how it feeds the label ───────────────────────────────────────────────


def test_the_transcript_beats_settings(tmp_path, monkeypatch):
    """`/effort ultracode` writes nothing to settings, so a settings file can
    only ever be staler than the transcript."""
    home = tmp_path / "home"
    (home / ".claude").mkdir(parents=True)
    (home / ".claude" / "settings.json").write_text('{"ultracode": false}',
                                                    encoding="utf-8")
    monkeypatch.setattr(sl.os.path, "expanduser",
                        lambda p: str(home) if p == "~" else p)
    monkeypatch.delenv("CLAUDE_CODE_EFFORT_LEVEL", raising=False)
    t = tmp_path / "s.jsonl"
    t.write_text(_cmd("ultracode") + "\n", encoding="utf-8")

    assert sl.ultracode_active("xhigh", str(tmp_path), str(t)) is True


def test_a_transcript_saying_xhigh_clears_the_label(tmp_path, monkeypatch):
    home = tmp_path / "home"
    (home / ".claude").mkdir(parents=True)
    (home / ".claude" / "settings.json").write_text('{"ultracode": true}',
                                                    encoding="utf-8")
    monkeypatch.setattr(sl.os.path, "expanduser",
                        lambda p: str(home) if p == "~" else p)
    monkeypatch.delenv("CLAUDE_CODE_EFFORT_LEVEL", raising=False)
    t = tmp_path / "s.jsonl"
    t.write_text(_cmd("xhigh") + "\n", encoding="utf-8")

    assert sl.ultracode_active("xhigh", str(tmp_path), str(t)) is False
