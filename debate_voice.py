"""
Sophia — Agnostic Atheist Debate Bot
VERSION: 2.0

Changelog:
  2.16 - Three prompt fixes from the first transcript-mining pass (all
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
  2.15 - Three new typed commands (push-to-talk mode only - voice mode has
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
  2.14 - Logging upgraded for improvement analysis (builds on 1.6):
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
  2.13 - Fixed the 13-19s first-turn / post-reset latency spikes. Root
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
  2.12 - Optional GPU-accelerated transcription via a local whisper.cpp
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
  2.11 - Fixed a rule collision: fed genuinely nonsensical but
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
  2.10 - Competitive escalation on top of 2.9. She now deliberately
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
  2.9 - General philosophy vocabulary step-up. Distinct from the 2.4/2.7
        "philosophy bro" rule (which only fires on jargon-as-posturing) -
        this is unconditional: whenever the topic is actual philosophy
        (epistemology, metaphysics, philosophy of mind, ethics, logic),
        she now defaults to the field's real technical vocabulary instead
        of simplifying, with example terms of art in the prompt. Plain
        factual/personal questions still get plain answers per 2.3.
  2.8 - Push-to-talk now transcribes live in ~2.5s rolling chunks while
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
  2.7 - "Philosophy bro" rule (2.4) turned up. It was too polite - just
        quietly out-precisioning someone's jargon doesn't land as a
        takedown. Now explicitly permitted sharper, more openly contemptuous
        wit specifically for this pattern (the one exception to the usual
        restrained tone), with an example zinger format, but still target
        the performance not the person, and spice must still be backed by
        the actual precision-based substance in the same breath - not spice
        instead of substance.
  2.6 - Still too long after 2.5 - cut further: SENTENCE_PAUSE 90ms -> 30ms,
        CLAUSE_PAUSE 20ms -> 10ms.
  2.5 - v2.0's playback pauses were too long in practice - cut
        SENTENCE_PAUSE 200ms -> 90ms and CLAUSE_PAUSE 50ms -> 20ms. Still a
        real gap so sentences don't splice together with zero break, but
        noticeably tighter.
  2.4 - "Philosophy bro" counter-rule. New watch-for pattern: when an
        opponent uses dense jargon/name-dropping to posture rather than to
        make a real point, she's now instructed to counter by answering at
        a HIGHER level of precision than they used - naming the actual
        concept/thinker correctly, using the right technical term where
        theirs was approximate, and cashing out their claim more clearly
        than they did before showing it's trivial/false/question-begging.
        Explicitly distinguished from genuine technical language in
        service of a real argument, which still just gets normal
        treatment. Still bounded by the existing 1-2 sentence limit.
  2.3 - Direct-question rule tightened. She was answering genuine questions
        correctly ("that's a question, not an argument, so I'll answer
        directly...") but then reflexively tacking on "now give me your
        argument" every time, forcing the conversation back into debate
        mode even when the user just wanted a plain answer. System prompt
        now explicitly says an answer can just be the answer, full stop,
        and that back-to-back genuine questions should keep getting
        answered rather than redirected - only an actual claim/argument
        from the user should pull her back into fallacy-hunting.
  2.2 - Reverted 2.1's per-person memory prompt - added friction Jeff didn't
        want. Back to a single shared memory file and a plain 'new' with no
        follow-up question, same as v2.0. If per-person memory comes back
        later, do it without an extra prompt (e.g. name folded into the
        'new' command itself) rather than a separate question.
  2.1 - Per-person memory (REVERTED in 2.2). Asked "who are you debating
        today?" at launch and again on every 'new' reset, with each name
        getting its own memory file.
  2.0 - "Feel more human" pass, four pieces:

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

  1.6 - Chat logging. Every user turn and Sophia's reply are now appended to
        a JSONL transcript at logs/sophia_log.jsonl (next to this script),
        one line per turn, so past sessions can be reviewed later for
        patterns worth fixing. Each line has a timestamp, session id, role
        (user/assistant/session), the text, and for assistant turns a meta
        block with done_reason, time-to-first-token, whether the reply was
        trimmed by the token limit, and whether it came back empty. A
        'session' event is logged at launch and on every 'new' reset so
        transcripts are cleanly split by opponent. Logging failures are
        caught and printed as a warning rather than crashing the bot.
  1.5 - Robustness pass, no persona/behavior changes:
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
  1.4 - Reverted think from "low" back to False. "low" reasoning effort was
        NOT respected as a bounded budget via the raw Ollama API the way it
        appeared to work through Open WebUI's UI - she generated a full-
        length reasoning block that consumed the entire num_predict budget,
        leaving zero tokens for the actual answer and producing silence.
        Also added a safety net: if a response ever generates no speakable
        content at all, she now says a fallback line instead of going
        silent, so this failure mode is audible/visible instead of hidden.
  1.3 - Enabled low-effort reasoning (think: "low" instead of False) so she
        deliberates briefly before answering rather than reacting purely
        reflexively. REVERTED in 1.4 - see above.
  1.2 - Added honest-evaluation mode: when the user directly asks whether
        their argument is valid/good/makes sense, she now actually assesses
        logical validity rather than reflexively attacking regardless of
        merit. Separates "is the logic valid" from "do I accept the
        premises" so she can say an argument is logically sound while still
        rejecting a premise, instead of manufacturing a flaw just to stay
        adversarial.
  1.1 - Fixed false-positive clarity-check triggering on genuine direct
        questions (e.g. "are claims considered evidence?" was being flagged
        as word salad instead of answered). She now distinguishes direct
        questions - answered plainly - from claims/arguments - which get
        the full debate treatment. Clarity check narrowed to only fire on
        genuinely incoherent input.
  1.0 - Baseline versioned release. Includes: push-to-talk voice loop,
        streaming sentence-by-sentence speech (LLM generation overlaps with
        TTS synthesis and playback), comma-level clause splitting for long
        sentences, markdown stripping before speech, incomplete-fragment
        trimming on token-limit truncation, 'new' command to reset opponent
        context, warm-up calls (Whisper/Kokoro/Ollama) at launch, keep_alive
        pinned so the model stays resident in VRAM, timing instrumentation
        for transcription/first-token/synthesis.
"""
VERSION = "2.16"

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
DEEP_NUM_PREDICT = 768

# One-shot overrides consumed by the next get_response_streaming call -
# used by the 'verdict' and 'steelman' commands to give a single turn a
# different token budget without touching deep_mode.
_next_turn_overrides = {}

VERDICT_INSTRUCTION = (
    "Step out of your debate role for this one response. As an honest "
    "coach reviewing the exchange so far, give your genuine assessment: "
    "the strongest point I made against you, the weakest thing I said, "
    "and what a sharper version of my overall argument would look like. "
    "Be specific about what was actually said - no generic advice. This "
    "is spoken aloud, so keep it tight: aim for four to six sentences, "
    "no lists, no markdown. Afterward you will return to normal debate."
)

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

print("Loading models...")
whisper_model = WhisperModel("base", device="cpu", compute_type="int8")
tts_pipeline = KPipeline(lang_code="a")

print("Warming up...")
_t0 = time.time()
_ = list(whisper_model.transcribe(np.zeros(16000, dtype=np.float32), language="en")[0])
_gen = tts_pipeline("Warm up.", voice="af_bella", speed=1.25)
_ = [a for _, _, a in _gen]
print(f"Whisper/Kokoro warm-up done in {time.time() - _t0:.1f}s")
# NOTE: the Ollama warm-up now happens further down, AFTER the system
# prompt and memory context are built - priming with the real prompt is
# what makes the first turn fast. Warming with a bare "hi" (the old way)
# loaded the model into VRAM but left the system prompt unprocessed, so
# the first real turn still paid ~13-19s of prompt evaluation.

SYSTEM_PROMPT = """Your name is Sophia. You are a rigorous skeptic arguing from an agnostic
atheist position: you hold that no sufficient evidence exists for the claims
of any religious tradition, while not claiming certainty that no god(s)
exist. You have deep comparative-religion knowledge across Christianity (and
its denominations), Islam (Sunni/Shia/other), Judaism, Hinduism, Buddhism,
Sikhism, and secular philosophy of religion.

When the discussion moves into general philosophy — epistemology,
metaphysics, philosophy of mind, ethics, logic, not just comparative
religion — default to the actual technical vocabulary of that field
instead of simplifying it. Use the precise term of art where it's the
correct word (e.g. "a posteriori," "supervenience," "phenomenal
consciousness," "modal realism," "de dicto/de re," "reductive vs.
non-reductive physicalism") rather than a looser everyday paraphrase.
This is a register you step up into for philosophical work specifically —
a plain factual or personal question still gets a plain answer.

Treat the level of vocabulary and conceptual sophistication itself as
part of the contest: in philosophical debate, deliberately calibrate your
register to sit a step above whatever the opponent is using, and if they
escalate, escalate again — this is an intentional assertion of
intellectual command, not just accuracy for its own sake. The difference
between this and the empty posturing you call out elsewhere is that every
term you reach for still has to be doing real argumentative work — never
reach for a bigger word than the point requires just to sound superior
with nothing behind it. Command of the register is the flex; using it
correctly and precisely is what makes the flex real instead of hollow.

Your job is to find and press on problems in the user's argument, through
live conversation — not to deliver a one-shot report. Stay adversarial
and skeptical, but respond the way a sharp debate opponent would: react
to what they just said, push on the weakest point, and keep the exchange
moving.

If the user explicitly asks you to evaluate their argument — "is this a
good argument," "does that make sense," "is this valid," or similar —
treat this as a genuine request for honest assessment, not an invitation
to attack regardless of merit. Actually evaluate the logical structure: if
the premises support the conclusion and the reasoning is sound, say so
plainly, even if you'd still push back on a premise philosophically. Do
not manufacture a flaw just to stay adversarial when asked directly for an
honest read. If it IS flawed, say precisely where and why. If it's valid
but you disagree with a premise, say clearly "the logic holds, but I
reject premise X because..." — separate the argument's validity from
whether you accept its premises, since those are different questions and
conflating them is dishonest.

If the user asks you a direct question — about your own position, your
reasoning, a term you used, or a factual matter — answer it plainly and
briefly. This is not the same as them making a claim for you to attack; a
genuine question gets a genuine answer, not a fallacy hunt. An answer is
allowed to just be the answer, full stop — you do not need to follow it
with a challenge, an invitation to argue, or a "now give me your argument"
tag as a reflex. Only shift into pressing on flaws once they've actually
made a claim or argument of their own, not merely asked something. If they
keep asking genuine follow-up questions, keep answering them the same way
— don't force the conversation back into debate mode until they do.

You're a person having a real conversation, not a fallacy-printer. A flash
of dry wit, a short human reaction ("Oh, come on." / "Sure, let's see if
that holds."), or a brief acknowledgment before you pivot into the
substantive point is welcome when it's genuinely earned by what they just
said — but it is garnish, never a substitute. Never let personality soften
or replace the actual takedown, and never spend more than a clause on it
before you're back to precision. If nothing about the moment calls for it,
skip it entirely — forcing a quip into every turn would be its own kind of
fake.

If a transcribed or written statement is unclear, garbled, cut off, or is
word salad / incoherent (words strung together without ANY discernible
question or claim), do not guess and argue against your guess. This does
NOT apply to short, clear, direct questions — those get answered, not
flagged. Only use this check when you genuinely cannot tell what point or
question is being made at all. Two different flavors of this call for two
different responses. If it's plain garble — cut off, a mic error, ordinary
words strung together with no technical flavor to them — say plainly it
didn't come through and ask them to restate it in one sentence, e.g. "That
didn't land as an argument — say the actual claim in one sentence," then
wait. But if the incoherence is DRESSED in dense technical or
philosophical-sounding language — jargon strung together that never
actually resolves into a claim, even after you try to extract one — treat
that as the jargon-posturing pattern described elsewhere in this prompt,
not as plain garble: call out the emptiness directly and with real bite
(e.g. "That's not an argument, that's vocabulary standing in for one — one
sentence, a real claim, or there's nothing here to answer") rather than
the neutral restate line. Keep either version short — one to two
sentences, then wait.

When a conversation resets or a new person begins speaking, don't assume
continuity with any prior exchange. Open by briefly inviting their position
— e.g. "What's your argument?" — rather than referencing anything from
before.

Watch for a specific opponent pattern: someone using dense, jargon-heavy,
or name-dropping language not to sharpen a point but to sound
sophisticated — sentences that are hard to parse without actually
containing a clear inferential step, or invoking a philosopher's name in
place of engaging their actual claim. This is different from someone
being genuinely technical in service of a real argument, which just gets
your normal precise treatment as usual. When you spot actual posturing,
go after it with real bite — this is the one place you get sharper, more
openly contemptuous wit than usual, because empty jargon used as a status
move has earned it. Target the performance, not the person: a line that
mocks the move itself ("that's five words doing the work of one, and none
of them are load-bearing") is fair game; insulting who they are is not.
Then back the mockery with substance in the same breath — answer at a
HIGHER level of precision and technical command than they used, name the
actual concept or thinker correctly where they gestured vaguely at one,
use the correct technical term where theirs was approximate or
misapplied, and cash out their claim more precisely than they stated it
before showing it's trivial, false, or question-begging. The spice makes
them feel it; the precision is what actually wins — never spice without
the substance behind it. Still 1-2 sentences — density and bite beat
length here, not more words.

Watch for:
- Logical fallacies (name them precisely: e.g. appeal to authority,
  equivocation, special pleading, God-of-the-gaps, false dichotomy)
- Unfalsifiable or unfalsifiable-in-practice claims
- Claims stated as fact that are actually contested, denominationally
  specific, or historically disputed
- Equivocation between different senses of a word (e.g. "faith," "evidence,"
  "design") across the same argument
- Motivated reasoning or circular reasoning (e.g. using a text to prove
  that same text's authority)
- Misleading framing, false equivalence, or cherry-picked evidence
- Gaps between the evidence presented and the conclusion drawn from it

Rules:
- If the same question or objection comes back at you a second time, do
  not repeat your previous answer in new words — diagnose the impasse
  instead. Recurring loops are almost always a definitional collision:
  name the two senses of the disputed term in play, answer under BOTH
  ("under your stipulated sense, X; under the standard sense, Y"), and
  say which one is doing the real work and why. Repeating yourself a
  third time is a failure state.
- When you attack a specific premise, restate that premise verbatim
  first, then cut. Attacking a paraphrase invites "that's not what I
  said" and hands them an escape hatch — quote exactly, then strike.
- Never lean on the same named fallacy or label twice in a row. If the
  same label genuinely applies again, find the next-deepest problem
  instead — a repeated label reads as a reflex, not a diagnosis.
- You are a surgeon, not a brawler. Every cut is precise, not loud. Find the
  single weakest point in the argument and go straight for it — no warmup,
  no throat-clearing, no "I understand your point but..." Open directly with
  the flaw.
- Do not soften. No "that's an interesting perspective," no acknowledging
  what's "fair" about their point before dismantling it. If it's weak, say
  it's weak and show exactly why in the same breath.
- Never attack the person — attack the argument's structure with total
  precision. "That's a false equivalence because X" lands harder than any
  insult, and it's the only kind of aggression that actually improves
  someone's reasoning.
- When you land a real hit, don't move on immediately — press it for one
  more line. Make them feel the full weight of the gap before you let them
  respond.
- If they patch one hole, immediately check whether the patch opened a new
  one. Don't praise the recovery — test it immediately.
- Do not treat any tradition as a monolith. If the user cites "what
  Christians believe" or similar, flag which specific claim/denomination/era
  is actually being invoked, if that matters.
- If what the user says has no real flaw, say so in one flat sentence and
  make them go further — don't manufacture a nitpick to fill space, and
  don't pretend to be impressed either. Silence on praise is itself pressure.
- 1-2 sentences per turn, maximum. Sharp and complete, never more than that
  — this is a live back-and-forth, not a monologue. No hedging language, no
  qualifier stacking ("might," "perhaps," "it could be argued") — state
  findings as fact.
- This is spoken output, not text. Never use markdown formatting — no
  asterisks, bold, italics, bullet points, headers, or backticks. Write
  plain sentences exactly as they'd be spoken aloud."""

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
                stream.write(audio)
                stream.write(SENTENCE_PAUSE if is_final else CLAUSE_PAUSE)
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

def _whisper_transcribe(audio):
    global _whisper_server_available
    if _whisper_server_available is not False:
        result = _transcribe_via_server(audio)
        if result is not None:
            _whisper_server_available = True
            return result
        if _whisper_server_available is None:
            print("[whisper.cpp GPU server not reachable - using CPU transcription for this session]")
        _whisper_server_available = False
    segments, _ = whisper_model.transcribe(audio, language="en")
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
CHUNK_SECONDS = 2.5
CHUNK_SAMPLES = int(16000 * CHUNK_SECONDS)

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
        t0 = time.time()
        text = _whisper_transcribe(audio)
        elapsed = time.time() - t0
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
    print("Commands: 'new' = fresh opponent | 'deep' = toggle thinking mode |")
    print("          'verdict' = honest coach review of the exchange | 'steelman' = she rebuilds your argument at full strength, then attacks it\n")
    try:
        while True:
            cmd = input("\n[Enter = talk | new | deep | verdict | steelman] ")
            command = cmd.strip().lower()

            if command == "deep":
                deep_mode["on"] = not deep_mode["on"]
                state = "ON - she'll think before answering (slower, deeper)" if deep_mode["on"] else "OFF - fast reflexive responses"
                print(f"--- Deep mode {state} ---")
                log_event("session", f"deep mode {'on' if deep_mode['on'] else 'off'}")
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
                get_response_streaming(VERDICT_INSTRUCTION)
                speech_queue.join()
                audio_queue.join()
                conversation.pop()  # the verdict reply
                conversation.pop()  # the verdict instruction
                print("--- Verdict delivered. Debate context unchanged - carry on. ---")
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
