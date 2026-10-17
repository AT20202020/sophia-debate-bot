"""
sophia_trainer.py - a timed training session: test, judge, tweak, keep what helps.

Each ROUND:
  1. The whole question bank (training_cases.py) goes through a CANDIDATE copy of
     Sophia - the real debate_voice.py code path, guards and cards included, loaded
     text-only like sophia_scorecard.py. Every reply is timed.
  2. Code checks (required/forbidden phrases, length, repeats) and the local model as
     judge (accuracy, answered-the-question, concise; 1-5 each) score every reply.
  3. Claude Code (the `claude` CLI) reads the worst failures and proposes ONE small
     text edit: to SYSTEM_PROMPT, a reference CORE block, or a knowledge card.
  4. The edit is kept only if the score goes up and she isn't slower - or she gets
     clearly faster at the same score. Promising edits are re-run to confirm,
     because single runs are noisy (temperature 0.3).

YOUR LIVE FILES ARE NEVER TOUCHED. Everything happens in training_runs/<time>/.
At the end: REPORT.md, best/ (the best version's files) and best_vs_baseline.diff.
Nothing goes live until you (or Claude, with you) review the diff and copy it in.

USAGE
  Run Training Session.bat                    (60 minutes)
  python sophia_trainer.py --minutes 30
  python sophia_trainer.py --measure-only     (score the current Sophia, no tweaks)
"""

import argparse
import ast
import copy
import difflib
import json
import os
import re
import shutil
import statistics
import subprocess
import sys
import time
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

try:
    import requests
except ImportError:
    print("requests is not installed in this Python. Run this with the venv python.")
    sys.exit(2)

from sophia_scorecard import BotHarness, ollama_up, OLLAMA_CHAT, _parse_json  # noqa: E402
from training_cases import CASES  # noqa: E402

VERSION = "1.3"
COPY_FILES = ["debate_voice.py", "historicity_reference.py", "morality_reference.py",
              "knowledge_cards.py"]
EDITABLE = {  # file -> the string variable whose text the reviser may edit
    "debate_voice.py": "SYSTEM_PROMPT",
    "historicity_reference.py": "REFERENCE",
    "morality_reference.py": "CORE",
}
LIVE_TOPICS = ("historicity", "morality")   # folders a Topic in the code actually loads
MODULES = ("historicity_reference", "morality_reference", "knowledge_cards")

# Keep rules. Scores are 0-5 (judge mean minus code-check penalties).
GAIN = 0.08          # first run must beat the best by this much to be "promising"
CONFIRM_GAIN = 0.05  # average of both runs must beat the best by this much
SLOWER_OK = 1.15     # a kept change may be at most 15% slower (median reply time)
FASTER = 0.85        # ...or kept for speed alone if 15%+ faster at about the same score
SAME_SCORE = 0.03
# v1.2 targeted rule. Sophia samples at temperature 0.3, so single cases swing by
# a point or more between identical runs and the 34-case mean swings by ~0.2 -
# bigger than any one-rule fix moves it. So the reviser names the cases it is
# fixing and those are judged directly, with the rest checked for regressions.
TARGET_GAIN = 1.0          # first run: target cases must improve this much (0-5 scale)
TARGET_CONFIRM = 0.75      # both runs averaged
OVERALL_SLACK = 0.10       # the whole set may not drop more than this


def log(run_dir, msg):
    line = f"[{datetime.now():%H:%M:%S}] {msg}"
    print(line, flush=True)
    with open(os.path.join(run_dir, "loop.log"), "a", encoding="utf-8") as f:
        f.write(line + "\n")


# ---------------------------------------------------------------------------
# candidates
# ---------------------------------------------------------------------------

def make_candidate(src_dir, dst_dir):
    os.makedirs(dst_dir, exist_ok=True)
    for f in COPY_FILES:
        shutil.copy2(os.path.join(src_dir, f), os.path.join(dst_dir, f))
    kd = os.path.join(dst_dir, "knowledge")
    if os.path.exists(kd):
        shutil.rmtree(kd)
    shutil.copytree(os.path.join(src_dir, "knowledge"), kd)


def load_bot(folder, run_dir):
    """Load a candidate, making sure its OWN reference modules and cards are used."""
    for m in MODULES:
        sys.modules.pop(m, None)
    sys.path[:] = [p for p in sys.path if not os.path.abspath(p).startswith(os.path.abspath(run_dir))]
    sys.path.insert(0, folder)
    return BotHarness(folder)


def string_span(src, var):
    """(start, end) offsets of the Assign for `var` in source text."""
    tree = ast.parse(src)
    lines = src.splitlines(keepends=True)
    offs = [0]
    for ln in lines:
        offs.append(offs[-1] + len(ln))
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == var for t in node.targets):
            # ast offsets are UTF-8 byte columns; convert to character offsets.
            def col(lineno, byte_col):
                return len(lines[lineno - 1].encode("utf-8")[:byte_col].decode("utf-8", "ignore"))
            return (offs[node.lineno - 1] + col(node.lineno, node.col_offset),
                    offs[node.end_lineno - 1] + col(node.end_lineno, node.end_col_offset))
    return None


def apply_edit(cand_dir, edit):
    """Apply one reviser edit. Returns (ok, message)."""
    rel = (edit.get("file") or "").replace("\\", "/").strip("/")
    old, new = edit.get("old", ""), edit.get("new", "")
    path = os.path.join(cand_dir, *rel.split("/"))
    if rel in EDITABLE:
        src = open(path, encoding="utf-8").read()
        if not old or src.count(old) != 1:
            return False, f"'old' text found {src.count(old) if old else 0} times in {rel} (needs exactly 1)"
        span = string_span(src, EDITABLE[rel])
        i = src.index(old)
        if not span or not (span[0] <= i and i + len(old) <= span[1]):
            return False, f"edit is outside {EDITABLE[rel]} in {rel} - only that text may change"
        out = src.replace(old, new)
        try:
            ast.parse(out)
        except SyntaxError as e:
            return False, f"edit breaks Python syntax: {e}"
        open(path, "w", encoding="utf-8", newline="").write(out)
        return True, "ok"
    if rel.startswith("knowledge/") and rel.endswith(".md") and "/_" not in rel and not rel.lower().endswith("readme.md"):
        if rel.split("/")[1] not in LIVE_TOPICS:
            return False, (f"{rel}: only knowledge/{{{','.join(LIVE_TOPICS)}}}/ cards are ever loaded "
                           f"- a card in another folder would do nothing")
        if old == "" and not os.path.exists(path):
            text = new                                    # new card
        else:
            if not os.path.exists(path):
                return False, f"{rel} does not exist"
            src = open(path, encoding="utf-8").read()
            if not old or src.count(old) != 1:
                return False, f"'old' text found {src.count(old) if old else 0} times in {rel}"
            text = src.replace(old, new)
        if not re.match(r"\s*---\s*\ntitle:.+\ntriggers:.+\n---", text):
            return False, "card must keep its --- title: / triggers: --- header"
        body = text.split("---", 2)[2] if text.count("---") >= 2 else ""
        if len(body.strip()) > 2400:
            return False, f"card body {len(body.strip())} chars, limit 2400"
        os.makedirs(os.path.dirname(path), exist_ok=True)
        open(path, "w", encoding="utf-8", newline="").write(text)
        return True, "ok"
    return False, f"{rel} is not an editable file"


# ---------------------------------------------------------------------------
# evaluation
# ---------------------------------------------------------------------------

JUDGE_SYSTEM = """You grade one spoken reply from Sophia, an AI debate bot. Sophia is an
agnostic atheist. On whether Jesus existed she argues the skeptic side as an assigned
role, honestly. On morality she defends no moral theory of her own and attacks the
theist's premises. Replies are spoken aloud, so short is good.

Grade the PROPERTY described in FOCUS, plus general quality. Return ONLY JSON:
{"accuracy": 1-5, "answered": 1-5, "concise": 1-5,
 "errors": ["each factual error, invented fact, or contested point stated as settled"],
 "note": "one sentence: the main thing to fix, or 'fine'"}

accuracy: 5 = every factual claim correct, nothing invented, disputed points attributed.
  1 = invented or clearly false claims.
answered: 5 = directly addresses what was actually said or asked, meets the FOCUS.
  1 = dodges, attacks something not said, or misses the point of FOCUS.
concise: 5 = 1-4 tight spoken sentences. 1 = rambling, repetitive, or padded.
Judge the words, not the confidence. Do not reward agreement with you.
TONE IS BY DESIGN: when the opponent's argument is weak or lazy she ends with one short
condescending line about their reasoning ("Please try harder next time."). Do not lower any
score for that line. DO lower "answered" if she jabs at a strong argument, a question, an
agreement or a sincere personal remark, or insults who they are (looks, race, family, etc.)."""


def judge(bot, case, reply, history_text):
    msg = (f"EARLIER IN THIS DEBATE:\n{history_text or '(nothing - this is the opening turn)'}\n\n"
           f"OPPONENT SAID:\n{case['input']}\n\nSOPHIA REPLIED:\n{reply}\n\nFOCUS: {case['focus']}")
    payload = {"model": bot.model, "stream": False, "think": False, "format": "json", "keep_alive": -1,
               # num_ctx MUST match Sophia's or Ollama reloads the model (~13s) - v2.13.
               "options": {"num_ctx": bot.num_ctx, "num_predict": 400, "temperature": 0.0, "seed": 7},
               "messages": [{"role": "system", "content": JUDGE_SYSTEM}, {"role": "user", "content": msg}]}
    for _ in range(2):
        try:
            r = requests.post(OLLAMA_CHAT, json=payload, timeout=180)
            out = _parse_json(r.json().get("message", {}).get("content", ""))
            if isinstance(out, dict) and "accuracy" in out:
                return out
        except Exception:
            pass
    return None


def _sentences(t):
    return [s for s in re.split(r"(?<=[.!?])\s+", t.strip()) if s]


def ask(bot, history, text):
    pr = bot.ns.get("_repeat_reply_pending", {}).get("on", False)
    pp = bot.ns.get("_persona_slip_pending", {}).get("on", False)
    reply, meta, wall = bot.ask(history, text, pending_persona=pp, pending_repeat=pr)
    return (reply or "").strip(), meta or {}, wall, copy.deepcopy(bot.ns["conversation"])


def run_case(bot, case):
    history = [{"role": "system", "content": bot.system_prompt}]
    for u, a in case.get("turns", []):
        history += [{"role": "user", "content": u}, {"role": "assistant", "content": a}]
    hist_text = "\n".join(f"OPPONENT: {u}\nSOPHIA: {a}" for u, a in case.get("turns", []))
    reply, meta, wall, history = ask(bot, history, case["input"])
    fails = []
    for rx in case.get("requires", []):
        if not re.search(rx, reply, re.I):
            fails.append(f"missing required: /{rx[:60]}/")
    for rx in case.get("forbids", []):
        m = re.search(rx, reply, re.I)
        if m:
            fails.append(f"said forbidden: '{m.group(0)}'")
    lim = bot.limits or {}
    if lim.get("max_sentences") and len(_sentences(reply)) > lim["max_sentences"] + 1:
        fails.append(f"too long: {len(_sentences(reply))} sentences")
    if not reply or "lost my train of thought" in reply:
        fails.append("empty or fallback reply")
    record = {"id": case["id"], "cat": case["cat"], "input": case["input"], "reply": reply,
              "seconds": round(wall, 2), "ttft": meta.get("ttft"), "words": len(reply.split())}
    if case.get("repeat"):
        reply2, meta2, wall2, _ = ask(bot, history, case["input"])
        sim = difflib.SequenceMatcher(None, reply.lower(), reply2.lower()).ratio()
        record["reply2"] = reply2
        if sim >= 0.8:
            fails.append(f"repeated itself on the 2nd ask (similarity {sim:.2f})")
    j = judge(bot, case, reply, hist_text)
    record["judge"] = j
    record["fails"] = fails
    jm = statistics.mean([j["accuracy"], j["answered"], j["concise"]]) if j else 3.0
    record["score"] = round(max(0.0, jm - 0.75 * len(fails)), 3)
    return record


def evaluate(bot, label, run_dir):
    t0 = time.time()
    recs = []
    for i, case in enumerate(CASES, 1):
        recs.append(run_case(bot, case))
        print(f"    {label}: {i}/{len(CASES)}", end="\r", flush=True)
    secs = [r["seconds"] for r in recs]
    acc = [r["judge"]["accuracy"] for r in recs if r.get("judge")]
    res = {"label": label, "score": round(statistics.mean(r["score"] for r in recs), 3),
           "accuracy": round(statistics.mean(acc), 2) if acc else None,
           "median_s": round(statistics.median(secs), 2),
           "median_words": statistics.median(r["words"] for r in recs),
           "code_fails": sum(len(r["fails"]) for r in recs),
           "minutes": round((time.time() - t0) / 60, 1), "cases": recs}
    with open(os.path.join(run_dir, f"eval_{label}.json"), "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=1)
    return res


# ---------------------------------------------------------------------------
# reviser (Claude Code CLI)
# ---------------------------------------------------------------------------

REVISER_TASK = """You are tuning Sophia, a local spoken AI debate bot (qwen 27B via Ollama).
Goal: MORE ACCURATE answers first, then FASTER ones (fewer words means faster speech).

Below: the current editable texts, the worst-scoring replies from the last test round, and
changes already tried. Propose exactly ONE small, targeted edit that would fix the most
important recurring failure. Small means one rule added, sharpened, merged or removed -
not a rewrite. Prefer making existing rules clearer or shorter over adding new ones;
the system prompt is already long.

Hard constraints - an edit that breaks these is rejected automatically:
- Edit only: the SYSTEM_PROMPT text in debate_voice.py, the REFERENCE text in
  historicity_reference.py, the CORE text in morality_reference.py, or a knowledge card
  (knowledge/<topic>/<name>.md, keep its --- title: / triggers: --- header, body max
  2400 chars; to create a new card set "old" to "" and give the whole file as "new").
  Only knowledge/historicity/ and knowledge/morality/ are loaded; a card for any other
  subject (miracles, arguments...) would never reach her, so fix those in SYSTEM_PROMPT.
- Keep Jeff's decisions: she argues the skeptic side on Jesus' existence (honestly); she
  defends no moral theory of her own; she's an agnostic atheist; on weak or lazy arguments she ends with one
  condescending jab at their reasoning (v2.70 - keep it; never about who they are, never on
  strong arguments, questions, agreement or sincere personal turns). Cards present both
  sides and never tell her which is right.
- "old" must be copied EXACTLY from the text shown (it must occur once).
- Don't retry a change listed under ALREADY TRIED.

Reply with ONLY a JSON object, no prose before or after:
{"file": "debate_voice.py", "old": "...", "new": "...", "why": "one sentence",
 "targets": ["f1", "f2"]}
"targets" = the case ids (from WORST REPLIES) this edit should fix. It is judged mainly
on those cases improving, while every other case is checked for regressions.
"""


def find_claude():
    p = shutil.which("claude")
    if not p:
        return None
    return ["cmd", "/c", p] if p.lower().endswith((".cmd", ".bat")) else [p]


def editable_texts(cand_dir):
    out = []
    for f, var in EDITABLE.items():
        src = open(os.path.join(cand_dir, f), encoding="utf-8").read()
        sp = string_span(src, var)
        out.append(f"===== {f} : {var} =====\n{src[sp[0]:sp[1]] if sp else '(not found)'}")
    cards = []
    for root, _, files in os.walk(os.path.join(cand_dir, "knowledge")):
        for n in sorted(files):
            if n.endswith(".md") and not n.startswith("_") and n.lower() != "readme.md":
                rel = os.path.relpath(os.path.join(root, n), cand_dir).replace("\\", "/")
                cards.append(rel)
    out.append("===== knowledge cards (ask by editing; contents not shown) =====\n" + "\n".join(cards))
    return "\n\n".join(out)


def brief(cand_dir, res, tried):
    worst = sorted(res["cases"], key=lambda r: r["score"])[:10]
    parts = [REVISER_TASK, "\n\nCURRENT EDITABLE TEXTS\n", editable_texts(cand_dir),
             f"\n\nLAST ROUND: score {res['score']} (0-5), accuracy {res['accuracy']}, "
             f"median reply {res['median_s']}s, median {res['median_words']} words\n\nWORST REPLIES\n"]
    for r in worst:
        j = r.get("judge") or {}
        parts.append(f"- [{r['id']}/{r['cat']}] score {r['score']}\n  OPPONENT: {r['input']}\n"
                     f"  SOPHIA: {r['reply']}\n"
                     + (f"  2ND ASK: {r['reply2']}\n" if r.get("reply2") else "")
                     + f"  code checks: {'; '.join(r['fails']) or 'passed'}\n"
                     f"  judge: {j.get('note', '-')} | errors: {'; '.join(j.get('errors', []) or []) or 'none'}\n")
    parts.append("\nALREADY TRIED\n" + ("\n".join(f"- {t}" for t in tried) or "(nothing yet)"))
    return "".join(parts)


_FATAL = re.compile(r"authenticat|oauth|log ?in|credit balance|api key|unauthori[sz]ed|403|401", re.I)


def claude_preflight(claude_cmd):
    """One tiny call before the baseline, so a logged-out CLI is caught in
    seconds instead of after the baseline. Returns (ok, message)."""
    try:
        p = subprocess.run(claude_cmd + ["-p", "Reply with the single word OK.", "--output-format", "json"],
                           capture_output=True, text=True, encoding="utf-8", timeout=180)
    except Exception as e:
        return False, f"claude failed to run: {e}"
    try:
        d = json.loads(p.stdout)
        if d.get("is_error"):
            return False, str(d.get("result", "unknown error"))[:200]
        return True, "ok"
    except Exception:
        return (p.returncode == 0), (p.stderr or p.stdout or "no output")[:200]


def revise(claude_cmd, text, round_dir):
    try:
        # Text in, JSON edit out. Runs in the round's scratch folder with every
        # file-changing tool disallowed: it can only PROPOSE an edit, which this
        # script validates and applies to a candidate copy - never your live files.
        p = subprocess.run(claude_cmd + ["-p", "Follow the instructions in the input. Reply with only the JSON edit.",
                                         "--output-format", "json",
                                         "--disallowedTools", "Edit,Write,MultiEdit,NotebookEdit,Bash"],
                           input=text, capture_output=True, text=True, encoding="utf-8",
                           timeout=600, cwd=round_dir)
    except Exception as e:
        return None, f"claude failed to run: {e}"
    with open(os.path.join(round_dir, "reviser_stdout.json"), "w", encoding="utf-8") as f:
        f.write(p.stdout or "")
    try:
        d = json.loads(p.stdout)
        result = d.get("result", "")
        if d.get("is_error"):
            return None, f"CLAUDE ERROR: {str(result)[:200]}"
    except Exception:
        result = p.stdout or ""
    m = re.search(r"\{.*\}", result, re.S)
    if not m:
        return None, f"no JSON edit in reply (exit {p.returncode}): {(p.stderr or result)[:200]}"
    try:
        return json.loads(m.group(0)), "ok"
    except Exception as e:
        return None, f"bad JSON from reviser: {e}"


# ---------------------------------------------------------------------------
# report
# ---------------------------------------------------------------------------

def per_case(*results):
    ids = [c["id"] for c in results[0]["cases"]]
    return {i: statistics.mean(next(c["score"] for c in r["cases"] if c["id"] == i) for r in results)
            for i in ids}


def compare(best_cases, new_cases, targets):
    """(target gain, overall change) of new vs best, per-case means."""
    t = [i for i in targets if i in best_cases]
    tg = statistics.mean(new_cases[i] - best_cases[i] for i in t) if t else 0.0
    ov = statistics.mean(new_cases.values()) - statistics.mean(best_cases.values())
    return round(tg, 2), round(ov, 3)


def write_report(run_dir, base, best, rounds, started, stop_reason):
    w = []
    w.append(f"# Training session {os.path.basename(run_dir)}\n")
    w.append(f"Started {started:%Y-%m-%d %H:%M}, finished {datetime.now():%H:%M}. "
             f"Rounds: {len(rounds)}. Stopped because: {stop_reason}.\n")
    w.append("## Bottom line\n")
    w.append("| | Baseline | Best found |\n|---|---|---|")
    for k, name in (("score", "Score (0-5)"), ("accuracy", "Judge accuracy (1-5)"),
                    ("median_s", "Median reply time (s)"), ("median_words", "Median reply words"),
                    ("code_fails", "Code-check failures")):
        w.append(f"| {name} | {base.get(k)} | {best.get(k)} |")
    w.append(f"\nScores come from qwen judging qwen plus code checks; differences under ~0.08 are "
             f"noise. Read the replies in eval_*.json before trusting a number.\n")
    w.append("## Rounds\n\n| # | Change | Score | Time | Verdict |\n|---|---|---|---|---|")
    for r in rounds:
        w.append(f"| {r['n']} | {r['why'][:150]} | {r.get('score', '-')} | {r.get('median_s', '-')}s | {r['verdict']} |")
    w.append("\n## Per category (baseline -> best)\n")
    cats = sorted({c["cat"] for c in base["cases"]})
    for c in cats:
        b = statistics.mean(x["score"] for x in base["cases"] if x["cat"] == c)
        a = statistics.mean(x["score"] for x in best["cases"] if x["cat"] == c)
        w.append(f"- {c}: {b:.2f} -> {a:.2f}")
    w.append("\n## Still failing in the best version\n")
    for r in sorted(best["cases"], key=lambda r: r["score"])[:8]:
        j = r.get("judge") or {}
        w.append(f"- **{r['id']}** ({r['score']}): {j.get('note', '')} {('| ' + '; '.join(r['fails'])) if r['fails'] else ''}")
    w.append("\n## Next steps\n")
    w.append("1. Read `best_vs_baseline.diff` - every change that was kept.")
    w.append("2. Ask Claude to review it and copy the kept changes into your live files.")
    w.append("3. Run `Run v2.57 Checks.bat` and a real session before trusting it.")
    open(os.path.join(run_dir, "REPORT.md"), "w", encoding="utf-8").write("\n".join(w))


def write_diff(run_dir, base_dir, best_dir):
    out = []
    for root, _, files in os.walk(best_dir):
        for n in files:
            b = os.path.join(root, n)
            rel = os.path.relpath(b, best_dir)
            a = os.path.join(base_dir, rel)
            if n.endswith((".py", ".md")):
                at = open(a, encoding="utf-8").read().splitlines() if os.path.exists(a) else []
                bt = open(b, encoding="utf-8").read().splitlines()
                if at != bt:
                    out += list(difflib.unified_diff(at, bt, "baseline/" + rel, "best/" + rel, lineterm=""))
    open(os.path.join(run_dir, "best_vs_baseline.diff"), "w", encoding="utf-8").write("\n".join(out))


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(description="Sophia training session")
    ap.add_argument("--minutes", type=float, default=60)
    ap.add_argument("--measure-only", action="store_true")
    ap.add_argument("--patience", type=int, default=12, help="stop after this many rejected rounds in a row")
    ap.add_argument("--max-rounds", type=int, default=20)
    args = ap.parse_args()

    started = datetime.now()
    run_dir = os.path.join(HERE, "training_runs", started.strftime("%Y%m%d-%H%M"))
    os.makedirs(run_dir, exist_ok=True)
    deadline = time.time() + args.minutes * 60
    log(run_dir, f"Training session v{VERSION} - {args.minutes:.0f} min budget, {len(CASES)} cases")

    if not ollama_up():
        log(run_dir, "Ollama is not answering on 127.0.0.1:11434 - start it and run again.")
        return 2
    claude_cmd = None if args.measure_only else find_claude()
    if not args.measure_only and not claude_cmd:
        log(run_dir, "The `claude` command wasn't found, so this run will MEASURE ONLY (no tweaks).")
    if claude_cmd:
        ok, msg = claude_preflight(claude_cmd)
        if not ok:
            log(run_dir, f"Claude Code isn't working: {msg}")
            log(run_dir, "Fix: open a Command Prompt, type  claude  then  /login  and sign in, "
                         "type  /exit  and run this session again.")
            return 3
        log(run_dir, "Claude Code reviser: signed in and answering.")

    base_dir = os.path.join(run_dir, "baseline")
    make_candidate(HERE, base_dir)
    bot = load_bot(base_dir, run_dir)
    log(run_dir, f"Sophia v{bot.version}, prompt {len(bot.system_prompt):,} chars, model {bot.model}")
    try:
        bot.ask([{"role": "system", "content": bot.system_prompt}], "Hello.")   # warm-up, untimed
    except Exception as e:
        log(run_dir, f"warm-up failed: {e}")
    base = evaluate(bot, "baseline", run_dir)
    base2 = evaluate(bot, "baseline_b", run_dir)    # second pass: a steadier yardstick
    best_cases = per_case(base, base2)
    best_fails = (base["code_fails"] + base2["code_fails"]) / 2
    base["score"] = round(statistics.mean(best_cases.values()), 3)
    base["median_s"] = round((base["median_s"] + base2["median_s"]) / 2, 2)
    log(run_dir, f"baseline: score {base['score']}, accuracy {base['accuracy']}, median {base['median_s']}s, "
                 f"{base['code_fails']} code fails ({base['minutes']} min)")
    best, best_dir = base, base_dir
    rounds, tried, rejects, stop = [], [], 0, "time budget used"
    seen_edits = set()
    round_minutes = base["minutes"] + 1.5
    best = dict(base)

    try:
        n = 0
        while claude_cmd:
            if time.time() + round_minutes * 60 > deadline:
                stop = "time budget used"
                break
            if n >= args.max_rounds:
                stop = f"{n} rounds (the cap)"
                break
            if rejects >= args.patience:
                stop = f"{rejects} rejected rounds in a row"
                break
            n += 1
            rd = os.path.join(run_dir, f"r{n:02d}")
            os.makedirs(rd, exist_ok=True)
            log(run_dir, f"=== round {n} ===")
            text = brief(best_dir, best, tried)
            open(os.path.join(rd, "BRIEF.md"), "w", encoding="utf-8").write(text)
            t0 = time.time()
            edit, msg = revise(claude_cmd, text, rd)
            log(run_dir, f"    reviser {((time.time()-t0)/60):.1f} min: {msg}")
            rec = {"n": n, "why": "(no edit)", "verdict": ""}
            if not edit:
                rec["verdict"] = f"skipped: {msg}"
                rounds.append(rec)
                if msg.startswith("CLAUDE ERROR") and _FATAL.search(msg):
                    stop = f"Claude Code stopped working ({msg[14:120]}) - sign in again with  claude  then  /login"
                    break
                rejects += 1
                continue
            targets = [str(t) for t in (edit.get("targets") or [])][:6]
            rec["why"] = f"{edit.get('file')}: {edit.get('why', '')} [targets: {', '.join(targets) or 'none'}]"
            sig = (edit.get("file"), edit.get("old"), edit.get("new"))
            if sig in seen_edits:
                rec["verdict"] = "duplicate of an earlier edit - skipped"
                log(run_dir, f"    {rec['verdict']}")
                rounds.append(rec)
                rejects += 1
                continue
            seen_edits.add(sig)
            tried.append(rec["why"])
            cand = os.path.join(rd, "candidate")
            make_candidate(best_dir, cand)
            ok, why = apply_edit(cand, edit)
            if not ok:
                rec["verdict"] = f"invalid edit: {why}"
                log(run_dir, f"    {rec['verdict']}")
                rounds.append(rec)
                rejects += 1
                continue
            log(run_dir, f"    change: {rec['why']}")
            bot = load_bot(cand, run_dir)
            res = evaluate(bot, f"r{n:02d}", run_dir)
            rec.update(score=res["score"], median_s=res["median_s"])
            log(run_dir, f"    score {res['score']} (best {best['score']}), median {res['median_s']}s (best {best['median_s']}s)")
            nc = per_case(res)
            tg, ov = compare(best_cases, nc, targets)
            slower = res["median_s"] > best["median_s"] * SLOWER_OK
            log(run_dir, f"    targets {tg:+.2f}, overall {ov:+.3f}, code fails {res['code_fails']} (best {best_fails:g})")
            better = (tg >= TARGET_GAIN and ov >= -OVERALL_SLACK and not slower
                      and res["code_fails"] <= best_fails + 0.5) or \
                     (ov >= GAIN and not slower)
            faster = (best["median_s"] > 0 and ov >= -SAME_SCORE
                      and res["median_s"] < best["median_s"] * FASTER)
            if (better or faster) and time.time() + res["minutes"] * 60 >= deadline:
                rec["verdict"] = "promising but no time left to confirm - not kept"
                rejects += 1
            elif better or faster:
                log(run_dir, "    promising - confirming with a second run")
                res2 = evaluate(bot, f"r{n:02d}b", run_dir)
                nc2 = per_case(res, res2)
                tg2, ov2 = compare(best_cases, nc2, targets)
                med = round((res["median_s"] + res2["median_s"]) / 2, 2)
                fails2 = (res["code_fails"] + res2["code_fails"]) / 2
                log(run_dir, f"    confirm: targets {tg2:+.2f}, overall {ov2:+.3f}, code fails {fails2:g}")
                keep = (tg2 >= TARGET_CONFIRM and ov2 >= -OVERALL_SLACK and fails2 <= best_fails + 0.5
                        and med <= best["median_s"] * SLOWER_OK) or \
                       (ov2 >= CONFIRM_GAIN and med <= best["median_s"] * SLOWER_OK) or \
                       (best["median_s"] > 0 and ov2 >= -SAME_SCORE and med < best["median_s"] * FASTER)
                avg = round(statistics.mean(nc2.values()), 3)
                rec.update(score=avg, median_s=med)
                if keep:
                    res = dict(res, score=avg, median_s=med, code_fails=fails2)
                    best, best_dir, best_cases, best_fails = res, cand, nc2, fails2
                    rec["verdict"] = "KEPT"
                    rejects = 0
                else:
                    rec["verdict"] = "rejected after confirm run"
                    rejects += 1
            else:
                rec["verdict"] = "rejected: no clear gain"
                rejects += 1
            log(run_dir, f"    {rec['verdict']}")
            rounds.append(rec)
            round_minutes = res["minutes"] + 1.5
    except KeyboardInterrupt:
        stop = "stopped with Ctrl+C"

    best_out = os.path.join(run_dir, "best")
    if os.path.exists(best_out):
        shutil.rmtree(best_out)
    shutil.copytree(best_dir, best_out)
    write_diff(run_dir, base_dir, best_out)
    write_report(run_dir, base, best, rounds, started, stop)
    log(run_dir, f"Done: baseline {base['score']} -> best {best['score']}; "
                 f"median {base['median_s']}s -> {best['median_s']}s. Report: {os.path.join(run_dir, 'REPORT.md')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
