"""Tests for the shimmer sweep."""
from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))

import shimmer as sh  # noqa: E402

TEXT = "Working"


def lit(index: int, text: str = TEXT) -> str:
    """Which characters the band is on in that frame."""
    line = sh.frame(text, index)
    hot = f"38;2;{sh.SHIMMER[0]};{sh.SHIMMER[1]};{sh.SHIMMER[2]}m"
    return "".join(
        part[len(hot)] for part in line.split("\033[")[1:] if part.startswith(hot)
    )


def test_the_band_is_three_characters_wide():
    assert lit(3) == "rki"


def test_the_band_moves_one_character_per_frame():
    assert lit(3) == "rki"
    assert lit(4) == "kin"


def test_the_band_is_clipped_at_the_left_edge():
    """Entering, only part of it is over the text."""
    assert lit(0) == "Wo"


def test_the_band_is_clipped_at_the_right_edge():
    assert lit(len(TEXT) - 1) == "ng"


def test_the_lead_in_leaves_the_text_entirely_dim():
    """Ten frames of run-up before the first character lights. This is what
    makes it read as a sweep arriving rather than a blink."""
    assert lit(-sh.LEAD) == ""
    assert lit(-2) == ""


def test_the_cycle_covers_the_lead_in_and_the_lead_out():
    gen = sh.sweep(TEXT)
    first = next(gen)[0]
    seen = [first] + [next(gen)[0] for _ in range(len(TEXT) + 2 * sh.LEAD - 1)]

    assert first == -sh.LEAD
    assert max(seen) == len(TEXT) + sh.LEAD - 1
    assert next(gen)[0] == -sh.LEAD, "it must wrap back to the run-up"


def test_combining_marks_ride_with_their_base_character():
    """Lighting half a glyph looks like a rendering fault, not motion."""
    assert sh.graphemes("café") == ["c", "a", "f", "é"]
