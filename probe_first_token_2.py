"""
probe_first_token_2.py - is the fixed ~2.1s Ollama's request path, or this GPU?

WHERE THIS PICKS UP
-------------------
probe_first_token.py (2026-09-12) found ~2.08s of first-token delay that
nothing in the request explains: short prompt 2.23s, full 18k prompt 2.27s,
num_predict 80 or 800 identical, streaming or not identical, keep_alive on
or off identical. Prompt eval was 0.19s and load was 0.00s, so it is neither
prompt processing nor a reload. Its own conclusion was "fixed overhead in
Ollama's request path - test a newer Ollama build or llama.cpp directly."

That conclusion is now awkward. You are on Ollama 0.33.3, the newest stable
(0.34.0 is still rc). So "newer build" is barely a lever, and llama.cpp
direct is a day of work. Before spending either, this settles WHICH KIND of
fixed cost it is, because the two have completely different fixes:

  request-path cost  - same ~2s no matter how big the model is.
                       Lives in Ollama's HTTP/scheduler/template path.
                       Fix: 0.34.0-rc, or bypass the endpoint.

  per-request GPU or  - cost scales with model size or allocated KV.
  KV-cache cost        Lives below Ollama, in the runner/ROCm/Vulkan path.
                       Fix: smaller num_ctx, a different backend, or
                       llama.cpp direct. A newer Ollama will NOT help.

WHAT IT VARIES (one thing at a time, same raw-HTTP method as probe 1)
---------------------------------------------------------------------
  A. qwen3.8:27b, already warm, num_ctx 16384
     1 baseline               reproduce probe 1's 2.27s today
     2 reused connection      rules out per-request TCP/HTTP setup
     3 tiny request, np=1     the least work a request can possibly ask for
     4 /api/generate raw      bypasses the chat template + /api/chat handler
     5 /api/generate raw tiny both bypasses at once
  B. llama3.2:1b  <- THE DISCRIMINATOR. Same code path, 1/17th the weights.
     6 full prompt, ctx 16384
     7 tiny request, ctx 16384
     8 tiny request, ctx 2048   does the cost track ALLOCATED context?
  C. qwen3.8:27b reloaded at num_ctx 8192 (this one reloads the model)
     9 baseline at 8192        if overhead halves, num_ctx is the knob

CLEANUP: unloads llama3.2 and re-primes qwen3.8 at 16384 with keep_alive -1,
so your next Sophia session starts warm exactly as it does now.

Nothing here touches debate_voice.py and no audio is generated. ~6 minutes.

USAGE (from the Ai Chat Bot 2 folder, with Ollama running):
  & "$env:USERPROFILE\\open-webui-env\\Scripts\\python.exe" probe_first_token_2.py

Writes probe_first_token_2_<timestamp>.txt next to itself.
"""
import json
import os
import statistics
import time
from datetime import datetime

import requests

HOST = "http://127.0.0.1:11434"
CHAT = f"{HOST}/api/chat"
GEN = f"{HOST}/api/generate"

BIG = "qwen3.8:27b"
SMALL = "llama3.2:1b"
NUM_CTX = 16384
REPEAT = 3

HERE = os.path.dirname(os.path.abspath(__file__))
SESSION = requests.Session()


def load_system_prompt():
    """Read SYSTEM_PROMPT out of debate_voice.py rather than restating it."""
    src = open(os.path.join(HERE, "debate_voice.py"), encoding="utf-8").read()
    marker = 'SYSTEM_PROMPT = """'
    start = src.index(marker) + len(marker)
    return src[start:src.index('"""', start)]


FULL = load_system_prompt()
USER = "Do you believe in God or not?"
TINY = "Hi"


def call(model, *, system=None, user=USER, think=None, num_predict=800,
         num_ctx=NUM_CTX, raw=False, reuse=False, keep_alive=-1):
    """One request. Returns first-token time plus Ollama's own accounting."""
    options = {"num_ctx": num_ctx, "num_predict": num_predict, "temperature": 0.3}
    if raw:
        url = GEN
        text = (system + "\n\n" + user) if system else user
        payload = {"model": model, "prompt": text, "raw": True,
                   "stream": True, "options": options, "keep_alive": keep_alive}
        field = lambda d: d.get("response") or ""
    else:
        url = CHAT
        msgs = ([{"role": "system", "content": system}] if system else []) + \
               [{"role": "user", "content": user}]
        payload = {"model": model, "messages": msgs,
                   "stream": True, "options": options, "keep_alive": keep_alive}
        field = lambda d: (d.get("message") or {}).get("content") or ""
    # think is a qwen3.8 API. llama3.2 has no reasoning mode, so the key is
    # omitted entirely for it - sending it would measure an error path.
    if think is not None:
        payload["think"] = think

    poster = SESSION if reuse else requests
    first, stats = None, {}
    t0 = time.time()
    with poster.post(url, json=payload, stream=True, timeout=300) as r:
        r.raise_for_status()
        for line in r.iter_lines():
            if not line:
                continue
            d = json.loads(line)
            if field(d) and first is None:
                first = time.time() - t0
            if d.get("done"):
                stats = d
    total = time.time() - t0
    ns = lambda k: (stats.get(k) or 0) / 1e9
    if first is None:            # model emitted nothing at all
        first = total
    return {"first": first, "total": total, "load": ns("load_duration"),
            "peval": ns("prompt_eval_duration"), "ptok": stats.get("prompt_eval_count") or 0,
            "eval": ns("eval_duration"), "etok": stats.get("eval_count") or 0}


def main():
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    out_file = open(os.path.join(HERE, f"probe_first_token_2_{stamp}.txt"),
                    "w", encoding="utf-8")

    def out(line=""):
        print(line, flush=True)
        out_file.write(line + "\n")

    try:
        tags = requests.get(f"{HOST}/api/tags", timeout=5)
        tags.raise_for_status()
        have = {m["name"] for m in tags.json().get("models", [])}
    except Exception as e:
        raise SystemExit(f"Ollama isn't answering on localhost:11434 ({e})")
    for m in (BIG, SMALL):
        if m not in have:
            raise SystemExit(f"{m} is not pulled. `ollama pull {m}` first.")

    out(f"probe_first_token_2 - {datetime.now():%Y-%m-%d %H:%M}")
    out(f"big {BIG}  small {SMALL}  prompt {len(FULL)} chars  repeat {REPEAT}")
    out("")

    rows = []

    def run(label, note, **kw):
        """Median of REPEAT runs. The first run absorbs any cache miss."""
        runs = [call(**kw) for _ in range(REPEAT)]
        med = lambda k: statistics.median(r[k] for r in runs)
        r = {"label": label, "note": note, "first": med("first"),
             "peval": med("peval"), "load": med("load"),
             "ptok": med("ptok"), "etok": med("etok")}
        r["unexp"] = r["first"] - r["peval"] - r["load"]
        rows.append(r)
        out(f"  {label}")
        out(f"      first token {r['first']:.2f}s  =  prompt eval {r['peval']:.2f}s"
            f"  +  load {r['load']:.2f}s  +  UNEXPLAINED {r['unexp']:.2f}s"
            f"   [{r['ptok']:.0f} prompt tok]")
        return r

    # ---- A: the big model, already warm, exactly as Sophia calls it --------
    out(f"A. {BIG} at num_ctx {NUM_CTX} (warm)")
    call(BIG, system=FULL, think=False)          # untimed settle
    a1 = run("1 baseline (probe 1's baseline, repeated)", "",
             model=BIG, system=FULL, think=False)
    run("2 same, over one reused HTTP connection", "",
        model=BIG, system=FULL, think=False, reuse=True)
    a3 = run("3 tiny prompt, num_predict 1", "",
             model=BIG, system=None, user=TINY, think=False, num_predict=1)
    run("4 /api/generate raw (no chat template)", "",
        model=BIG, system=FULL, think=False, raw=True)
    a5 = run("5 /api/generate raw, tiny, num_predict 1", "",
             model=BIG, system=None, user=TINY, think=False, num_predict=1, raw=True)
    out("")

    # ---- B: the discriminator ---------------------------------------------
    out(f"B. {SMALL} - same code path, 1/17th the weights ('think' omitted)")
    out("   (loading it; both models fit in 24GB, qwen stays resident)")
    cold = call(SMALL, system=FULL, num_predict=800)
    out(f"   load: {cold['load']:.2f}s")
    b1 = run("6 full Sophia prompt, num_ctx 16384", "",
             model=SMALL, system=FULL, num_predict=800)
    b2 = run("7 tiny prompt, num_predict 1, num_ctx 16384", "",
             model=SMALL, system=None, user=TINY, num_predict=1)
    b3 = run("8 tiny prompt, num_predict 1, num_ctx 2048", "",
             model=SMALL, system=None, user=TINY, num_predict=1, num_ctx=2048)
    out("")
    call(SMALL, user=TINY, num_predict=1, keep_alive=0)   # unload the small one

    # ---- C: does allocated context drive it? (this reloads the big model) --
    out(f"C. {BIG} reloaded at num_ctx 8192 (a reload; ~30s)")
    c0 = call(BIG, system=FULL, think=False, num_ctx=8192)
    out(f"   reload: {c0['load']:.2f}s")
    c1 = run("9 baseline at num_ctx 8192", "",
             model=BIG, system=FULL, think=False, num_ctx=8192)
    out("")
    out(f"   restoring {BIG} at num_ctx {NUM_CTX}, keep_alive -1 ...")
    call(BIG, system=FULL, think=False)
    out("   restored - your next Sophia session starts warm as usual.")
    out("")

    # ---- reading it -------------------------------------------------------
    out("=" * 72)
    out("READING IT")
    out("=" * 72)
    out("")
    out(f"  {'variant':<44}{'first':>8}{'unexplained':>13}")
    for r in rows:
        out(f"  {r['label']:<44}{r['first']:>7.2f}s{r['unexp']:>12.2f}s")
    out("")

    big_floor = min(a3["unexp"], a5["unexp"])
    small_floor = min(b2["unexp"], b3["unexp"])
    out(f"  smallest unexplained cost, {BIG:<14} {big_floor:.2f}s")
    out(f"  smallest unexplained cost, {SMALL:<14} {small_floor:.2f}s")
    out("")

    ratio = (small_floor / big_floor) if big_floor > 0.01 else 1.0
    if ratio > 0.6:
        out("  => SAME COST ON BOTH MODELS. It is fixed per-request overhead in")
        out("     Ollama's request path, independent of the model. A 1b model")
        out("     paying the same 2s as a 27b one cannot be compute.")
        out("     Next: Ollama 0.34.0-rc, or llama.cpp's server directly.")
    elif ratio < 0.25:
        out("  => THE COST SCALES WITH THE MODEL. It is not Ollama's request")
        out("     path - it is per-request work in the runner/ROCm path on the")
        out("     7900 XTX. A newer Ollama will NOT fix this.")
        out("     Next: llama.cpp direct with the same GGUF, and compare the")
        out("     ROCm and Vulkan backends.")
    else:
        out("  => PARTIAL SCALING. Some fixed, some model-dependent. Read the")
        out("     num_ctx rows below before choosing a direction.")
    out("")

    tmpl = a3["unexp"] - a5["unexp"]
    out(f"  chat template / endpoint cost (A3 - A5)   {tmpl:+.2f}s")
    if tmpl > 0.3:
        out("     /api/generate raw is meaningfully faster. That is a change you")
        out("     can make inside debate_voice.py today, without changing runtime.")
    else:
        out("     Not the endpoint. /api/chat's template work is not the delay.")
    out("")

    ctx_small = b2["unexp"] - b3["unexp"]
    ctx_big = a1["unexp"] - c1["unexp"]
    out(f"  allocated-context cost, {SMALL} 16384 vs 2048   {ctx_small:+.2f}s")
    out(f"  allocated-context cost, {BIG} 16384 vs 8192  {ctx_big:+.2f}s")
    if ctx_big > 0.4:
        out("     Overhead tracks allocated KV, not the request. Halving num_ctx")
        out("     bought real time - weigh that against conversation length,")
        out("     since the prompt alone is ~4,600 tokens.")
    else:
        out("     num_ctx is not the knob. Leave it at 16384.")
    out("")
    out("  (A1 is the number to compare against probe 1's 2.27s / 2.08s. If it")
    out("   has moved a lot, something changed on the box and the rest of this")
    out("   run should be read with that in mind.)")
    out("")
    out_file.close()
    print(f"saved next to this script: probe_first_token_2_{stamp}.txt")


if __name__ == "__main__":
    main()
