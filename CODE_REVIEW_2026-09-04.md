# Sophia v2.42 — code-grounded review (2026-09-04)

Scope: read debate_voice.py (all 1727 lines), Start Sophia.bat (both copies),
requirements.txt, sophia_eval.py, README.md, CHANGELOG.md, ARCHITECTURE_NOTES.md,
and mined logs/sophia_log.jsonl (823 rows, 28 sessions) because several premises
in the brief turned out to be from the qwen3.6 era. Line numbers refer to the
current debate_voice.py. Confidence labels: VERIFIED = seen in code or log;
INFERRED = reasoning from documented library behavior, not run here.

## 0. Headline correction: the brief's latency numbers are pre-qwen3.8

From the log, assistant turns with Ollama counters:

| sessions | model | turns | TTFT median | time-to-first-audio | eval_count | est. thinking tokens | reply words |
|---|---|---|---|---|---|---|---|
| v2.30-2.35 (Aug 28) | qwen3.6, think=False | 135 | 2.63-2.72s | 3.25-3.8s | 33-38 | ~2 | 23-25 |
| v2.39 (Sep 4, 17:42-18:08) | qwen3.8, think="low" | 21 | 7.99s | 7.74s | 246 | ~200 | 33 |

Tail transcription (GPU server) 2.13s vs 1.55s (CPU). So Enter-to-voice is
~10s now vs ~4.9s before the model swap, and ~5s of it is the "low" reasoning
block (~200 tokens at ~38 tok/s). TTS is not the bottleneck: time-to-first-audio
minus TTFT is 0.5s. The v2.38 changelog predicted 2.5-3s of thinking; the real
session shows about double that. Everything below is ranked against this.

## 1. The GPU whisper-server path is slower than CPU AND silently discards the vocabulary prompt and chunk context — VERIFIED

- `_transcribe_via_server()` (L1040-1066) posts only `file` and
  `response_format`. `DOMAIN_VOCAB_PROMPT` and the `context` argument are used
  only in the CPU branch (L1113-1126). When the server answers, the function
  returns at L1108 before either is ever applied.
- Log: `gpu_transcription: true` on every user turn since v2.38 (Sep 1 onward).
  Per-chunk time is 2.12s ± 0.03 across 79 chunks regardless of audio length
  (min 2.07, max 2.8), vs 1.54-1.85s median on the CPU path in the Aug 28
  sessions. A dead-flat 2.1s for a 244M model on a 7900 XTX smells like the
  server is not actually on Vulkan (ggml-cpu.dll fallback) or is running
  whisper.cpp's slower defaults — check the whisper-server console for a
  `ggml_vulkan: Found N Vulkan devices` line, and time one curl by hand.
- Consequence: v2.18's two strongest accuracy levers (vocab biasing, chunk
  context) have been off in every session since the server went in. The
  v2.36 "definiens" vocab fix cannot have taken effect. And the reason
  Moonshine was rejected (no prompt biasing) already describes the path in use.
- Fix options: (a) send `prompt` as a multipart field — whisper-server's
  /inference accepts `prompt`, `temperature`, `temperature_inc` (INFERRED from
  whisper.cpp's server example; confirm with `whisper-server.exe --help`); or
  (b) stop the launcher from starting it and let faster-whisper run — an
  immediate ~0.6s/turn win plus vocab/context back, zero code. Either way, the
  startup warm-up (L351) only exercises the CPU model, so the server's first
  call is cold.
- Cost if wrong: none for (b); (a) is one form field.

## 2. Cross-session memory has been silently dead since the qwen3.8 migration — VERIFIED

- `summarize_and_save_memory()` L753 sends `think: "low"` with `num_predict: 80`.
  qwen3.8 spends 58-404 thinking tokens per turn in the log (the shortest
  v2.39 reply, 12 words, used 194 tokens). 80 tokens is consumed entirely by
  reasoning, `content` comes back empty, and L757 `if not summary: return`
  swallows it with no message.
- Evidence: memory/sophia_memory.jsonl's last entry is 2026-08-29 00:01. The
  Sep 4 17:42 session ran 19 user turns and then `new` at 18:08:40, which calls
  the summarizer on a full conversation — nothing was written.
- This is the third instance of the exact bug class fixed in v2.38/v2.39/v2.41,
  in the one remaining Ollama call that wasn't audited. Fix: `num_predict`
  ~400, and print `done_reason` when the summary comes back empty so the next
  regression is visible.
- The same class exists in check_ollama_cache.py and profile_latency.py — see #9.

## 3. If no output stream opens, the bot hangs on its first turn instead of running silent — VERIFIED

- `playback_worker()` L927-931 returns on open failure ("audio is disabled this
  session"). Nothing else consumes `audio_queue`, so the main loop's
  `audio_queue.join()` (L1722; also L1660/1675/1698) blocks forever after the
  first sentence is synthesized. The message promises degraded operation; the
  behavior is a silent freeze.
- Who hits it: a cloner with no output device, a headless box, or any machine
  where all three fallback tiers fail (which v2.29 showed is possible).
- Fix: on open failure keep looping, `get()` items and `task_done()` them
  (optionally print the text), or set a flag that makes `synth_worker` skip
  the `audio_queue.put`.

## 4. First turn of every qwen3.8 session re-evaluates the entire prompt (~5.4s) — VERIFIED symptom, cause INFERRED

- First-turn `prompt_eval_ms` per session, qwen3.8: 5526, 5473, 179, 5433,
  5359 (steady state ~370). `load_ms` is 3 on all of them, so this is not the
  v2.13 runner reload — it's a KV-cache miss on the primed prefix. In the
  qwen3.6 era first turns were 1.2-1.4s vs 0.28 steady, so priming was only
  ever partially effective; on qwen3.8 it is not landing at all.
- The one hit (17:42 session, 179ms) was launched one minute after another
  launch had already primed — consistent with a slot/cache-selection issue
  rather than a prompt mismatch. Cheapest test: add `OLLAMA_NUM_PARALLEL=1`
  to the launcher env block (only effective when the launcher starts Ollama —
  see #10) and check server.log for the slot/cache lines around the first
  request. Also worth trying: prime with a request shaped like a real turn
  (system + one user message) rather than system-only.
- Combined with #5, the first turn after launch is currently 13-23s to voice.

## 5. Thinking is half the wait; the blocker on "skip reasoning" is unverified, not verified-impossible — VERIFIED cost, INFERRED fix

- ~200 thinking tokens median ≈ 5s per turn. ARCHITECTURE_NOTES #4 correctly
  refuses to guess in the live bot, and says the right next step is a
  controlled probe against /api/chat. That probe is ~30 lines: send the real
  prompt with `think` = `false`, omitted, `"none"`, `"minimal"` and report,
  for each, HTTP status, whether a `thinking` field appears, `eval_count`,
  `done_reason`, and the content. Two minutes on your machine settles what
  has been an open question for four versions. I can write it if you want.
- If a no-think mode exists, apply it deterministically from code (question
  mark / "what does X mean" / "I don't understand" detected in the
  transcript, plus `mod`), not from the model's own routing judgment — this is
  also the "if it recurs a fourth time, do it in code" plan already in the
  persona notes, and it keeps the retry safety net.
- Cost: reasoning quality on turns the detector misroutes; reopening the
  empty-reply class if the setting behaves like v1.3's "low" — which is why
  it must be probed outside the bot first.

## 6. NORMAL_NUM_PREDICT=450 still clips ~1 in 10 turns, and the retry costs 23s when it fires — VERIFIED

- v2.39 session: one empty-at-450 → retry at 900 (TTFT 23.4s, the first turn
  of the debate), one trim at 450 ("You're smuggling in the conclusion."
  dropped), two trims at the stale 400 (fixed in v2.41). Thinking on normal
  turns ranged 58-404 tokens.
- `num_predict` is a ceiling; raising it to ~800 costs nothing on turns that
  finish. The retry only fires on fully-empty replies, so a trimmed last
  sentence is currently just lost. Cost: a pathological turn runs longer
  before failing.

## 7. faster-whisper truncates the prompt from the FRONT, so the vocab list loses its head on every chunk after the first — INFERRED mechanism, VERIFIED code

- faster-whisper keeps only the last `max_length//2 - 1` = 223 tokens of
  `initial_prompt`. L1116 builds `f"{DOMAIN_VOCAB_PROMPT} {context[-300:]}"` —
  vocab first, context after — so when the total exceeds 223 tokens the part
  discarded is the START of the vocab list: "theist, atheist, agnostic,
  contingency, contingent, necessary being, cosmological argument..." — the
  exact v2.18 mishearings. My estimate is ~190-210 tokens for the vocab alone
  (GPT-2 BPE on rare words) plus ~70 for 300 chars of context; I could not
  fetch the tokenizer from this environment to count exactly. One-liner in
  the venv: `from faster_whisper import WhisperModel; m=WhisperModel("small.en",device="cpu",compute_type="int8"); print(len(m.hf_tokenizer.encode(" "+PROMPT).ids))`.
- Fix: cut the vocab list to terms Whisper actually mishears (drop "valid,
  sound, premise, conclusion, analytic, synthetic, multiverse, emergence"
  etc.), cap context at ~150 chars, and assert the combined token count at
  startup. L310's comment ("under ~200 words") states the wrong limit and the
  wrong unit. The same last-N truncation applies in whisper.cpp if #1a is done.

## 8. Dropping tails under 0.5s can lose the last word — INFERRED

- L1203 drops any final tail shorter than 0.5s. That guard was added (v2.24)
  for near-silent tails echoing the prompt; v2.42's RMS gate now handles that
  case before Whisper is called. What the guard still does is discard a
  0.3-0.5s tail that contains the last word when the utterance ends just past
  a 6s boundary. Fix: lower to ~0.15s and rely on the gate, or carry the last
  ~1s of the previous chunk's audio into the tail so a boundary word gets
  both halves.

## 9. Both diagnostic scripts are stale enough to mislead — VERIFIED

- check_ollama_cache.py and profile_latency.py still use `qwen3.6:27b`,
  `num_ctx: 8192`, `think: False`. Running profile_latency.py today would force
  a runner reload (mismatched num_ctx) and send a boolean think — it would
  measure the two bugs this project already fixed, not the ~2-2.5s unexplained
  gap it was written for (which is still present on qwen3.8: TTFT 7.99 minus
  ~0.37 prompt eval minus ~5.1s thinking leaves ~2.5s).
- Fix: a tiny `sophia_config.py` holding MODEL, NUM_CTX, and `_think_effort`,
  imported by debate_voice.py, sophia_eval.py and both diagnostics. That also
  collapses the model name from six places (four in debate_voice.py, the .bat,
  the eval) to one.

## 10. Launcher env block: two of four variables don't do what the comment says — INFERRED (medium-high)

- `AMD_SERIALIZE_KERNEL=3` is a ROCm/HIP debugging flag that serializes kernel
  launches (wait before and after each enqueue). It is used to debug hangs;
  it slows execution, it never speeds it up.
- `HSA_OVERRIDE_GFX_VERSION=11.0.0` is a no-op on a real gfx1100 (7900 XTX)
  and is NOT harmless on other AMD cards: an RDNA2 user (RX 6000, gfx1030)
  starting Ollama through this launcher would get gfx1100 kernels loaded on
  the wrong architecture.
- Neither variable (nor OLLAMA_FLASH_ATTENTION / KV type) reaches Ollama when
  it is already running as the Windows tray app, which is the default
  install behavior. If that's your setup, the flash-attention confirmation in
  server.log is Ollama's own default, not the launcher's doing. Verify from
  server.log's startup env dump, then A/B tok/s with AMD_SERIALIZE_KERNEL
  unset. Recommend keeping OLLAMA_FLASH_ATTENTION and OLLAMA_KV_CACHE_TYPE,
  dropping the other two (or gating them on a GPU check).

## 11. SYSTEM_PROMPT critique (routing logic)

a. The mechanical mode-1 tie-breaker (L441-447: "if there is a question
   anywhere in the turn, you are in mode 1, full stop") swallows mode 2:
   "is this valid?" is a question, so by the letter it routes to "answer
   plainly, then STOP, no finding the weakest point" — the opposite of mode
   2's "if it is flawed, say precisely where." It also captures rhetorical
   questions inside arguments ("how could a timeless being act?"), forcing a
   plain answer where the person was arguing. In practice the model mostly
   handles it, but the text fights itself, and this is the section the
   persona notes flag as the most-patched. Scope the tie-breaker to questions
   asked OF Sophia for information, and state that an evaluation request
   wins over mode 1 — or move the routing into code (#5).
b. Two different defaults for uncertainty: "When genuinely unsure, answer"
   (L447) vs mode 3's "If you cannot tell which, assume transcription failure
   and ask them to restate" (L508).
c. Direct contradiction at the prompt's end: L700-702 says "On a reset or a
   new speaker, assume no continuity with any prior exchange... rather than
   referencing anything from before," and `load_memory_context()` appends
   immediately after it "You have spoken with this user in past debate
   sessions... recall of what came up before." The memory block is also
   phrased "this user" while `new` means a new opponent and the file is
   shared. Once #2 is fixed and memory starts working again, this collision
   is live.
d. Mode 4 has no length bound ("more room than a debate turn allows"), and
   `mod` turns get 900 tokens. Log: the three v2.41 mod replies were 217,
   429, and 290 words — 1.5-3 minutes of audio each. A soft cap ("four to six
   sentences unless the moderator asks for more") would match verdict.
e. `verdict` and `steelman` arrive as plain user messages that the routing
   procedure has no mode for; they work by instruction-following, which the
   v2.19 history shows is the fragile mechanism. Sending them with
   MODERATOR_PREFIX puts them inside mode 4, which already grants
   out-of-character voice and extra room.
f. The BITE block and the criterion-of-embarrassment example are permanent
   payload on every request for topics that come up occasionally. Cheap
   alternative once a per-turn nudge mechanism exists (#5): inject reference
   blocks only when a keyword appears in the transcript, appended to the
   user message so the cached system-prompt prefix is untouched.
g. Minor tension: "restate a premise verbatim before cutting it" vs "1-2
   sentences, ten seconds aloud" — a long premise quoted verbatim eats the
   whole budget.

## 12. Smaller code issues — VERIFIED

- L1453 appends `{"role":"assistant","content": ""}` after an empty reply or
  connection error; the spoken fallback line isn't what goes in history, an
  empty assistant turn is. Pop the user message or append the fallback text.
- Interrupt path (L1335) breaks out of `iter_lines()` without `resp.close()`,
  so Ollama keeps generating the abandoned reply until GC closes the socket —
  the next request queues behind it. Voice-activated mode only.
- Echo guard (L1212) drops any chunk identical to the previous one, including
  a legitimate "No. No." It exists for the context-echo case, which only
  happens on the CPU path with context.
- `SENTENCE_END` (L977) requires the sentence terminator to be immediately
  before whitespace, so `..." She` (period inside a closing quote) doesn't
  split until the following sentence ends — the first-audio delay for replies
  that open with a quotation. Two fixed-width lookbehinds handle it.
- The CPU Whisper model and its warm-up (~480MB, several seconds) load even
  when the server is going to be used; fine as fallback, but the warm-up
  should also hit the server when it's reachable.
- Input stream (L1176) uses PortAudio's MME default, the same class of stale
  device index that v2.29 fixed on the output side. Not seen failing; noted.
- `_next_turn_overrides["think"]` for `mod`/`verdict`/`steelman` is always
  what the default would compute anyway.

## 13. Cold-clone / portability gaps

- `.requirements.sha256` lives next to the script, not in the venv. Delete
  `sophia-env` to reinstall and the launcher recreates an empty venv, sees an
  unchanged hash, skips pip, and debate_voice.py dies on `import sounddevice`.
  Write the hash inside the venv folder (or delete it when creating the venv).
- requirements.txt is unpinned (`faster-whisper`, `kokoro`, `numpy`...). The
  hash-check means pinning costs one reinstall, and it protects a stranger
  from numpy/ctranslate2/torch drift a year from now.
- README drift: "~2.5s chunks" (CHUNK_SECONDS is 6.0), "Typical response
  latency is ~2.6s from end of speech to first audio" (log says ~10s on the
  current model). A cloner will judge their setup as broken against that.
- The whisper-server section tells people to build a Vulkan whisper.cpp; per
  #1 the result today is slower and vocabulary-blind. Either fix #1 or label
  it experimental.
- Ollama tray autostart makes the launcher's env block a no-op for most
  Windows users (#10); say so in the README or write the vars with `setx`.
- Any machine without an openable output device hangs (#3).
- Windows-only launcher; the manual steps cover Linux/macOS adequately.

## 14. Testing and evaluation gaps

- debate_voice.py runs at import (loads Whisper/Kokoro, primes Ollama, starts
  threads). Nothing pure — `parse_rating`, the sentence splitter,
  `_strip_nonspeech_tags`, `_is_effectively_silent`, `_trim_silence` — can be
  unit-tested without a GPU. A `main()` guard plus a `test_helpers.py` gives
  a zero-model test layer; sophia_eval.py already has to scrape the prompt
  out as text because of this.
- sophia_eval.py: single-turn only (the v2.16 impasse/label-repetition/
  opener-variety rules and v2.24's concede-when-caught are multi-turn by
  definition); no mechanical assertions (ends with `?`, sentence count,
  markdown chars, the four banned mode-3 phrases, `done_reason == "length"`,
  empty content — all deterministic and cheap); it tests the bare
  SYSTEM_PROMPT, not the live prompt with the memory block appended (#11c);
  writes nothing to disk, so runs can't be diffed; no case for the mode-1/
  mode-2 collision (#11a), a rhetorical question inside an argument,
  evidentialism-cuts-both-ways in mode 5 (the case that failed live), or a
  homophone that should be silently reconstructed.
- No metrics script: the per-version table at the top of this review is a
  40-line pass over the JSONL and would have shown the v2.38 latency change
  and the dead memory file immediately. Worth keeping next to
  export_transcripts.py.
- STT has no ground truth, which is the stated blocker for Moonshine and for
  judging vocab-prompt changes. Twenty recorded philosophy sentences with
  reference text is a one-time 15-minute job; after that, backend and prompt
  changes get a WER number instead of a guess.

## On "a genuinely different architecture"

No. The log decomposes the wait as ~5s thinking + ~2.1s tail transcription +
~2.5s fixed Ollama gap + 0.5s TTS. None of that is the cascade's fault, and
the notes' reasoning on Moshi/CSM holds. The only architecture-adjacent change
worth naming: a silence-triggered early flush inside
`record_and_transcribe_live()` — when the pending buffer ends in ~700ms below
SILENCE_RMS_THRESHOLD, flush it then, so the tail is usually transcribed by
the time you reach for Enter (hides most of the 1.5-2.1s). Push-to-talk
semantics are unchanged; nothing is sent until Enter. Cost: extra Whisper
calls at mid-sentence pauses, slightly more boundary risk. A step further —
speculatively starting the LLM request on the flushed transcript and
cancelling if speech resumes — would also hide part of the thinking, but it
competes with the next request for the GPU and needs #4 sorted first.

## Suggested order

1. #2 memory (one number). 2. #1 decide fix-vs-disable the server. 3. #3
playback hang. 4. #6 budget. 5. #5 probe script. 6. #4 priming test.
Everything else after a fresh log from those.
