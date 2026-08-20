# Tuning log — VONNEGUT

Every version of `output-styles/vonnegut.md`, what changed, what it measured,
and whether it survived. Kept because two of the edits in here looked obviously
right and made the writing measurably worse.

## Method

Each version answers a fixed set of technical questions. Half the answers come
from the version under test, half from a no-style control. Samples are stripped
of labels, ordered by a hash of their own text, and read by judges who are not
told that any style exists. The key stays sealed until the scores are in.

Three axes, each scored 1–10 by a separate blind judge:

| axis | what it measures |
|---|---|
| **voice** | Vonnegut technique — chapter structure, the homely analogy, cadence, humane voice |
| **useful** | actionable + complete + directness of bad news, summed (max 30) |
| **harms** | places where a stylistic choice damaged the information, counted |

Judges verify empirical claims by running them — building scratch pnpm
workspaces, reading git's own docs, executing the Python.

## Version history

| ver | change | voice | useful | harms | verdict |
|---|---|---|---|---|---|
| v1 | initial: three books, three techniques | **9.00** | 25.50 | 7 | superseded |
| v2 | + "say how you know"; analogy anti-tic | 8.33 | 26.67 | 8 | shipped as 1.2.1 |
| v3 | + ban epistemic labels and meta-headings | 8.33 | 22.33 | 14 | **reverted** |
| v4 | + close analogies on a consequence | **9.00** | 26.00 | **6** | superseded |
| v5 | + show the analogy's edge, never announce it | 8.50 | 23.17 | 11 | **champion** |

Control, for scale: voice 3.0–3.8, useful 23.2–23.8, harms 11–15.

Scores are only comparable **within** a batch. Different batches use different
questions, and the whole field moves with them — every variant scored lower on
the batch-2 question set, champion included. That is why champion and
challengers are always judged in one packet.

## The arena

After v3, round-over-round comparison was abandoned: it was measuring judge
severity as much as style. Versions v4 onward come from a champion-versus-
challenger tournament. Each challenger is one patch with one hypothesis, all of
them generated and judged in the same sealed packet as the reigning champion. A
challenger takes the title only by tying or beating on voice **and** not losing
usefulness. A regression cannot ship, because it never becomes champion.

Ten challengers were run across three batches.

| # | hypothesis | result |
|---|---|---|
| V1 | close the analogy on a consequence, not a human/machine contrast | **WIN** → v4 |
| V2 | source the object from the question's own domain | mixed |
| V3 | fewer, rarer analogies — only when the plain sentence failed | loss (−2.83 useful) |
| V4 | V2 retested on v4 | loss (−1.50 useful) — dead, two strikes |
| V5 | show the analogy's edge, never announce it | **WIN** → v5 |
| V6 | every recommended command comes with how it fails quietly | mixed, twice |
| V7 | V6 retested on v5 | mixed (+0.50 voice / −0.67 useful) |
| V8 | make one object pay twice | mixed (+1.17 voice / −0.83 useful) |
| V9 | stop the consequence-close from templating | mixed (+1.00 / −1.33) |
| V10 | name the first-reach objects, require moving past them | mixed (+0.50 / −1.67) |

Batch 3 was unanimous in shape: **every** challenger bought voice and paid
usefulness. V8 is the strongest unresolved case — it wrote the judge's first and
second best samples of thirty while the champion wrote two of the three weakest,
and its −0.83 usefulness sits inside the ~1-point noise floor while its +1.17
voice sits above it. It did not meet the pre-registered bar, so it did not ship.
Changing the bar after seeing the numbers would have made the whole exercise
decorative.

## What each version bought

**v1 → v2.** v1 read marginally better and diagnosed worse. Both its styled
samples deduced a working directory the log cannot establish, and one printed a
real error block under a caption it had invented. v2 added one rule that
outranks the rest — say how you know, and name what the evidence cannot settle.
The false-inference rate went from 0-of-2 correct to 2-of-2. Its usefulness
margin over its own control was the best of any version, +3.50.

**v2 → v3, reverted.** v3 banned the labels that v2's rules had hardened into
("How I know:", "The concern, said once"). The labels went and the behaviour
went with them: usefulness fell to 22.33, *below its own control* — the only
time that happened — harms nearly doubled, and a sample presented its own test
fixture as the user's manifest, the exact failure the rule existed to prevent.
A cosmetic fix that broke something load-bearing.

**v3 → v4.** Judges found that every analogy in the corpus closed the same way:
a competent human contrasted against an indifferent machine, five times across
five different objects. v4 replaced the move rather than banning the words —
close on what the difference makes you *do*, not on the contrast. Tested against
the champion in the same packet, it won all three axes and wrote two of the
judge's three best samples.

## What did not work, so nobody retries it

**Banning a phrase does not remove the behaviour.** v1 had a fixed hinge. It was
banned; v2 grew a fixed heading. That was banned; v3 produced a third
construction that a judge counted five times. The vocabulary changed every
round. The move never did. What finally worked was replacing the move with a
different one, not forbidding the words it wore.

**Instructions leak their own vocabulary.** v1–v3 said *"Say where the
comparison stops being true."* Seven samples then announced the limit with
near-identical phrasing — "the comparison stops here", "where the picture stops
being true". The rule handed the model its wording.

**Fewer, rarer analogies is worse.** Tested as a challenger against v4: voice
−0.33, usefulness −2.83, harms +3. Rejected.

**A winning fix becomes the next tic.** v4's consequence-close won its batch and
was then used by 25 of 30 samples in the next — unanimously, 10 of 10, on one
question, with the literal words "So the fix is" closing nine of them. A judge
put it plainly: *"The first time this shape appears it is excellent. By the
twenty-fifth it is a chassis."*

**And banning a move can overshoot.** v4 removed the human-versus-machine close.
Two batches later a judge counted it **once in thirty samples** and called that
"a missed register, not an overused one." The style now under-uses Vonnegut's
most characteristic figure because of a fix that worked too well.

**Objects still come off one shelf, and no instruction has changed that.** Two
attempts failed from opposite directions — telling the model where to source the
object (V2/V4, lost twice) and naming the objects to avoid (V10, worst result in
batch 3). Nine of ten answers to one question landed in three bins. All ten
answers to another reached for the same figure: a narrow aperture that meters
items rather than mass — toll booth, mail slot, loading dock, service window,
freight elevator.

## Reproducing

Snapshots are content-addressed by sha256 of the style file, so any number in
this table can be checked against the exact bytes that produced it.

| ver | sha256 (first 12) | reproduce with |
|---|---|---|
| v1 | `4759f2c9803d` | `git show 7bfe50c:plugins/prose/output-styles/vonnegut.md \| sha256sum` |
| v2 | `87b860868b0a` | `git show fd0940f:plugins/prose/output-styles/vonnegut.md \| sha256sum` |
| v3 | — | never committed; reconstructable from the v3 section above |
| v4 | `dc6ddff147b3` | superseded; rebuild by reverting the v5 patch |
| v5 | `221eb1409a21` | `sha256sum plugins/prose/output-styles/vonnegut.md` |

These are hashes of the bytes on disk, so `sha256sum` agrees with them. An
earlier draft of this table hashed newline-normalised text and did not
reproduce — worth knowing if you ever see `48cbebafa407` quoted anywhere.

## Caveats on the numbers

Six samples per arm per version. The control drifted 23.83 → 23.17 → 23.83 on
identical questions, so roughly one point of usefulness is noise.

The voice gap between styled and control (about 5 points) is far too wide to be
noise. The usefulness gap (about 1–3 points) is not, and should not be quoted as
though it were.
