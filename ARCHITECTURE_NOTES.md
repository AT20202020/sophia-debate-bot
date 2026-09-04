# Sophia — Architecture & Speed Review (Sept 2026)

Written after a deep pass on how other real-time voice AI projects (commercial
and open-source) actually achieve fast responses, checked against what
Sophia is already doing. Goal: an honest inventory, not a sales pitch for
whatever's newest. Sources are linked inline; general claims (not
Sophia-specific measurements) are marked accordingly since they're
industry benchmarks, not numbers from this machine.

## The headline finding: don't switch architectures

The most aggressive version of "a completely different approach" is an
end-to-end audio-native model — Moshi (Kyutai) or Sesame's CSM — that
skips the STT→LLM→TTS cascade entirely and processes speech in and out of
one model. These are real and they're fast: Moshi is reported around
160ms end-to-end on compatible hardware
([localaimaster](https://localaimaster.com/blog/moshi-realtime-speech-guide),
[ai.ksopyla.com](https://ai.ksopyla.com/posts/voice-to-voice-models-2026-review/)).

Two things rule it out for Sophia specifically, not on principle but on
the actual goal of this project:

1. **No AMD/ROCm support.** Moshi's own hardware guidance lists AMD as
   unsupported ("ROCm not yet") as of the sources checked. The 7900 XTX's
   24GB VRAM would be plenty if it ran — it doesn't run there today.
2. **Reasoning depth.** Even where it runs, these audio-native models are
   built around much smaller language backbones than a dedicated 27B text
   model — one comparison describes Moshi as "7B-level" reasoning. Sophia's
   entire value is rigorous philosophical argumentation: tracking a
   multi-turn dialectic, naming a specific fallacy, building a steelman.
   That's exactly the kind of task where a small audio-native model is
   reported to fall down — one benchmark cited in the same review scores a
   comparable model 1.26/5 on task adherence.

The middle-ground architecture — "Thinker-Talker" models like Qwen-Omni,
which separate a full reasoning model from a streaming voice head in one
system — is a real design and worth watching, but isn't yet something
you'd run today on Ollama/llama.cpp the way qwen3.8:27b is. Worth
revisiting in 6-12 months, not now.

**Conclusion: the cascade (STT → LLM → TTS) Sophia already uses is the
right architecture for a bot whose whole point is careful reasoning, not
just natural-sounding chat.** The same 2026 review put it plainly: this
cascade "remains production-viable" and hits sub-1-second latency with
proper streaming — which is the standard to hold Sophia's *implementation*
to, not a reason to replace the design.

One more reframe worth having explicitly: a chunk of the industry
material this pass turned up (Deepgram, OpenAI, Telnyx) is about
*network*-bound latency — round trips to a cloud API, WebSocket/QUIC
tuning, regional points-of-presence. None of that applies to Sophia:
everything runs on your own machine over loopback. That whole category of
"low-latency voice AI" advice is solving a problem Sophia doesn't have.

## What Sophia is already doing right (confirmed against production patterns)

- **Streaming LLM output straight into sentence-by-sentence TTS**, so
  audio starts before the full reply is generated. This is exactly the
  "ASR feeds LLM, LLM streams to TTS, TTS streams to output" pattern
  described as the core of low-latency pipelines
  ([Deepgram](https://deepgram.com/learn/low-latency-voice-ai)).
- **Kokoro for TTS.** Checked against current alternatives (F5-TTS,
  XTTS, Chatterbox, Piper, Bark): Kokoro's real-time factor (~0.03, i.e.
  ~30x faster than real-time) is reported as roughly 5x faster than
  F5-TTS and nothing else surveyed beats it on speed
  ([localaimaster](https://localaimaster.com/blog/best-local-tts-models)).
  There's no faster local option to switch to here — this part is already
  optimal.
- **Rolling chunked transcription while you're still talking** (the
  `CHUNK_SECONDS` push-to-talk design) is the same idea as "streaming
  ASR emits partial tokens while the user keeps speaking" — the
  production pattern, not a workaround.
- **GPU inference tuned**: 100% GPU offload confirmed, flash attention
  confirmed active in the server log, quantized KV cache on, and
  qwen3.8:27b ships speculative decoding (MTP) on by default. This is
  already a fully-tuned local LLM serving setup, not a naive one.
- **Push-to-talk sidesteps a whole category of latency work.** A lot of
  what "fast" voice bots spend engineering effort on is *knowing when the
  user has stopped talking* without waiting a fixed silence timeout (more
  below). Sophia's Enter-to-stop design gets that signal for free, at
  zero latency cost. This is a real, if accidental, advantage over
  voice-activated designs — worth keeping in mind before "upgrading" to
  hands-free.

## Meaningful things worth doing, in priority order

### 1. Fix the actual whisper hallucination class, not just the two tags we caught (low effort, do first)

This session already patched `[BLANK_AUDIO]`/`[SNIFF]` leaking into
transcripts. Turns out that's a well-documented, systemic Whisper failure
mode, not a one-off: "Whisper generates phantom text during silences —
words, phrases, sometimes entire sentences that were never spoken"
([onresonant.com](https://www.onresonant.com/resources/local-stt-models-2026)).
Our regex catches the *tagged* form. It won't catch Whisper inventing a
plausible-sounding sentence with no tag at all on a quiet chunk. Two
options, not mutually exclusive:
- Tighten `MIN_FINAL_CHUNK_SAMPLES`/add a simple energy-based silence gate
  before a chunk is even sent to Whisper (skip transcribing chunks that
  are near-silent, rather than trusting Whisper to say nothing).
- Consider Moonshine (see #2) specifically because it's reported to not
  have this failure mode by design, rather than needing to be patched
  around it.

### 2. Try Moonshine for the final (post-Enter) chunk specifically (medium effort, worth a real test)

Moonshine is a 245M-parameter streaming ASR model reported to match or
beat Whisper Large v3 on English benchmarks at a fraction of the size,
built specifically so "words appear as you speak them, with minimal
revision" — and explicitly recommended for push-to-talk-style short
utterances
([onresonant.com](https://www.onresonant.com/resources/local-stt-models-2026),
[yuv.ai](https://yuv.ai/blog/moonshine)). Two honest caveats before
committing to this: it's unconfirmed here whether Moonshine supports the
same `initial_prompt`/domain-vocabulary biasing `_whisper_transcribe()`
relies on (`DOMAIN_VOCAB_PROMPT`) for philosophy jargon, and it wasn't
checked against your specific whisper.cpp GPU server setup. Given that,
the sane test is small and reversible: try Moonshine as an *additional*
backend option specifically for the short final tail chunk (which is
exactly the short-utterance case it's built for, and exactly where the
`[BLANK_AUDIO]`-style hallucinations showed up), not a wholesale
replacement of the GPU whisper-server path that's already working well
for the bulk of a long utterance.

### 3. Leave TTS and the core Ollama serving setup alone

Both are already at or near the ceiling for local options, per the
research above. Further gains there would mean quantizing the LLM
further (a real logic/precision tradeoff, discussed and deliberately not
done this session) — not a free architecture change.

### 4. A tiered response budget: not every turn needs full "low" reasoning effort

This is the one genuinely new idea out of this research, not something
already half-done. Right now every ordinary turn gets the same reasoning
effort regardless of how simple the exchange is. Production voice bots
increasingly route trivial turns (acknowledgments, simple factual
questions, "wait, what do you mean by X") to a cheaper/faster path and
reserve full effort for turns that actually need it. For Sophia, a light
version of this could be: skip "low" reasoning entirely (still same
model, same prompt, same weights) for short/simple moderator exchanges or
direct definitional questions where the existing SYSTEM_PROMPT already
routes to a plain-answer mode — since those turns don't need adversarial
argument construction, they may not need explicit reasoning tokens either.
This wants real testing (via `sophia_eval.py`-style comparison, since
it's a behavior change) before trusting it, and is exactly the kind of
change that should be proposed and tested one variable at a time rather
than shipped speculatively — flagging it here as an idea, not doing it
without your go-ahead.

### 5. Semantic turn detection — relevant only if you ever move off push-to-talk

If voice-activated (hands-free) mode ever becomes the preferred way to
use Sophia, the fixed-silence-timeout VAD it currently falls back to
(when `webrtcvad` isn't installed) or even proper `webrtcvad` both share
the same weakness: waiting ~800ms of silence to be sure you're done
talking, on every single turn. The current open-source answer to this is
Smart Turn v3 (pipecat-ai), a small open, self-hostable model built
specifically to answer "has this person actually stopped talking" from
the audio itself — reported at under 60ms inference
([HuggingFace](https://huggingface.co/pipecat-ai/smart-turn-v3),
[daily.co](https://www.daily.co/blog/smart-turn-v2-faster-inference-and-13-new-languages-for-voice-ai/)).
Worth knowing about, not worth installing right now: push-to-talk's Enter
key already gives Sophia this exact signal for free, at zero latency and
zero extra dependency. This only pays off if the interaction model
changes.

### 6. Keep the perspective the research kept surfacing

One 2026 industry review put it directly: "latency is a solved problem at
this point... the real differentiators are conversational naturalness,
script adherence, and knowledge grounding" — not shaving another few
hundred milliseconds
([ai.ksopyla.com](https://ai.ksopyla.com/posts/voice-to-voice-models-2026-review/)).
Sophia's median time-to-first-token is already ~2.7s with a fully local
27B reasoning model doing real philosophical work — that's a genuinely
good number for what's being asked of it. The honest recommendation is
to spend further effort on #1/#2 (the STT hallucination class, since bad
input actively produces bad *arguments*, not just slow ones) and #4
(reasoning budget targeting) before chasing more raw speed for its own
sake.

## What this rules out, explicitly

- Switching to Moshi/CSM or any end-to-end audio model: wrong tool for a
  debate bot that needs real reasoning, and unsupported on this GPU today
  regardless.
- Chasing sub-second "voice AI agent" latency benchmarks: those numbers
  come from shallow customer-service-style bots and cloud deployments
  solving network latency Sophia doesn't have. Not a fair target.
- Further LLM quantization as a "free" win: it isn't free, it's a
  precision trade explicitly outside what was asked for ("keep this level
  of logic").
