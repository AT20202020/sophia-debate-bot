"""
check_ollama_cache.py — Ollama prompt-cache diagnostic for Sophia

Answers a specific question: when a debate conversation grows turn over
turn, is Ollama reusing its KV-cache for the shared prefix (system prompt
+ earlier turns), or silently re-evaluating the whole thing from scratch
every time? The second case is the most likely explanation for the
10+ second time-to-first-token spikes seen in real sessions - Sophia's
system prompt has gotten substantially longer through several rounds of
tuning, so a cache miss now costs a lot more than it used to.

How it works: sends the model a sequence of chat requests with a
conversation that grows by one turn each time, exactly the pattern
debate_voice.py uses. num_predict=1 and temperature=0.0 isolate PROMPT
PROCESSING cost from generation cost - we only care about how long it
takes Ollama to digest the prompt, not how long it takes to write a
reply. Ollama's response includes prompt_eval_count (how many prompt
tokens had to be freshly evaluated) and prompt_eval_duration - if caching
is working, both should stay roughly flat after turn 1; if it's broken,
both grow turn over turn along with the whole conversation.

The system prompt used here is pulled directly out of debate_voice.py (as
plain text, NOT imported/executed - importing it would trigger loading
Whisper/Kokoro and opening a mic stream, which we don't want here) so
this test reflects the actual current prompt cost, not a stale copy.

Run with the same venv python used for the debate bots:
  "C:\\Users\\dobe2\\open-webui-env\\Scripts\\python.exe" check_ollama_cache.py

Expects debate_voice.py to be sitting in the same folder as this script.
"""
import os
import requests

MODEL = "qwen3.6:27b"
OLLAMA_URL = "http://localhost:11434/api/chat"

# Reused across turns to simulate a real back-and-forth debate, so the
# conversation actually grows the way it would in a live session. Content
# doesn't matter for this test - only length/shape does.
FAKE_USER_TURNS = [
    "The cosmological argument proves God exists because everything needs a cause.",
    "But quantum events happen without a cause, so that premise is false.",
    "Quantum indeterminacy isn't the same thing as coming from absolutely nothing.",
    "Fine, but who caused the cause? Doesn't that lead to an infinite regress?",
    "Explain why you think an unmoved mover actually avoids that regress.",
    "That still sounds like special pleading for one exception to your own rule.",
]
FAKE_ASSISTANT_REPLY = (
    "That's a placeholder reply used only to make the conversation grow "
    "realistically for this timing test - its content is irrelevant."
)

def load_system_prompt():
    """Pulls SYSTEM_PROMPT out of debate_voice.py as plain text. Falls
    back to a rough-length placeholder if the file isn't found or the
    marker can't be located, so the script still runs (with a warning)
    rather than crashing."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    target = os.path.join(script_dir, "debate_voice.py")
    placeholder = "You are a helpful assistant. " * 200  # rough stand-in length

    if not os.path.exists(target):
        print(f"[couldn't find debate_voice.py next to this script at {target} - using a placeholder prompt instead]")
        return placeholder

    with open(target, "r", encoding="utf-8") as f:
        source = f.read()

    marker = 'SYSTEM_PROMPT = """'
    start = source.find(marker)
    if start == -1:
        print("[couldn't locate SYSTEM_PROMPT in debate_voice.py - using a placeholder prompt instead]")
        return placeholder
    start += len(marker)
    end = source.find('"""', start)
    if end == -1:
        print("[SYSTEM_PROMPT block looked malformed - using a placeholder prompt instead]")
        return placeholder
    return source[start:end]

def fmt(value, unit=""):
    if isinstance(value, (int, float)):
        return f"{value:.0f}{unit}"
    return str(value)

def run_diagnostic():
    system_prompt = load_system_prompt()
    approx_tokens = len(system_prompt) // 4  # rough rule of thumb, not exact
    print(f"System prompt: {len(system_prompt)} characters (~{approx_tokens} tokens, rough estimate)\n")

    conversation = [{"role": "system", "content": system_prompt}]

    header = f"{'turn':<6}{'prompt_eval_count':<20}{'prompt_eval_ms':<18}{'total_ms':<12}"
    print(header)
    print("-" * len(header))

    for i, user_text in enumerate(FAKE_USER_TURNS, start=1):
        conversation.append({"role": "user", "content": user_text})

        try:
            resp = requests.post(OLLAMA_URL, json={
                "model": MODEL,
                "messages": conversation,
                "think": False,
                "stream": False,
                "options": {"num_ctx": 8192, "num_predict": 1, "temperature": 0.0},
                "keep_alive": -1,
            }, timeout=120)
            data = resp.json()
        except Exception as e:
            print(f"{i:<6}[request failed: {e}]")
            continue

        prompt_eval_count = data.get("prompt_eval_count", "?")
        prompt_eval_ms = data.get("prompt_eval_duration", None)
        prompt_eval_ms = prompt_eval_ms / 1e6 if isinstance(prompt_eval_ms, (int, float)) else "?"
        total_ms = data.get("total_duration", None)
        total_ms = total_ms / 1e6 if isinstance(total_ms, (int, float)) else "?"

        print(f"{i:<6}{str(prompt_eval_count):<20}{fmt(prompt_eval_ms):<18}{fmt(total_ms):<12}")

        conversation.append({"role": "assistant", "content": FAKE_ASSISTANT_REPLY})

    print("""
How to read this:
  CACHE WORKING   - prompt_eval_count stays roughly flat after turn 1
                    (just the new turn's tokens, not the whole growing
                    history), and prompt_eval_ms stays low and roughly
                    constant turn over turn.
  CACHE BROKEN    - prompt_eval_count grows turn over turn, roughly in
                    step with the whole conversation so far, and
                    prompt_eval_ms grows right along with it. That means
                    Ollama is re-processing the entire system prompt +
                    history from scratch on every single turn - very
                    likely the real explanation for the 10+ second
                    time-to-first-token spikes, and it gets worse the
                    longer a debate runs.

If it's broken: the next things to try are (1) confirming the model
isn't being reloaded between turns (nothing else on the machine evicting
it from VRAM), (2) trimming SYSTEM_PROMPT length since every wasted
token costs more per turn when caching isn't helping, and (3) checking
your Ollama version - this has been a moving target across releases.
""")

if __name__ == "__main__":
    run_diagnostic()
