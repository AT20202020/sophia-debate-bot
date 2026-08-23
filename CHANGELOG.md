# Changelog — Sophia

Full version history. Extracted from the `debate_voice.py` module docstring in v2.20,
where it had grown to 396 lines — a quarter of the file.


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

