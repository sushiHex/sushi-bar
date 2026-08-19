# ✍️ prose

Three selectable **output styles** for Claude Code. They change how Claude writes
*to you*. They do not change what it builds.

```
/plugin install prose@sushi-bar
```

Then pick one in **`/config` → Output style**:

| Style | Reads like |
|---|---|
| `prose:ELI5` | Plain language, everyday analogies, every technical term defined on first use |
| `prose:ASD-STE100` | Simplified Technical English — short sentences, active voice, one instruction per sentence |
| `prose:STELI5` | Both: ELI5's explaining, under STE's sentence discipline |

Set it in `settings.json` instead if you prefer:

```json
{ "outputStyle": "prose:ELI5" }
```

## What they change, and what they don't

Both styles set `keep-coding-instructions: true`, so Claude Code's normal
engineering behaviour stays fully in place. Only the prose around the work
changes.

Both also declare technical content out of reach of the writing rules, as a
*structural slot* rather than an exemption clause:

- Code, commands, file paths, function names, flags and error text are copied
  **verbatim**. A path you cannot copy is a broken answer.
- Implementation quality is held to the normal standard.
- A caveat that matters is never dropped for being "advanced" — it is explained
  more simply instead.
- Bad news is stated plainly. Simple language makes it clearer, not vaguer.
- Commit messages, PR bodies, code comments, docstrings and in-repo docs keep
  **their project's** conventions. The style governs replies to you.

## 🧒 ELI5

Explains to a smart person who is new to *this* topic. Assumes intelligence,
assumes no background.

An answer is built from named parts, in order — the plain answer first, then
what is going on, an analogy only when the idea is genuinely hard (with its
limits stated), the exact technical detail, then the catch if a real one
exists. Depth is calibrated: a direct question gets a direct answer rather than
a lesson, and a term is defined once per conversation.

## ✈️ ASD-STE100

[ASD-STE100](https://www.asd-ste100.org/) is the controlled-language standard
the aerospace and defence industries use for maintenance documentation.

Applies the writing rules: one word one meaning, no more than 20 words in an
instruction and 25 in a description, one instruction per sentence, imperative
verbs, active voice, simple tenses, no `-ing` forms, articles kept, noun
clusters capped at three. Technical Names and Technical Verbs are explicitly
permitted, so "repository", "compiler" and "mutex" stay as they are rather than
being circumlocuted.

> **Honest limit, also stated inside the style:** this applies the *writing
> rules* only. The ~900-word approved dictionary is licensed by the AeroSpace
> and Defence Industries Association of Europe and is not bundled, so output is
> **not** verified against it. The style forbids Claude from claiming full
> compliance.

## 🥢 STELI5

The merge. ELI5 knows *what* to explain but its length rules did not bind;
ASD-STE100 has the sentence machinery but says nothing about teaching. STELI5
runs ELI5's job through STE's discipline — short sentences, active voice, one
idea each, numbered steps, consistent terms, plus term definitions and "say why".

The two parents contradict each other in exactly one place, and the style
resolves it rather than picking a side. STE bans figures of speech so a reader
can never mistake one for a fact; ELI5 needs analogies. A comparison is
therefore allowed only when **marked** ("This works like a queue at a counter")
and **bounded** ("The difference is that the queue never reorders itself"). An
unmarked metaphor is still banned, which honours STE's actual intent.

Measured against both parents and a no-guidance control, 4 reps each, same
probe:

| | words | median sentence | longest | >25w | >35w |
|---|---|---|---|---|---|
| control | 265–305 | 14–18 | 28–44 | 11 | 2 |
| ELI5 | 208–361 | 12–19 | 35–49 | 11 | 3 |
| ASD-STE100 | 180–201 | 8–10 | 18–25 | 0 | 0 |
| **STELI5** | 237–377 | **9–14** | **21–34** | **2** | **0** |

It inherits the discipline — zero sentences over 35 words where ELI5 had three,
and `>25w` down from 11 to 2 — while writing *more* than ASD-STE100, which is
the point: it explains.

## How these were built

Both were iterated against a measured baseline rather than written and shipped.
Each candidate was run with a no-guidance control, 4 reps per arm, and scored on
sentence length, output-size variance and verbatim survival of technical tokens.

That process rejected two plausible-looking drafts. A word-count *limit*
("never over 35 words") did not bind — reps ignored it. Replacing it with a
positive **contract** (name the parts of an answer, in order) cut ELI5's
output-size spread from 263 words to 64. Separately, adding one extra rule to a
working recipe made it measurably noisier, so it was reverted.

**Requirements:** none. No dependencies, no scripts, cross-platform.
