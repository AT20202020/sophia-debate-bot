# Sophia — Full Project Review: Mistakes, Cascading Effects, and the Path to Near-Instant

Written at Jeff's request for a complete, honest audit of the project so far: what
early decisions cost us later, whether the current stack (AMD 7900 XTX, Ollama,
qwen3.8:27b) is actually the right one for this job, and a concrete, prioritized
plan to get response latency down as far as it can realistically go without
giving up reasoning quality. Covers the full version history (v1.0 → v2.45),
the current code, both prior review docs (ARCHITECTURE_NOTES.md,
CODE_REVIEW_2026-09-04.md), and fresh research against the 2026 landscape rather
than assuming anything from before this project's own testing is still current.

Bottom line up front, for the impatient version: **no, you don't need better
hardware, and no, you don't need a smaller model.** The stack is correct. The
thing costing you 8-10 seconds a turn is how many tokens qwen3.8:27b spends
*thinking before it starts talking*, not raw GPU speed, not the serving
software, and not the architecture. That's fixable in software, this week,
for free - the "how" is already in flight (`compare_think_effort.py`, waiting
on your test run). Everything else in this document either backs that up with
real numbers or explains why it's a smaller, later lever.

## Part 1 — Mistakes with cascading effects

You asked specifically to look for early mistakes whose effects rippled
forward. Reading all 46 versions back to back surfaces a few real patterns -
not one-off bugs, but the same shape of mistake recurring because its root
cause was never addressed, only its latest symptom.

### 1.1 The reasoning-token-budget bug: discovered in v1.3, never actually fixed, patched six times

This is the single clearest thread in the whole history. `num_predict` on a
reasoning model caps thinking AND the visible answer *together*, in one shared
budget. The first time this bit the project was v1.3→v1.4 (very early):
`think: "low"` was enabled, the model spent its entire budget reasoning, and
Sophia went silent mid-turn. The fix at the time was to revert thinking
entirely (`think: False`).

Every time reasoning was reintroduced or the model changed, the *exact same
failure* came back, because the underlying fact - a shared token budget, and
no way to know in advance how many tokens a given question will make the model
think for - was never actually solved, only patched with a bigger number:

- v2.17: deep mode's 768-token budget wasn't enough; a real turn burned all
  768 on reasoning and got 5 words of trimmed answer. Raised to 2560.
- v2.38: the qwen3.6→qwen3.8 model migration reproduced v1.3's exact failure
  the moment the old boolean `think: true` was sent to the new model's string
  API. Required live API testing to even discover `think` had become a string.
- v2.39/v2.40: normal turns started clipping too (160→280→450) because
  qwen3.8 spends budget on reasoning on *every* turn, not just deep-mode ones.
  A one-time automatic retry-at-double-budget was added as a permanent safety
  net - which is itself an admission that the ceiling can never be fully
  trusted to be high enough.
- v2.41: `mod`/`verdict`/`steelman`'s override budget (400, set when the
  normal ceiling was 280) silently became *lower* than the normal-turn budget
  after v2.39's bump - three commands that explicitly need more room than an
  ordinary turn were quietly getting less.
- v2.43: cross-session memory's summarizer used `num_predict: 80` and had
  been silently producing empty summaries for weeks - **the third occurrence
  of this exact bug class in the one Ollama call nobody was watching for it.**
- v2.45 (this week's transcript analysis): even at 800, it still happens
  (~5% of turns), costing 40-48 seconds when it does.

The pattern: every new place a request gets sent to Ollama is a fresh chance
to reintroduce this bug, and it has been reintroduced independently at least
four times (deep mode, model migration, mod/verdict/steelman, memory
summarization) because there was never one place that owned "how many tokens
does this kind of call need" - just separate literals, tuned separately, each
one eventually found empirically after an actual live failure. **This is also
the direct cause of the latency problem you're asking about right now** - the
"how much does she reason" question this bug class kept dancing around
without addressing is the same question `compare_think_effort.py` is now
trying to answer properly, from first principles, instead of by raising a
ceiling number again.

### 1.2 The stale-literal bug: the same mistake, six separate times

A narrower but very concrete version of "no single source of truth": a
constant gets defined once, then hand-copied to two or three other places
(a comment, a log snapshot, a diagnostic script, an eval script), and only
one of the copies gets updated when the value changes.

- v2.39→v2.40: the session-log snapshot still said `"num_predict": 280` after
  the real value moved to 450.
- v2.38→v2.43: `sophia_eval.py` kept `qwen3.6:27b`, boolean `think`,
  `num_ctx: 8192` for **five versions** after the live bot had moved on -
  meaning the regression-test tool would have caught nothing real for the
  entire time it was most needed (right after a model migration).
- v2.41→v2.44: `sophia_eval.py`'s `num_predict` (450) drifted from the live
  `NORMAL_NUM_PREDICT` (800) after v2.43 changed the latter; caught and fixed
  this week (v2.45), three versions late.
- v2.44: `TTS_SPEED`'s `1.25` literal was duplicated in three places (two
  `tts_pipeline()` calls, one log snapshot) before finally getting a named
  constant.
- `check_ollama_cache.py` and `profile_latency.py` are *still* stale right
  now (model name, `num_ctx`, boolean `think`) - flagged in the
  2026-09-04 review, not yet fixed. Running either today would measure bugs
  this project already fixed, not anything real.

None of these individually mattered much. Collectively, they describe a
project that has paid for "one source of truth" the hard way, six times, and
still hasn't actually built one. Fable 5.1's review independently proposed
the fix (a single `sophia_config.py` holding `MODEL`, `NUM_CTX`, and
`_think_effort`, imported everywhere instead of copied) - worth doing simply
because this exact mistake keeps recurring on its own schedule regardless of
how many times a single instance gets fixed.

### 1.3 SYSTEM_PROMPT bloat: a threshold was set, documented, crossed, and crossed again

v2.11 and v2.19 both found the same failure shape: two prompt rules collided
and the wrong one won. v2.21 responded correctly - a real architectural fix
(routing procedure instead of a rule pile), shrinking the prompt 14,379 →
8,933 chars, with an explicit standing rule written down: *if a third
collision shows up, consolidate, don't patch again.*

It grew back. By v2.34 it had reached 18,930 chars - more than double the
post-consolidation size - and the changelog itself flagged this in bold with
a strong recommendation to run the regression suite and consolidate before
adding anything else. That recommendation was **not followed**: v2.35 and
v2.37 only trimmed it to 18,512 (a ~2% cut against a >100% regrowth), and in
that same window a real, live regression surfaced (v2.35's mode-routing typo,
sitting silently wrong for an unknown number of versions; v2.36's live
"definiens" called word salad, a rule the prompt explicitly bans violating).
As of right now the prompt is **18,493 characters** - essentially unchanged
since v2.37, over 2x the size that twice already caused rule collisions, and
it has had no consolidation pass in 8 versions despite the project's own
written rule saying it should.

This isn't free: every cache-miss (first turn, and any turn after the prompt
itself is ever edited) re-evaluates the whole thing, and it's sitting on
top of a documented collision-risk threshold with no enforcement mechanism
beyond "remember to check" - which the project's own history shows doesn't
reliably happen.

### 1.4 The regression-suite discipline gap enabled 1.3, and possibly 1.1

`sophia_eval.py` exists specifically to catch prompt regressions before they
ship. The changelog documents, repeatedly, that it *wasn't run*: "hasn't been
run since v2.21" (v2.31), "still hasn't been run since v2.21, and this is now
the fifth prompt edit since then" (v2.34), "it still hasn't been run since
v2.21" (v2.35, the version that found a live routing typo). That's at least
five SYSTEM_PROMPT edits shipped with zero automated regression coverage,
including the two that turned out to contain real bugs. This wasn't
negligence exactly - the tool itself needed Jeff's machine to run, and there
was no reliable way to prompt for it every time - but the effect was the
same: the safety net existed and wasn't used at the moments it mattered most.

### 1.5 A "GPU acceleration" feature ran for roughly six versions doing net harm, undetected

v2.12 added an optional whisper.cpp GPU server specifically because
faster-whisper has no ROCm backend - a real, structural AMD limitation, not a
bad call at the time. It shipped explicitly untested ("no AMD GPU available
here to verify against"). It then ran, apparently successfully
(`gpu_transcription: true`, no crashes, real transcriptions coming back) for
roughly six versions and every session from v2.38 onward, while actually
being **both slower than the CPU path it replaced (2.1s vs 1.5-1.85s per
chunk) and completely blind to the philosophy-vocabulary prompt and
conversation context** that make Sophia's transcription accurate - because
`_transcribe_via_server()` only ever sent the audio file, never the prompt.
The v2.36 "definiens" vocabulary fix, in particular, could never have taken
effect while this was running silently in the background. This was only
caught by a second, independent code review reading the function body
directly - not by any log metric, because "did it return text" and "was that
text actually informed by the tuning we did" are different questions, and
only the first one was being checked.

**The common thread across 1.1-1.5:** every one of these is a case where a
real signal existed (a log line, a diff, a documented threshold) but nothing
forced it to be looked at before shipping the next change. That's not a
reasoning-quality problem, it's a process gap - and it's the same gap that
made this specific speed investigation necessary: ARCHITECTURE_NOTES.md's own
headline number (see 1.6) went stale the same way.

### 1.6 A live example, caught while writing this review: ARCHITECTURE_NOTES.md's own number is now wrong

ARCHITECTURE_NOTES.md's closing argument is "Sophia's median time-to-first-
token is already ~2.7s... a genuinely good number... spend further effort
elsewhere before chasing more speed." That figure mixed 135 qwen3.6 turns
(2.63-2.72s, a non-reasoning model) in with 21 real qwen3.8 turns without
separating them - the qwen3.6/qwen3.8 model swap happened mid-document. The
real qwen3.8 number, confirmed twice now independently (the 2026-09-04 code
review's log analysis, and this week's full-transcript analysis of a real
session) is **7.99s and 8.53s median** across two different sessions - three
times worse than the number the document currently leads with. I've corrected
this in ARCHITECTURE_NOTES.md as part of this review (see the changelog entry)
so it stops being cited as a reason not to pursue exactly what you're asking
for right now.

## Part 2 — What's already correct (validated against current, 2026 research)

Before recommending anything, I checked whether the fundamentals still hold
up, rather than trusting either this project's own prior conclusions or my
own training data at face value. They do, with more confidence than before:

**Ollama is the right serving software for this workload, specifically
*because* it's single-user.** A direct 2026 benchmark comparing Ollama and
vLLM at one concurrent request found Ollama *faster* on time-to-first-token
(45ms vs 82ms) and roughly tied on throughput - vLLM's whole advantage is
continuous batching across many simultaneous requests, which never happens
here (Sophia only ever has one request in flight). Switching serving
frameworks would be a strict downgrade for this exact use case, not an
upgrade.

**ROCm is a legitimate inference platform in 2026, not a compromise.** "For
pure inference, ROCm is a real choice in 2026" per current benchmarking, and
flash attention shows real, confirmed speedups on this exact card family
(1.57x in one measured case). The GPU platform choice was not a mistake -
the *specific bugs* around it (the whisper.cpp GPU server, the launcher
env-var cargo-culting from a bad blog post) were real, but they were bugs in
how the project used ROCm, not evidence ROCm itself was the wrong choice.

**Speculative decoding (MTP) is on and doing real work, but philosophical
argumentation is close to its worst case.** qwen3.8:27b's built-in
multi-token-prediction is confirmed active. Current benchmarks show 1.5-3x
realistic single-user speedups from this technique generally - but they also
show it depends heavily on acceptance rate, and "creative/high-entropy text"
(exactly what open-ended philosophical reasoning is) gets the *worst*
acceptance rates of any content type, sometimes swinging speculative decoding
from a win to a net loss. The 33-38 tok/s you're measuring is plausible for
this hardware, this quantization, and this specific low-acceptance-rate
workload - it isn't evidence the setup is misconfigured.

**Kokoro TTS and the STT/LLM/TTS cascade architecture are already correct**
for a bot whose entire value is careful reasoning rather than natural small
talk - this was already established in ARCHITECTURE_NOTES.md and nothing in
fresh research changes that conclusion. End-to-end audio-native models
(Moshi, Sesame CSM) remain both unsupported on AMD and reasoning-shallow by
design; that's a settled question, not one worth revisiting again soon.

**Push-to-talk continues to be the correct default**, not a compromise -
it gets Sophia the "user has stopped talking" signal for free, at zero
latency cost, which voice-activated designs spend real engineering effort
(VAD tuning, and now dedicated turn-detection models) trying to approximate.

## Part 3 — Do you need better hardware?

Short answer: no, not to fix what's actually slow right now, but here's the
honest math if you ever want an additional multiplier on top of the software
fix.

The RX 7900 XTX has ~960 GB/s of memory bandwidth. Token generation for a
dense model like qwen3.8:27b is memory-bandwidth-bound - you're reading the
whole ~17GB of weights (Q4_K_M) roughly once per token - so raw bandwidth is
the real ceiling on tokens/second, not compute. An RTX 4090, same VRAM tier,
has almost identical bandwidth (~1008 GB/s) - upgrading to a 4090 specifically
would buy you maybe 5% more raw throughput, not a meaningful win, and you'd
be trading a card that's already working (once the launcher bugs are fixed)
for CUDA's ecosystem maturity alone.

The one hardware option that would move a real number: the RTX 5090 (32GB
GDDR7, 1,792 GB/s - nearly double the 7900 XTX's bandwidth). For a
bandwidth-bound decode workload, that plausibly translates to something like
1.5-1.8x more tokens/second once real-world overhead is accounted for -
meaningful, not transformative. It would take an 8.5s median time-to-first-
token to roughly 5-5.5s, not to "near instant." It would also give you 8GB
more headroom (useful for a bigger KV cache / longer context) and would
finally put faster-whisper on native CUDA, eliminating the entire GPU-whisper-
server side-quest and its bug (1.5) by construction, since faster-whisper
just runs on the GPU directly with no separate server process needed at all.

That's a real, honest option if you want it later - but it's roughly $2,000
for a 1.5-1.8x multiplier, applied on top of whatever the software fix
achieves, not instead of it. The software fix (below) is free and the bigger
lever. Do that first; revisit hardware only if you still want more after.

## Part 4 — Do you need a smaller or different model?

No - and specifically not for the reason you might expect. The whole reason
qwen3.8:27b is slow per-turn is reasoning tokens, and a smaller model
wouldn't reason *less* per question, it would just reason *worse* per token,
which is the opposite of what you told me to protect back when we did the
qwen3.6→qwen3.8 upgrade ("keep this level of logic"). Dropping to a smaller
dense model trades quality for a speed problem that has a free, non-quality-
costing fix available (see Part 5). The MoE trap already documented in v2.33
(qwen3.6:35b-a3b scoring *worse* on reasoning despite being "bigger," because
only 3B of it is active per token) is exactly this same mistake in a
different shape - "bigger/different" is not automatically "better" or
"faster" for what this bot needs.

Worth noting for the record: qwen3.8:27b's own model family (the Qwen3 line)
is explicitly designed and documented to support "seamless switching between
thinking mode for complex reasoning and non-thinking mode for efficient
dialogue" as an intentional, first-class feature - not a hack. That's
independent confirmation that `think=false` is a legitimate, supported mode
for this model family, not something to be nervous about testing.

## Part 5 — The actual roadmap to as-fast-as-it-gets-without-losing-logic

In priority order, cheapest and highest-confidence first:

**1. `compare_think_effort.py` - STATUS: run, results in, one caveat, not
shipped yet.** Confirmed: 2.01x aggregate speedup (158.6s -> 78.7s across
all 14 cases), matching the earlier single-question probe almost exactly.
13 of 14 cases hold up on quality, including one case where `think=false`
actually avoided this project's own empty-reply bug that `think=low` hit
live during the test. But Case 1 (direct question, plain-answer mode) shows
`think=false` regressing on the exact v2.3 no-pivot-back-to-debate rule
that case exists to check ("What's your argument?" reappearing). Per the
tool's own decision guidance, one routing miss is reason enough to hold off
on a global switch at temperature 0.3 without ruling out noise first.
**Next action: rerun Case 1 a handful more times to confirm it's systematic
before routing anything.** If it holds up as real, the fallback is a
partial rollout - `think=false` for moderator/mod/verdict/steelman turns
(tested clean, and the no-pivot rule doesn't even apply there) while plain
Q&A stays on `think=low` until the prompt can be hardened for it. Either
way this is very close to done, not still speculative.

**2. Set a realistic floor, and go chase it: the ~2.5s "unexplained Ollama
gap."** Even in the best case - reasoning removed entirely - the 2026-09-04
review's own log breakdown shows a roughly 2.5-second fixed cost per request
that isn't prompt eval, isn't model load, and isn't thinking. That's the real
ceiling on "near instant" with this stack: something closer to the qwen3.6
baseline of ~2.7s median, not sub-second. `profile_latency.py` was written
specifically to isolate this and is currently stale (wrong model name, wrong
num_ctx, boolean think) - fixing it to match the current config and actually
running it is the next real lever after #1, and it's the difference between
"probably good enough" and knowing exactly what's left on the table.

**3. First-turn-after-launch/reset penalty - STATUS: resolved, not a bug.**
Jeff's `llama-server` console log from the `compare_think_effort.py` run
answered this directly: it's not a KV-cache-slot issue, and
`OLLAMA_NUM_PARALLEL=1` wouldn't change anything - it's already the live
config (`n_slots=1` confirmed in the log). `llama-server`'s longest-common-
prefix prompt cache reuses the ~4270-4320-token SYSTEM_PROMPT (measured for
the first time, not estimated) across every request after the first, so
only the ~460-610 differing trailing tokens get evaluated per turn
(~800-950ms). The first request of a session pays the full cold-cache cost
for the whole prompt - that's the entire ~5.4s spike. Nothing to fix here;
it's an unavoidable one-time cost per session/model-load, not a recurring
tax. No action needed.

**4. Consolidate SYSTEM_PROMPT - overdue since v2.37.** Currently 18,493
chars, over 2x the last verified-safe size, sitting on a documented collision
risk with no automated guard. This has a real (if secondary) latency cost -
every cache-miss re-evaluates all of it - and a real correctness cost, since
it's exactly this kind of bloat that produced two live bugs before (v2.11,
v2.19, and arguably v2.35/v2.36). Run `sophia_eval.py` before and after, per
the project's own standing rule.

**5. Close the process gap that let 1.1-1.5 happen.** Concretely: build the
single `sophia_config.py` (model name, num_ctx, `_think_effort`) Fable's
review proposed, so the stale-literal bug class structurally can't recur the
same way again; fix `check_ollama_cache.py` and `profile_latency.py` to match
current config before using either; and make "run `sophia_eval.py`" an actual
gate rather than a note in the changelog that's easy to skip under time
pressure - now that the device bridge exists (even if it's been flaky this
week), the right target is having *me* run it automatically after any
SYSTEM_PROMPT or model-request edit, not relying on it getting remembered.

**6. Later, exploratory, real engineering cost - not this week:** the
2026-09-04 review's speculative early-flush idea. Right now the tail of your
speech (the bit after your last full sentence, before you press Enter) has to
be transcribed *after* you press Enter, adding 1.5-2s serially. If the
recording loop flushes and transcribes a trailing chunk as soon as it detects
~700ms of silence - before Enter - that transcription is usually already done
by the time you actually press Enter. A further, bolder version -
speculatively starting the LLM request on that flushed text and cancelling if
you keep talking - would hide part of the reasoning wait too, but it
competes with the next real request for the same GPU and needs #3 sorted
first. Real complexity, real payoff, not a quick win - worth a dedicated pass
once 1-4 are done and you can measure what's actually left.

## What I did not touch

I corrected ARCHITECTURE_NOTES.md's stale ~2.7s figure (Part 1.6) since
leaving a document with a known-wrong headline number sitting in the repo as
a citable "we already checked, it's fine" is exactly the kind of drift this
whole review is about. I did not touch SYSTEM_PROMPT, the launcher, or any
runtime behavior beyond that correction - everything in Part 5 is a
recommendation for you to sequence, not something I shipped unilaterally,
since #1 is already mid-flight on your machine and the rest depend on its
result.
