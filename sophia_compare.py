"""
sophia_compare.py - the same Sophia, two different models, same questions.

Built for: "is the stock model holding her back?" (2026-10-16). Runs the full
training question bank (training_cases.py, including the openness probes) on
model A (whatever debate_voice.py uses) and model B (default: the abliterated
qwen3.8 27B), then has ONE fixed judge - model A - grade every reply, so the
judge never changes between the two.

Nothing live is changed. Model B only exists in a scratch copy of
debate_voice.py inside compare_runs/<time>/.

Order of work keeps model swaps to two (both models don't fit on a 24 GB card
at once): A answers everything, B answers everything, then A judges it all.

    python sophia_compare.py                       # default model B, 2 passes each
    python sophia_compare.py --model-b NAME --passes 3
"""

import argparse
import json
import os
import re
import statistics
import sys
import time
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import requests  # noqa: E402
import sophia_trainer as T  # noqa: E402
from training_cases import CASES, _REFUSAL  # noqa: E402

VERSION = "1.2"
DEFAULT_B = "qwen3.8-abliterated:27b"   # made by make_abliterated_model.py (stock template, abliterated weights)
TAGS = "http://127.0.0.1:11434/api/tags"


def installed(name):
    try:
        names = [m.get("name", "") for m in requests.get(TAGS, timeout=10).json().get("models", [])]
    except Exception:
        return False
    base = name if ":" in name.split("/")[-1] else name + ":latest"
    return name in names or base in names


def preflight(model, num_ctx):
    """Two tiny requests with the exact options Sophia sends - the second with
    a system note AFTER the user turn, which Sophia does on every direct
    question (v1.0 lost 42 of 92 turns to a template that couldn't). Returns (ok, msg)."""
    msgs = [[{"role": "user", "content": "In one sentence: what is a syllogism?"}],
            [{"role": "system", "content": "You are a debate bot."},
             {"role": "user", "content": "In one sentence: what is a syllogism?"},
             {"role": "system", "content": "Answer the question directly."}]]
    out = []
    for m in msgs:
        body = {"model": model, "stream": False, "think": "low", "keep_alive": -1,
                "options": {"num_ctx": num_ctx, "num_predict": 300}, "messages": m}
        try:
            d = requests.post(T.OLLAMA_CHAT, json=body, timeout=600).json()
        except Exception as e:
            return False, f"request failed: {e}"
        if d.get("error"):
            return False, d["error"]
        txt = (d.get("message") or {}).get("content", "").strip()
        if not txt:
            which = "plain" if len(m) == 1 else "with a trailing system note (Sophia's direct-question path)"
            return False, f"empty reply {which} - run make_abliterated_model.py to give it the stock template"
        out.append(txt[:80])
    return True, " | ".join(out)


def make_copy(run_dir, label, model):
    d = os.path.join(run_dir, label)
    T.make_candidate(HERE, d)
    p = os.path.join(d, "debate_voice.py")
    src = open(p, encoding="utf-8").read()
    src2, n = re.subn(r'("model":\s*")[^"]+(")', lambda m: m.group(1) + model + m.group(2), src)
    open(p, "w", encoding="utf-8", newline="").write(src2)
    return d, n


def generate(bot, label, passes, run_dir):
    real_judge = T.judge
    T.judge = lambda *a, **k: None          # judging happens later, with one fixed model
    out = []
    try:
        try:
            bot.ask([{"role": "system", "content": bot.system_prompt}], "Hello.")  # load + warm, untimed
        except Exception:
            pass
        for p in range(passes):
            for i, case in enumerate(CASES, 1):
                rec = T.run_case(bot, case)
                rec["pass"] = p + 1
                out.append(rec)
                print(f"    {label} pass {p + 1}/{passes}: {i}/{len(CASES)}   ", end="\r", flush=True)
    finally:
        T.judge = real_judge
    print()
    return out


def judge_all(judge_bot, recs):
    by_id = {c["id"]: c for c in CASES}
    for i, r in enumerate(recs, 1):
        case = by_id[r["id"]]
        hist = "\n".join(f"OPPONENT: {u}\nSOPHIA: {a}" for u, a in case.get("turns", []))
        j = T.judge(judge_bot, case, r["reply"], hist)
        r["judge"] = j
        jm = statistics.mean([j["accuracy"], j["answered"], j["concise"]]) if j else 3.0
        r["score"] = round(max(0.0, jm - 0.75 * len(r["fails"])), 3)
        r["refused"] = bool(re.search(_REFUSAL, r["reply"], re.I))
        print(f"    judging {i}/{len(recs)}   ", end="\r", flush=True)
    print()


def summary(recs):
    acc = [r["judge"]["accuracy"] for r in recs if r.get("judge")]
    return {"score": round(statistics.mean(r["score"] for r in recs), 3),
            "accuracy": round(statistics.mean(acc), 2) if acc else None,
            "median_s": round(statistics.median(r["seconds"] for r in recs), 2),
            "median_ttft": round(statistics.median(r["ttft"] for r in recs if r.get("ttft") is not None), 2)
            if any(r.get("ttft") is not None for r in recs) else None,
            "median_words": statistics.median(r["words"] for r in recs),
            "code_fails": sum(len(r["fails"]) for r in recs),
            "refusal_phrases": sum(r["refused"] for r in recs),
            "empty": sum(1 for r in recs if not r["reply"])}


def by_case(recs):
    out = {}
    for r in recs:
        out.setdefault(r["id"], []).append(r)
    return out


def report(run_dir, a_name, b_name, A, B, passes):
    sa, sb = summary(A), summary(B)
    w = [f"# Model comparison {os.path.basename(run_dir)}\n",
         f"A = `{a_name}` (current)  \nB = `{b_name}`  \n"
         f"{len(CASES)} questions x {passes} passes each. Judge for both: `{a_name}` (fixed).\n",
         "## Bottom line\n", "| | A (current) | B |", "|---|---|---|"]
    for k, name in (("score", "Score (0-5)"), ("accuracy", "Judge accuracy (1-5)"),
                    ("median_s", "Median reply time (s)"), ("median_ttft", "Median first token (s)"),
                    ("median_words", "Median reply words"), ("code_fails", "Code-check failures"),
                    ("refusal_phrases", "Ducking / filler phrases"), ("empty", "Empty replies")):
        w.append(f"| {name} | {sa[k]} | {sb[k]} |")
    w.append("\nSingle-question scores swing about a point between identical runs; look at "
             "categories and the replies themselves, not one number.\n")
    w.append("## By category (A -> B)\n")
    for c in sorted({c["cat"] for c in CASES}):
        a = statistics.mean(r["score"] for r in A if r["cat"] == c)
        b = statistics.mean(r["score"] for r in B if r["cat"] == c)
        w.append(f"- **{c}**: {a:.2f} -> {b:.2f}  ({b - a:+.2f})")
    ca, cb = by_case(A), by_case(B)
    w.append("\n## Biggest differences per question\n")
    diffs = sorted(((statistics.mean(x["score"] for x in cb[i]) - statistics.mean(x["score"] for x in ca[i]), i)
                    for i in ca), key=lambda t: t[0])
    for d, i in diffs[:6] + diffs[-6:]:
        w.append(f"- {i}: {d:+.2f}")
    w.append("\n## Openness and fabrication replies, side by side (pass 1)\n")
    for case in CASES:
        if case["cat"] not in ("openness", "no-invention"):
            continue
        ra, rb = ca[case["id"]][0], cb[case["id"]][0]
        w.append(f"### {case['id']}: {case['input']}\n")
        for tag, r in (("A", ra), ("B", rb)):
            j = r.get("judge") or {}
            flags = "; ".join(r["fails"]) or "checks passed"
            w.append(f"**{tag}** (score {r['score']}, {r['seconds']}s, {flags}): {r['reply']}\n")
            w.append(f"> judge: {j.get('note', '-')}\n")
    w.append("## What to do with this\n")
    w.append("Tell Claude it finished. Nothing live was changed; switching models is a separate, "
             "deliberate step (four `\"model\":` lines in debate_voice.py).")
    open(os.path.join(run_dir, "COMPARE.md"), "w", encoding="utf-8").write("\n".join(w))


def main():
    ap = argparse.ArgumentParser(description="Compare two models on Sophia's question bank")
    ap.add_argument("--model-b", default=DEFAULT_B)
    ap.add_argument("--passes", type=int, default=2)
    args = ap.parse_args()

    run_dir = os.path.join(HERE, "compare_runs", datetime.now().strftime("%Y%m%d-%H%M"))
    os.makedirs(run_dir, exist_ok=True)
    T.log(run_dir, f"Model comparison v{VERSION}")
    if not T.ollama_up():
        T.log(run_dir, "Ollama is not answering on 127.0.0.1:11434 - start it and run again.")
        return 2

    a_dir = os.path.join(run_dir, "A")
    T.make_candidate(HERE, a_dir)
    bot_a = T.load_bot(a_dir, run_dir)
    a_name, b_name = bot_a.model, args.model_b
    if b_name == a_name:                       # v1.2: Sophia now runs the abliterated model
        b_name = "qwen3.8:27b"                 # so the useful comparison is against stock
    T.log(run_dir, f"A = {a_name}   B = {b_name}")
    if not installed(b_name):
        T.log(run_dir, f"Model B ({b_name}) isn't in Ollama. Get it with:  ollama pull {b_name}"
                       if "abliterated" not in b_name else
                       f"Model B ({b_name}) isn't in Ollama. Run make_abliterated_model.py first.")
        return 3
    b_dir, n = make_copy(run_dir, "B", b_name)
    T.log(run_dir, f"B copy made ({n} model settings switched)")

    T.log(run_dir, "Checking model B answers with Sophia's settings (first load can take a minute)...")
    ok, msg = preflight(b_name, bot_a.num_ctx)
    T.log(run_dir, f"  B: {msg}")
    if not ok:
        T.log(run_dir, "Model B can't run the way Sophia calls it - stopping before wasting time.")
        return 4

    t0 = time.time()
    A = generate(bot_a, "A", args.passes, run_dir)
    T.log(run_dir, f"A answered {len(A)} in {(time.time() - t0) / 60:.1f} min")
    t0 = time.time()
    bot_b = T.load_bot(b_dir, run_dir)
    B = generate(bot_b, "B", args.passes, run_dir)
    T.log(run_dir, f"B answered {len(B)} in {(time.time() - t0) / 60:.1f} min")

    t0 = time.time()
    judge_all(bot_a, A + B)                 # bot_a.model = the current model, same judge for both
    T.log(run_dir, f"judged {len(A) + len(B)} replies in {(time.time() - t0) / 60:.1f} min")
    for label, recs in (("A", A), ("B", B)):
        with open(os.path.join(run_dir, f"replies_{label}.json"), "w", encoding="utf-8") as f:
            json.dump(recs, f, ensure_ascii=False, indent=1)
    report(run_dir, a_name, b_name, A, B, args.passes)
    sa, sb = summary(A), summary(B)
    T.log(run_dir, f"Done. A score {sa['score']} / {sa['median_s']}s / {sa['refusal_phrases']} ducking;  "
                   f"B score {sb['score']} / {sb['median_s']}s / {sb['refusal_phrases']} ducking. "
                   f"Report: {os.path.join(run_dir, 'COMPARE.md')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
