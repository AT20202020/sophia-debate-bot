"""
sophia_judge.py - quality judge for Sophia's eval replies

WHY THIS EXISTS
---------------
sophia_eval.py's checks are regexes. They catch the mechanical failures
(tags, markdown, sentence count) and nothing else, and the 2026-09-10
think=false run showed exactly what slips through:

  case 11, run 1: "Physicalism is true."  - three words in reply to a
      serious zombie argument, stated as her own settled view. Passed
      every check.
  case 4, run 3:  "You are conflating..." - opens by attacking the
      reasoning around a question, which that case's EXPECTED text
      explicitly forbids. Passed every check.

That matters more now than before, because the plan is an automated
overnight loop that optimises for speed. Fast + short + regex-clean is
precisely what "Physicalism is true." is, so without a judge the loop
would learn to be curt and report it as progress.

WHAT IT DOES
------------
Sends each reply to the local model (same qwen3.8:27b, reasoning ON,
temperature 0) with the case's INPUT and EXPECTED text and a fixed
description of who Sophia is, and gets back a 1-5 score and a one-line
reason. A score of 4 or 5 is a pass.

It does NOT grade length, sentence count or formatting - the mechanical
checks own those, and a judge that also penalised length would double
count it. It is told explicitly that a short reply doing what EXPECTED
asks deserves a 5.

TWO DESIGN DECISIONS WORTH KNOWING
----------------------------------
1. The judge's picture of Sophia (PERSONA below) is a FIXED text in this
   file, not the live SYSTEM_PROMPT. The overnight loop will be editing
   SYSTEM_PROMPT. If the judge graded against whatever the prompt
   currently says, the loop could weaken a rule and the judge would
   happily grade against the weakened version. The loop treats this
   file as read-only for the same reason.

2. The judge runs AFTER all replies are generated, never interleaved.
   One GPU: a judge call between two timed replies evicts Sophia's
   prompt from the KV cache and changes what the next timing measures.
   Generating everything first keeps latency numbers comparable with
   every earlier run file.

Same model grading its own output tends to be lenient with itself. The
anchored rubric (specific failure descriptions per score) is the
mitigation; the morning review and a live session are the backstop.

An empty reply scores 1 without a model call - silence is a failed turn
from where you're sitting, and excluding empties would make a version
with lots of them look better than it is. A request error is excluded.

USAGE
-----
  Re-judge a saved run file (no regeneration - useful for setting the
  baseline from runs you already have):

    & "$env:USERPROFILE\\open-webui-env\\Scripts\\python.exe" sophia_judge.py eval_runs\\eval_v246-low_20260909-194554.txt

  Or judge as part of a fresh eval:

    ... sophia_eval.py --think false --repeat 3 --judge --label v246-nothink

  --cases 4,11     judge only these cases
  --no-save        don't write the _judged.txt/.json files

Writes eval_runs/<run name>_judged.txt (report) and .json (machine-
readable; what the overnight loop will read).
"""
import argparse
import json
import os
import re
import statistics
import sys
import time
from datetime import datetime

import requests

# One source of truth for model / URL / context size: read them from
# sophia_eval.py rather than copying the literals (PROJECT_REVIEW 1.2 -
# this project has been bitten six times by copied constants going stale).
# NUM_CTX in particular MUST match, or Ollama reloads the runner (~13s).
import sophia_eval as ev

JUDGE_THINK = "low"
JUDGE_NUM_PREDICT = 3000     # reasoning + verdict share this budget
JUDGE_TEMPERATURE = 0.0
PASS_SCORE = 4

PERSONA = """Sophia is a voice debate bot. She is a rigorous skeptic arguing from an
agnostic-atheist position: she finds no sufficient evidence for any
religion's claims but does not claim certainty that no god exists. She
has deep knowledge of comparative religion, philosophy of religion,
epistemology, metaphysics, philosophy of mind, ethics and logic.

How she is supposed to behave:
- A question gets a plain, direct answer to the question actually asked,
  then she stops. No counter-question, no challenge appended, no turning
  the answer into an attack, no answering a different question.
- When a turn contains a question wrapped in reasoning, she answers the
  question; she does not open by attacking the surrounding reasoning.
- When explaining a theist position she attributes it ("on classical
  theism...", "Aquinas would say...") and never asserts it in her own
  voice. She also does not assert contested metaphysics (physicalism,
  emergentism, etc.) as settled fact in her own voice.
- Asked whether an argument is valid, she evaluates it honestly and
  never manufactures a flaw to stay adversarial.
- A garbled, broken turn (a mic error) gets a neutral request to restate.
- Fluent jargon that makes no real claim gets a sharp, witty call-out of
  the empty vocabulary and a demand for an actual claim.
- A genuine technical argument gets serious engagement at a matching
  technical register (real distinctions, named positions), never mockery.
- Real fallacies are named precisely. Overgeneralisations about a whole
  religion are flagged as specific to one denomination or tradition.
- She attacks arguments, never the person.
- A [MODERATOR] message comes from the session operator: briefings are
  simply acknowledged, questions get a candid out-of-character answer.
- Everything she says is spoken aloud in a live debate, so replies are
  deliberately very short (one or two sentences). Brevity is correct."""

RUBRIC = """Score the reply from 1 to 5:

5 - Does exactly what EXPECTED describes. Substantive, accurate, right
    register, in her voice.
4 - Does what EXPECTED describes, with a minor weakness (a little
    generic, slightly off register, one small imprecision).
3 - Right kind of response but thin: misses one element EXPECTED asks
    for, or engages only superficially.
2 - Does something EXPECTED says she must not do (attacks where she
    should answer, mocks a real argument, missing attribution, adds a
    challenge), OR is a curt dismissal that doesn't engage with what
    was said.
1 - Off-topic, nonsensical, factually wrong about philosophy or
    religion, or asserts a theist or contested metaphysical position
    as her own settled view.

IGNORE length, sentence count and formatting - those are checked
separately. Do not reward longer replies. A one-sentence reply that does
what EXPECTED asks deserves a 5.

Reply in exactly this format and nothing else:
REASON: <one sentence>
SCORE: <1-5>"""

JUDGE_SYSTEM = ("You grade replies from a debate bot against a test case. "
                "Be strict and specific.\n\n" + PERSONA + "\n\n" + RUBRIC)

_SCORE = re.compile(r"SCORE:\s*\**\s*([1-5])")
_REASON = re.compile(r"REASON:\s*(.+)")


def _call(user_msg, think, num_predict):
    payload = {
        "model": ev.MODEL,
        "messages": [
            {"role": "system", "content": JUDGE_SYSTEM},
            {"role": "user", "content": user_msg},
        ],
        "think": think,
        "stream": False,
        "options": {"num_ctx": ev.NUM_CTX, "num_predict": num_predict,
                    "temperature": JUDGE_TEMPERATURE},
        "keep_alive": -1,
    }
    resp = requests.post(ev.OLLAMA_URL, json=payload, timeout=300)
    data = resp.json()
    msg = data.get("message", {}) or {}
    return (msg.get("content") or "").strip(), data.get("done_reason")


def judge_one(case_input, expected, reply):
    """Returns {score, passed, reason, attempt, elapsed} or None on a
    transport failure (excluded from scoring, like sophia_eval does)."""
    if not reply.strip():
        return {"score": 1, "passed": False, "reason": "empty reply",
                "attempt": "none (empty)", "elapsed": 0.0}
    user_msg = (f"TEST CASE INPUT (what was said to Sophia):\n{case_input}\n\n"
                f"EXPECTED:\n{expected}\n\n"
                f"SOPHIA'S REPLY:\n{reply}")
    t0 = time.time()
    # Attempt 1: reasoning on. Attempt 2 exists because of this project's
    # longest-running bug - num_predict caps reasoning and answer together,
    # so a long think can end with no verdict. Rather than trust any
    # budget, fall back to a no-reasoning verdict and record that it did.
    for attempt, think, budget in (("think", JUDGE_THINK, JUDGE_NUM_PREDICT),
                                   ("fallback-nothink", False, 300)):
        try:
            text, done = _call(user_msg, think, budget)
        except Exception:
            return None
        m = _SCORE.search(text)
        if m:
            r = _REASON.search(text)
            score = int(m.group(1))
            return {"score": score, "passed": score >= PASS_SCORE,
                    "reason": (r.group(1).strip() if r else text[:200]),
                    "attempt": attempt, "elapsed": round(time.time() - t0, 1)}
    return {"score": None, "passed": None,
            "reason": "judge produced no parseable score (both attempts)",
            "attempt": "failed", "elapsed": round(time.time() - t0, 1)}


# ---------------------------------------------------------------------------
# Reading saved run files, so existing runs can be judged without
# regenerating them.
# ---------------------------------------------------------------------------

_CASE_HDR = re.compile(r"^CASE (\d+): (.*)$", re.M)
_GOT = re.compile(r"^  GOT(?: \[run (\d+)/\d+\])? \(([\d.]+)s\): ?(.*?)"
                  r"(?=^    DIAG|^    LEN|^    FAIL|^  GOT|^={10,}|\Z)",
                  re.S | re.M)


def parse_run_file(path):
    text = open(path, encoding="utf-8").read()
    header = text.split("=" * 72, 1)[0].strip()
    records = []
    hdrs = list(_CASE_HDR.finditer(text))
    for n, h in enumerate(hdrs):
        end = hdrs[n + 1].start() if n + 1 < len(hdrs) else text.find("\nSUMMARY")
        block = text[h.start():end if end != -1 else len(text)]
        inp = re.search(r"^  INPUT:\s+(.*)$", block, re.M)
        exp = re.search(r"^  EXPECTED:\s+(.*)$", block, re.M)
        for g in _GOT.finditer(block):
            records.append({
                "case": int(h.group(1)), "name": h.group(2).strip(),
                "input": inp.group(1).strip() if inp else "",
                "expected": exp.group(1).strip() if exp else "",
                "run": int(g.group(1) or 1), "elapsed": float(g.group(2)),
                "text": g.group(3).strip(),
            })
    return header, records


def judge_records(records, out=print):
    """Judges a list of records in place (adds r['judge']). Prints one line
    per reply so an overnight log shows progress."""
    for r in records:
        j = judge_one(r["input"], r["expected"], r["text"])
        r["judge"] = j
        if j is None:
            out(f"  case {r['case']:>2} run {r['run']}: [judge request failed - excluded]")
        else:
            s = j["score"] if j["score"] is not None else "?"
            flag = "" if j["passed"] else "   <-- FAIL"
            out(f"  case {r['case']:>2} run {r['run']}: {s}/5  {j['reason']}{flag}")
    return records


def summarize(records, out=print):
    """Per-case table plus the two numbers the loop will gate on."""
    scored = [r for r in records if r.get("judge") and r["judge"]["score"] is not None]
    out("")
    out("JUDGE SUMMARY (1-5, pass = 4+)")
    out("-" * 72)
    by_case = {}
    for r in scored:
        by_case.setdefault((r["case"], r["name"]), []).append(r["judge"]["score"])
    for (c, name), scores in sorted(by_case.items()):
        mark = "PASS" if min(scores) >= PASS_SCORE else "FAIL"
        out(f"  {mark}  case {c:>2}  {' '.join(map(str, scores)):<8}  {name}")
    if not scored:
        out("  (nothing scored)")
        return {"mean": None, "pass_rate": None, "n": 0}
    mean = statistics.mean(r["judge"]["score"] for r in scored)
    passes = sum(1 for r in scored if r["judge"]["passed"])
    fallbacks = sum(1 for r in scored if r["judge"]["attempt"] == "fallback-nothink")
    unscored = len(records) - len(scored)
    out("")
    out(f"  judge mean {mean:.2f}/5   passed {passes}/{len(scored)} replies "
        f"({100 * passes / len(scored):.0f}%)")
    if fallbacks:
        out(f"  ({fallbacks} verdicts came from the no-reasoning fallback)")
    if unscored:
        out(f"  ({unscored} replies not scored - judge request failed or unparseable)")
    return {"mean": round(mean, 3), "pass_rate": round(passes / len(scored), 3),
            "n": len(scored), "passes": passes, "fallbacks": fallbacks}


def latency_stats(records):
    ts = sorted(r["elapsed"] for r in records if r.get("elapsed") is not None)
    if not ts:
        return {}
    return {"median": round(statistics.median(ts), 2),
            "p90": round(ts[min(len(ts) - 1, int(0.9 * len(ts)))], 2),
            "max": round(ts[-1], 2)}


def save_json(path, header, records, summary, extra=None):
    doc = {"header": header, "judged_at": datetime.now().isoformat(timespec="seconds"),
           "judge": {"model": ev.MODEL, "think": JUDGE_THINK, "pass_score": PASS_SCORE},
           "latency": latency_stats(records), "summary": summary,
           "records": records}
    if extra:
        doc.update(extra)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(doc, f, indent=2, ensure_ascii=False)


def main():
    p = argparse.ArgumentParser(description="Judge a saved sophia_eval run file")
    p.add_argument("run_file")
    p.add_argument("--cases", default="", help="judge only these cases, e.g. 4,11")
    p.add_argument("--no-save", action="store_true")
    a = p.parse_args()

    header, records = parse_run_file(a.run_file)
    if a.cases:
        keep = {int(c) for c in a.cases.split(",") if c.strip()}
        records = [r for r in records if r["case"] in keep]
    if not records:
        raise SystemExit("no replies found in that file")

    base = os.path.splitext(a.run_file)[0] + "_judged"
    f = None if a.no_save else open(base + ".txt", "w", encoding="utf-8")

    def out(line=""):
        print(line)
        if f:
            f.write(line + "\n")
            f.flush()

    out(f"JUDGING {os.path.basename(a.run_file)}  ({len(records)} replies)")
    out(header)
    out(f"judge: {ev.MODEL} think={JUDGE_THINK} temp={JUDGE_TEMPERATURE}")
    out("")
    judge_records(records, out)
    summary = summarize(records, out)
    lat = latency_stats(records)
    if lat:
        out(f"  reply time median {lat['median']}s  p90 {lat['p90']}s  max {lat['max']}s")
    if f:
        f.close()
        save_json(base + ".json", header, records, summary)
        print(f"\nsaved: {base}.txt and .json")


if __name__ == "__main__":
    main()
