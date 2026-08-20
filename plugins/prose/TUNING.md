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

| ver | change | batch | voice | useful | harms | verdict |
|---|---|---|---|---|---|---|
| v1 | initial: three books, three techniques | b0 | **9.00** | 25.50 | 7 | superseded |
| v2 | + "say how you know"; analogy anti-tic | b0 | 8.33 | **26.67** | 8 | shipped as 1.2.1 |
| v3 | + ban epistemic labels and meta-headings | b0 | 8.33 | 22.33 | 14 | **reverted** |
| v4 | + close analogies on a consequence | b1 | **9.00** | 26.00 | 6 | superseded |
| v5 | + show the analogy's edge, never announce it | b2 | 8.50 | 23.17 | 11 | superseded |
| v6 | + make one object pay twice | b4 | 8.83 | 25.17 | **5** | **champion** |

Control, for scale: voice 3.0–3.8, useful 23.2–23.8, harms 11–15.

Read a row only against the other rows from its own batch. v5 appears here with
its winning batch-2 numbers and appears in the ledger with its batch-3
re-measurement of 7.17/24.50/9. Neither is wrong. They are different question
sets, and the whole field moves between them.

Scores are only comparable **within** a batch. Different batches use different
questions, and the whole field moves with them — every variant scored lower on
the batch-2 question set, champion included. That is why champion and
challengers are always judged in one packet.

## Does the file earn its length?

Ten challengers were all edits *inside* a 1,253-word file. Nobody had ever tested
whether the file needed to be that long. Batch 4 ran that control: five arms in
one sealed packet, same questions, same judges, prompts from eleven words to
1,322.

| arm | prompt | voice | useful | harms |
|---|---|---|---|---|
| TINY | 11 words — "Explain things the way Kurt Vonnegut would." | 7.33 | 24.33 | 5 |
| MIN | 64 words — two paragraphs | 7.33 | 25.00 | 7 |
| MID | 256 words — every rule once, no elaboration | **8.33** | 23.50 | 9 |
| CHAMP | 1,253 words — v5 | 8.17 | 25.00 | 6 |
| V8B | 1,322 words — v5 + one patch | **8.83** | **25.17** | **5** |

Three things fell out of it.

**The rules buy the voice, and they saturate around 256 words.** MID is a
paraphrase of the champion with every explanation stripped out. It matched the
champion on voice at a fifth of the length — 8.33 against 8.17, comfortably
inside noise. If voice were the only axis, four fifths of this file would be
decoration.

**The other thousand words buy accuracy.** MID lost 1.50 usefulness against the
champion whose rules it restates, and carried three more harms. The elaboration
is not there to make the writing better. It is there to stop the writing from
costing the reader a fact.

**Below about 64 words the voice does not form at all.** TINY and MIN both
scored 7.33, a clear point under every arm that actually states the rules.

Output length turned out to be nearly independent of prompt length: TINY
averaged 660 words per answer, CHAMP 772. A long style file does not make a
windy model.

### The ban on lifted signatures is load-bearing

This was written down before the key was opened, so it counts as a prediction
rather than a story told afterwards.

The voice judge flagged "So it goes" and "Listen:" across the packet and refused
to credit either — *"lifted signature, not technique."* The champion forbids the
first one by name. Counting them per arm, six samples each:

| marker | TINY | MIN | MID | CHAMP | V8B |
|---|---|---|---|---|---|
| "So it goes" | **6** | 1 | 0 | 0 | 0 |
| "Listen:" | **3** | 0 | 0 | 0 | 0 |

MID is the shortest arm that carries the line *"Never shrug at a real failure.
'So it goes' is for novels"*, and it is the shortest arm with zero leakage. MIN
drops that line and leaked once. TINY drops it and did an impression in every
single sample.

So the rule works, and it is the cheapest thing in the file. Without it a short
prompt produces costume.

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
| V8B | V8 rerun on fresh questions, batch 4 | **WIN** → v6 |

Batch 3 was unanimous in shape: **every** challenger bought voice and paid
usefulness. V8 was the strongest unresolved case — it wrote the judge's first and
second best samples of thirty while the champion wrote two of the three weakest,
and its −0.83 usefulness sat inside the ~1-point noise floor while its +1.17
voice sat above it. It did not meet the pre-registered bar, so it did not ship.
Changing the bar after seeing the numbers would have made the whole exercise
decorative.

Instead it was rerun in batch 4 on a different question set, where it took all
three axes: voice +0.67, usefulness +0.17, one harm fewer. Two batches, two
different question sets, and the voice gain kept its sign both times. The
usefulness sign flipped from −0.83 to +0.17, which is what a quantity inside the
noise floor does. That is the whole argument for shipping it, and it is a
stronger argument than either batch made alone.

### The uncomfortable part of that win

V8B tied for the lowest harm count in the packet and still wrote the single worst
defect in it. One of its git answers built a fenced, copy-pasteable block around
`$OLD` without ever assigning `$OLD`. A colleague pastes the line, bash drops the
empty word, and `git rebase --onto origin/main main` throws away their two
unpushed commits and prints **"Successfully rebased and updated
refs/heads/main"**. The judge reproduced it. No error, no warning, a success
message, in the exact branch written for the person with work to lose.

The same sample also contains the best epistemic moment in all thirty — it
guessed that `--force-if-includes` might be a no-op next to an explicit-SHA lease
and *declined to assert it*, which git's own docs confirm. Careful reasoning,
unsafe artifact, one sample.

`harms` is an unweighted count. It cannot tell that rebase line apart from an
omitted `LOAD_SMALL_INT` in a `dis` listing, and it scored them the same. That
flaw has been in the metric since v1, so it was not discovered conveniently — but
it does mean the harm column is the weakest of the three, and a tie on it should
not be read as a safety result.

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

**v5 → v6.** Nine of the ten challengers tried to change *how* an analogy is
built. This one changed how many times it gets used. The reader has already paid
to load an object into their head, so bring that object back rather than buying a
second one. What the judge kept quoting was the return trip: a ringing phone in
one chapter that turns out to be the `CALL` opcode in the next, a jar whose label
saves you opening it — an index-only scan. Both of those came from v6 samples,
and both do technical work a fresh object could not do.

The move also has a failure mode worth naming, because the judge caught it: an
object that comes back with nothing new to say is worse than no return at all.
The rule says *pay twice*, not *appear twice*.

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

**Ten rounds ran before anyone tested the obvious control.** Every challenger
from V1 to V10 was an edit inside a file whose length nobody had questioned. The
batch-4 ladder found that a 256-word paraphrase matches the champion on voice.
Had that run at V1, four of the ten hypotheses would have been aimed somewhere
better. The lesson is not about this style: **run the does-it-matter-at-all
control before optimising inside the thing.**

## Reproducing

Snapshots are content-addressed by sha256 of the style file, so any number here
can be checked against the exact bytes that produced it.

There is a catch, and it has now bitten this table twice. The judged runs read
the file **from the working tree**, where it has CRLF line endings. Git stores
the blob with LF. So the bytes that produced a score and the bytes in the commit
have different hashes, and only one of them is the one the numbers belong to.
Both are listed. **The worktree hash is the authoritative one** — it is what the
model actually read.

| ver | worktree sha256 (judged bytes) | git blob sha256 | commit |
|---|---|---|---|
| v1 | `4759f2c9803d` | `4759f2c9803d` (same, file was LF) | `7bfe50c` |
| v2 | `87b860868b0a` | `87b860868b0a` (same, file was LF) | `fd0940f` |
| v3 | — | — | never committed; see the v3 section above |
| v4 | `dc6ddff147b3` | not recorded | superseded; revert the v5 patch |
| v5 | `221eb1409a21` | `65686a091f05` | `e846087` |
| v6 | `8111e4d9185a` | `f7ad5bd8bd22` | this commit |

Check a worktree hash with `sha256sum <file>` after checking that version out.
Check a blob hash with `git show <commit>:plugins/prose/output-styles/vonnegut.md
| sha256sum`. Running the second command and expecting the first column is how
the v5 row was wrong when it was written.

The file switched from LF to CRLF somewhere between `fd0940f` and `e846087`,
which is why the two columns agree for v1 and v2 and diverge afterwards.

This is the second reproducibility bug in this table. The first: an early draft
hashed newline-normalised text for every row, so nothing reproduced under
`sha256sum` — worth knowing if you ever see `48cbebafa407` quoted anywhere. Both
bugs had the same cause, which is that line endings are invisible.

## Caveats on the numbers

Six samples per arm per version. The control drifted 23.83 → 23.17 → 23.83 on
identical questions, so roughly one point of usefulness is noise.

The voice gap between styled and control (about 5 points) is far too wide to be
noise. The usefulness gap (about 1–3 points) is not, and should not be quoted as
though it were.

Six samples per arm is thin, and v6 shipped on a +0.67 voice margin. What makes
that margin worth acting on is not its size — it is that the same patch gained
voice in two batches with different questions and different judges. A single
batch could not have carried it.

`harms` is a count with no severity weighting, and batch 4 showed exactly how
that misleads: the arm that tied for fewest harms wrote the one defect that
silently destroys a colleague's commits. Treat the harm column as a rough
tripwire, never as a safety argument.
