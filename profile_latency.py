"""
profile_latency.py — find where Sophia's response delay actually goes

Session logs show a consistent ~2.7s time-to-first-token, of which Ollama
only accounts for ~0.35s of prompt evaluation and ~0.27s of load. That
leaves roughly 2.1 SECONDS unexplained, and it is the single largest
component of the wait after you stop talking. This script isolates it.

It runs the same Ollama request four ways and compares:

  A. Tiny prompt, streaming      - Ollama's fixed per-request overhead
  B. Full system prompt, cold    - what a cache MISS costs
  C. Full system prompt, warm    - what a normal turn costs
  D. Full prompt, non-streaming  - is the delay in HTTP streaming setup?

Reading the result:
  * If A is already ~2s, the delay is fixed Ollama/model overhead and has
    nothing to do with prompt size - shrinking the system prompt would
    not help, and the fix is a smaller/faster model or different runtime.
  * If A is fast but C is slow, the system prompt is the problem even
    when cached, and trimming it is worth real time.
  * If D is much faster than C, the cost is in HTTP streaming setup, and
    the client code can be fixed.
  * If B is far worse than C, cache hits are doing a lot of work and
    anything that invalidates the prefix (memory changes, 'new') is
    expensive.

Run with the venv python:
  & "$env:USERPROFILE\\open-webui-env\\Scripts\\python.exe" "...\\Ai Chat Bot\\profile_latency.py"
"""
import json
import os
import time
import requests

MODEL = "qwen3.6:27b"
URL = "http://localhost:11434/api/chat"
OPTS = {"num_ctx": 8192, "num_predict": 40, "temperature": 0.3}


def load_system_prompt():
    here = os.path.dirname(os.path.abspath(__file__))
    target = os.path.join(here, "debate_voice.py")
    src = open(target, encoding="utf-8").read()
    marker = 'SYSTEM_PROMPT = """'
    s = src.index(marker) + len(marker)
    return src[s:src.index('"""', s)]


def timed_request(messages, stream=True, label=""):
    """Returns (time_to_first_token, ollama_stats)."""
    t0 = time.time()
    ttft = None
    stats = {}
    if stream:
        r = requests.post(URL, json={"model": MODEL, "messages": messages,
                                     "think": False, "stream": True,
                                     "options": OPTS, "keep_alive": -1},
                          stream=True, timeout=180)
        for line in r.iter_lines():
            if not line:
                continue
            c = json.loads(line)
            if c.get("message", {}).get("content") and ttft is None:
                ttft = time.time() - t0
            if c.get("done"):
                stats = c
                break
    else:
        r = requests.post(URL, json={"model": MODEL, "messages": messages,
                                     "think": False, "stream": False,
                                     "options": OPTS, "keep_alive": -1},
                          timeout=180)
        stats = r.json()
        ttft = time.time() - t0  # whole response, not first token
    ms = lambda k: round(stats.get(k, 0) / 1e6) if stats.get(k) else 0
    return ttft, {
        "prompt_tokens": stats.get("prompt_eval_count", "?"),
        "prompt_eval_ms": ms("prompt_eval_duration"),
        "eval_ms": ms("eval_duration"),
        "load_ms": ms("load_duration"),
        "total_ms": ms("total_duration"),
    }


def show(label, ttft, st, note=""):
    unexplained = ttft * 1000 - st["prompt_eval_ms"] - st["load_ms"]
    print(f"\n{label}")
    print(f"  time to first token : {ttft:.2f}s")
    print(f"  prompt tokens       : {st['prompt_tokens']}")
    print(f"  prompt_eval         : {st['prompt_eval_ms']}ms")
    print(f"  load                : {st['load_ms']}ms")
    print(f"  UNEXPLAINED         : {unexplained:.0f}ms   <-- the mystery")
    if note:
        print(f"  {note}")


def main():
    sp = load_system_prompt()
    print(f"System prompt: {len(sp)} chars (~{len(sp)//4} tokens)")
    print("Running 4 tests, ~1-2 minutes...")

    q = "State your position on the cosmological argument in one sentence."

    ttft, st = timed_request(
        [{"role": "system", "content": "You are a helpful assistant."},
         {"role": "user", "content": q}], label="A")
    show("A. TINY PROMPT, streaming  (Ollama's fixed overhead)", ttft, st,
         "If this is already ~2s, prompt size is NOT your problem.")

    full = [{"role": "system", "content": sp}, {"role": "user", "content": q}]
    ttft_b, st_b = timed_request(full)
    show("B. FULL PROMPT, first call (cache cold)", ttft_b, st_b)

    ttft_c, st_c = timed_request(
        full + [{"role": "assistant", "content": "Noted."},
                {"role": "user", "content": "Now defend that against a Thomist."}])
    show("C. FULL PROMPT, second call (cache warm - a NORMAL turn)", ttft_c, st_c)

    ttft_d, st_d = timed_request(full, stream=False)
    print("\nD. FULL PROMPT, non-streaming")
    print(f"  full response time  : {ttft_d:.2f}s  (includes generating 40 tokens)")
    print(f"  prompt_eval         : {st_d['prompt_eval_ms']}ms")
    print(f"  eval                : {st_d['eval_ms']}ms")

    print("\n" + "=" * 62)
    print("VERDICT")
    base = ttft
    print(f"  Fixed Ollama overhead (test A)        : {base:.2f}s")
    print(f"  Extra cost of the real prompt (C - A) : {ttft_c - base:.2f}s")
    if base > 1.5:
        print("\n  -> Most of the delay is FIXED per-request cost, independent")
        print("     of prompt size. Trimming the system prompt will NOT help.")
        print("     Levers that would: a smaller model (qwen3.6:14b or 8b), a")
        print("     quantized build, or a different runtime (llama.cpp/vLLM).")
    else:
        print("\n  -> The prompt itself is costing real time even when cached.")
        print("     Trimming SYSTEM_PROMPT is worth doing.")
    print("=" * 62)


if __name__ == "__main__":
    main()
