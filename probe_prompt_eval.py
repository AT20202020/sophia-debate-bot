"""
probe_prompt_eval.py - why does every turn now pay ~841ms of prompt eval?

WHERE THIS PICKS UP
-------------------
sophia_bench.py, two runs of the same 4,222-token prompt:

    v2.47 (2026-09-11)   prompt eval  155ms min / 168ms median / 4686ms max
    v2.49 (2026-09-13)   prompt eval  811ms min / 841ms median / 1410ms max

Both report prompt_eval_count = 4222. But 4,222 tokens in 168ms is 25,000
tok/s, which a 27b model cannot actually do - that was Ollama reporting a
CACHE HIT and counting the tokens anyway. 841ms is ~5,000 tok/s, which is a
plausible real prefill. So the prefix cache has stopped being hit and every
turn now pays ~0.7s of genuine prompt evaluation.

That is most of what the v2.49 IPv6 fix just won back (first token went
2.25s -> 0.89s), so it is worth the same treatment: change one thing at a
time and let the numbers say which.

WHAT IT VARIES
--------------
  A back-to-back identical requests  - is the cache hit at all, ever?
  B a gap between requests           - does the cache decay with time?
  C another model loaded in between  - does VRAM pressure evict it?
  D heavy CPU work in between        - does a long non-Ollama pause do it?
  E a changed system prefix          - what a genuine cache MISS costs here,
                                       so the other rows have a scale
  F options varied per request       - does num_ctx/temperature churn reset it?

READING prompt_eval_count
-------------------------
Ollama reports the token count whether or not it evaluated them, so the
COUNT never proves a hit. The duration does. This probe prints tok/s for
every row, because that is the number that separates the two cases:

    > 15,000 tok/s   cache hit, nothing was really evaluated
    ~  5,000 tok/s   real prefill of the whole prompt
    in between       partial reuse

No model is unloaded and nothing is written except the report. ~4 minutes.

USAGE (from the Ai Chat Bot 2 folder, with Ollama running):
  & "$env:USERPROFILE\\open-webui-env\\Scripts\\python.exe" probe_prompt_eval.py
"""
import hashlib
import json
import os
import statistics
import time
from datetime import datetime

import requests

HOST = "http://127.0.0.1:11434"
CHAT = f"{HOST}/api/chat"
BIG = "qwen3.8:27b"
SMALL = "llama3.2:1b"
NUM_CTX = 16384
HERE = os.path.dirname(os.path.abspath(__file__))


def load_system_prompt():
    src = open(os.path.join(HERE, "debate_voice.py"), encoding="utf-8").read()
    marker = 'SYSTEM_PROMPT = """'
    start = src.index(marker) + len(marker)
    return src[start:src.index('"""', start)]


FULL = load_system_prompt()


def ask(system, user, *, model=BIG, num_ctx=NUM_CTX, temperature=0.3,
        num_predict=1, keep_alive=-1):
    """One request. num_predict=1 so generation time can't hide anything."""
    payload = {
        "model": model,
        "messages": [{"role": "system", "content": system},
                     {"role": "user", "content": user}],
        "think": False,
        "stream": False,
        "options": {"num_ctx": num_ctx, "num_predict": num_predict,
                    "temperature": temperature},
        "keep_alive": keep_alive,
    }
    t0 = time.time()
    d = requests.post(CHAT, json=payload, timeout=300).json()
    wall = time.time() - t0
    pe_ms = (d.get("prompt_eval_duration") or 0) / 1e6
    pe_n = d.get("prompt_eval_count") or 0
    load_ms = (d.get("load_duration") or 0) / 1e6
    tok_s = (pe_n / (pe_ms / 1000)) if pe_ms > 0 else 0
    return {"wall": wall, "pe_ms": pe_ms, "pe_n": pe_n,
            "load_ms": load_ms, "tok_s": tok_s}


def main():
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    f = open(os.path.join(HERE, f"probe_prompt_eval_{stamp}.txt"), "w", encoding="utf-8")

    def out(line=""):
        print(line, flush=True)
        f.write(line + "\n")

    try:
        requests.get(f"{HOST}/api/tags", timeout=5).raise_for_status()
    except Exception as e:
        raise SystemExit(f"Ollama isn't answering on 127.0.0.1:11434 ({e})")

    digest = hashlib.sha256(FULL.encode("utf-8")).hexdigest()[:12]
    out(f"probe_prompt_eval - {datetime.now():%Y-%m-%d %H:%M}")
    out(f"model {BIG}  num_ctx {NUM_CTX}")
    out(f"SYSTEM_PROMPT {len(FULL)} chars  sha256:{digest}")
    out("")
    out("  reading tok/s:  >15000 = cache hit    ~5000 = real prefill")
    out("")

    rows = []

    def row(label, r, note=""):
        rows.append((label, r))
        out(f"  {label:<46}{r['pe_ms']:>8.0f}ms {r['pe_n']:>6} tok "
            f"{r['tok_s']:>9.0f} tok/s{'  ' + note if note else ''}")
        return r

    # ---- A: does the cache EVER get hit? --------------------------------
    out("A. Five identical requests, back to back")
    ask(FULL, "Warm.")                       # untimed: seed the cache
    for i in range(5):
        row(f"   request {i + 1}", ask(FULL, f"Question number {i + 1}, please answer."))
    a_med = statistics.median(r["pe_ms"] for _, r in rows)
    out("")

    # ---- E: what a genuine miss costs, for scale ------------------------
    out("E. Changed system prefix (a deliberate cache MISS, for scale)")
    miss = row("   novel prefix", ask("You are a helpful assistant. " + FULL[:4000],
                                      "Answer briefly."))
    out("")

    # ---- B: does it decay with time? ------------------------------------
    out("B. The same request after a pause (does the cache decay?)")
    ask(FULL, "Re-seed.")
    for wait in (15, 60):
        out(f"   waiting {wait}s ...")
        time.sleep(wait)
        row(f"   after {wait}s idle", ask(FULL, "Answer after the wait."))
    out("")

    # ---- C: does another model evict it? --------------------------------
    out(f"C. After loading {SMALL} in between (VRAM pressure)")
    ask(FULL, "Re-seed.")
    try:
        ask("You are brief.", "Hello.", model=SMALL, num_ctx=2048, keep_alive="30s")
        row("   back to the big model", ask(FULL, "Answer after the small model."))
    except Exception as e:
        out(f"   skipped: {e}")
    out("")

    # ---- D: heavy local work in between ---------------------------------
    out("D. After ~20s of heavy CPU work (what STT/TTS look like to Ollama)")
    ask(FULL, "Re-seed.")
    t0 = time.time()
    x = 0
    while time.time() - t0 < 20:
        x = (x * 1103515245 + 12345) % (2 ** 31)
    row("   after busy CPU", ask(FULL, "Answer after the busy period."))
    out("")

    # ---- F: does churning the options reset it? -------------------------
    out("F. Same prefix, different request options")
    ask(FULL, "Re-seed.")
    row("   temperature 0.0 instead of 0.3", ask(FULL, "Answer.", temperature=0.0))
    row("   num_predict 800 instead of 1", ask(FULL, "Answer.", num_predict=800))
    row("   num_ctx 8192 instead of 16384", ask(FULL, "Answer.", num_ctx=8192),
        note="<- a reload here is expected")
    out("")

    # ---- reading it -----------------------------------------------------
    out("=" * 74)
    out("READING IT")
    out("=" * 74)
    out("")
    hit = a_med < 300
    out(f"  section A median prompt eval   {a_med:.0f}ms")
    out(f"  a genuine miss (section E)     {miss['pe_ms']:.0f}ms")
    out("")
    if hit:
        out("  => THE CACHE IS WORKING RIGHT NOW. The 841ms in the v2.49 bench")
        out("     run was therefore situational, not a standing regression -")
        out("     something in that run's sequence cost it. The sections below")
        out("     say which: whichever one is slow is the culprit.")
    else:
        out("  => THE CACHE IS NOT BEING HIT EVEN BACK TO BACK. That is a")
        out("     standing ~0.7s tax on every turn, not a bench artefact.")
        out("     Next: OLLAMA_NUM_PARALLEL=1 and OLLAMA_KEEP_ALIVE explicitly")
        out("     set, then re-run this. If it stays, the Ollama 0.34.0-rc")
        out("     prefix-cache behaviour is worth testing after all.")
    out("")
    out("  Any section below whose row is far above section A's median is a")
    out("  cache-eviction cause. In a live session the model sits idle for")
    out("  seconds at a time while Whisper transcribes, so B and D are the")
    out("  ones that would show up on every real turn.")
    f.close()
    print(f"\nsaved: probe_prompt_eval_{stamp}.txt")


if __name__ == "__main__":
    main()
