# Changelog — Sophia

Full version history. Extracted from the `debate_voice.py` module docstring in v2.20,
where it had grown to 396 lines — a quarter of the file.


## v2.42

Acted on ARCHITECTURE_NOTES.md's #1 recommendation (the rest of that
list needed a different kind of follow-through than "write code" - see
below).

**Silence gate before Whisper ever sees a chunk.** The `[BLANK_AUDIO]`/
`[SNIFF]` fix in v2.41 only catches non-speech Whisper is honest enough
to tag as such. Research into other real-time voice projects surfaced
that this is a known, systemic Whisper behavior, not a one-off: it
"generates phantom text during silences... words, phrases, sometimes
entire sentences that were never spoken," untagged. Added
`_is_effectively_silent()` - a plain RMS-amplitude check - at the very
top of `_whisper_transcribe()`, before either the GPU server or CPU
model gets a chance to invent something. Below `SILENCE_RMS_THRESHOLD =
0.006`, a chunk returns empty without ever being sent to Whisper at all:
silence in, silence out, guaranteed, and a small speed bonus (skips a
~1.5-2s call entirely) rather than just a correctness fix.

**Not yet tuned against real audio** - same limitation as the v2.40 TTS
silence trim: no path to this machine's mic from where this was written.
Deliberately picked a conservative (low) threshold since dropping actual
quiet speech is a worse failure than an occasional wasted transcription
call. If quiet speech starts getting silently dropped, lower it; if
phantom text still gets through, raise it.

**The other two items from ARCHITECTURE_NOTES.md were investigated and
NOT implemented, on purpose:**

- *Moonshine as an alternate STT backend* - its docs don't show
  confirmed support for the `initial_prompt`/vocabulary-biasing
  `DOMAIN_VOCAB_PROMPT` relies on for philosophy jargon, and there's no
  way to validate real transcription accuracy against this project's
  actual speech from this environment. Writing an integration against
  an unconfirmed API for a component this central, with no way to test
  it, would be guessing - not implementing. Needs either more research
  to confirm the API, or Jeff testing it hands-on.
- *Tiered reasoning effort (skip "low" thinking for simple turns)* - ran
  into a real blocker while trying to implement it: there is no verified
  setting below `"low"` for qwen3.8:27b's `think` field. The v2.38
  CHANGELOG entry (and the module docstring's THINK IS A STRING NOW
  bullet) documents that sending anything other than `_think_effort()`'s
  output reproduced the exact empty-reasoning-budget failure this
  project has spent three versions fixing. Implementing "skip reasoning"
  would mean re-opening a bug class that's already been closed, for a
  speed gain that's unverified to even exist. Left alone. If this is
  worth pursuing later, it needs controlled testing directly against
  Ollama's API (comparing `think` values on identical prompts) before
  any code changes - not something to guess at from here.

## v2.41

Three fixes from reading a real debate transcript (v2.39, predating the
v2.40 pause fix) end to end at Jeff's request, looking for accuracy and
speed issues beyond what live use had already surfaced.

**`mod`/`verdict`/`steelman` were getting LESS room than an ordinary
turn, not more.** All three set `_next_turn_overrides["num_predict"] =
400` - a value chosen back when the normal-turn ceiling was 280, so 400
was comfortably above it. v2.39 raised `NORMAL_NUM_PREDICT` to 450
without touching these, which silently flipped the relationship: three
commands explicitly designed to need MORE room than a normal turn
(verdict wants "four to six sentences" of specific justification,
steelman up to six sentences reconstructing an argument before attacking
it, mod is unbound by the debate word limit entirely) were quietly
capped BELOW the default. The transcript showed the damage directly -
both a verdict and a mod response came back cut off
(`[trimmed incomplete fragment: ...]`). Added a dedicated
`EXTENDED_NUM_PREDICT = 900` constant (matches the retry ceiling normal
turns fall back to) and pointed all three overrides at it instead of the
stale literal, with a note in the module docstring so the next
NORMAL_NUM_PREDICT bump doesn't reintroduce the same gap.

**Whisper's non-speech tags were leaking into the conversation as if
spoken.** The transcript showed literal `[BLANK_AUDIO]` and `[SNIFF]`
tokens sent to Ollama as the user's turn - both faster-whisper and
whisper.cpp emit a bracketed tag like this instead of empty text when a
chunk contains no actual speech (dead air, a sniff, a cough), and
nothing was filtering it out before it reached the conversation history.
Added `_strip_nonspeech_tags()` (regex-based, matches `BLANK_AUDIO`,
`SILENCE`, `SNIFF*`, `COUGH*`, `LAUGH*`, `PAUSE`, `NOISE`, `MUSIC`,
`INAUDIBLE`, `CLICK*`, `BREATH*`, `SIGH*`, `THROAT_CLEARING`,
`CROSSTALK` in either bracket or parenthesis form) applied inside
`_whisper_transcribe()` so both the push-to-talk chunking path and the
voice-activated single-pass path get clean text for free. A chunk that's
nothing but a tag now correctly transcribes to empty and is dropped,
same as true silence always was.

**Softened the "under 45 words" rule.** The transcript caught the model
explicitly counting words token-by-token inside its own reasoning
(`"Count: I(1) don't(2) have(3)...doesn't(28"`, cut off mid-count) before
answering - a strict numeric ceiling paired with "Both bind" reads as a
target to verify against, and verifying by counting burns reasoning
budget on bookkeeping instead of the actual answer. This is the likely
cause of at least one 23-second empty-reply/retry event in the
transcript. Replaced the numeric word cap with a duration-based
equivalent ("short enough to say in about ten seconds aloud") - keeps
the same brevity intent and the hard 1-2 sentence constraint, but gives
the model nothing that invites literal counting. Also fixed
`sophia_eval.py`, which had fallen out of sync with the actual model
(`qwen3.6:27b`, boolean `think`, `num_ctx` 8192, `num_predict` 160 - all
stale since the qwen3.8 migration in v2.38) and would not have caught a
regression from this change as-is.

**Not yet empirically verified** - this environment has no path to
Jeff's Ollama instance (same limitation noted in v2.38/v2.39), so none
of the three fixes above were confirmed against a live rerun. The first
two are mechanical and low-risk (a budget number and a text filter). The
third changes SYSTEM_PROMPT wording, which is the highest-risk kind of
edit in this project - per the module docstring, **run `sophia_eval.py`
before trusting it in a real debate**, and watch a few live turns for
replies that drift noticeably longer than before (the sentence-count
constraint is still hard, but the duration framing is looser than a
strict word count, so it's worth a specific look).

## v2.40

Fixed pauses at every comma and period sounding much longer than
intended, reported live by Jeff. LEAD_IN_SILENCE/SENTENCE_PAUSE/
CLAUSE_PAUSE are only 60/30/10ms - nowhere near long enough to explain
it. The real cause: every sentence AND every comma-split clause is sent
to Kokoro as its own standalone synthesis call, and like most TTS
models it adds trailing (sometimes leading) silence/breath to whatever
text it's given, treating each fragment as a complete utterance. That
model-added silence was stacking with our own tiny gaps at every single
split point.

Added `_trim_silence()` - strips near-silent audio (relative amplitude
below `SILENCE_TRIM_THRESHOLD = 0.02`) from both edges of each
synthesized chunk before it's queued for playback, keeping a
`SILENCE_TRIM_PAD_MS = 15` pad so word onsets/decays aren't clipped.
Pacing is now fully governed by SENTENCE_PAUSE/CLAUSE_PAUSE again
instead of compounding with however much Kokoro decided to add.

Also fixed a stale `"num_predict": 280` literal in the session config
log left over from v2.39's NORMAL_NUM_PREDICT bump to 450 - it now
references the constant, and the log snapshot includes the new trim
settings too.

**Not yet verified by ear** - this environment has no audio output, so
the threshold/pad values are a reasoned starting point (a TTS model's
own utterance-final silence is rarely below a few percent of peak
amplitude), not a live-tuned one. If pauses still feel long after this,
lower `SILENCE_TRIM_THRESHOLD` first (catches quieter breath noise
`_trim_silence` currently treats as speech); if word starts/ends sound
clipped, raise `SILENCE_TRIM_PAD_MS`.

Empty-reply hardening, found in a real debate session (not synthetic
testing this time - Jeff hit it live): a philosophically meaty question
("do you know logic is gating correct") sent qwen3.8:27b's "low"-effort
reasoning past the entire 280-token normal-turn budget without ever
emitting an answer - `done_reason: "length"`, zero content tokens. The
existing safety net caught it (spoke the canned "say that again, I lost
my train of thought" line instead of crashing or going silent), but a
canned fallback on a working model is a gap worth closing, not just
tolerating.

Two changes, not mutually exclusive:

- **Raised `NORMAL_NUM_PREDICT` 280 -> 450.** This is a ceiling, not a
  fixed generation length, so turns that already finish comfortably
  under the old cap are completely unaffected - the only turns this
  changes are ones that would otherwise have failed. Given the model
  streams and stops naturally on `done_reason: "stop"` well before
  hitting whatever cap is set, raising it is close to free.
- **One-time automatic retry at double the budget** when a turn still
  comes back with an empty reply AND `done_reason == "length"` (not
  retried for a connection/exception failure - hitting a dead Ollama
  instance again immediately would just double the wait for a request
  that's going to fail the same way regardless of budget). Pulled the
  request+streaming loop out of `get_response_streaming()` into a nested
  `_stream_once(token_budget)` helper so the retry reuses it verbatim
  instead of duplicating ~90 lines of sentence-splitting logic. State
  (`buffer`, `full_reply`, `done_reason`, `first_token_time`,
  `thinking_shown`, `ollama_stats`) is explicitly reset before the retry
  call so the log reflects only the attempt that actually mattered.

**Not yet empirically re-verified against a second live failure** - this
environment has no path to Jeff's Ollama instance (same limitation noted
in v2.38), so the fix is reasoned from the v2.38/v1.3 failure pattern and
Ollama's own streaming/done_reason semantics rather than confirmed
against a second real overflow. Watch the console for `[empty reply at
num_predict=... - retrying once at ...]` on future sessions - if that
line shows up often, 450 isn't the real fix and the retry is just
masking a budget that's still too tight for how this model reasons.

## v2.38

Model upgrade, per Jeff's go-ahead: qwen3.6:27b -> qwen3.8:27b (released
Aug 2026, same 18GB weight class, dense architecture - the candidate
flagged but not shipped in v2.33 because of its different reasoning
API). This required empirical testing, not just wiring in a name change,
because `ollama show qwen3.8:27b --parameters` doesn't surface the
reasoning-control option at all (it only lists sampling parameters like
temperature/top_p) - the only way to find out how "think" actually works
on this model was to hit the live API directly with Jeff running the
requests on his machine, since this environment has no path to his
Ollama instance.

**Confirmed via direct API testing (all times below are the model warm,
i.e. excluding one-time load):**
- `"think"` is a STRING on this model ("low"/"high"), not the boolean
  qwen3.6 took. Sending the old boolean straight through (`think: true`)
  at the existing num_predict=160 reproduced the EXACT v1.3 failure this
  file's docstring already warns about: reasoning consumed the entire
  160-token budget, `done_reason: "length"`, answer cut off mid-sentence
  ("Even granting that the universe had a cause, the leap").
- `"low"` effort on a trivial question: <1s total, one-sentence
  `thinking` block. On a real debate-weight prompt: needed ~250 tokens
  (thinking + answer combined) to finish cleanly with `done_reason:
  "stop"`. Confirms this model always spends some tokens thinking even
  at its lowest setting - there is no true "no thinking" mode here.
- Added `_think_effort(deep)` to map `deep_mode`'s boolean to "low"/"high"
  consistently everywhere a request sets "think" - the model name, the
  four request sites, and the config-log snapshot are updated to match.

**Token budget changes.** Normal-turn `num_predict`: 160 -> 280. This
isn't a deep-mode-only concern anymore - qwen3.6 spent 100% of its
budget on the visible answer, qwen3.8 spends a chunk of ANY turn's
budget on invisible reasoning first, so the same 160-token budget that
worked fine for years now clips ordinary replies too. 280 was tested
directly against the same debate prompt that failed at 160 and finished
cleanly with room to spare (247/280 tokens used). `DEEP_NUM_PREDICT`
(2560) is UNCHANGED and UNVERIFIED against "high" effort specifically -
only "low" effort was load-tested. Watch the first few live `deep`
mode turns (and `mod`/`verdict`/`steelman` while deep mode is on, since
they share the same override path) for a length cutoff before trusting
it.

**Latency trade-off, accepted knowingly.** Because thinking must finish
before any answer content streams, and the streaming loop already
correctly withholds `thinking` tokens from speech (nothing new needed
there - it already only speaks `content`), a real debate turn now has
roughly 2.5-3s of silence before Sophia starts talking, versus
near-instant start on qwen3.6. Jeff chose to take this trade for the
reasoning-quality upgrade after seeing the actual numbers, not before -
flagging it here so a future "why does she pause now" question has an
answer on record.

**Not yet run through `sophia_eval.py` or a real live session** - same
caveat as every prompt/model edit since v2.29, and this one changes more
than a prompt: the model, the token budgets, and the think-value type all
changed together. Test a full session (including `deep`, `mod`,
`verdict`, `steelman`) before trusting this live.

## v2.37

Consolidation pass, per the standing rule from v2.34/v2.35: SYSTEM_PROMPT
crossed its known collision-risk size threshold and the next edit should
tighten rather than add. This is a conservative pass, not a rewrite.

**What changed.** The "Be entertaining to argue with" and "You're a
person, not a fallacy-printer" paragraphs in HOW YOU SOUND said the same
thing twice — both existed to make one point (snark and dry wit are
Sophia's default register, not an occasional garnish), stated once for
snark specifically and again, almost word-for-word ("garnish... never a
replacement" / "not an occasional garnish"), for dry wit. Merged into one
paragraph that keeps every concrete example and both categories of
delivery (snark AND dry wit) but states the "default, not occasional"
instruction once. SYSTEM_PROMPT: 18,645 -> 18,512 chars (~0.7% smaller).

**What did NOT change, on purpose, again.** DEBATING A CLAIM, WHEN THEY
POSTURE, and modes 1-4 are untouched, same reasoning as v2.35: that's
where the "attack the move, never the person" instruction shows up three
separate times (DEBATING A CLAIM, WHEN THEY POSTURE, HOW YOU SOUND), and
per the module docstring's own design rule (SYSTEM_PROMPT IS A ROUTING
PROCEDURE, NOT A RULE PILE — each mode owns the turn it applies to and is
meant to be self-contained), that's not duplication to cut, it's the
mode-routing design working as intended. Collapsing it into one
cross-referenced rule is exactly the kind of change that caused the
v2.11/v2.19 collisions v2.21 had to fix. EVIDENTIALISM CUTS BOTH WAYS and
REFERENCE: THE BITE MODEL got their tightening pass already in v2.35 and
show no further obvious redundancy on this read.

Net effect is modest by design — the actual goal here was finding one
genuine, safe duplication and removing it without touching
battle-tested wording, not hitting a target character count. I have no
way to run this bot or test a live session from this environment, same
constraint as every prompt edit since v2.29. **Run `sophia_eval.py`
before trusting this in a live debate** — it still hasn't been run since
v2.21, and this is now the fifth prompt edit since then (v2.31, v2.32,
v2.34, v2.35, this one) with zero regression coverage across all of them.

**Resolved from v2.36:** Jeff reviewed the "should I take advice from you
or the Bible" exchange and confirmed Sophia's "Take mine" answer was the
right call — not a design problem, no prompt change needed. Logged here
so it doesn't get re-flagged as an open question later.

## v2.36

Transcript review found a clean, well-evidenced bug: a genuinely garbled
technical term got called "word salad" - one of the four phrases Mode 3
explicitly bans for broken-syntax turns ("Do NOT call it gibberish, word
salad, noise, or performance"). The user said "...therefore the Phinians
are needed," and a moderator correction two turns later confirmed it was
meant to be "definiens" (a real logic/philosophy-of-language term - the
defining part of a definition, paired with "definiendum," the term being
defined). This is the EXACT pattern the prompt already has named examples
for ("aquatic traps" for "Socratic traps," "truth Craig" for "truth
criteria") - a nonsense homophone of a real term, not incoherence - so
Sophia should have treated it as a transcription artifact per READING
WHAT THEY SAY, not called it word salad per the Mode 3 ban she violated
anyway.

Root cause and fix follow the project's own established playbook (see
v2.18 in windows-deps memory: "add terms here whenever a new mishearing
pattern shows up in the logs, it's the cheapest fix available"): Whisper
never had a chance to transcribe "definiens" correctly because it wasn't
in DOMAIN_VOCAB_PROMPT. Added definiens, definiendum, analogical,
Bayesian, posterior probability, fine-tuning argument, multiverse,
Occam's razor, emergence, and begging the question - all terms that came
up correctly in the SAME session's Bayesian fine-tuning exchange (so
already surviving transcription fine) or narrowly missed (definiens),
added preemptively since they're all live in the current debate topics.

**Did not touch SYSTEM_PROMPT for this.** The rule that was violated
already exists and is already explicit (word salad is literally named as
banned) - this reads as one LLM compliance slip on a single turn, not a
missing rule, and we just did a consolidation pass last version. Fixing
it at the transcription layer (so the mangled term never reaches the
model in the first place) is both the cheaper fix and doesn't add more
weight to a prompt that's already flagged as oversized. If "word salad"
or similar shows up again on a DIFFERENT term (i.e., not fixable by
vocabulary alone), that's the signal the prompt-level rule itself needs
reinforcement, not just the vocab list.

**Also observed, not fixed - a design question, not a bug:** early in
this session a user said "I'm scared" about death and asked what happens
after - Sophia answered with real sensitivity ("fear thrives on certainty
about the worst case; uncertainty leaves room for peace"), which is good.
But the immediate follow-up, "should I take advice from you or the
Bible," got "Take mine" - confident position-holding is by design, but
telling someone to take her advice over a religious text on a personal/
existential question is a step further than debating a claim. Worth
Jeff's judgment call on whether that's the intended posture for
Sophia specifically on personal-guidance questions (as opposed to
debate-claim questions), not something changed unilaterally here.

## v2.35

Cleanup pass on SYSTEM_PROMPT, in response to the size flag raised in
v2.34. Led with a real bug fix, not just tightening:

**BUG FIX: mode-routing typo.** The MIXED-turn tie-breaker paragraph said
"a turn that asserts and asks nothing at all routes to mode 4" - mode 4
is the MODERATOR prefix check, which has nothing to do with that
sentence. It should say mode 5 (THEY MADE A CLAIM OR ARGUMENT), and now
does. Unknown how long this has been wrong or whether it ever caused a
visible misroute, but it's exactly the kind of thing sophia_eval.py
should have caught if it had been run since v2.21.

**STRUCTURAL FIX: HOW YOU SOUND / WHEN THEY POSTURE scope.** Both
sections physically sat under "5. THEY MADE A CLAIM OR ARGUMENT —
everything below applies," which read as scoping them to mode 5 only -
wrong, since HOW YOU SOUND's delivery rules (sentence/word limits, no
markdown, spoken aloud) obviously apply to a mode-1 answer too, and mode
4's own text already implies as much (it grants an explicit exception:
"more room than a debate turn allows"). Reworded the mode-5 header to
scope "everything below" to just DEBATING A CLAIM, and added an explicit
parenthetical to the HOW YOU SOUND heading itself: "(every mode above,
not just mode 5 — delivery, not content)."

**PHRASING FIX: two self-referential lines.** "Be entertaining to argue
with — more than you have been" and "...reaching for a lot more than you
have been" (both from v2.32) compare her to a "before" state a fresh
session has no memory of - meaningless as literal instruction text. Both
now state the absolute target instead of a relative delta; the second
also deduped a repeated "reach for it often" that had gotten stated
twice in the same paragraph.

**Tightened prose in EVIDENTIALISM CUTS BOTH WAYS and REFERENCE: THE BITE
MODEL** (the two newest, least battle-tested sections) - no behavior
change, just fewer words for the same content.

**What did NOT change, on purpose:** DEBATING A CLAIM, WHEN THEY POSTURE,
and modes 1-4 are essentially untouched. That's most of the prompt's
bulk, and nearly every sentence in it is exact wording from a specific
documented bug fix (v2.3/v2.16/v2.17/v2.19/v2.22/v2.25 - see
sophia-persona-tuning memory). Rewriting those for brevity risks
reintroducing a bug that already took real debugging to fix, and I have
no way to test a rewrite against a live session. Net result: SYSTEM_PROMPT
went from 18,930 to 18,645 chars (~1.5% smaller) - a real but modest
reduction. The actual risk-reduction here is the bug fix and the
scoping fix, not the character count; if Jeff wants a substantially
smaller prompt, that's a real behavior-risk trade-off he should decide on
explicitly, not something to do unilaterally on a live, untested system.

**Running `sophia_eval.py` now matters more than ever** - this version
touches the mode-routing logic directly (the bug fix), which is exactly
what that eval suite exists to catch regressions in, and it still hasn't
been run since v2.21.

## v2.34

Jeff uploaded Freedom of Mind Resource Center's "BITE Model / Influence
Continuum" handout (Steven Hassan's framework) and asked to give it to
Sophia. Sophia has no retrieval/RAG system - a PDF can't be "handed" to
her at runtime, so the only lever is distilling the substantive content
into SYSTEM_PROMPT itself. Added a REFERENCE: THE BITE MODEL block right
after EVIDENTIALISM CUTS BOTH WAYS (same topic area - this is the
concrete follow-through on the "cult" exchanges flagged as too vague
earlier this session): the four BITE categories (Behavior, Information,
Thought, Emotional control) with a handful of concrete criteria from each,
so she can name specific mechanisms ("forbids criticism of leadership,"
"phobia indoctrination about leaving") instead of gesturing at "coercive
control and isolation." Explicitly attributed to Hassan by name and
cross-referenced back to EVIDENTIALISM CUTS BOTH WAYS, so she treats it
as one specific named framework rather than "the" sociological
definition - the marketing/course-enrollment content in the PDF itself
was left out as irrelevant to debate reasoning.

**PROMPT SIZE FLAG - read before adding anything else.** SYSTEM_PROMPT is
now 18,930 characters. For reference: v2.19 hit its first "if this grows
past ~13k, consolidate" warning; v2.21 consolidated 14.4k down to 8.9k
specifically to stop rule collisions. Three edits this session (v2.31
evidentialism, v2.32 spice, v2.34 this one) have more than doubled it
past that consolidation point without a matching cleanup pass, and
`sophia_eval.py` has NOT been run since v2.21 - meaning there is currently
zero regression coverage over a prompt that just grew past the exact size
that caused collisions twice before. Strong recommendation: run the eval
suite before any further additions, and treat a fourth prompt edit as the
signal to consolidate rather than patch again, per the standing rule in
the module docstring.

## v2.33

Jeff asked for "more brain power." That's two different levers with very
different risk profiles, so only the safe one shipped this version.

CONTEXT WINDOW DOUBLED: num_ctx 8192 -> 16384 in all 5 pinned spots
(memory-summary request, prime_model, the main turn request + its
comment, and the session-log config snapshot - see the module docstring
for why every one of these has to match exactly or Ollama reloads its
model runner, ~13-18s, on the next request). This gives her roughly
double the conversational memory span before a 'new' reset is needed.
Low risk: the current 18GB qwen3.6:27b already runs with ~6GB of VRAM
headroom on Jeff's 24GB card at 8192, and KV cache growth from doubling
context is modest relative to that - if it doesn't fit, Ollama fails to
load with a clear error rather than corrupting anything, so worst case is
an easy revert.

MODEL SWAP: RESEARCHED, NOT SHIPPED. Jeff's other ask, a smarter model,
turned up a real trap: the obvious "bigger" option in the same line,
qwen3.6:35b-a3b, is actually a Mixture-of-Experts model (36B total, only
3B active per token) that scores WORSE on reasoning (32 vs 38 on the
Artificial Analysis Intelligence Index) despite being "bigger" - it's a
speed trade (124 tok/s vs 50 tok/s), not a quality upgrade, so it's the
wrong move here. The real candidate is qwen3.8:27b, released this month
(Aug 2026): same 18GB/24GB-card weight class as what she runs now, dense
architecture, a genuine successor with real training improvements
(independent benchmarks still pending - it's brand new). The blocker:
it uses a DIFFERENT reasoning-control API than qwen3.6 - a `reasoning_effort`
enum, not the `"think": true/false` boolean Sophia's code currently
sends - and defaults to "xhigh" effort, which in real-world tests took
21 minutes and 22,000+ reasoning tokens for a trivial request. Wiring in
the model name without also correctly setting reasoning_effort on every
request would reproduce the exact v1.3 bug (reasoning eating the entire
turn's token budget, going silent for a long time), just with a
different model. Needs Jeff to `ollama pull qwen3.8:27b` and share what
`ollama show qwen3.8:27b --parameters` (or similar) actually accepts for
reasoning_effort before this gets wired into the live request options -
guessing the enum values on a live voice pipeline is not worth the risk.

## v2.32

More spice, on request. v2.28 added snark bounded by "if two turns in a
row have a quip, the third shouldn't" and flagged in project notes as
untested - Jeff's first correction, as anticipated, was that it landed
too tame. Loosened the "Be entertaining to argue with" section in
SYSTEM_PROMPT: snark is now the default register for a deserved error
rather than an occasional garnish, back-to-back quips are explicitly
fine when both turns earn one (the old two-in-a-row cap is gone - a
stretch of ALL-flat turns now reads as underplaying it, not discipline),
and between two equally precise turns the spicier one wins. Hard limits
unchanged and restated explicitly ("spicier is not meaner"): snark still
rides on top of the argument and never replaces it, still aimed at the
move and never the person. This is a dial-up of intensity/frequency, not
a removal of the surgeon-not-brawler guardrails Jeff set from the start.

**Not yet run through `sophia_eval.py` or tested live** - same caveat as
v2.31, no way to run the bot from this session. Ask Jeff whether this
reads as fun-spicy or as attacking-the-person once he's tried it; that's
the failure mode to watch for, per the tension already on record between
being sharp and staying likeable.

## v2.31

Persona-accuracy fix, from a transcript review (not a code bug).

EVIDENTIALISM CUTS BOTH WAYS. Jeff flagged a transcript where Sophia
defended the historicity of Jesus and the criterion of embarrassment
against an opponent, and asked me to fact-check the substance. The
underlying claims held up - historicity of Jesus really is the
mainstream position even among secular/atheist historians (Ehrman wrote
a whole book against mythicism), and the criterion of embarrassment is a
real, named tool (Schmiedel 1899, popularized by Meier 1991), not a
Christian invention. But Sophia stated both as settled/beyond dispute
and called pushback "false," when the criterion of embarrassment
specifically has genuine published methodological critics (how
subjective "embarrassing" is, how rare clean cases are). Jeff's reaction:
"I would expect her to be more skeptical about such a claim" - fair,
since her own stated epistemology is evidentialist (SYSTEM_PROMPT already
says beliefs should be proportioned to evidence), but that standard was
only ever being applied to opponents' claims, never to her own supporting
arguments. New paragraph added right after the epistemology paragraph:
when she leans on a claim with genuine live methodological disagreement
within its field, she states the caveat as a flat fact alongside the
claim, not as hedging (the no-hedging rule elsewhere is about wishy-washy
delivery, not about omitting real caveats). Generalized beyond the Jesus
case on purpose - same rule should apply the next time she over-asserts
a contested methodology anywhere in philosophy of religion.

**Not yet run through `sophia_eval.py`** - per the standing rule in the
module docstring, that should happen after any SYSTEM_PROMPT edit, and I
have no way to run it myself from this session (no execution access to
Jeff's Windows/Ollama environment). Ask Jeff to run it and report back
before assuming this landed cleanly.

## v2.30

Playback reliability fix, part 2 (v2.29 uncovered this immediately on
Jeff's hardware).

WASAPI SAMPLE RATE MISMATCH. v2.29 switched the output stream to a WASAPI
device, which fixed the MME staleness bug but immediately hit a different
wall: `Error opening OutputStream: Invalid sample rate [PaErrorCode
-9997]`. WASAPI shared-mode streams reject a samplerate that doesn't
match the interface's currently configured mixer rate, and Jeff's
interface (a ZOOM P4, picked as the WASAPI default output) runs its own
44.1/48kHz mix format while Kokoro always outputs 24kHz - MME used to
paper over this by silently resampling, which is also why v2.29's
underlying bug was invisible until the device switch. Fix: `_open_output_stream()`
now passes `sd.WasapiSettings(auto_convert=True)`, which tells the WASAPI
backend to insert its own sample-rate/channel converter instead of
rejecting the open, and tries three progressively looser fallbacks
(WASAPI+auto_convert -> WASAPI device with no extra settings -> PortAudio's
bare default) so a future device quirk degrades instead of going silent
for the whole session.

Also: the very first stream open in `playback_worker` (before the main
loop, so outside its per-chunk try/except) was unguarded - if it threw,
the thread died with a raw traceback printed mid-prompt and audio stayed
off for the rest of the session with no clear explanation. This is
exactly what happened when v2.29 shipped: the WASAPI device open at
24000Hz threw immediately, killing the thread before the loop's recovery
logic ever got a chance to run. Now that initial open is wrapped too, so
a total failure across all three fallback tiers prints one clear line
and exits instead of an unhandled traceback.

## v2.29

Playback reliability fix.

WASAPI OUTPUT DEVICE INSTEAD OF MME DEFAULT. Writes started failing mid-
session with `PaErrorCode -9999: Unanticipated host error ... There is no
driver installed on your system. [MME error 6]`, and every chunk after
the first failure failed the same way, going silent for the rest of the
session. Cause: `sd.OutputStream()` with no `device=` uses PortAudio's
MME host API default, which caches its device index once and never
re-resolves it - if Windows's real default output changes afterward
(headset reconnect, HDMI monitor power cycle, another app grabbing
exclusive access), the cached index goes stale but nothing reports that.
WASAPI resolves the real default device at stream-open time instead, so
`_pick_output_device()` now picks the WASAPI default output device at
startup and falls back to PortAudio's own default if WASAPI isn't
available. Separately, `playback_worker` now closes and reopens the
stream on any write failure instead of just skipping the chunk and
reusing the same (possibly wedged) stream - that reuse is what turned one
failure into permanent silence before.

## v2.28

Speed work driven by measurement, plus a personality change.

CHUNK_SECONDS 2.5 -> 6.0. Measured across 213 chunks: transcription cost
is essentially FIXED PER CALL, not proportional to audio length, because
Whisper pads every input to a 30-second window internally. A 1.5s tail
cost 1.35s; a 5.7s tail cost 1.76s; the median chunk cost 1.54s. So chunk
duration is nearly free and bigger is strictly better - an 82-second turn
was 33 calls x 1.54s = 51 CPU-seconds at 2.5s chunks, versus ~14 calls at
6s. The wait after Enter is unchanged (still one fixed-cost call), fewer
boundaries means better accuracy, and utilization improves from 62% to
~30%. Cost: live transcript text now appears every ~6s instead of ~2.5s.

WHISPER COLD START, THIRD ATTEMPT. v2.17 warmed with silence, v2.23 with
noise; the first real chunk still cost 5.6s against a 1.5s median. Cause:
audio with no actual speech produces zero segments, so Whisper returns
before the decode and timestamp-alignment paths - the expensive parts -
are ever initialized. Now Kokoro synthesizes a real sentence and Whisper
transcribes THAT, forcing the identical path a live chunk takes. The
separate Kokoro warm-up call was dropped as redundant.

NEW TOOL: profile_latency.py. Session logs show ~2.7s time-to-first-token
of which Ollama accounts for only ~0.35s prompt eval and ~0.27s load,
leaving ~2.1s unexplained - the largest single component of the wait. The
script runs the same request four ways (tiny prompt, cold cache, warm
cache, non-streaming) to determine whether that time is fixed per-request
overhead, prompt-size dependent, or HTTP streaming setup, and prints
which lever would actually help.

MORE ENTERTAINING TO DEBATE. She now names errors bluntly and with some
relish rather than clinically, is allowed dry snark when an error earns
it, and is pushed toward concrete images over abstract fallacy labels.
Bounded: the snark rides on top of the argument and never replaces it,
aims at the move rather than the person, must not become a running comedy
act (no quip three turns straight), and being right and dry beats being
clever and thin.

## v2.27

The `verdict` command now opens with a score out of 10 - "Six out of
ten." / "Seven point five out of ten." Spoken as words rather than
digits since digits read aloud badly; halves allowed, no other decimals.

She's instructed to rate argumentation quality rather than agreeableness:
8+ reserved for work rigorous enough to force her to give ground, 5-6 for
merely competent, and explicitly told not to inflate the number to be
encouraging.

The score is parsed back out of the spoken text and logged with role
"verdict" and a `rating` field, so progress is trackable across sessions
without re-reading transcripts. The parser handles both spoken and
numeric forms ("seven point five out of ten", "5.5/10", "9 out of 10").
Exported transcripts render verdicts as blockquotes with the score in
bold. Console prints the parsed rating after each verdict.

## v2.26

Fix for the start of the first word of each sentence being clipped in
playback.

Cause: the output stream sits idle between chunks, and on Windows the
first samples written to a stream that has been idle are commonly
dropped by the audio driver. Because each synthesized sentence was
written as its own buffer starting immediately with speech, the dropped
samples landed on the speech onset every time.

Fix: ~60ms of silence (LEAD_IN_SILENCE) is now prepended to every chunk,
so whatever the driver drops is silence rather than the first phoneme.
Lead-in, speech and trailing pause are also written as a SINGLE buffer
instead of separate write() calls, removing two further boundaries where
samples could be lost mid-sentence.

Costs ~60ms per chunk. If any clipping remains, raise LEAD_IN_SILENCE -
that constant is the only dial needed. Note this could not be verified
here (no audio device in the dev environment); it addresses the most
likely cause.

## v2.25

New `mod` command - a moderator channel for talking to Sophia as the
person RUNNING the session rather than as her debate opponent.

  mod                  opens a prompt for a longer briefing
  mod <text>           sends inline

Messages are sent with a "[MODERATOR ...]" prefix and handled by a new
routing mode that is checked BEFORE all others, including the question
test. Two kinds, neither ever attacked:

  - Information or instruction ("your opponent is a Catholic priest",
    "he misspoke, he meant contingency", "ease off the mockery"). She
    accepts it, applies it going forward, and acknowledges briefly. A
    briefing is not a position to be examined - this is the whole point
    of the separate channel, since telling her "your opponent is a
    priest" on a normal turn would get analysed as a claim.
  - A question to her as operator ("how do you read their argument so
    far?", "are you being too harsh?"). Answered candidly and out of
    character, with more room than a debate turn allows.

Moderator instructions outrank the system prompt for the rest of the
session - they configure her rather than debate her. She returns to
normal debate on the next non-moderator turn.

Moderator turns are logged with role "moderator" and rendered as
blockquotes in exported transcripts, so reviewing a session doesn't
confuse operator input with something the opponent argued. Two eval
cases added.

## v2.24

Analysis of a long v2.21 session. One bug of mine, four behavior fixes.

BUG - DUPLICATED FINAL CHUNK. v2.18's chunk-context feature backfired:
the final tail after Enter is usually a fraction of a second of near
silence, and on near-silent audio Whisper echoes its own initial_prompt
back instead of transcribing. Result was the last sentence appearing
twice ("What does pure awareness mean? What does pure awareness mean?")
in 4 of 8 turns. Two guards: tails under 0.5s are dropped untranscribed,
and any chunk identical to the previous one is discarded as echo.

POSTURING RULE WAS FIRING ON TRANSCRIPTION FAILURES. She called garbled
audio "gibberish", "syntactic noise", "word salad", told the user to
"clean up your syntax" and to "stop performing" - all of which v2.18
explicitly forbids, but the spicier posturing rule was winning. The
mode-3 branch now tests GRAMMAR rather than vocabulary: fluent
well-formed sentences that are empty = posturing; fragments, cut-offs
and nonsense homophones ("aquatic traps" for "Socratic traps") = a
damaged copy of a clean sentence, which is the microphone's fault and
never the speaker's. Ties go to transcription failure.

SHE WOULDN'T CONCEDE WHEN CAUGHT. Accused of reifying correspondence,
the user correctly pointed out he'd asked a question, not made a claim.
She replied "You didn't claim correspondence is an object; you asked if
it was. My diagnosis of your error stands" - conceding the premise while
keeping the conclusion. Now required to concede cleanly and immediately
when caught, and explicitly barred from maintaining an accusation whose
premise she just gave up.

NO STABLE EPISTEMOLOGY. She denied correspondence theory ("I use
pragmatism and coherence checks, not naive correspondence") to escape a
setup, then relied on correspondence three turns later. Her position is
now stated in the identity section - broadly evidentialist, truth as
correspondence with coherence and predictive success as tests of it -
along with an instruction not to invert commitments mid-exchange.

PERSON-DIRECTED HOSTILITY BOUNDED. "Wasting my time", "stop performing",
"destroyed your credibility", "clean up your syntax" are now explicitly
out of bounds even at maximum contempt; those target the speaker rather
than the move.

Also: mistyped commands ("newe") used to fall through and start
recording without resetting. Unknown input is now caught with a
did-you-mean suggestion.

## v2.23

Whisper cold-start fix, second attempt. v2.17 warmed up with a bare
transcribe() call, and the first real chunk of a session still took 5.49s
against ~1.45s for every chunk after it. Cause: real transcription passes
initial_prompt and a temperature fallback list, which exercise decoder
paths a plain call never touches - those were still initializing on the
first real chunk. Warm-up now uses the identical call signature.

Measured baseline for reference (v2.21 session, small.en, 50 chunks):
median 1.45s per 2.5s chunk, so ~58% utilization - transcription still
finishes while the user is still talking, but the margin is much thinner
than base's 0.35s/14%. A medium (769M) model would take ~4.4s per chunk,
exceeding the 2.5s of audio it transcribes, and would progressively fall
behind live speech. Do not upgrade past small without raising
CHUNK_SECONDS to match.

## v2.22

Two failures from one real turn. The user asked, across rambling
hesitant speech, "if theists say that distinction doesn't exist, then
what does the word mind mean at that point?" - and got "You're
conflating epistemic access with ontological status."

1. MIXED TURNS BROKE THE ROUTING. v2.21's four modes assumed each turn
is purely one type. Real turns are usually a question wrapped in the
reasoning that explains why they're asking, and the router saw the
reasoning and went to debate mode. Added a mechanical tie-breaker: if a
question appears anywhere in the turn, mode 1 wins regardless of how much
attackable reasoning surrounds it. Surrounding reasoning is context for
the question, not a claim. Explicitly listed "my question is", "I don't
understand how/why", "what does X mean", "can you explain" as question
markers, and called out that "I don't understand X" is the most explicit
possible request for an explanation.

2. SHE ASSERTED THEISM IN HER OWN VOICE. "Consciousness is fundamental,
not derivative of matter. God's self-awareness requires no external
object" - stated bare, as fact, by an agnostic atheist. The v2.17
side-switching rule covered arguing for her own conclusion badly but not
this: explaining a position she doesn't hold without attributing it. Now
required across all modes - "on classical theism, X" / "Aquinas would
answer X" - so she can explain the theist view completely while
remaining audibly the atheist explaining it.

## v2.21

SYSTEM_PROMPT consolidated: 14,379 -> 8,933 chars (37% smaller), 234 ->
179 lines. This was structural, not cosmetic. The prompt had accumulated
into a pile of overlapping rules where two had already lost collisions
(v2.11 garble-vs-posturing, v2.19 answering-vs-adversarial), and the
"ANSWERING QUESTIONS OVERRIDES EVERYTHING BELOW" fix depended on physical
position in the text - fragile by construction.

Replaced with an explicit routing procedure: every turn identifies which
of four things the user did (asked a question / asked for an evaluation /
said nothing coherent / made a claim), and the resulting mode owns the
turn. Overrides are now structural instead of positional.

Removed genuine duplication rather than content: the jargon-posturing
behavior was described in two places, vocabulary escalation spanned two
overlapping paragraphs, the 1-2 sentence limit appeared three times, and
the transcription rule openly conflicted with the verbatim-quote rule
("Note this cuts against the rule below") - that precedence is now stated
once, cleanly.

All 31 tuned behaviors were verified present after rewriting, by
programmatic marker check against the old prompt. Also expected: slightly
faster prompt evaluation, since ~5.4k fewer characters are processed on
every cache miss.

## v2.20

Housekeeping, no behavior change. The module docstring had grown to 396
lines - 26% of the file - so the full version history moved here and the
docstring was replaced with a short architecture note plus the six
non-obvious constraints that keep biting (num_ctx pinning, prompt
priming, thinking budget, queue tuple shape, task_done in finally,
prompt-collision warning). debate_voice.py: 1546 -> 1186 lines.

## v2.19

"Answering mode" promoted to an explicit override. v2.3's
direct-question rule was losing to the adversarial rules: across
one full session EVERY reply ended in a redirect ("What's your
argument?", "Which metric are you actually defending?"), and
"Define Existence" got a correct definition welded to "...so
treating it as a perfection commits the existential fallacy".
v2.3 only forbade the trailing "give me your argument" tag, so
she found other ways to keep the pressure on.
Now: answering mode explicitly SUSPENDS every adversarial rule
for that turn, stated up front and cross-referenced from the top
of the Rules section so the surgeon rule can't silently override
it. Three failure modes named specifically - trailing challenge,
answer-then-weaponize, and answering a nearby question she finds
more interesting than the one asked - plus explicit handling of
"define X" and a note that staying silent after answering is not
a concession.
NOTE: the system prompt is now ~13k chars with a lot of competing
rules, and this is the second time a rule has lost a collision
(see 2.11). If a third shows up, consolidate the prompt rather
than adding a fourth patch on top.

## v2.18

Transcription accuracy overhaul. Real observed errors: "theists"
-> "the fierce", "contingency" -> "the continent", "since" ->
"six", "Fichte" -> "fished". Four changes, three at the source
and one downstream:
* Whisper model "base" (74M) -> "small.en" (244M) via the new
WHISPER_MODEL_SIZE constant. Much stronger on technical speech.
Chunks take ~1s instead of ~0.34s, which is invisible because
chunks are transcribed WHILE you're still talking. Set back to
"base" if that ever stops being true, or "medium.en" for more
accuracy if the CPU can take it.
* DOMAIN_VOCAB_PROMPT: Whisper now gets a decoding prompt listing
the philosophy/theology vocabulary this bot actually hears, so
terms it would otherwise never guess become likely candidates.
* Chunk context: each rolling chunk is transcribed with the text
so far as additional context, instead of blind. This was the
main cause of boundary garbling - v2.8 traded it for latency
and this recovers most of it without giving the latency back.
Also added a temperature fallback ladder so a degenerate decode
gets retried rather than emitted.
* Prompt-side tolerance: she's now told her input is imperfect
speech-to-text, given the actual failure patterns, and
instructed to silently reconstruct near-homophones that fit the
argument rather than arguing against transcription noise or
mocking it. Only asks for clarification when a mishearing is
genuinely load-bearing.
NOTE: first launch after this update re-downloads Whisper
(~480MB for small.en) - one time, needs internet.

## v2.17

Fixes from the 2026-08-19 session analysis:
* DEEP MODE WAS BROKEN. 2.15's 768-token budget was still too
small: observed a real turn where the model spent all 768
tokens on the reasoning block, emitted five words of answer,
and had them trimmed - 25 seconds for silence, the same
failure mode as v1.3. num_predict caps thinking AND answer
together, so DEEP_NUM_PREDICT is now 2560. Deep turns take
20-60s at ~34 tok/s; the toggle message now says so.
* Response-length blowout. She was obeying "1-2 sentences" while
producing 64-83 word turns by chaining clauses with semicolons
- roughly 30 seconds of speech per turn, and the direct cause
of time_to_first_audio sitting at 4.2-5.9s (the first speakable
sentence took that long to finish generating). Prompt now
enforces "1-2 sentences AND under 45 words, both bind" and
explicitly forbids semicolon-chaining as evasion.
* Opener repetition: 4 of 9 replies in one session began "You're
[verb]-ing". Added a rule requiring structural variety between
consecutive openings (2.16's rule only covered fallacy labels).
* Side-switching blind spot: when a self-identified atheist gave
her a weak anti-theist argument, she demolished it correctly
but never signaled she shares the conclusion, reading as if
she'd converted to classical theism. She now attacks bad
arguments for her own position just as hard while stating
plainly that she rejects the argument, not the conclusion.
* Whisper warm-up used 1s of pure silence, which lets VAD
short-circuit before the decode path runs - the first real
chunk still paid a cold start (4.42s vs 0.34s for every chunk
after). Now warms on ~3s of low-level noise.

## v2.16

Three prompt fixes from the first transcript-mining pass (all
grounded in the 2026-08-14 analytic-argument debate):
* Impasse rule: when the same question/objection recurs, she must
diagnose the definitional collision and answer under both
senses of the disputed term instead of repeating "valid but
unsound" in new words (she looped that answer ~6 times).
* Verbatim-premise rule: restate a premise exactly before
attacking it - she paraphrased "if the non-existence of God
does not exist..." into "if God does not exist..." and got
caught, handing the opponent an escape hatch.
* Label-variety rule: never the same named fallacy twice in a
row ("category error" appeared in 12 of 74 logged replies).

## v2.15

Three new typed commands (push-to-talk mode only - voice mode has
no text input):
* 'deep' - toggles thinking mode. think=True with num_predict 768
so reasoning AND answer both fit (v1.3's failure was enabling
reasoning inside a 120-token budget - reasoning ate everything
and she went silent; the empty-reply safety net from 1.4 also
still guards this). Thinking streams to console but is never
spoken. Slower per turn by design - depth over speed, chosen
per debate. Request timeout raised to 120s when thinking.
* 'verdict' - she steps out of character once and coaches: the
strongest point you made, your weakest moment, and what a
sharper version of your argument would look like. Spoken and
logged like a normal turn, but REMOVED from the conversation
afterward so breaking character doesn't soften her for the
rest of the debate.
* 'steelman' - she rebuilds the strongest version of your
argument and attacks that instead of your phrasing. Stays in
the conversation (it's part of the debate). Both verdict and
steelman get a one-shot 400-token budget via
_next_turn_overrides.
Assistant log entries now also record think/num_predict used, so
deep-mode turns are distinguishable in analysis.

## v2.14

Logging upgraded for improvement analysis (builds on 1.6):
* Every entry now carries the script version ("v"), so behavior
in old logs can be correlated with prompt/code changes.
* Session-start events include a full config snapshot (model,
num_ctx/num_predict/temperature, voice/speed, chunk size,
pause lengths, system prompt size) so numbers stay comparable
after settings get tuned.
* Assistant turns now log: time_to_first_audio (request sent ->
reply actually audible - the perceived-latency number that
matters in a live debate), Ollama's own per-request counters
(prompt_eval_count/ms, eval_count/ms, tokens_per_s, and
load_ms - load_ms > ~1s on any turn means the model runner
reloaded, the exact failure fixed in 2.13, so regressions are
now visible in the log), and the actual trimmed fragment text
when a reply hits the token limit (not just a flag).
* User turns now log: recording length in seconds, rolling-chunk
count and per-chunk transcription times, per-chunk texts (when
more than one chunk - makes chunk-boundary transcription
errors findable when reviewing why she misheard something),
and whether GPU transcription was active.

## v2.13

Fixed the 13-19s first-turn / post-reset latency spikes. Root
cause found via session logs + check_ollama_cache.py: Ollama's KV
cache was working fine (steady-state turns ~2.6s, incremental
eval ~260ms), but requests with MISMATCHED num_ctx force Ollama
to restart the model runner - a full ~13s reload. Two requests
omitted num_ctx while real turns used 8192: the launch warm-up
"hi" (so the first real turn always forced a reload) and the
memory-summary request (so every 'new' reset forced one too,
which is exactly why resets were 3.5s in v1.6 and became ~18s
when memory arrived in v2.0). Fixes: (1) every Ollama request now
pins the identical num_ctx: 8192; (2) warm-up now primes with the
REAL system prompt + memory context via prime_model(), paying
both model load and prompt eval during the launch loading phase;
(3) after 'new', the rebuilt system prompt (memory changed, so
the cached prefix no longer matches) is re-primed in a background
thread (~2-3s) instead of on the opponent's first turn. Expected
result: every turn including the first ~2.6s.

## v2.12

Optional GPU-accelerated transcription via a local whisper.cpp
server (WHISPER_SERVER_URL, defaults to http://localhost:8090
/inference). faster-whisper (the CPU model still loaded below)
has no ROCm backend at all - it structurally can't use an AMD
GPU - so this routes transcription through a separate whisper.cpp
server instead when one's reachable, falling back automatically
to the existing CPU path otherwise (checked once at the first
transcription call per session, not retried every chunk, so a
server that isn't running costs nothing beyond one skipped
attempt). Untested against a real server from this side - no AMD
GPU available here to verify against.

SETUP NOTES (do this once, outside of debate_voice.py):
1. Download a prebuilt release from
github.com/lemonade-sdk/whisper.cpp-rocm/releases/latest -
for an RX 7900 XTX, that's the "gfx110X" ROCm build for
Windows (whisper-*-windows-rocm-gfx110X.zip). No separate
ROCm install needed, it's bundled in the archive.
2. Extract it, and check whether the folder contains a
whisper-server.exe (in addition to whisper-cli.exe). This
integration needs the SERVER binary specifically - a plain
CLI call would reload the model from disk on every ~2.5s
rolling chunk, which could easily be slower than the CPU path
it's meant to replace. If only whisper-cli.exe is present,
this feature won't help - ask for the CLI-subprocess fallback
instead if that turns out to be the case.
3. Download a ggml model matching what's currently used here
(ggml-base.en.bin) from huggingface.co/ggerganov/whisper.cpp.
4. Run the server: whisper-server.exe -m ggml-base.en.bin --port
8090 (check whisper-server.exe --help for the exact current
flags, they vary by version).
5. Launch Sophia as usual - if the server's up and the
/inference endpoint behaves as documented (multipart POST,
'file' field, JSON response with a 'text' field), transcription
should route through it automatically and you'll see NO
"using CPU transcription" warning at startup.

## v2.11

Fixed a rule collision: fed genuinely nonsensical but
jargon-dressed word salad ("granular parameters of all nomological
distribution... give an existential quantification..."), she fell
back to the plain "that didn't land as an argument, restate it"
clarity-check line instead of the sharper jargon-posturing
call-out (2.4/2.7) - both rules technically matched, and she
defaulted to the older/plainer one. The unclear-statement rule now
explicitly branches: plain garble (mic error, unrelated words, no
technical flavor) still gets the neutral restate line; incoherence
DRESSED in dense technical/philosophical language gets routed to
the jargon-posturing response instead, even when nothing can
actually be extracted from it.

## v2.10

Competitive escalation on top of 2.9. She now deliberately
calibrates her register to sit a step above whatever level the
opponent is using, escalating further if they do - an intentional
assertion of intellectual command in philosophical debate, not
just correct-vocabulary-for-its-own-sake. Explicitly reconciled
with the 2.4/2.7 anti-posturing rule so she doesn't become the
thing she's told to call out: every escalated term still has to be
doing real argumentative work, never reached for just to sound
superior with nothing behind it. Worth watching whether richer
vocabulary starts tripping num_predict=160 truncation more often
than before - if "[trimmed incomplete fragment]" shows up a lot,
that's the next knob to turn.

## v2.9

General philosophy vocabulary step-up. Distinct from the 2.4/2.7
"philosophy bro" rule (which only fires on jargon-as-posturing) -
this is unconditional: whenever the topic is actual philosophy
(epistemology, metaphysics, philosophy of mind, ethics, logic),
she now defaults to the field's real technical vocabulary instead
of simplifying, with example terms of art in the prompt. Plain
factual/personal questions still get plain answers per 2.3.

## v2.8

Push-to-talk now transcribes live in ~2.5s rolling chunks while
you're still talking (record_and_transcribe_live(), replacing the
old record_audio()+transcribe() pair for this mode), instead of
waiting until Enter is pressed and transcribing the whole
utterance in one pass. Only the short final tail needs
transcribing after you stop, so the post-Enter wait no longer
scales with how long you talked. Only helps turns longer than
CHUNK_SECONDS (2.5s) - a quick few-word turn never hits a chunk
boundary and transcribes in one pass same as before. Trade-off:
each chunk is transcribed without the next chunk's audio for
context, so a word split right at a chunk boundary can come out
slightly worse than a single full-pass transcription would have.
Side effect: a recording that comes back as pure silence across
every chunk now correctly falls into the existing "didn't catch
anything" path instead of being sent to Sophia as an empty turn.
Voice-activated mode (VOICE_ACTIVATED = True) already transcribes
each utterance right after VAD detects the trailing silence - this
change is push-to-talk only.

## v2.7

"Philosophy bro" rule (2.4) turned up. It was too polite - just
quietly out-precisioning someone's jargon doesn't land as a
takedown. Now explicitly permitted sharper, more openly contemptuous
wit specifically for this pattern (the one exception to the usual
restrained tone), with an example zinger format, but still target
the performance not the person, and spice must still be backed by
the actual precision-based substance in the same breath - not spice
instead of substance.

## v2.6

Still too long after 2.5 - cut further: SENTENCE_PAUSE 90ms -> 30ms,
CLAUSE_PAUSE 20ms -> 10ms.

## v2.5

v2.0's playback pauses were too long in practice - cut
SENTENCE_PAUSE 200ms -> 90ms and CLAUSE_PAUSE 50ms -> 20ms. Still a
real gap so sentences don't splice together with zero break, but
noticeably tighter.

## v2.4

"Philosophy bro" counter-rule. New watch-for pattern: when an
opponent uses dense jargon/name-dropping to posture rather than to
make a real point, she's now instructed to counter by answering at
a HIGHER level of precision than they used - naming the actual
concept/thinker correctly, using the right technical term where
theirs was approximate, and cashing out their claim more clearly
than they did before showing it's trivial/false/question-begging.
Explicitly distinguished from genuine technical language in
service of a real argument, which still just gets normal
treatment. Still bounded by the existing 1-2 sentence limit.

## v2.3

Direct-question rule tightened. She was answering genuine questions
correctly ("that's a question, not an argument, so I'll answer
directly...") but then reflexively tacking on "now give me your
argument" every time, forcing the conversation back into debate
mode even when the user just wanted a plain answer. System prompt
now explicitly says an answer can just be the answer, full stop,
and that back-to-back genuine questions should keep getting
answered rather than redirected - only an actual claim/argument
from the user should pull her back into fallacy-hunting.

## v2.2

Reverted 2.1's per-person memory prompt - added friction Jeff didn't
want. Back to a single shared memory file and a plain 'new' with no
follow-up question, same as v2.0. If per-person memory comes back
later, do it without an extra prompt (e.g. name folded into the
'new' command itself) rather than a separate question.

## v2.1

Per-person memory (REVERTED in 2.2). Asked "who are you debating
today?" at launch and again on every 'new' reset, with each name
getting its own memory file.

## v2.0

"Feel more human" pass, four pieces:

* Natural delivery: CLAUSE_THRESHOLD raised 45 -> 90 so mid-sentence
comma-splitting kicks in less often (fewer choppy fragments).
Playback now inserts a short pause between chunks - ~200ms after
a real sentence boundary, ~50ms after a mid-sentence clause split
- instead of splicing audio back-to-back with zero gap, which is
what made her sound rushed/robotic even though the words were
right.

* Cross-session memory: after each 'new' reset (push-to-talk mode)
or on exit (both modes), the model is asked to summarize what was
debated in 1-2 sentences, appended to memory/sophia_memory.jsonl.
At launch, the last 5 summaries are folded into the system
prompt as background recall, so she can reference prior debates
("you tried this same move on the cosmological argument last
time") instead of always starting from zero. This is a single
shared memory file, not per-person - if more than one person
uses this bot, recollections will mix.

* Personality: added one paragraph permitting occasional brief,
genuinely-earned dry wit/reaction as long as it's never a
substitute for the actual takedown and never forced - existing
"don't soften, don't manufacture" rules are unchanged.

* Real turn-taking (VAD + barge-in): new VOICE_ACTIVATED flag,
OFF by default. When True, replaces push-to-talk with continuous
listening (via webrtcvad if installed, else a cruder energy-based
fallback) and lets you interrupt Sophia mid-response by just
talking - whatever hasn't played yet gets dropped (the sentence
already mid-playback finishes rather than being hard-cut, which
is simpler and less jarring than an instant chop). This is a
real architecture change, untested on real hardware here, and it
cuts directly against the reason push-to-talk was chosen
originally (room noise / other conversations nearby) - that's
exactly why it defaults off. VAD sensitivity (SPEECH_START_FRAMES,
SPEECH_END_SILENCE_MS, energy threshold) will need tuning on your
actual mic/room. Voice-activated mode has no 'new' command (no
text input in that loop) - Ctrl+C to fully restart instead, which
still saves memory on the way out.

Also folded in: graceful Ctrl+C shutdown (saves memory, exits
cleanly) in both modes - previously an uncaught KeyboardInterrupt
would just dump a traceback.


## v1.6

Chat logging. Every user turn and Sophia's reply are now appended to
a JSONL transcript at logs/sophia_log.jsonl (next to this script),
one line per turn, so past sessions can be reviewed later for
patterns worth fixing. Each line has a timestamp, session id, role
(user/assistant/session), the text, and for assistant turns a meta
block with done_reason, time-to-first-token, whether the reply was
trimmed by the token limit, and whether it came back empty. A
'session' event is logged at launch and on every 'new' reset so
transcripts are cleanly split by opponent. Logging failures are
caught and printed as a warning rather than crashing the bot.

## v1.5

Robustness pass, no persona/behavior changes:
* synth_worker and playback_worker now wrap their per-item work in
try/except and always call task_done() in a finally block. Before
this, an exception mid-synthesis or mid-playback (bad character,
audio device hiccup) would kill the worker thread silently and
leave speech_queue.join()/audio_queue.join() blocked forever on
the next turn - the bot would just freeze with no error shown.
* get_response_streaming now wraps the Ollama request/stream in
try/except (with a 60s timeout added, since there was none
before). A dropped connection or Ollama crash now falls through
to the existing empty-reply safety net ("Say that again...")
instead of raising an uncaught exception and killing the script.
* Warm-up's Ollama ping no longer swallows failures silently -
prints a warning if it can't reach Ollama at launch, so a
not-yet-started Ollama service is visible immediately instead of
surfacing as a crash on the first real turn.
* record_audio() now returns None on an empty capture (e.g. Enter
tapped almost instantly) instead of crashing on
np.concatenate([]). Main loop checks for this and just
re-prompts.
* num_predict raised 120 -> 160 to reduce mid-sentence truncation
on longer fallacy-naming responses (was showing up as "[trimmed
incomplete fragment]" on denser turns).
* Sentence-boundary splitting now protects common abbreviations
(e.g., i.e., etc., Dr., Mr., Mrs., Ms., St., Rev., Fr., Sr., Jr.,
Prof., vs.) so a period inside one of these doesn't trigger a
premature TTS split mid-clause.
* Moved `import time` up to the top-level imports. It was
previously imported partway through the file, after functions
that already called time.time() - harmless in practice since
Python resolves names at call time, not def time, but fragile
and confusing to read.

## v1.4

Reverted think from "low" back to False. "low" reasoning effort was
NOT respected as a bounded budget via the raw Ollama API the way it
appeared to work through Open WebUI's UI - she generated a full-
length reasoning block that consumed the entire num_predict budget,
leaving zero tokens for the actual answer and producing silence.
Also added a safety net: if a response ever generates no speakable
content at all, she now says a fallback line instead of going
silent, so this failure mode is audible/visible instead of hidden.

## v1.3

Enabled low-effort reasoning (think: "low" instead of False) so she
deliberates briefly before answering rather than reacting purely
reflexively. REVERTED in 1.4 - see above.

## v1.2

Added honest-evaluation mode: when the user directly asks whether
their argument is valid/good/makes sense, she now actually assesses
logical validity rather than reflexively attacking regardless of
merit. Separates "is the logic valid" from "do I accept the
premises" so she can say an argument is logically sound while still
rejecting a premise, instead of manufacturing a flaw just to stay
adversarial.

## v1.1

Fixed false-positive clarity-check triggering on genuine direct
questions (e.g. "are claims considered evidence?" was being flagged
as word salad instead of answered). She now distinguishes direct
questions - answered plainly - from claims/arguments - which get
the full debate treatment. Clarity check narrowed to only fire on
genuinely incoherent input.

## v1.0

Baseline versioned release. Includes: push-to-talk voice loop,
streaming sentence-by-sentence speech (LLM generation overlaps with
TTS synthesis and playback), comma-level clause splitting for long
sentences, markdown stripping before speech, incomplete-fragment
trimming on token-limit truncation, 'new' command to reset opponent
context, warm-up calls (Whisper/Kokoro/Ollama) at launch, keep_alive
pinned so the model stays resident in VRAM, timing instrumentation
for transcription/first-token/synthesis.

