"""
probe_connection.py - the 2.05s is connection setup. Which part of it?

WHERE THIS PICKS UP
-------------------
probe_first_token_2.py, variant 2: the identical request over ONE reused HTTP
connection took 0.19s instead of 2.23s. Unexplained went 2.07s -> 0.03s. Every
other variant - 1b model, raw endpoint, num_ctx 2048 - still paid ~2.05s.

So the delay is not Ollama, not the model, not the prompt, not the endpoint.
It is the cost of opening a new TCP connection to localhost, and
debate_voice.py opens one per request: bare `requests.post(...)` at lines 827,
877 and 1533, plus the whisper server at 1177. No Session anywhere.

TWO CANDIDATE CAUSES, DIFFERENT FIXES
-------------------------------------
  1. "localhost" resolves to ::1 (IPv6) first. Ollama listens on 127.0.0.1
     only, so every request attempts IPv6, waits, then falls back to IPv4.
     FIX: use 127.0.0.1 in the URL. One find-and-replace.

  2. The cost is in the connect itself regardless of address (per-connection
     work: firewall/AV inspection, WFP callout, Windows loopback setup).
     FIX: hold one requests.Session for the life of the process, so the cost
     is paid once at startup instead of once per turn.

These are not exclusive - if both show up, do both.

HOW IT DECIDES
--------------
It measures the layers separately, bottom-up, so the answer does not depend on
trusting `requests`:
  - getaddrinfo("localhost")  - what order do addresses come back in?
  - raw socket connect to ::1 / 127.0.0.1 / localhost - the actual TCP cost
  - requests to /api/tags, fresh connection vs reused, both spellings
  - one real /api/chat request (num_predict 1), fresh vs reused
/api/tags does no model work at all, so its time IS the transport cost.

No model is loaded or unloaded. Nothing is written except the report. ~40s.

USAGE (from the Ai Chat Bot 2 folder):
  & "$env:USERPROFILE\\open-webui-env\\Scripts\\python.exe" probe_connection.py
"""
import os
import socket
import statistics
import time
from datetime import datetime

import requests

PORT = 11434
REPEAT = 5
HERE = os.path.dirname(os.path.abspath(__file__))


def med(fn, n=REPEAT):
    """Median of n timed calls. Returns (median_seconds, error_or_None)."""
    times, err = [], None
    for _ in range(n):
        t0 = time.time()
        try:
            fn()
        except Exception as e:
            err = f"{type(e).__name__}: {e}"
            times.append(time.time() - t0)
            continue
        times.append(time.time() - t0)
    return statistics.median(times), err


def main():
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    f = open(os.path.join(HERE, f"probe_connection_{stamp}.txt"), "w", encoding="utf-8")

    def out(line=""):
        print(line, flush=True)
        f.write(line + "\n")

    out(f"probe_connection - {datetime.now():%Y-%m-%d %H:%M}")
    out("")

    # ---- layer 0: name resolution ----------------------------------------
    out("0. What does 'localhost' resolve to, and in what order?")
    t0 = time.time()
    infos = socket.getaddrinfo("localhost", PORT, proto=socket.IPPROTO_TCP)
    dns_s = time.time() - t0
    for fam, _, _, _, addr in infos:
        out(f"     {'IPv6' if fam == socket.AF_INET6 else 'IPv4'}  {addr[0]}")
    out(f"   getaddrinfo took {dns_s*1000:.0f}ms")
    first_is_v6 = infos and infos[0][0] == socket.AF_INET6
    out(f"   first address tried: {'::1 (IPv6)' if first_is_v6 else '127.0.0.1 (IPv4)'}")
    out("")

    # ---- layer 1: raw TCP, no requests involved --------------------------
    out("1. Raw TCP connect (socket only - `requests` is not in the picture)")

    def raw(host):
        def go():
            s = socket.create_connection((host, PORT), timeout=10)
            s.close()
        return go

    raw_rows = {}
    for host in ("::1", "127.0.0.1", "localhost"):
        t, err = med(raw(host))
        raw_rows[host] = t
        out(f"     {host:<12} {t*1000:7.0f}ms" + (f"   [{err}]" if err else ""))
    out("")

    # ---- layer 2: requests, fresh vs reused, both spellings --------------
    out("2. GET /api/tags (no model work - this is pure transport)")
    tag_rows = {}
    for host in ("localhost", "127.0.0.1"):
        url = f"http://{host}:{PORT}/api/tags"
        t_fresh, _ = med(lambda u=url: requests.get(u, timeout=10))
        s = requests.Session()
        s.get(url, timeout=10)                      # pay the first connect
        t_reuse, _ = med(lambda u=url: s.get(u, timeout=10))
        s.close()
        tag_rows[host] = (t_fresh, t_reuse)
        out(f"     {host:<12} fresh connection {t_fresh*1000:7.0f}ms"
            f"   |   reused {t_reuse*1000:7.0f}ms")
    out("")

    # ---- layer 3: the real call Sophia makes -----------------------------
    out("3. POST /api/chat, num_predict 1 (the real call, minimum work)")
    body = {"model": "qwen3.8:27b",
            "messages": [{"role": "user", "content": "Hi"}],
            "stream": False, "think": False, "keep_alive": -1,
            "options": {"num_ctx": 16384, "num_predict": 1}}
    chat_rows = {}
    for host in ("localhost", "127.0.0.1"):
        url = f"http://{host}:{PORT}/api/chat"
        t_fresh, _ = med(lambda u=url: requests.post(u, json=body, timeout=120), n=3)
        s = requests.Session()
        s.post(url, json=body, timeout=120)
        t_reuse, _ = med(lambda u=url: s.post(u, json=body, timeout=120), n=3)
        s.close()
        chat_rows[host] = (t_fresh, t_reuse)
        out(f"     {host:<12} fresh connection {t_fresh:7.2f}s"
            f"   |   reused {t_reuse:7.2f}s")
    out("")

    # ---- environment that could be involved ------------------------------
    proxies = {k: v for k, v in os.environ.items()
               if k.upper() in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "NO_PROXY")}
    out(f"4. Proxy env vars: {proxies or 'none set'}")
    out("")

    # ---- reading it ------------------------------------------------------
    out("=" * 72)
    out("READING IT")
    out("=" * 72)
    out("")
    v6, v4 = raw_rows["::1"], raw_rows["127.0.0.1"]
    lh_fresh, lh_reuse = tag_rows["localhost"]
    ip_fresh, ip_reuse = tag_rows["127.0.0.1"]

    ipv6_cost = lh_fresh - ip_fresh
    out(f"  cost of spelling it 'localhost' instead of '127.0.0.1'   {ipv6_cost*1000:+.0f}ms")
    out(f"  cost of a fresh connection even on 127.0.0.1             {(ip_fresh-ip_reuse)*1000:+.0f}ms")
    out("")

    if ipv6_cost > 0.5:
        out("  => CAUSE 1 CONFIRMED: the IPv6-first fallback is the delay.")
        out("     FIX: replace 'localhost' with '127.0.0.1' in debate_voice.py")
        out(f"     (lines 827, 877, 1533 for Ollama; 1147 for whisper). Raw connect")
        out(f"     to ::1 was {v6*1000:.0f}ms vs {v4*1000:.0f}ms to 127.0.0.1.")
        out("     This is the cheaper, lower-risk fix - do it first.")
    if (ip_fresh - ip_reuse) > 0.5:
        out("  => CAUSE 2 CONFIRMED: opening any new connection is expensive here,")
        out("     even straight to 127.0.0.1. Per-connection work on this box")
        out("     (firewall/AV loopback inspection is the usual culprit).")
        out("     FIX: one module-level requests.Session reused for every call,")
        out("     so the cost is paid once at startup, not once per turn.")
    if ipv6_cost <= 0.5 and (ip_fresh - ip_reuse) <= 0.5:
        out("  => NEITHER shows up at the /api/tags layer, which contradicts")
        out("     probe 2 variant 2. Compare section 3 against section 2 before")
        out("     changing anything - the cost may be specific to POST or to")
        out("     the streaming path.")
    out("")
    out("  Expected saving per turn, from section 3 (real /api/chat):")
    for host, (a, b) in chat_rows.items():
        out(f"     {host:<12} {a:.2f}s -> {b:.2f}s   ({(a-b):.2f}s per turn)")
    out("")
    out("  NOTE: a Session pays the connect cost ONCE, on the first request.")
    out("  Sophia already primes the model at startup, so that first request")
    out("  absorbs it and no live turn pays it.")
    f.close()
    print(f"\nsaved: probe_connection_{stamp}.txt")


if __name__ == "__main__":
    main()
