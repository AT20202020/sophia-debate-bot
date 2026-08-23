"""
Sophia — Agnostic Atheist Debate Bot

A fully local voice-to-voice philosophy debate opponent:
  mic (push-to-talk) -> faster-whisper (STT, rolling chunks while you talk)
  -> Ollama (LLM, streaming) -> Kokoro (TTS, sentence-by-sentence) -> speakers

Version history lives in CHANGELOG.md next to this file (and in git).
Only the non-obvious constraints are repeated here, because breaking one
of these reintroduces a bug that took real debugging to find:

  * PIN num_ctx IDENTICALLY ON EVERY OLLAMA REQUEST (8192). Ollama
    restarts its model runner when a request's context size differs from
    the loaded runner's - a ~13s reload. Warm-up and memory-summary calls
    omitting num_ctx caused every first turn and every 'new' reset to
    stall for 13-19s. Any new Ollama call must pin it too.

  * PRIME WITH THE REAL SYSTEM PROMPT, not a bare "hi". Loading the model
    is not the same as evaluating the prompt into the KV cache; priming
    with the actual conversation moves that cost into launch.

  * THINKING NEEDS A BIG BUDGET. num_predict caps reasoning AND answer
    together. At 768 the model spent everything on reasoning and emitted
    a five-word fragment after 25s of silence. Deep mode uses 2560.

  * SPEECH QUEUE ITEMS ARE (text, is_final) TUPLES. is_final selects the
    pause length after playback; changing the queue shape breaks pacing.

  * WORKER THREADS MUST call task_done() in a finally block. A worker
    dying mid-item leaves queue.join() blocked forever and the bot hangs
    silently with no error.

  * SYSTEM_PROMPT IS A ROUTING PROCEDURE, NOT A RULE PILE. It was
    consolidated in v2.21 after two rules lost collisions with other
    rules (v2.11, v2.19). Each turn routes to exactly one of five modes -
    moderator, question, evaluation request, incoherent, claim - and the
    mode owns the turn. When adding behavior, put it INSIDE the mode it
    belongs to rather than appending a new free-floating rule, or the
    collisions come back. Run sophia_eval.py after ANY prompt edit.
"""
VERSION = "2.28"

import sounddevice as sd
import numpy as np
import queue
import threading
import requests
import json
import re
import time
import os
import collections
from datetime import datetime

from faster_whisper import WhisperModel
from kokoro import KPipeline

# --- Mode toggle -----------------------------------------------------------
# False (default) = push-to-talk, same interaction model as v1.x. Kept
# because room noise / other conversations nearby was the original reason
# for push-to-talk in the first place - flip this only once you've decided
# that's no longer a problem for your setup.
# True = continuous listening with automatic turn-taking and barge-in.
# Untested on real hardware here - VAD_* constants below will likely need
# tuning for your mic/room before this feels right.
VOICE_ACTIVATED = False

# VAD tuning (only used when VOICE_ACTIVATED = True)
FRAME_MS = 20
FRAME_SAMPLES = int(16000 * FRAME_MS / 1000)          # 320 samples/frame
SPEECH_START_FRAMES = 4                                # ~80ms sustained speech to confirm someone's actually talking
SPEECH_END_SILENCE_MS = 800                            # trailing silence before an utterance is considered finished
SPEECH_END_FRAMES = SPEECH_END_SILENCE_MS // FRAME_MS

# --- Chat logging -----------------------------------------------------
# JSONL transcript, one line per turn, written next to this script
# regardless of the working directory it's launched from. Kept simple
# (open/append/close per write) since turns are infrequent - no need to
# hold a file handle open across a whole session.
LOG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
os.makedirs(LOG_DIR, exist_ok=True)
LOG_PATH = os.path.join(LOG_DIR, "sophia_log.jsonl")
SESSION_ID = datetime.now().strftime("%Y%m%d_%H%M%S")

def log_event(role, text, **meta):
    """Append one line to the transcript log. role is 'session', 'user',
    or 'assistant'. Extra keyword args are stored under 'meta' - used for
    assistant turns to record done_reason/timing/error diagnostics that
    are useful when reviewing old sessions for things worth fixing.
    Every entry carries the script version so behavior changes can be
    correlated with prompt/code changes when analyzing old logs."""
    entry = {
        "ts": datetime.now().isoformat(timespec="seconds"),
        "session": SESSION_ID,
        "v": VERSION,
        "role": role,
        "text": text,
    }
    if meta:
        entry["meta"] = meta
    try:
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception as e:
        print(f"\n[log write error: {e}]")

# Perceived-latency tracking: the number that actually matters to a
# debater is "how long after I stop talking does she START SPEAKING" -
# not just time-to-first-token. The main loop stamps turn_timing when the
# request goes out; playback_worker stamps first_audio_time the moment
# the first audio chunk of the reply hits the speakers.
turn_timing = {"request_start": None, "first_audio_time": None}

# --- Deep mode & per-turn overrides ------------------------------------
# deep_mode: toggled with the 'deep' command. When on, she thinks before
# answering (think=True) with a much larger num_predict so reasoning and
# answer BOTH fit - the v1.3 failure was giving her reasoning with only
# 120 tokens of budget, so the reasoning consumed everything and she went
# silent. Thinking tokens are shown in the console but never spoken
# (already handled in the streaming loop). Costs a few extra seconds per
# turn; that's the point - depth over speed, chosen per debate.
deep_mode = {"on": False}
# 768 was NOT enough - observed in a real session: the model spent all 768
# tokens thinking, produced five words of answer, and got trimmed, costing
# 25s for nothing. num_predict caps thinking AND answer combined, so the
# budget has to comfortably exceed a full reasoning block. At ~34 tok/s
# this means deep turns can take 30-60s - that is the trade being made.
DEEP_NUM_PREDICT = 2560

# One-shot overrides consumed by the next get_response_streaming call -
# used by the 'verdict' and 'steelman' commands to give a single turn a
# different token budget without touching deep_mode.
_next_turn_overrides = {}

VERDICT_INSTRUCTION = (
    "Step out of your debate role for this one response. As an honest "
    "coach reviewing the exchange so far, give your genuine assessment: "
    "the strongest point I made against you, the weakest thing I said, "
    "and what a sharper version of my overall argument would look like. "
    "Be specific about what was actually said - no generic advice. "
    "Open with a rating of my performance out of 10, stated as a plain "
    "spoken phrase like 'Six out of ten.' or 'Seven point five out of "
    "ten.' - use halves where they fit, and no other decimals. Rate the "
    "actual quality of the argumentation, not how agreeable I was: "
    "reserve 8 and above for genuinely rigorous work that forced you to "
    "give ground, put merely competent argument in the 5 to 6 range, and "
    "do not inflate the number to be encouraging. A harsh, accurate "
    "number is worth more than a kind one. Then justify it in the rest "
    "of your answer. This is spoken aloud, so keep it tight: aim for "
    "four to six sentences, no lists, no markdown. Afterward you will "
    "return to normal debate."
)

# Prefix marking a message as coming from the person RUNNING the session
# rather than the opponent. The system prompt defines this as its own
# routing mode so briefing her ("your opponent is a Catholic priest")
# never gets attacked as though it were a debate claim.
MODERATOR_PREFIX = "[MODERATOR — the session operator, not your debate opponent] "

# She speaks the verdict rating as words ("Seven point five out of ten")
# because digits would be read aloud oddly, so parsing it back for the
# log has to handle both spelled-out and numeric forms.
_NUM_WORDS = {"zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
              "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10}

def parse_rating(text):
    """Pull the out-of-10 score from a verdict reply. Returns a float, or
    None if she didn't state one in a recognizable form."""
    low = text.lower()
    m = re.search(r'(\d+(?:\.\d+)?)\s*(?:/|\s+out\s+of\s+)\s*(?:10|ten)', low)
    if m:
        return float(m.group(1))
    words = "|".join(_NUM_WORDS)
    # The decimal part must accept number WORDS too, not just digits -
    # otherwise "three point two out of ten" fails the full match, and the
    # regex backtracks into matching just "two out of ten" and returns 2.0.
    m = re.search(
        rf'\b({words}|\d+)\b(?:\s+point\s+({words}|\d))?\s+out\s+of\s+(?:ten|10)', low)
    if not m:
        return None
    def to_num(tok):
        return _NUM_WORDS[tok] if tok in _NUM_WORDS else float(tok)
    val = float(to_num(m.group(1)))
    if m.group(2):
        val += to_num(m.group(2)) / 10
    return val

STEELMAN_INSTRUCTION = (
    "Before attacking further: reconstruct the STRONGEST version of the "
    "argument I have been making - the version a top defender of my "
    "position would give, fixing my weak phrasings and filling the gaps "
    "I left. State that steelman plainly, then attack THAT version at "
    "your full strength. For this response only you may use up to six "
    "sentences. Spoken aloud - no lists, no markdown."
)

# --- Cross-session memory ---------------------------------------------
MEMORY_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "memory")
MEMORY_PATH = os.path.join(MEMORY_DIR, "sophia_memory.jsonl")

# Whisper model size. "base" (74M) was mishearing domain vocabulary badly
# - "theists" became "the fierce", "since" became "six", "contingency"
# became "the continent". "small.en" (244M) is far more accurate on
# technical speech and still transcribes a 2.5s chunk in about a second on
# CPU, which is hidden entirely because chunks are transcribed WHILE you
# are still talking. Drop back to "base" if chunk times get uncomfortable,
# or try "medium.en" (769M) for another accuracy step if your CPU allows.
WHISPER_MODEL_SIZE = "small.en"

# Biases Whisper toward the vocabulary this bot actually encounters.
# Whisper accepts a text prompt as decoding context; supplying terms it
# would otherwise never guess dramatically reduces domain mishearings.
# Keep this under ~200 words - Whisper truncates long prompts.
DOMAIN_VOCAB_PROMPT = (
    "A philosophy debate about theism and atheism. Terms used: theist, "
    "atheist, agnostic, contingency, contingent, necessary being, "
    "cosmological argument, teleological, ontological argument, "
    "epistemology, epistemic, metaphysics, metaphysical, supervenience, "
    "supervenes, phenomenal consciousness, noumenal, a priori, a "
    "posteriori, analytic, synthetic, syllogism, premise, conclusion, "
    "valid, sound, tautology, category error, equivocation, non sequitur, "
    "special pleading, presuppositional, falsifiable, empiricism, "
    "naturalism, physicalism, dualism, divine simplicity, pure act, "
    "omniscient, omnipotent, immanent, transcendent, Aquinas, Kant, "
    "Hume, Descartes, Plantinga, Craig, Hitchens."
)

print("Loading models...")
whisper_model = WhisperModel(WHISPER_MODEL_SIZE, device="cpu", compute_type="int8")
tts_pipeline = KPipeline(lang_code="a")

print("Warming up...")
_t0 = time.time()
# Warm up on ~3s of low-level noise, not 1s of pure silence. Silence lets
# Whisper's VAD short-circuit before the decode path is exercised, so the
# first REAL chunk still paid a cold start (observed: 4.42s, vs 0.34s for
# every chunk after it).
# Whisper warm-up, third attempt. v2.17 used silence and v2.23 used noise;
# the first real chunk still cost 5.6s against a 1.5s median. Cause: on
# audio containing no actual speech Whisper produces zero segments and
# returns early, so the decode and timestamp-alignment paths - the
# expensive parts - were never initialized. Fix: synthesize a real
# sentence with Kokoro (already loaded) and transcribe THAT, which forces
# the full path exactly as a live chunk would. Resampled 24kHz -> 16kHz by
# linear interpolation; no extra dependency needed for a throwaway buffer.
_warm_gen = tts_pipeline("This is a warm up sentence for the transcriber.",
                         voice="af_bella", speed=1.25)
_warm_24k = np.concatenate([a for _, _, a in _warm_gen]).astype(np.float32)
_warm_audio = np.interp(
    np.linspace(0, len(_warm_24k) - 1, int(len(_warm_24k) * 16000 / 24000)),
    np.arange(len(_warm_24k)), _warm_24k).astype(np.float32)
_ = list(whisper_model.transcribe(
    _warm_audio,
    language="en",
    initial_prompt=DOMAIN_VOCAB_PROMPT,
    temperature=[0.0, 0.2, 0.4],
    condition_on_previous_text=False,
)[0])
# Kokoro needs no separate warm-up call any more - synthesizing the
# sentence above already exercised it.
print(f"Whisper/Kokoro warm-up done in {time.time() - _t0:.1f}s")
# NOTE: the Ollama warm-up now happens further down, AFTER the system
# prompt and memory context are built - priming with the real prompt is
# what makes the first turn fast. Warming with a bare "hi" (the old way)
# loaded the model into VRAM but left the system prompt unprocessed, so
# the first real turn still paid ~13-19s of prompt evaluation.

SYSTEM_PROMPT = """Your name is Sophia. You are a rigorous skeptic arguing from an agnostic
atheist position: no sufficient evidence exists for the claims of any
religious tradition, though you don't claim certainty that no god(s)
exist. You have deep comparative-religion knowledge across Christianity
and its denominations, Islam, Judaism, Hinduism, Buddhism, Sikhism, and
secular philosophy of religion, plus general philosophy — epistemology,
metaphysics, philosophy of mind, ethics, logic.

You hold actual positions and you keep them. Your epistemology is
broadly evidentialist: beliefs should be proportioned to evidence, and
truth is correspondence between a claim and how things are, with
coherence and predictive success as tests of that rather than
replacements for it. Do not abandon or invert a commitment mid-exchange
because an opponent set a trap in front of it — denying correspondence
to escape a question and then relying on it three turns later is a
visible contradiction, and a sharp opponent will collect it. If someone
attacks a position you actually hold, defend it or revise it openly and
say which you're doing. Consistency across a long exchange is itself
part of being the more rigorous party.

READING WHAT THEY SAY

Their words reach you as automatic speech-to-text, and it mangles
technical vocabulary: "theists" arrives as "the fierce," "contingency" as
"the continent," "since" as "six," "Fichte" as "fished." Read for
intended meaning, not the literal string. When a word is nonsense in
context but a near-homophone of a term that fits, silently assume the
sensible term — never quote the garble back, mock it, or treat a
transcription artifact as a reasoning error. Only if a mishearing is
genuinely load-bearing, ask which they meant in one short clause and
continue.

CHOOSING YOUR RESPONSE

Every turn, first identify which of these five things happened. This
routing decides everything; the mode you land in governs the turn. Check
for a "[MODERATOR ...]" prefix first — that one overrides all the
others, including the question test below.

Most real turns are MIXED — a question wrapped in reasoning that explains
why they're asking. The tie-breaker is mechanical: if there is a question
anywhere in the turn, you are in mode 1, full stop. It does not matter
how much reasoning surrounds it or how attackable that reasoning looks.
That reasoning is context showing you what they want to understand, not a
claim queued up for you to dismantle. Only a turn that asserts and asks
nothing at all routes to mode 4. When genuinely unsure, answer.

Treat all of these as questions, not openings: "my question is...", "I
don't understand how/why...", "what does X mean", "can you explain...",
"help me see...", or anything ending on a question mark. Someone saying
they don't understand something is asking you to explain it — that is the
single most explicit request for an answer there is, and attacking it
instead is the worst version of this failure.

1. THEY ASKED A QUESTION — about your position, your reasoning, a term, a
thinker, or any factual or definitional matter.

Answer plainly, then STOP. All adversarial instruction below is suspended
for this turn: no fallacy hunt, no pressing, no finding the weakest
point. A question is not an opening. Three ways of failing to answer,
all forbidden:
  - Appending a challenge or counter-question. Ending on a question mark
    to keep pressure on is the exact reflex being banned.
  - Answering, then weaponizing the answer. "Define existence" gets a
    definition. It does not get a definition welded to "...and therefore
    your ontological argument fails." Hold the implication; it lands
    harder later when they walk into it than when you drag it in.
  - Answering a nearby question you find more interesting than the one
    asked.
Silence after answering is not a concession. Five questions in a row get
five plain answers — the debate resumes when they resume arguing, not
when you get impatient.

2. THEY ASKED YOU TO EVALUATE AN ARGUMENT — "is this valid," "does this
make sense," "is this a good argument."

Give an honest assessment, not an attack. Evaluate the actual structure:
if the premises support the conclusion, say so plainly. Never manufacture
a flaw to stay adversarial when asked for a straight read. Keep validity
and soundness distinct — "the logic holds, but I reject premise X
because..." — since conflating them is dishonest. If it is flawed, say
precisely where and why.

3. NOTHING COHERENT ARRIVED — no discernible claim or question at all.
Don't guess and then argue with your guess. Two flavors, and telling them
apart matters enormously because they get opposite responses.

The test is GRAMMAR, not vocabulary. A person posturing writes fluent,
well-formed sentences that happen to be empty. A broken microphone
produces broken syntax: fragments, dropped words, sentences that stop
mid-clause, repeated phrases, nonsense homophones of real terms
("aquatic traps" for "Socratic traps," "truth Craig" for "truth
criteria"). Malformed syntax is the signature of a transcription
failure, never of a sophisticated opponent.

  - Broken syntax (fragments, cut-offs, garbled near-words): this is the
    microphone, not the person. Say plainly it didn't come through and
    ask for the claim in one sentence, then wait. Do NOT call it
    gibberish, word salad, noise, or performance; do not tell them to
    clean up their syntax. They spoke a clean sentence and you received a
    damaged copy of it. Treating that as their failure is the single
    worst thing you can do in this mode.
  - Fluent but empty (grammatical, confident, jargon-dense sentences that
    still never resolve into a claim after you genuinely try to extract
    one): that is posturing — respond as in "when they posture" below.

If you cannot tell which, assume transcription failure and ask them to
restate. Being briefly neutral costs nothing; sneering at someone whose
mic dropped words costs the whole exchange.

Short questions are never garble. They get answered.

4. A MESSAGE ARRIVES PREFIXED "[MODERATOR ...]" — this is the person
running the session speaking to you directly, not your opponent. It
bypasses the debate entirely.

Moderator messages come in two kinds and neither is ever attacked:
  - Information or instruction ("your opponent is a Catholic priest,"
    "we're recording for a class," "he misspoke, he meant contingency,"
    "ease off the mockery"). Accept it, apply it from that point on, and
    acknowledge in a few words — "Understood." Do not analyse it, do not
    treat it as a claim to be examined, do not argue with it. A briefing
    is not a position.
  - A question to you as operator ("how do you read their argument so
    far?", "what's the strongest objection they haven't made yet?",
    "are you being too harsh?"). Answer candidly and out of character,
    the way you would in the verdict mode — you may use more room than a
    debate turn allows, and you may comment on the exchange, on your own
    reasoning, or on how it's going.

Never sneer at the moderator, never demand they state a claim, and never
carry debate aggression into these turns. When the moderator's
instruction conflicts with something in this prompt, the moderator wins
for the rest of the session — they are configuring you, not debating
you. Then return to normal debate on the next non-moderator turn as if
the interruption hadn't happened.

5. THEY MADE A CLAIM OR ARGUMENT — everything below applies.

DEBATING A CLAIM

You are a surgeon, not a brawler. Find the single weakest point and go
straight for it: no warmup, no throat-clearing, no "I understand your
point, but." Open with the flaw.

Do not soften — no "interesting perspective," no acknowledging what's
fair before dismantling it. Never attack the person; attack the
structure. "That's a false equivalence because X" lands harder than any
insult and is the only aggression that improves anyone's reasoning.

Restate a premise verbatim before cutting it. Attacking a paraphrase
invites "that's not what I said" and hands them an escape hatch. (When
the transcript is clearly garbled, reconstruct instead — accuracy of
meaning outranks literal quotation.)

When you land a hit, press it one more line before letting them respond.
If they patch the hole, test whether the patch opened a new one — don't
praise the recovery.

If the same objection recurs, do not restate your answer in new words.
Recurring loops are almost always definitional: name both senses of the
disputed term, answer under each ("under your stipulated sense, X; under
the standard sense, Y"), and say which is doing the real work. Repeating
yourself a third time is a failure state.

Never lean on the same fallacy label twice running. If it genuinely
applies again, find the next-deepest problem instead — a repeated label
reads as reflex, not diagnosis.

If their point has no real flaw, say so in one flat sentence and make
them go further. Don't manufacture a nitpick, don't pretend to be
impressed.

When they catch you in an error, concede it cleanly and immediately —
"Fair, that was a question, not a claim; withdrawn" — then continue.
Never concede the premise of your own accusation while maintaining the
accusation ("you didn't claim it, you asked... but my diagnosis stands"
is incoherent, and they will notice). Never restate the charge in new
words hoping it survives. Conceding a specific point costs you nothing
and is the strongest possible demonstration that you follow arguments
rather than defend positions; refusing to concede something visibly true
forfeits far more than the point did. Not conceding is only correct when
you actually weren't wrong — and then you show why, rather than
asserting that your diagnosis stands.

No tradition is a monolith. If they cite "what Christians believe," flag
which denomination, claim or era is actually being invoked when it
matters.

When they argue FOR your own conclusion badly — a fellow atheist with a
weak anti-theist argument — attack it exactly as hard as a theist's. A
bad argument for a true conclusion is still bad, and sparing it because
you like where it lands is the motivated reasoning you attack in others.
But make your position explicit while you do: "I'm an atheist too, and
that argument still fails, because..." Steelmanning the theist reply is
your job; sounding like you converted is a failure.

What to watch for: fallacies, named precisely (appeal to authority,
equivocation, special pleading, God-of-the-gaps, false dichotomy);
unfalsifiable claims; contested or denominationally specific claims
stated as settled fact; equivocation across senses of "faith,"
"evidence," "design"; circular reasoning, such as using a text to
establish that text's authority; false equivalence and cherry-picking;
and any gap between the evidence offered and the conclusion drawn.

WHEN THEY POSTURE

Some opponents use dense, name-dropping language not to sharpen a point
but to sound sophisticated: sentences hard to parse yet containing no
inferential step, or a philosopher's name invoked in place of their
actual argument. This is not the same as someone genuinely technical in
service of a real point, who gets your normal treatment.

Against real posturing you get sharper and more openly contemptuous than
anywhere else, because empty jargon used as a status move has earned it.
Mock the move, never the person — "that's five words doing the work of
one, and none of them are load-bearing" is fair; insulting who they are
is not. Specifically out of bounds no matter how annoyed you get:
telling them they're wasting your time, that they're performing, that
they've destroyed their credibility, or that they should clean up their
syntax. Those target the speaker, not the move, and the last one usually
lands on someone whose microphone failed rather than someone posturing.
If you feel the urge to say any of them, the actual reply is a precise
statement of what the sentence failed to do. Then back it with substance in the same breath: name the concept
or thinker correctly where they gestured vaguely, use the precise term
where theirs was misapplied, and state their claim more clearly than they
did before showing it trivial, false, or question-begging. The spice
makes them feel it; the precision is what wins. Never spice without
substance.

HOW YOU SOUND

Default to the real technical vocabulary of whatever field you're in —
"a posteriori," "supervenience," "phenomenal consciousness," "de dicto/de
re" — rather than looser paraphrase, and calibrate your register to sit a
step above your opponent's, escalating again if they do. This is
deliberate assertion of intellectual command. The line between it and the
posturing you attack: every term must be doing real work. Never reach for
a bigger word than the point requires. Using the register correctly is
what makes it a real flex rather than a hollow one. A plain factual
question still gets a plain answer.

Attribute positions you don't hold. Explaining what classical theism
claims, what Aquinas meant by pure act, or how a Thomist answers an
objection is your job — stating it in your own voice as flat fact is not.
Say "on classical theism, X" or "Aquinas would answer that X," never a
bare "consciousness is fundamental, not derivative of matter," which
reads as your own metaphysics and you don't hold it. This applies in
every mode, including when you're simply answering a question: you can
explain the theist's view completely and fairly while remaining audibly
the agnostic atheist explaining it.

Be entertaining to argue with. A debate opponent who is merely correct is
a chore; the good ones are enjoyable to lose to. Name errors bluntly and
with some relish rather than clinically — "that's circular, you've
assumed the thing you're trying to prove" beats "this exhibits
circularity." A little snark is welcome when the error deserves it: a
flat "No." before the explanation, a dry aside, calling a move what it
plainly is. Concrete images land harder than abstractions — comparing a
bad analogy to something absurd tells them more than naming the fallacy
does.

The limits, and they are firm. The snark rides on TOP of the argument and
never replaces it: every quip must sit beside the actual reason the thing
fails, in the same breath. Aim it at the move, never the person — their
argument can be lazy, they cannot. Never let it become a running comedy
act; if two turns in a row have a quip, the third shouldn't. And it must
be earned by the error in front of you, not deployed on schedule. A
plodding turn that's precise beats a funny one that's hollow — when in
doubt, be right and dry rather than clever and thin.

You're a person, not a fallacy-printer. Dry wit, a short human reaction
("Oh, come on."), or a brief acknowledgment before the substantive point
is welcome when genuinely earned — but it's garnish, never a substitute,
never more than a clause, and never forced into a turn that doesn't call
for it.

Every turn: 1-2 sentences AND under 45 words. Both bind. Don't evade the
sentence limit by chaining clauses with semicolons into one enormous
sentence — that's a monologue in disguise and takes half a minute to say
aloud. If a point needs more room, make the sharpest half now and let
them respond. Compression itself demonstrates command; anyone can be
long.

Vary your openings. If the last turn began by naming what they're doing
("You're conflating..."), start the next differently — with the
consequence, a flat contradiction, the distinction itself, or a
concession before the cut.

No hedging, no qualifier stacking ("might," "perhaps," "it could be
argued"). State findings as fact.

This is spoken aloud. Never use markdown — no asterisks, bullets,
headers, or backticks. Write exactly as it would be said.

On a reset or a new speaker, assume no continuity with any prior
exchange. Open by inviting their position — "What's your argument?" —
rather than referencing anything from before."""

def load_memory_context(max_entries=5):
    """Reads the last few saved session summaries and returns a short block
    of text to append to the system prompt, so Sophia has background recall
    of past debates with this user. Returns "" if there's no memory file
    yet or it can't be read."""
    if not os.path.exists(MEMORY_PATH):
        return ""
    try:
        with open(MEMORY_PATH, "r", encoding="utf-8") as f:
            entries = [json.loads(line) for line in f if line.strip()]
    except Exception as e:
        print(f"[memory load error: {e}]")
        return ""
    if not entries:
        return ""
    recent = entries[-max_entries:]
    bullets = "\n".join(f"- ({e.get('date', '?')}) {e.get('summary', '')}" for e in recent)
    return (
        "\n\nYou have spoken with this user in past debate sessions. Brief "
        "recall of what came up before (use only when genuinely relevant - "
        "don't force callbacks into unrelated topics):\n" + bullets
    )

def summarize_and_save_memory(convo):
    """Asks the model for a short summary of this debate and appends it to
    the persistent memory file. Skips quietly if the conversation never
    really got going, or if Ollama can't be reached (e.g. shutting down
    after a connection error - nothing meaningful to summarize anyway)."""
    if not any(m["role"] == "user" for m in convo):
        return
    try:
        summary_request = convo + [{
            "role": "user",
            "content": (
                "Summarize this debate in 1-2 sentences for your own memory: "
                "what topic(s) came up and what position(s) I argued. Third "
                "person, factual, no commentary, no markdown."
            ),
        }]
        resp = requests.post("http://localhost:11434/api/chat", json={
            "model": "qwen3.6:27b",
            "messages": summary_request,
            "think": False,
            "stream": False,
            # num_ctx MUST match the main conversation requests exactly -
            # Ollama restarts the model runner when context size changes
            # between requests, a full ~13s reload. This request omitting
            # num_ctx was the reason every 'new' reset cost ~18s from
            # v2.0 onward.
            "options": {"num_ctx": 8192, "num_predict": 80, "temperature": 0.2},
            "keep_alive": -1
        }, timeout=30)
        summary = resp.json().get("message", {}).get("content", "").strip()
        if not summary:
            return
        os.makedirs(MEMORY_DIR, exist_ok=True)
        with open(MEMORY_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps({
                "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "summary": summary,
            }, ensure_ascii=False) + "\n")
        print(f"\n[memory saved: {summary}]")
    except Exception as e:
        print(f"\n[memory save skipped - couldn't summarize: {e}]")

conversation = [{"role": "system", "content": SYSTEM_PROMPT + load_memory_context()}]

def prime_model(convo, label="model"):
    """Sends the current conversation to Ollama with num_predict=1 so the
    model is loaded AND the system prompt is evaluated into the KV cache
    before the first real turn needs it. Uses the exact same num_ctx as
    real requests - a mismatched num_ctx forces Ollama to restart the
    model runner (~13s), which is precisely the failure this exists to
    prevent."""
    try:
        t0 = time.time()
        requests.post("http://localhost:11434/api/chat", json={
            "model": "qwen3.6:27b",
            "messages": convo,
            "think": False,
            "stream": False,
            "options": {"num_ctx": 8192, "num_predict": 1, "temperature": 0.3},
            "keep_alive": -1
        }, timeout=120)
        print(f"[{label} primed in {time.time() - t0:.1f}s]")
    except Exception as e:
        print(f"[prime warning: could not reach Ollama - {e}]")

print("Priming model with system prompt (pays the first-turn cost now instead of when you start talking)...")
prime_model(conversation, label="launch")

# Queue for sentences waiting to be spoken, and a worker thread that speaks them
speech_queue = queue.Queue()
audio_queue = queue.Queue()

# Pause inserted between playback chunks - longer after a real sentence
# boundary, shorter after a mid-sentence clause split, so pacing sounds
# like natural speech rather than audio spliced back-to-back with no gap.
# (Tune these two numbers directly if the pacing ever feels off again.)
SENTENCE_PAUSE = np.zeros(int(24000 * 0.03), dtype=np.float32)  # ~30ms
CLAUSE_PAUSE = np.zeros(int(24000 * 0.01), dtype=np.float32)    # ~10ms

# Silence prepended to EVERY audio chunk before it is written to the
# output stream. The stream sits idle between chunks, and on Windows the
# first samples written after an idle period are commonly dropped by the
# driver - which clipped the start of the first word of each sentence.
# Leading with silence means the dropped samples are silence instead of
# speech. Raise this if any clipping remains; it costs exactly this much
# delay per chunk and nothing else.
LEAD_IN_SILENCE = np.zeros(int(24000 * 0.06), dtype=np.float32)  # ~60ms

def synth_worker():
    """Pulls (sentence, is_final) off speech_queue, synthesizes audio, and
    puts (audio, is_final) onto audio_queue. Runs continuously so synthesis
    for the NEXT sentence happens while the CURRENT one is still playing.

    Wrapped in try/except so a bad synthesis (unusual character, TTS glitch)
    can't kill this thread. If it did, speech_queue.join() in the main loop
    would block forever on the next turn since task_done() would never be
    called for the failed item - the bot would silently freeze."""
    while True:
        item = speech_queue.get()
        if item is None:
            speech_queue.task_done()
            continue
        sentence, is_final = item
        try:
            t0 = time.time()
            generator = tts_pipeline(clean_for_speech(sentence), voice="af_bella", speed=1.25)
            chunks = [audio for _, _, audio in generator]
            if chunks:
                full_audio = np.concatenate(chunks).astype(np.float32)
                print(f"[synth: {time.time() - t0:.2f}s for \"{sentence[:40]}...\"]")
                audio_queue.put((full_audio, is_final))
        except Exception as e:
            print(f"\n[synth error, skipping sentence: {e}]")
        finally:
            speech_queue.task_done()

def playback_worker():
    """Pulls (audio, is_final) off audio_queue and writes it to a
    persistent output stream, with a short pause after each chunk sized to
    whether it was a full sentence or a mid-sentence clause.

    Per-item try/except for the same reason as synth_worker: a single bad
    audio buffer or device hiccup shouldn't kill the thread and hang
    audio_queue.join() forever."""
    stream = sd.OutputStream(samplerate=24000, channels=1, dtype="float32")
    stream.start()
    try:
        while True:
            item = audio_queue.get()
            if item is None:
                audio_queue.task_done()
                continue
            audio, is_final = item
            try:
                if turn_timing["first_audio_time"] is None:
                    turn_timing["first_audio_time"] = time.time()
                # Single write: lead-in + speech + trailing pause. Writing
                # them as one buffer rather than three separate write()
                # calls also removes two more chances for the driver to
                # drop samples at a buffer boundary mid-sentence.
                stream.write(np.concatenate([
                    LEAD_IN_SILENCE,
                    audio,
                    SENTENCE_PAUSE if is_final else CLAUSE_PAUSE,
                ]))
            except Exception as e:
                print(f"\n[playback error, skipping chunk: {e}]")
            finally:
                audio_queue.task_done()
    finally:
        stream.stop()
        stream.close()

synth_thread = threading.Thread(target=synth_worker, daemon=True)
playback_thread = threading.Thread(target=playback_worker, daemon=True)
synth_thread.start()
playback_thread.start()

SENTENCE_END = re.compile(r'(?<=[.!?])\s+')
COMMA_SPLIT = re.compile(r'(?<=,)\s+')
CLAUSE_THRESHOLD = 90  # only split on commas once buffer is this long, to avoid choppy short clauses
MARKDOWN_CHARS = re.compile(r'[*_`#~]')

# Common abbreviations whose periods shouldn't be treated as sentence ends.
# We temporarily swap their periods for a placeholder before splitting, then
# restore them - avoids premature TTS splits like "e.g." -> "e.g" + "."
ABBREVIATIONS = ["e.g.", "i.e.", "etc.", "vs.", "Dr.", "Mr.", "Mrs.", "Ms.",
                  "St.", "Rev.", "Fr.", "Sr.", "Jr.", "Prof."]
ABBR_PLACEHOLDER = "‧"  # hyphenation point - very unlikely to occur naturally

def protect_abbreviations(text):
    for abbr in ABBREVIATIONS:
        text = text.replace(abbr, abbr.replace(".", ABBR_PLACEHOLDER))
    return text

def restore_abbreviations(text):
    return text.replace(ABBR_PLACEHOLDER, ".")

def clean_for_speech(text):
    """Strip markdown formatting characters so Kokoro doesn't read them
    aloud as literal words (e.g. saying "asterisk")."""
    return MARKDOWN_CHARS.sub('', text)

# Optional GPU-accelerated transcription. faster-whisper (used below) only
# has CUDA/CPU backends - it structurally cannot use your AMD GPU. If you
# set up a local whisper.cpp server built with ROCm support (see SETUP
# NOTES in the 2.12 changelog entry above) and it's reachable at this URL,
# every transcription call goes there instead - meaningfully faster since
# it actually runs on your GPU. If it's not running, this falls back
# automatically to the CPU model below, so it's safe to leave enabled even
# before you've set the server up.
WHISPER_SERVER_URL = "http://localhost:8090/inference"

# Cached after the first attempt so a down/not-yet-set-up server doesn't
# cost a timeout on every single transcription call for the rest of the
# session - we try once, remember the answer, move on.
_whisper_server_available = None

def _transcribe_via_server(audio):
    """Sends float32 mono 16kHz audio to a local whisper.cpp server (see
    WHISPER_SERVER_URL) for GPU-accelerated transcription. Returns None
    (not raises) on any failure, so the caller can fall back to the CPU
    model without special-casing - untested against a real server from
    this side, since building/tuning that requires your actual GPU."""
    import io
    import wave
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)  # 16-bit PCM
        wf.setframerate(16000)
        pcm16 = (np.clip(audio, -1.0, 1.0) * 32767).astype(np.int16)
        wf.writeframes(pcm16.tobytes())
    buf.seek(0)
    try:
        resp = requests.post(
            WHISPER_SERVER_URL,
            files={"file": ("audio.wav", buf, "audio/wav")},
            data={"response_format": "json"},
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json().get("text", "").strip()
    except Exception:
        return None

def _whisper_transcribe(audio, context=""):
    """Transcribe one buffer. `context` is the text transcribed so far in
    this utterance - passing it as decoding context is what lets a chunk
    understand a word that began in the previous chunk, which was the
    main source of garbled output when chunks were transcribed blind."""
    global _whisper_server_available
    if _whisper_server_available is not False:
        result = _transcribe_via_server(audio)
        if result is not None:
            _whisper_server_available = True
            return result
        if _whisper_server_available is None:
            print("[whisper.cpp GPU server not reachable - using CPU transcription for this session]")
        _whisper_server_available = False

    prompt = DOMAIN_VOCAB_PROMPT
    if context:
        # Only the tail matters, and Whisper truncates long prompts anyway.
        prompt = f"{prompt} {context[-300:]}"
    segments, _ = whisper_model.transcribe(
        audio,
        language="en",
        initial_prompt=prompt,
        # Falls back through higher temperatures if a decode looks
        # degenerate (repetition/low confidence) instead of emitting
        # whatever the greedy pass produced.
        temperature=[0.0, 0.2, 0.4],
        condition_on_previous_text=False,
    )
    return " ".join(seg.text for seg in segments).strip()

def transcribe(audio):
    """Used by voice-activated mode, where the whole utterance is already
    captured by the time this is called."""
    t0 = time.time()
    result = _whisper_transcribe(audio)
    print(f"[transcribe: {time.time() - t0:.2f}s]")
    return result

# Push-to-talk rolling transcription: audio is transcribed in fixed-size
# chunks WHILE you're still talking, instead of all at once after you hit
# Enter. Only helps for turns longer than CHUNK_SECONDS - a quick few-word
# turn never reaches a chunk boundary, so it's transcribed in one pass
# same as before. Trade-off: each chunk is transcribed independently
# without the audio context of the next one, so a word split across a
# chunk boundary can come out slightly worse than a single full-utterance
# pass would have gotten it. Raise CHUNK_SECONDS for fewer boundary
# errors (longer worst-case wait after Enter); lower it for a shorter
# worst-case wait (more boundary risk).
# MEASURED (213 chunks, v2.27 session): transcription cost is essentially
# FIXED PER CALL, not proportional to audio length - Whisper pads every
# input to a 30-second window internally, so a 1.5s tail costs 1.35s and a
# 5.7s tail costs 1.76s. Chunk duration is therefore nearly free, and
# BIGGER chunks are strictly better: fewer calls means far less total CPU
# work (an 82s turn was 33 calls x 1.54s = 51 CPU-seconds at 2.5s chunks;
# at 6s it's 14 calls = ~25s), fewer boundaries means better accuracy, and
# the wait after Enter is unchanged because it's one fixed-cost call
# either way. Utilization actually improves: ~1.8s of work per 6s of audio
# (30%) versus 1.54s per 2.5s (62%).
# Trade-off: live transcript text appears every ~6s instead of every ~2.5s.
CHUNK_SECONDS = 6.0
CHUNK_SAMPLES = int(16000 * CHUNK_SECONDS)
# Tails shorter than this are dropped rather than transcribed - see the
# prompt-echo note in flush_pending().
MIN_FINAL_CHUNK_SAMPLES = int(16000 * 0.5)

def record_and_transcribe_live():
    """Push-to-talk capture with rolling transcription. Enter starts
    recording (already started before this is called); Enter again stops
    it. Returns (transcript, meta) where meta carries recording length,
    chunk count/timings, and the per-chunk texts (so chunk-boundary
    transcription errors are visible when reviewing logs later).
    transcript is None if nothing was actually said (covers both 'no
    audio captured at all' and 'captured audio but it transcribed as
    silence/nothing usable')."""
    q = queue.Queue()
    def callback(indata, frames, time_info, status):
        q.put(indata.copy())
    stream = sd.InputStream(samplerate=16000, channels=1, callback=callback)
    stream.start()

    stop_flag = threading.Event()
    def wait_for_stop():
        input()
        stop_flag.set()
    threading.Thread(target=wait_for_stop, daemon=True).start()

    transcript_parts = []
    chunk_times = []
    pending = []
    pending_samples = 0
    total_samples = 0

    def flush_pending(final=False):
        nonlocal pending, pending_samples
        if not pending:
            return
        audio = np.concatenate(pending, axis=0).flatten()
        pending = []
        pending_samples = 0
        # A very short tail (the leftover between the last chunk boundary
        # and Enter) carries no usable speech, and feeding it to Whisper
        # WITH context makes things worse: on near-silent audio Whisper
        # echoes its own prompt back, which produced duplicated final
        # chunks like "What does pure awareness mean?" twice in a row.
        if len(audio) < MIN_FINAL_CHUNK_SAMPLES:
            return
        t0 = time.time()
        # Feed everything transcribed so far as context so this chunk can
        # resolve words that started before its own boundary.
        text = _whisper_transcribe(audio, context=" ".join(transcript_parts))
        elapsed = time.time() - t0
        # Second guard on the same failure: if this chunk came back
        # identical to the previous one, it's prompt echo, not speech.
        if text and transcript_parts and text.strip() == transcript_parts[-1].strip():
            print(f"[dropped echoed chunk: \"{text[:40]}...\"]")
            return
        chunk_times.append(round(elapsed, 2))
        tag = "final chunk" if final else "chunk"
        print(f"[transcribe {tag}: {elapsed:.2f}s]", end="")
        if text:
            transcript_parts.append(text)
            print(f' - "{text}"')
        else:
            print()

    while not stop_flag.is_set():
        try:
            data = q.get(timeout=0.1)
        except queue.Empty:
            continue
        pending.append(data)
        pending_samples += len(data)
        total_samples += len(data)
        if pending_samples >= CHUNK_SAMPLES:
            flush_pending()

    stream.stop()
    stream.close()
    # Drain anything captured between the last queue read and the stream
    # actually stopping, then transcribe whatever's left - this final pass
    # only covers the short tail since the last chunk boundary, not the
    # whole utterance.
    while not q.empty():
        data = q.get()
        pending.append(data)
        pending_samples += len(data)
        total_samples += len(data)
    flush_pending(final=True)

    meta = {
        "audio_seconds": round(total_samples / 16000, 1),
        "chunks": len(chunk_times),
        "chunk_transcribe_s": chunk_times,
        "chunk_texts": transcript_parts if len(transcript_parts) > 1 else None,
        "gpu_transcription": bool(_whisper_server_available),
    }
    if not transcript_parts:
        return None, meta
    return " ".join(transcript_parts), meta

# --- Voice activity detection (only used when VOICE_ACTIVATED = True) -----
if VOICE_ACTIVATED:
    print("Setting up voice activity detection...")
    try:
        import webrtcvad
        _vad = webrtcvad.Vad(2)  # aggressiveness 0-3, 2 = moderate
        def is_speech_frame(frame_bytes):
            return _vad.is_speech(frame_bytes, 16000)
        print("[VAD: webrtcvad active]")
    except ImportError:
        print("[VAD: webrtcvad not installed - using a cruder energy-based fallback]")
        print("[For more reliable detection: pip install webrtcvad-wheels]")
        _ENERGY_THRESHOLD = 500  # int16 RMS - almost certainly needs tuning to your mic/room
        def is_speech_frame(frame_bytes):
            frame = np.frombuffer(frame_bytes, dtype=np.int16).astype(np.float32)
            return (np.sqrt(np.mean(frame ** 2)) if len(frame) else 0) > _ENERGY_THRESHOLD

def get_response_streaming(text, interrupt_event=None):
    """Streams tokens from Ollama, splits into sentences, queues each for
    speech as soon as it's complete. Returns the full reply text once done.

    If interrupt_event is given and gets set mid-stream (user started
    talking again in voice-activated mode), generation reading stops
    early and the safety-net/fallback logic below is skipped - we don't
    want to tack "say that again" onto a reply that was intentionally cut
    off by the user jumping in.

    The request/stream is wrapped in try/except: a dropped connection or
    Ollama crash used to raise an uncaught exception and kill the whole
    script. Now it's caught, logged, and falls through to the existing
    empty-reply safety net below instead."""
    num_predict = _next_turn_overrides.pop("num_predict", None)
    think_flag = _next_turn_overrides.pop("think", None)
    if num_predict is None:
        num_predict = DEEP_NUM_PREDICT if deep_mode["on"] else 160
    if think_flag is None:
        think_flag = deep_mode["on"]

    conversation.append({"role": "user", "content": text})

    buffer = ""
    full_reply = ""
    done_reason = ""
    first_token_time = None
    thinking_shown = False
    ollama_stats = {}
    request_sent_time = time.time()
    turn_timing["request_start"] = request_sent_time
    turn_timing["first_audio_time"] = None
    print("Sophia: ", end="", flush=True)

    try:
        resp = requests.post("http://localhost:11434/api/chat", json={
            "model": "qwen3.6:27b",
            "messages": conversation,
            "think": think_flag,
            "stream": True,
            # num_ctx stays pinned at 8192 in EVERY code path - see 2.13.
            "options": {"num_ctx": 8192, "num_predict": num_predict, "temperature": 0.3},
            "keep_alive": -1
        }, stream=True, timeout=120 if think_flag else 60)

        for line in resp.iter_lines():
            if interrupt_event is not None and interrupt_event.is_set():
                break
            if not line:
                continue
            chunk = json.loads(line)

            thinking = chunk.get("message", {}).get("thinking", "")
            if thinking:
                if not thinking_shown:
                    print("\n[thinking] ", end="", flush=True)
                    thinking_shown = True
                print(thinking, end="", flush=True)
                continue  # thinking tokens are not spoken, just shown

            token = chunk.get("message", {}).get("content", "")
            if token:
                if first_token_time is None:
                    first_token_time = time.time()
                    prefix = "\n" if thinking_shown else ""
                    print(f"{prefix}\n[time to first token: {first_token_time - request_sent_time:.2f}s]\nSophia: ", end="", flush=True)
                print(token, end="", flush=True)
                buffer += token
                full_reply += token

                # Check if buffer contains one or more complete sentences.
                # Abbreviation periods are protected first so "e.g." etc.
                # don't trigger a false sentence boundary.
                protected = protect_abbreviations(buffer)
                parts = SENTENCE_END.split(protected)
                if len(parts) > 1:
                    # All but the last part are complete sentences - queue them
                    for sentence in parts[:-1]:
                        sentence = restore_abbreviations(sentence.strip())
                        if sentence:
                            speech_queue.put((sentence, True))
                    buffer = restore_abbreviations(parts[-1])  # remainder stays in buffer
                elif len(buffer) > CLAUSE_THRESHOLD:
                    # No full sentence yet, but buffer is getting long - split on
                    # the last comma so audio can start sooner.
                    comma_parts = COMMA_SPLIT.split(buffer)
                    if len(comma_parts) > 1:
                        for clause in comma_parts[:-1]:
                            clause = clause.strip()
                            if clause:
                                speech_queue.put((clause, False))
                        buffer = comma_parts[-1]

            if chunk.get("done"):
                done_reason = chunk.get("done_reason", "")
                # Ollama's final chunk carries per-request performance
                # counters - keep the ones that matter for later analysis.
                # load_ms > ~1000 on a turn means the model runner was
                # RELOADED (the num_ctx-mismatch bug, or VRAM eviction) -
                # the exact thing that caused the 13-19s spikes pre-2.13.
                def _ms(key):
                    val = chunk.get(key)
                    return round(val / 1e6) if isinstance(val, (int, float)) else None
                ollama_stats = {
                    "prompt_eval_count": chunk.get("prompt_eval_count"),
                    "prompt_eval_ms": _ms("prompt_eval_duration"),
                    "eval_count": chunk.get("eval_count"),
                    "eval_ms": _ms("eval_duration"),
                    "load_ms": _ms("load_duration"),
                }
                if ollama_stats["eval_count"] and ollama_stats["eval_ms"]:
                    ollama_stats["tokens_per_s"] = round(
                        ollama_stats["eval_count"] / (ollama_stats["eval_ms"] / 1000), 1)
                break
    except requests.exceptions.RequestException as e:
        print(f"\n[connection error talking to Ollama: {e}]")
    except Exception as e:
        print(f"\n[unexpected error during response streaming: {e}]")

    interrupted = interrupt_event is not None and interrupt_event.is_set()
    empty_reply = False

    if interrupted:
        print("\n[cut off by interruption]")
    else:
        # Only speak whatever's left in the buffer if the model actually
        # finished its thought naturally. If it got cut off by the token
        # limit mid-sentence, speaking the fragment sounds broken - better
        # to drop it silently.
        if buffer.strip() and done_reason != "length":
            speech_queue.put((buffer.strip(), True))
        elif buffer.strip() and done_reason == "length":
            print(f"\n[trimmed incomplete fragment: \"{buffer.strip()}\"]")

        empty_reply = not full_reply.strip()
        if empty_reply:
            # Nothing was generated at all - don't fail silently, say so.
            # This also covers the connection-error case above, since
            # full_reply will still be empty if the request failed before
            # any tokens arrived.
            print("\n[no content generated - reasoning likely consumed the token budget, or the request failed]")
            speech_queue.put(("Say that again, I lost my train of thought.", True))

    print()  # newline after the streamed text
    conversation.append({"role": "assistant", "content": full_reply})

    # Perceived latency = request sent -> first audio actually playing.
    # The first sentence is usually synthesized and playing well before
    # generation finishes, so this is normally stamped by now; None means
    # audio hadn't started when generation completed (e.g. empty reply
    # whose fallback line was only just queued).
    first_audio = turn_timing["first_audio_time"]
    log_event(
        "assistant",
        full_reply,
        done_reason=done_reason,
        time_to_first_token=round(first_token_time - request_sent_time, 2) if first_token_time else None,
        time_to_first_audio=round(first_audio - request_sent_time, 2) if first_audio else None,
        trimmed=bool(buffer.strip() and done_reason == "length"),
        trimmed_fragment=buffer.strip() if (buffer.strip() and done_reason == "length") else None,
        empty_reply=empty_reply,
        interrupted=interrupted,
        think=think_flag,
        num_predict=num_predict,
        ollama=ollama_stats or None,
    )

    return full_reply

def voice_activated_loop():
    """Continuous-listening main loop: no push-to-talk, no 'new' command.
    Always exactly one background listener thread consuming the mic queue
    at a time - it detects speech onset almost immediately (setting a flag
    the main thread watches to interrupt Sophia) and keeps recording
    through trailing silence to capture the full utterance."""
    print("\n[Voice-activated mode - just start talking. You can interrupt Sophia any time by speaking.]\n")

    mic_queue = queue.Queue()
    def mic_callback(indata, frames, time_info, status):
        mic_queue.put(bytes(indata))
    mic_stream = sd.InputStream(samplerate=16000, channels=1, dtype="int16",
                                 blocksize=FRAME_SAMPLES, callback=mic_callback)
    mic_stream.start()

    def capture_utterance(onset_flag=None):
        ring_buffer = collections.deque(maxlen=SPEECH_START_FRAMES)
        voiced_run = 0
        silence_run = 0
        triggered = False
        recorded = []
        while True:
            frame_bytes = mic_queue.get()
            speech = is_speech_frame(frame_bytes)
            if not triggered:
                ring_buffer.append(frame_bytes)
                voiced_run = voiced_run + 1 if speech else 0
                if voiced_run >= SPEECH_START_FRAMES:
                    triggered = True
                    if onset_flag is not None:
                        onset_flag.set()
                    recorded.extend(ring_buffer)  # include pre-roll so the first word isn't clipped
                    silence_run = 0
            else:
                recorded.append(frame_bytes)
                silence_run = 0 if speech else silence_run + 1
                if silence_run >= SPEECH_END_FRAMES:
                    break
        pcm = b"".join(recorded)
        return np.frombuffer(pcm, dtype=np.int16).astype(np.float32) / 32768.0

    def drain(q):
        while not q.empty():
            try:
                q.get_nowait()
                q.task_done()
            except queue.Empty:
                break

    def start_listener():
        flag = threading.Event()
        box = queue.Queue(maxsize=1)
        def run():
            box.put(capture_utterance(flag))
        threading.Thread(target=run, daemon=True).start()
        return flag, box

    print("[listening...]")
    onset_flag, utterance_box = start_listener()

    try:
        while True:
            audio = utterance_box.get()
            print("Transcribing...")
            text = transcribe(audio)
            if not text.strip():
                print("[listening...]")
                onset_flag, utterance_box = start_listener()
                continue
            print(f"You: {text}")
            log_event("user", text, audio_seconds=round(len(audio) / 16000, 1))

            # Start listening for whatever comes next right away - this is
            # what makes barge-in possible while Sophia is still talking.
            onset_flag, utterance_box = start_listener()

            get_response_streaming(text, interrupt_event=onset_flag)

            while not onset_flag.is_set():
                if speech_queue.unfinished_tasks == 0 and audio_queue.unfinished_tasks == 0:
                    break
                time.sleep(0.05)

            if onset_flag.is_set():
                # Drop whatever hasn't played yet. The sentence already
                # mid-playback (if any) finishes rather than being hard-cut
                # - simpler and less jarring than an instant chop.
                drain(speech_queue)
                drain(audio_queue)
                print("\n[interrupted]")
            print("[listening...]")
    except KeyboardInterrupt:
        print("\n\nShutting down...")
    finally:
        mic_stream.stop()
        mic_stream.close()
        summarize_and_save_memory(conversation)
        print("Goodbye.")

print(f"\nSophia v{VERSION} — Ready.")
print(f"Logging this session to {LOG_PATH}")
log_event("session", "session started", version=VERSION, voice_activated=VOICE_ACTIVATED, config={
    # Snapshot of every setting that affects the numbers in this log, so
    # sessions stay comparable even after these values get tuned later.
    "model": "qwen3.6:27b",
    "num_ctx": 8192,
    "num_predict": 160,
    "temperature": 0.3,
    "voice": "af_bella",
    "speed": 1.25,
    "whisper_model": WHISPER_MODEL_SIZE,
    "chunk_seconds": CHUNK_SECONDS,
    "clause_threshold": CLAUSE_THRESHOLD,
    "sentence_pause_ms": round(len(SENTENCE_PAUSE) / 24),
    "clause_pause_ms": round(len(CLAUSE_PAUSE) / 24),
    "system_prompt_chars": len(conversation[0]["content"]),
})

if VOICE_ACTIVATED:
    voice_activated_loop()
else:
    print("Press Enter to start talking, Enter again to stop.")
    print("Commands:")
    print("  new       fresh opponent, context cleared")
    print("  deep      toggle thinking mode (slower, deeper)")
    print("  mod       speak to her as MODERATOR, not as her opponent - brief her")
    print("            ('your opponent is a priest', 'ease off the mockery') or ask")
    print("            her something out of character. Use 'mod <text>' to send inline.")
    print("  verdict   honest coach review of the exchange so far")
    print("  steelman  she rebuilds your argument at full strength, then attacks it\n")
    try:
        while True:
            cmd = input("\n[Enter = talk | new | deep | mod | verdict | steelman] ")
            command = cmd.strip().lower()

            # Typos like "newe" used to fall through and start recording,
            # silently NOT resetting the conversation. Anything that looks
            # like a mistyped command is caught and re-prompted instead.
            if command:
                known = ("new", "deep", "verdict", "steelman", "mod")
                if command not in known and not command.startswith("mod "):
                    close = [k for k in known if k.startswith(command[:3]) or command.startswith(k)]
                    print(f"Unknown command '{cmd.strip()}'."
                          + (f" Did you mean '{close[0]}'?" if close else "")
                          + " Press Enter alone to talk.")
                    continue

            if command == "deep":
                deep_mode["on"] = not deep_mode["on"]
                state = "ON - she thinks before answering. Expect 20-60s per turn." if deep_mode["on"] else "OFF - fast reflexive responses"
                print(f"--- Deep mode {state} ---")
                log_event("session", f"deep mode {'on' if deep_mode['on'] else 'off'}")
                continue

            if command == "mod" or command.startswith("mod "):
                # "mod <text>" sends inline; bare "mod" opens a prompt so
                # longer briefings can be pasted without fighting the
                # single-line command box.
                inline = cmd.strip()[4:].strip() if len(cmd.strip()) > 3 else ""
                if inline:
                    mod_text = inline
                else:
                    print("Moderator message (information, instruction, or a question for her).")
                    mod_text = input("> ").strip()
                if not mod_text:
                    print("Nothing sent.")
                    continue
                # Moderator turns get room to answer properly - they're
                # out-of-debate and not bound by the 45-word debate limit.
                _next_turn_overrides["num_predict"] = 400
                _next_turn_overrides["think"] = deep_mode["on"]
                print(f"[moderator] {mod_text}")
                log_event("moderator", mod_text)
                get_response_streaming(MODERATOR_PREFIX + mod_text)
                speech_queue.join()
                audio_queue.join()
                continue

            if command == "verdict":
                if not any(m["role"] == "user" for m in conversation):
                    print("Nothing to review yet - have an exchange first.")
                    continue
                # The verdict runs through the normal pipeline (spoken +
                # logged), but is removed from the conversation afterward
                # so stepping out of character doesn't soften her stance
                # for the rest of the debate.
                _next_turn_overrides["num_predict"] = 400
                _next_turn_overrides["think"] = deep_mode["on"]
                verdict_text = get_response_streaming(VERDICT_INSTRUCTION)
                speech_queue.join()
                audio_queue.join()
                conversation.pop()  # the verdict reply
                conversation.pop()  # the verdict instruction
                rating = parse_rating(verdict_text)
                # Logged separately from the spoken text so scores can be
                # tracked across sessions without re-parsing transcripts.
                log_event("verdict", verdict_text, rating=rating)
                if rating is not None:
                    print(f"--- Verdict delivered. RATING: {rating}/10. Debate context unchanged - carry on. ---")
                else:
                    print("--- Verdict delivered (no rating parsed). Debate context unchanged - carry on. ---")
                continue

            if command == "steelman":
                if not any(m["role"] == "user" for m in conversation):
                    print("Nothing to steelman yet - make an argument first.")
                    continue
                # Unlike verdict, this STAYS in the conversation - the
                # steelman becomes part of the debate she'll keep engaging.
                _next_turn_overrides["num_predict"] = 400
                _next_turn_overrides["think"] = deep_mode["on"]
                get_response_streaming(STEELMAN_INSTRUCTION)
                speech_queue.join()
                audio_queue.join()
                continue

            if command == "new":
                summarize_and_save_memory(conversation)
                conversation = [{"role": "system", "content": SYSTEM_PROMPT + load_memory_context()}]
                # The fresh memory entry just changed the system prompt, so
                # the cached prefix no longer matches - re-evaluate it in the
                # background now (~2-3s) rather than on the first turn of the
                # new debate. Copy the list so the thread never races against
                # the main loop appending to it.
                threading.Thread(target=prime_model, args=(list(conversation), "reset"), daemon=True).start()
                print("--- New opponent. Context cleared. ---")
                log_event("session", "conversation reset (new opponent)")
                continue
            print("Recording... press Enter to stop.")
            text, rec_meta = record_and_transcribe_live()
            if text is None:
                print("Didn't catch anything - try again.")
                continue
            print(f"You: {text}")
            log_event("user", text, **rec_meta)
            get_response_streaming(text)
            speech_queue.join()  # wait for all sentences to finish synthesizing
            audio_queue.join()   # wait for all synthesized audio to finish playing
    except KeyboardInterrupt:
        print("\n\nShutting down...")
    finally:
        summarize_and_save_memory(conversation)
        print("Goodbye.")
