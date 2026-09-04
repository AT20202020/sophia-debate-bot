"""
probe_think_effort.py — is there a real "no reasoning" mode for qwen3.8:27b?

Context: ~5s of every ~10s turn (Sep 4 v2.39 session, from the log) is spent
on "low"-effort reasoning before the model says anything at all.
ARCHITECTURE_NOTES.md's item #4 wanted to try disabling reasoning entirely
for simple turns, but debate_voice.py's own history (v2.38) documented that
sending anything other than _think_effort()'s "low"/"high" strings into the
live bot reproduced the exact empty-reply-on-token-budget failure that took
three versions to fix. That finding was never actually re-tested against
the CURRENT model/Ollama version - it was a reasonable "don't guess in the
live bot" decision, not a confirmed dead end.

This sends the SAME real system prompt (pulled from debate_voice.py, as
plain text - not imported, so it doesn't load Whisper/Kokoro or open a mic)
plus one representative user turn, once per candidate `think` value, and
reports exactly what came back. Nothing here touches debate_voice.py or any
live conversation - it's a standalone, disposable measurement.

Run with the same venv python used for the debate bot, from this folder:
  & "$env:USERPROFILE\\open-webui-env\\Scripts\\python.exe" probe_think_effort.py
(or the project-local sophia-env, if that's what's set up on this machine)

Expects debate_voice.py in the same folder as this script.
"""
import os
import time
import requests

MODEL = "qwen3.8:27b"
OLLAMA_URL = "http://localhost:11434/api/chat"
NUM_CTX = 16384
NUM_PREDICT = 450  # matches NORMAL_NUM_PREDICT's OLD value - deliberately
                    # not the new 800, so a failure here isn't disguised by
                    # a bigger budget than the bot used when this failure
                    # mode was first found.

# A real, moderately meaty debate turn - not a trivial one - so a "no
# reasoning" mode gets a fair test against the kind of turn most likely to
# need actual thought, not just the easy cases.
TEST_USER_TURN = (
    "If God is defined as a necessary being, doesn't that just make "
    "'necessary' do all the work by definition, rather than proving "
    "anything exists?"
)

# What to try. None means "omit the key entirely" (some APIs treat a
# missing field differently than an explicit false).
CANDIDATES = [
    ("low (current baseline)", "low"),
    ("false", False),
    ("omitted entirely", None),
    ('"none"', "none"),
    ('"minimal"', "minimal"),
]


def load_system_prompt():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    target = os.path.join(script_dir, "debate_voice.py")
    if not os.path.exists(target):
        raise SystemExit(f"debate_voice.py not found next to this script at {target}")
    with open(target, "r", encoding="utf-8") as f:
        source = f.read()
    marker = 'SYSTEM_PROMPT = """'
    start = source.find(marker)
    if start == -1:
        raise SystemExit("couldn't locate SYSTEM_PROMPT in debate_voice.py")
    start += len(marker)
    end = source.find('"""', start)
    if end == -1:
        raise SystemExit("SYSTEM_PROMPT block looks malformed")
    return source[start:end]


def run_one(label, think_value):
    print("=" * 72)
    print(f"CANDIDATE: think = {label}")
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": TEST_USER_TURN},
    ]
    payload = {
        "model": MODEL,
        "messages": messages,
        "stream": False,
        "options": {"num_ctx": NUM_CTX, "num_predict": NUM_PREDICT, "temperature": 0.3},
        "keep_alive": -1,
    }
    if think_value is not None:
        payload["think"] = think_value

    t0 = time.time()
    try:
        resp = requests.post(OLLAMA_URL, json=payload, timeout=120)
    except Exception as e:
        print(f"  REQUEST FAILED: {e}")
        return
    elapsed = time.time() - t0

    print(f"  HTTP status:   {resp.status_code}")
    if resp.status_code != 200:
        print(f"  BODY:          {resp.text[:500]}")
        return

    data = resp.json()
    message = data.get("message", {})
    thinking = message.get("thinking")
    content = message.get("content", "")
    done_reason = data.get("done_reason")
    eval_count = data.get("eval_count")
    eval_ms = round(data.get("eval_duration", 0) / 1e6) if data.get("eval_duration") else None
    tok_per_s = round(eval_count / (eval_ms / 1000), 1) if eval_count and eval_ms else None

    print(f"  wall time:     {elapsed:.2f}s")
    print(f"  done_reason:   {done_reason}")
    print(f"  eval_count:    {eval_count}  ({tok_per_s} tok/s)" if tok_per_s else f"  eval_count:    {eval_count}")
    print(f"  'thinking' field present: {thinking is not None}  (len={len(thinking) if thinking else 0})")
    print(f"  content empty: {not content.strip()}")
    print(f"  content:       {content.strip()[:300]!r}")
    print()


SYSTEM_PROMPT = load_system_prompt()

if __name__ == "__main__":
    print(f"Loaded SYSTEM_PROMPT: {len(SYSTEM_PROMPT)} chars.")
    print(f"Testing {len(CANDIDATES)} think values against {MODEL} at num_predict={NUM_PREDICT}.\n")
    for label, value in CANDIDATES:
        run_one(label, value)

    print("=" * 72)
    print("""
READ THIS BEFORE CHANGING debate_voice.py:

- If a candidate below "low" comes back with content empty=True AND
  done_reason=="length" AND a 'thinking' field IS present with real length
  in it: that candidate silently ate the whole budget on reasoning anyway,
  same as booleans did on qwen3.6->qwen3.8 migration (v2.38). Don't use it.
- If a candidate comes back with content empty=False and a much smaller (or
  absent) 'thinking' field than the "low" baseline above it, at a similar or
  better wall time: that's a real signal a lighter mode exists and works.
- Compare EVERY candidate's actual content quality against the "low"
  baseline's, not just whether it filled in - a fast, confident, WRONG
  answer to a real philosophical point is worse than a slow correct one.
- Whatever you find, paste this whole output back for a second read before
  wiring anything into the live bot - and if you do wire it in, gate it
  from a deterministic detector in code (question mark, "what does X mean"),
  never from the model's own judgment about whether to think.""")
