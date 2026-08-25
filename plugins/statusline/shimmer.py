#!/usr/bin/env python
"""Claude Code's shimmer sweep, reproduced.

The animation on "✻ Working…" is a narrow bright band travelling left to right
across dim text, over and over. Not a pulse and not a rainbow — a moving
highlight three characters wide.

Constants are read from the 2.1.241 binary rather than eyeballed:

    50ms per frame          oy(hasShimmer ? 50 : null)
    3-character band        indices t-1, t, t+1 of the grapheme sequence
    lead-in  10 columns     sweepStart = start - 10
    lead-out 10 columns     cycleLength = (end - start) + 20
    rgb(208,180,255)        theme key `autoAcceptShimmer`, the bright band
    rgb(153,153,153)        dim base text, theme key `subtle`

The lead-in and lead-out are what make it read as a sweep rather than a
blink: the band exists off the left edge for ten frames before it touches the
first character, and keeps going ten past the last.

    python shimmer.py                     sweep the default text until Ctrl-C
    python shimmer.py "Thinking…"         sweep your own
    python shimmer.py --frames 8          print 8 frames and exit (no cursor
                                          tricks, so it is diffable and safe
                                          to run where a TTY is not attached)

No third-party deps. Cross-platform.
"""
from __future__ import annotations

import argparse
import os
import sys
import time

# Straight from the theme table. The bright band is a pale lavender rather than
# a saturated purple - at three characters wide a strong colour reads as a
# defect on the line, not as motion.
SHIMMER = (208, 180, 255)
BASE = (153, 153, 153)

FRAME_SECONDS = 0.05
BAND_RADIUS = 1  # t-1 .. t+1, so three characters
LEAD = 10        # columns of run-up before the text, and of run-out after

DEFAULT_TEXT = "✻ Working…"


def rgb(c: tuple[int, int, int], s: str) -> str:
    return f"\033[38;2;{c[0]};{c[1]};{c[2]}m{s}\033[0m"


def graphemes(text: str) -> list[str]:
    """Split into user-perceived characters.

    Claude Code uses Intl.Segmenter. Python has no grapheme segmentation in the
    stdlib, so combining marks are joined onto the character they modify - which
    covers the accented and emoji-modifier cases that would otherwise light up
    half a glyph.
    """
    import unicodedata

    out: list[str] = []
    for ch in text:
        if out and unicodedata.combining(ch):
            out[-1] += ch
        else:
            out.append(ch)
    return out


def frame(text: str, index: int) -> str:
    """One frame: the band centred on `index`, everything else dim.

    `index` is allowed to sit outside the text on either side - that is the
    lead-in and lead-out, and the frame simply comes back fully dim.
    """
    cells = graphemes(text)
    lo, hi = index - BAND_RADIUS, index + BAND_RADIUS
    return "".join(
        rgb(SHIMMER if lo <= i <= hi else BASE, ch)
        for i, ch in enumerate(cells)
    )


def sweep(text: str):
    """Endless generator of (index, frame), matching the real cycle."""
    width = len(graphemes(text))
    start = -LEAD
    length = width + 2 * LEAD
    i = 0
    while True:
        index = start + (i % length)
        yield index, frame(text, index)
        i += 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("text", nargs="?", default=DEFAULT_TEXT)
    ap.add_argument("--frames", type=int, default=0,
                    help="print N frames and exit instead of animating")
    args = ap.parse_args()

    gen = sweep(args.text)

    if args.frames:
        for _ in range(args.frames):
            index, line = next(gen)
            print(f"{index:>4}  {line}")
        return 0

    if not sys.stdout.isatty():
        print("not a terminal - use --frames to see the output", file=sys.stderr)
        return 1

    sys.stdout.write("\033[?25l")  # hide the cursor; it would ride the band
    try:
        for _index, line in gen:
            sys.stdout.write("\r" + line)
            sys.stdout.flush()
            time.sleep(FRAME_SECONDS)
    except KeyboardInterrupt:
        pass
    finally:
        sys.stdout.write("\033[?25h\r\033[K")
        sys.stdout.flush()
    return 0


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    raise SystemExit(main())
