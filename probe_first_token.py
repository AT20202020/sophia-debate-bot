"""
probe_first_token.py - where does the fixed ~2.3s before Sophia's first word go?

THE QUESTION
------------
With thinking off, every live turn on 2026-09-11 took 2.33-2.48s to produce
its first token, 59 turns in a row, almost no variance. The prompt is
already cached (prompt_eval measured at 168ms), and the model writes ~36
tokens/s, so the first token should arrive in well under a second. Roughly
2 seconds per turn is unexplained, and it is now the largest single piece of
the delay between you finishing a sentence and Sophia starting one.

This asks Ollama directly, changing one thing at a time, so the cost can be
attributed instead of guessed at. It does not touch debate_voice.py and
generates no audio.

WHAT IT VARIES
--------------
  full prompt / short prompt   - is it prompt-dependent at all?
  streaming / non-streaming    - is it the stream setup?
  think False / "low"          - is the no-reasoning path itself slow?
  num_predict 800 / 80         - does the token budget cost time up front?
  keep_alive -1 / omitted      - is the model being touched between calls?
  cold / warm                  - does the first call differ from the rest?

Each variant runs 3 times; the median is what's reported. About 5 minutes.

USAGE (from the Ai Chat Bot 2 folder, with Ollama running):
  & "$env:USERPROFILE\\open-webui-env\\Scripts\\python.exe" probe_first_token.py

Writes probe_first_token_<timestamp>.txt next to itself.
"""
import json
import os
import statistics
import sys
import time
from datetime import datetime

import requests

URL = "http://127.0.0.1:11434/api/chat"
MODEL = "qwen3.8:27b"
NUM_CTX = 16384
REPEAT = 3

HERE = os.path.dirname(os.path.abspath(__file__))


def load_system_prompt():
    path = os.path.join(HERE, "debate_voice.py")
    src = open(path, encoding="utf-8").read()
    marker = 'SYSTEM_PROMPT = """'
    start = src.index(marker) + len(marker)
    return src[start:src.index('"""', start)]


FULL = load_system_prompt()
SHORT = "You are Sophia, a concise debate opponent. One or two sentences, spoken aloud."
USER = "Do you believe in God or not?"


def one_call(system, think, num_predict, stream, keep_alive=True):
    payload = {
        "model": MODEL,
        "messages": [{"role": "system", "content": system},
                     {"role": "user", "content": USER}],
        "think": think,
        "stream": stream,
        "options": {"num_ctx": NUM_CTX, "num_predict": num_predict, "temperature": 0.3},
    }
    if keep_alive:
        payload["keep_alive"] = -1
    t0 = time.time()
    if stream:
        first = None
        with requests.post(URL, json=payload, stream=True, timeout=180) as r:
            for line in r.iter_lines():
                if not line:
                    continue
                d = json.loads(line)
                piece = (d.get("message") or {}).get("content") or ""
                if piece and first is None:
                    first = time.time() - t0
                if d.get("done"):
                    stats = d
        total = time.time() - t0
    else:
        d = requests.post(URL, json=payload, timeout=180).json()
        total = first = time.time() - t0
        stats = d
    ns = lambda k: (stats.get(k) or 0) / 1e9
    return {"first_token_s": first, "total_s": total,
            "load_s": ns("load_duration"), "prompt_eval_s": ns("prompt_eval_duration"),
            "eval_s": ns("eval_duration"), "eval_count": stats.get("eval_count"),
            "prompt_eval_count": stats.get("prompt_eval_count")}


VARIANTS = [
    ("baseline: full prompt, stream, think=False, np=800", dict(system=FULL, think=False, num_predict=800, stream=True)),
    ("short prompt instead of the full one", dict(system=SHORT, think=False, num_predict=800, stream=True)),
    ("num_predict 80 instead of 800", dict(system=FULL, think=False, num_predict=80, stream=True)),
    ("think='low' (v2.46 behaviour)", dict(system=FULL, think="low", num_predict=800, stream=True)),
    ("no stream (total time only)", dict(system=FULL, think=False, num_predict=800, stream=False)),
    ("no keep_alive", dict(system=FULL, think=False, num_predict=800, stream=True, keep_alive=False)),
]


def main():
    out_path = os.path.join(HERE, f"probe_first_token_{datetime.now():%Y%m%d-%H%M%S}.txt")
    out_file = open(out_path, "w", encoding="utf-8")

    def out(line=""):
        print(line, flush=True)
        out_file.write(line + "\n")

    try:
        requests.get("http://127.0.0.1:11434/api/tags", timeout=5).raise_for_status()
    except Exception as e:
        raise SystemExit(f"Ollama isn't answering on 127.0.0.1:11434 ({e})")

    out(f"probe_first_token - {datetime.now():%Y-%m-%d %H:%M}")
    out(f"model {MODEL}  num_ctx {NUM_CTX}  prompt {len(FULL)} chars  repeat {REPEAT}")
    out("")
    out("Warming up (this first call also shows the cold-start cost)...")
    cold = one_call(FULL, False, 800, True)
    out(f"  cold call: first token {cold['first_token_s']:.2f}s "
        f"(load {cold['load_s']:.2f}s, prompt eval {cold['prompt_eval_s']:.2f}s)")
    out("")

    rows = []
    for name, kw in VARIANTS:
        runs = [one_call(**kw) for _ in range(REPEAT)]
        med = lambda k: statistics.median(r[k] for r in runs if r[k] is not None)
        row = (name, med("first_token_s"), med("prompt_eval_s"), med("eval_s"),
               statistics.median(r["eval_count"] or 0 for r in runs), med("load_s"))
        rows.append(row)
        out(f"{name}")
        out(f"    first token {row[1]:.2f}s | prompt eval {row[2]:.2f}s | "
            f"generation {row[3]:.2f}s for {row[4]:.0f} tokens | load {row[5]:.2f}s")

    base = rows[0]
    out("")
    out("=" * 70)
    out("READING IT")
    out("=" * 70)
    unexplained = base[1] - base[2] - base[5]
    out(f"  baseline first token           {base[1]:.2f}s")
    out(f"  of which prompt evaluation     {base[2]:.2f}s")
    out(f"  of which model load            {base[5]:.2f}s")
    out(f"  unexplained                    {unexplained:.2f}s")
    out("")
    out("  If 'unexplained' is near zero, the wait is prompt evaluation and the")
    out("  fix is a smaller prompt or better cache reuse. If it stays ~2s across")
    out("  every variant - including the short prompt - it is fixed overhead in")
    out("  Ollama's request path, and the next thing to test is a newer Ollama")
    out("  build or llama.cpp directly.")
    out("")
    out(f"saved: {out_path}")
    out_file.close()


if __name__ == "__main__":
    main()
