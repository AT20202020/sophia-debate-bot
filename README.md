# Sophia — Local Voice Debate Bot

Sophia is a fully local, voice-to-voice philosophy debate opponent. She argues from an agnostic-atheist position with deep comparative-religion knowledge, names fallacies precisely, escalates her technical vocabulary to match (and outdo) her opponent, and remembers past debates. Everything runs on your own machine — no cloud APIs, no data leaves your PC.

```
mic (push-to-talk) → faster-whisper (STT) → Ollama (LLM, streaming)
                   → Kokoro (TTS, sentence-by-sentence) → speakers
```

Speech starts playing while the LLM is still generating: tokens stream in, complete sentences are synthesized and queued immediately, and synthesis of the next sentence overlaps playback of the current one. Typical response latency is ~2.6s from end of speech to first audio on an RX 7900 XTX running qwen3.8:27b.

## Features

- **Push-to-talk voice loop** — Enter to talk, Enter to stop. Deliberate design: after each response you can discuss with people in the room without the bot reacting. An experimental voice-activated mode with barge-in interruption exists behind a flag (`VOICE_ACTIVATED`).
- **Live rolling transcription** — speech is transcribed in ~2.5s chunks *while you're still talking*, so the wait after you stop doesn't grow with how long you spoke.
- **A tuned debate persona** — surgeon-not-brawler precision, honest evaluation when you ask "is my argument valid?", plain answers to plain questions, impasse diagnosis instead of repetition, verbatim premise quoting before attack, a counter for jargon-posturing opponents, and deliberate vocabulary escalation in philosophical exchanges.
- **Cross-session memory** — she summarizes each debate and folds recent summaries into her context at launch, so she can reference what you argued last time.
- **Typed commands** at the talk prompt:
  - `new` — fresh opponent, context cleared (saves a memory summary first)
  - `deep` — toggle thinking mode: she reasons before answering (slower, deeper)
  - `mod` — speak to her as **moderator** rather than opponent: brief her ("your opponent is a Catholic priest", "ease off the mockery"), correct a mistranscription, or ask her something out of character. Briefings are applied, never argued with. `mod <text>` sends inline.
  - `verdict` — she steps out of character and coaches: your strongest point, weakest moment, and what a sharper version of your argument would look like
  - `steelman` — she rebuilds the strongest version of your argument, then attacks *that*
- **Structured JSONL logging** — full transcripts plus per-turn diagnostics (time-to-first-token, time-to-first-audio, Ollama eval counters, model-reload detection, transcription chunk timing) for later analysis.
- **Optional GPU transcription** — auto-detects a local [whisper.cpp](https://github.com/ggml-org/whisper.cpp) server built with Vulkan support (works on AMD/NVIDIA/Intel GPUs with Vulkan drivers, not just one vendor) and falls back to CPU transparently. `Start Sophia.bat` auto-starts it for you if it's set up - see below.

## Prerequisites

**Hardware:** a GPU with enough VRAM for your chosen LLM (24GB runs a 27B model comfortably; smaller models work on less — edit the model strings in `debate_voice.py`), a microphone, and speakers/headphones.

**Software, in order:**

1. **Python ≥3.10 and <3.13** — this is a hard requirement of the `kokoro` package, not a suggestion; 3.13 will fail to install it. 3.12 is what this project is tested on.
2. **[Ollama](https://ollama.com)** installed and able to run, with a model pulled (default: `qwen3.8:27b`).
3. **[espeak-ng](https://github.com/espeak-ng/espeak-ng/releases)** — required by Kokoro for phonemization of out-of-dictionary words. On Windows: download the latest `.msi` from the releases page and run it. On Debian/Ubuntu: `sudo apt install espeak-ng`.
4. **Linux only:** PortAudio for the mic/speaker streams — `sudo apt install libportaudio2`. (Windows wheels bundle it.)

**Notes:**
- `pip install -r requirements.txt` pulls PyTorch automatically as a Kokoro dependency. CPU-only torch is fine — the TTS model is only 82M parameters.
- **First launch needs internet**: faster-whisper downloads its `small.en` model and Kokoro downloads its weights (~570MB total) from Hugging Face. After that, everything runs offline.
- The launcher `.bat` uses `curl`, which is built into Windows 10+.

## Setup

```powershell
# 1. Create a venv with Python 3.12
py -3.12 -m venv sophia-env

# 2. Install dependencies (call the venv's python directly - avoids
#    PowerShell execution-policy issues with activation scripts)
.\sophia-env\Scripts\python.exe -m pip install -r requirements.txt

# 3. Pull the model
ollama pull qwen3.8:27b

# 4. Run
.\sophia-env\Scripts\python.exe debate_voice.py
```

Or use `Start Sophia.bat` (edit `VENV_PYTHON` at the top to point at your venv) — it checks that Ollama is up, starts it if not, and launches the bot.

### Optional: GPU-accelerated transcription

By default Sophia transcribes on CPU via `faster-whisper` - works fine, no setup needed. For faster transcription on your GPU:

1. Build [whisper.cpp](https://github.com/ggml-org/whisper.cpp) with Vulkan support (works across AMD/NVIDIA/Intel, not vendor-specific).
2. Create a `whisper-server` folder next to `debate_voice.py` and place in it:
   - `whisper-server.exe`
   - `ggml.dll`, `ggml-base.dll`, `ggml-cpu.dll`, `ggml-vulkan.dll`, `whisper.dll`
   - the model: [`ggml-small.en.bin`](https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-small.en.bin)
3. That's it - `Start Sophia.bat` checks for it on launch and starts it automatically on `127.0.0.1:8090`. This folder is gitignored (large, machine-specific binaries); everyone else just gets the CPU fallback.

First launch takes a while: Whisper and Kokoro load (downloading their models if it's the very first run), then the system prompt is primed into Ollama's KV cache so the first real turn is fast.

## Tools

| Script | Purpose |
|---|---|
| `sophia_eval.py` | Persona regression check — 12 canned inputs against the live system prompt with expected behaviors. Run after any prompt edit. |
| `export_transcripts.py` | Converts the JSONL log into readable per-session markdown transcripts with mechanical-failure flags and review-notes sections. |
| `check_ollama_cache.py` | Diagnoses Ollama KV-cache reuse and model-reload behavior across a growing conversation. |
| `profile_latency.py` | Isolates where response latency goes — fixed per-request overhead vs prompt size vs HTTP streaming — and reports which lever would actually help. |

Version history is in [CHANGELOG.md](CHANGELOG.md), including the reasoning behind each behavioral change.

## Performance notes (hard-won)

- **Pin `num_ctx` identically on every request.** Ollama restarts its model runner when a request's context size differs from the loaded runner's — a full ~13s reload. This bot pins `num_ctx: 16384` everywhere, including warm-up and memory-summary calls. If you add a new Ollama call, pin it there too.
- **Prime the real system prompt at launch.** Warming the model with a bare "hi" loads weights but leaves the system prompt unevaluated; the first real turn then pays several seconds of prompt processing. `prime_model()` sends the actual conversation with `num_predict: 1` during the loading phase.
- **`keep_alive: -1`** on every request so the model never unloads from VRAM between turns.
- **Thinking needs budget.** `num_predict` caps reasoning *and* answer together. At 768 the model spent the whole budget reasoning and emitted a five-word fragment after 25s of silence. Deep mode uses 2560.
- **Don't upgrade Whisper past `small` without raising `CHUNK_SECONDS`.** Rolling chunks only stay invisible while transcription is faster than the audio it covers. `small.en` takes ~1.45s per 2.5s chunk (58% headroom); `medium` would take ~4.4s and fall progressively behind live speech.
- **Whisper echoes its prompt on near-silent audio.** Passing prior text as decoding context improves accuracy across chunk boundaries, but on a very short tail the model returns the context instead of a transcription — producing duplicated sentences. Short tails are dropped and identical consecutive chunks discarded.

## Privacy

`logs/` (full transcripts + diagnostics) and `memory/` (debate summaries) are created next to the script at runtime and are **gitignored** — they contain everything said in your debates. Review before sharing anything from them.

## License

MIT — see [LICENSE](LICENSE).
