# Sophia — Local Voice Debate Bot

Sophia is a fully local, voice-to-voice philosophy debate opponent. She argues from an agnostic-atheist position with deep comparative-religion knowledge, names fallacies precisely, escalates her technical vocabulary to match (and outdo) her opponent, and remembers past debates. Everything runs on your own machine — no cloud APIs, no data leaves your PC.

```
mic (push-to-talk or hands-free) → faster-whisper (STT) → Ollama (LLM, streaming)
                   → Kokoro (TTS, sentence-by-sentence) → speakers
```

Speech starts playing while the LLM is still generating: tokens stream in, complete sentences are synthesized and queued immediately, and synthesis of the next sentence overlaps playback of the current one. Measured on an RX 7900 XTX running qwen3.8:27b: first token ~0.9s after the request, ~4.5s from the end of your speech to hearing her (most of that is transcription).

## Features

- **Two ways to run her, chosen at launch** — `Start Sophia.bat` asks `1` or `2`:
  - **Push-to-talk** (classic console) — Enter to talk, Enter to stop. After each response you can talk with people in the room without her reacting. All typed commands below work here.
  - **Hands-free** — a small window with Start / Pause / End. She greets the room, then listens on her own and answers when you stop talking. See [Hands-free mode](#hands-free-mode).
- **Live rolling transcription** — speech is transcribed in ~6s chunks *while you're still talking*, so the wait after you stop doesn't grow with how long you spoke.
- **A tuned debate persona** — surgeon-not-brawler precision, honest evaluation when you ask "is my argument valid?", plain answers to plain questions, impasse diagnosis instead of repetition, verbatim premise quoting before attack, a counter for jargon-posturing opponents, and deliberate vocabulary escalation in philosophical exchanges.
- **Cross-session memory** — she summarizes each debate and folds recent summaries into her context at launch, so she can reference what you argued last time.
- **Typed commands** at the push-to-talk prompt:
  - `new` — fresh opponent, context cleared (saves a memory summary first)
  - `deep` — toggle thinking mode: she reasons before answering (slower, deeper)
  - `mod` — speak to her as **moderator** rather than opponent: brief her ("your opponent is a Catholic priest", "ease off the mockery"), correct a mistranscription, or ask her something out of character. Briefings are applied, never argued with. `mod <text>` sends inline.
  - `verdict` — she steps out of character and coaches: your strongest point, weakest moment, and what a sharper version of your argument would look like
  - `steelman` — she rebuilds the strongest version of your argument, then attacks *that*
- **Structured JSONL logging** — full transcripts plus per-turn diagnostics (time-to-first-token, time-to-first-audio, Ollama eval counters, model-reload detection, transcription chunk timing) for later analysis.
- **Optional GPU transcription** — auto-detects a local [whisper.cpp](https://github.com/ggml-org/whisper.cpp) server built with Vulkan support (works on AMD/NVIDIA/Intel GPUs with Vulkan drivers, not just one vendor) and falls back to CPU transparently. `Start Sophia.bat` auto-starts it for you if it's set up - see below.

## Hands-free mode

Pick `2` when `Start Sophia.bat` asks. A small window opens (the console stays open behind it with the details):

| Control | What it does |
|---|---|
| **Start** | She says *"Hi, I'm Sophia. What's your claim about God?"* and starts listening. |
| **Pause / Resume** (or **Space**) | For side conversations: she's deaf until you resume. If she's mid-sentence she stops. |
| **End** | Saves her memory summary of the debate and clears context for the next opponent (what `new` does in push-to-talk). Closing the window does the same. |

How turn-taking works:
- **She only listens when the window says "Listening"** (or "Hearing you..." once you've started). From the moment your turn ends — while she transcribes, thinks, and speaks, plus half a second after — she hears nothing. The window says *"not listening"* the whole time.
- **She's never interrupted.** Talking over her isn't heard; wait for "Listening" and say it again.
- Your turn ends after **1.2s of quiet** (`END_SILENCE_MS` in `sophia_handsfree.py`). Raise it if she jumps in while you pause to think.
- Coughs, "um", "yeah" and Whisper's phantom phrases are ignored instead of answered.
- The typed commands (`mod`, `verdict`, `steelman`, `deep`) are push-to-talk only for now.

## System requirements

Tested on Windows with an AMD RX 7900 XTX (24GB) and a ZOOM P4 USB audio interface. The launcher is Windows-only; the Python runs elsewhere with manual setup.

**Both modes — minimum:**

| | Minimum | Notes |
|---|---|---|
| **GPU** | 24GB VRAM for the default `qwen3.8:27b` (~18GB weights + 16k-token context) | Smaller GPUs: pull a smaller model and change the model strings in `debate_voice.py`. AMD (ROCm) and NVIDIA both work through Ollama. |
| **CPU** | A modern multi-core desktop CPU | Speech-to-text (`small.en`) and text-to-speech run on the CPU. Each transcription takes ~1.5–3s on the test machine. |
| **Disk** | ~20GB free | The LLM plus ~570MB of Whisper/Kokoro models (downloaded on first run). |
| **OS / software** | Windows 10/11, Python 3.10–3.12, Ollama, espeak-ng | See [Prerequisites](#prerequisites). |
| **Audio** | A microphone and headphones or speakers | |

**Hands-free mode — additionally:**

- **A dedicated microphone close to whoever's speaking.** Speech is detected by volume against the room's noise floor, so a laptop mic across a noisy room will trigger on background talk. Use Pause for side conversations.
- **Nothing may feed the computer's own audio back into the mic input.** If your audio interface or Windows routes playback into the recording signal, she hears herself and answers her own words. Turn off any loopback or "mix" feature. On a **ZOOM PodTrak P4**: *Menu → Settings → USB Mix Minus → On*. In Windows, make sure "Listen to this device" is off and Stereo Mix isn't the input.
- **Headphones recommended.** She doesn't listen while she talks, so speakers work, but headphones keep the room quieter for detection.
- **Tkinter** for the window. It ships with the standard python.org installer; if it's missing, re-run the installer, choose *Modify*, and tick *tcl/tk and IDLE*.
- *Optional:* `pip install webrtcvad-wheels` for better speech detection in noisy rooms (detection works without it).

## Prerequisites

**Hardware:** a GPU with enough VRAM for your chosen LLM (24GB runs a 27B model comfortably; smaller models work on less — edit the model strings in `debate_voice.py`), a microphone, and speakers/headphones.

**Software, in order:**

*On Windows, `Start Sophia.bat` checks 1-3 itself and either fixes them or tells you what to do - this list is for manual setup or other platforms.*

1. **Python ≥3.10 and <3.13** — this is a hard requirement of the `kokoro` package, not a suggestion; 3.13 will fail to install it. 3.12 is what this project is tested on.
2. **[Ollama](https://ollama.com)** installed and able to run, with a model pulled (default: `qwen3.8:27b`).
3. **[espeak-ng](https://github.com/espeak-ng/espeak-ng/releases)** — required by Kokoro for phonemization of out-of-dictionary words. On Windows: download the latest `.msi` from the releases page and run it. On Debian/Ubuntu: `sudo apt install espeak-ng`.
4. **Linux only:** PortAudio for the mic/speaker streams — `sudo apt install libportaudio2`. (Windows wheels bundle it.)

**Notes:**
- `pip install -r requirements.txt` pulls PyTorch automatically as a Kokoro dependency. CPU-only torch is fine — the TTS model is only 82M parameters.
- **First launch needs internet**: faster-whisper downloads its `small.en` model and Kokoro downloads its weights (~570MB total) from Hugging Face. After that, everything runs offline.
- The launcher `.bat` uses `curl`, which is built into Windows 10+.

## Setup

### Quick start (Windows)

Just run `Start Sophia.bat`. It's self-installing: it finds a compatible Python (3.10-3.12), creates the `sophia-env` venv, installs `requirements.txt` into it, checks that Ollama is installed (offering to install it via `winget` if not) and running, pulls `qwen3.8:27b` if you don't have it yet, and warns - without blocking - if `espeak-ng` is missing. Every check either fixes itself or tells you exactly what's missing and where to get it. First run takes a while (Python packages, then a large model pull); every run after that is fast.

### Manual setup (any OS, or if you want full control)

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
