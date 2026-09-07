"""
compare_think_effort.py - reasoning-effort A/B test for Sophia

Built to answer one specific question: does disabling qwen3.8:27b's
reasoning ("think": false) hold up on QUALITY, in exchange for the
speedup probe_think_effort.py measured on a single representative
question (5.07s vs 10.01s for "low" - roughly 2x)?

Real-session data backs up that this matters: analyzing a live v2.43
debate (2026-09-06) put median time-to-first-token at 8.53s across 37
turns, with 46% over 10s and some over 15-19s. Every GPU/quant/flash-
attention/speculative-decoding lever has already been checked and is at
or near its ceiling (see ARCHITECTURE_NOTES.md) - "how much she reasons
per turn" is the biggest remaining lever, and it's also the one most
likely to quietly break something, since this project's history of
mode-routing bugs (v2.3, v2.7, v2.11, v2.19, v2.22, v2.25) were all
subtle judgment calls (question vs claim, spicy vs neutral, moderator
vs opponent, technical vs posturing) - exactly the kind of thing you'd
expect less reasoning to get wrong first.

So: runs sophia_eval.py's full persona-regression suite (the same 14
cases that already encode "what correct looks like" for every one of
those past bugs) TWICE per case - once at think="low" (today's live
setting) and once at think=false - and prints both answers side by side
against the EXPECTED behavior and the wall-clock time for each. Reuses
sophia_eval.py's CASES and system-prompt loader directly (single source
of truth - never drifts from the regression suite on its own).

This is a human-eyeball tool, not an auto-grader, same as sophia_eval.py
itself - judge each GOT against its own EXPECTED line, not against the
other GOT. A single case where think=false gets the MODE wrong (answers
when it should attack, or vice versa) is disqualifying even if every
other case is faster and fine - that is exactly the class of bug this
project has shipped before without a check like this.

Same generation params as debate_voice.py's normal turn as of v2.45:
MODEL qwen3.8:27b, num_ctx 16384, num_predict 800 (NORMAL_NUM_PREDICT),
temperature 0.3.

Run with the venv python, from the same folder as sophia_eval.py and
debate_voice.py:
  & "$env:USERPROFILE\\open-webui-env\\Scripts\\python.exe" "...\\Ai Chat Bot 2\\sophia-debate-bot\\compare_think_effort.py" *> think_compare_output.txt

(Redirected to a file for the same reason probe_think_effort.py's output
needed to be - Windows closes the console before you can read it if you
just double-click the script.)

Takes a while - 14 cases x 2 think settings = 28 real generations against
your local Ollama. Expect several minutes.
"""
import time
import requests
from sophia_eval import CASES, load_system_prompt, MODEL, OLLAMA_URL

NUM_CTX = 16384
NUM_PREDICT = 800  # NORMAL_NUM_PREDICT in debate_voice.py as of v2.45
TEMPERATURE = 0.3


def ask(system_prompt, user_input, think):
    t0 = time.time()
    resp = requests.post(OLLAMA_URL, json={
        "model": MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_input},
        ],
        "think": think,
        "stream": False,
        "options": {"num_ctx": NUM_CTX, "num_predict": NUM_PREDICT, "temperature": TEMPERATURE},
        "keep_alive": -1,
    }, timeout=180)
    elapsed = time.time() - t0
    result = resp.json()
    content = result.get("message", {}).get("content", "").strip()
    return elapsed, content, result.get("done_reason"), result.get("eval_count")


def run():
    system_prompt = load_system_prompt()
    print(f"Loaded SYSTEM_PROMPT: {len(system_prompt)} chars. "
          f"Running {len(CASES)} cases x 2 (think=low vs think=false)...\n")

    totals = {"low": 0.0, "false": 0.0}
    settings = [("low", "low"), (False, "false")]

    for i, (name, user_input, expectation) in enumerate(CASES, 1):
        print("=" * 72)
        print(f"CASE {i}: {name}")
        print(f"  INPUT:    {user_input}")
        print(f"  EXPECTED: {expectation}")

        for think_val, label in settings:
            try:
                elapsed, content, done_reason, eval_count = ask(system_prompt, user_input, think_val)
                totals[label] += elapsed
                flag = "" if done_reason == "stop" else f"  [!] done_reason={done_reason}"
                print(f"  think={label:<5s} ({elapsed:5.2f}s, {eval_count} tok){flag}: {content}")
            except Exception as e:
                print(f"  think={label:<5s}: [request failed: {e}]")
        print()

    print("=" * 72)
    if totals["false"] > 0:
        ratio = totals["low"] / totals["false"]
        print(f"Total time - think=low: {totals['low']:.1f}s   "
              f"think=false: {totals['false']:.1f}s   ({ratio:.2f}x faster)")
    print("""
Read each pair of GOT lines against its own EXPECTED line above it - not
against each other. Questions to answer per case:
  1. Did think=false land in the same MODE as think=low (answer vs
     attack, neutral vs spicy, in-character vs out-of-character)?
  2. Is the content itself still correct and on-topic, or noticeably
     thinner/more generic without the reasoning pass?
  3. Any done_reason other than "stop" (truncation / empty reply)?

If think=false matches EXPECTED as well as think=low does on ALL 14
cases, it's a strong candidate to route into live turns (either
globally, or just for the routing-safe cases like plain questions).
Any single mode-routing miss is a reason to hold off, even with a
clean speedup everywhere else - rerun that one case a couple more
times before deciding, since temperature 0.3 means any one run can
be a fluke.
""")


if __name__ == "__main__":
    run()
