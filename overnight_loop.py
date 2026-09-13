"""
overnight_loop.py - unattended test -> review -> change -> retest loop for Sophia

WHAT IT DOES
------------
Each round:
  1. Claude Code (headless, `claude -p`) reads a brief - current scores, the
     dev-case replies that failed, and every change already tried - and makes
     ONE focused edit to Sophia's SYSTEM_PROMPT.
  2. The edit is validated: prompt-only, no rule from check_prompt_rules.py
     lost, no size blow-up, no characters that would break the Python string.
  3. sophia_eval.py runs the dev cases x3 with thinking OFF, and the local
     judge grades every reply.
  4. If the dev score beat the current best by a clear margin (and it didn't
     get slower), the dev run is repeated to rule out a lucky draw, then the
     held-out cases are run. Only if the held-out cases didn't get worse is
     the change kept (committed to git). Otherwise it's reverted.
  5. REPORT.md is rewritten after every round, so if you stop it early the
     report is still current.

Stops at --rounds, --hours, or after --patience rejections in a row.

WHAT IT IS NOT ALLOWED TO TOUCH
-------------------------------
The reviser works in a throwaway folder containing only a copy of the prompt
text and the brief. It gets Read + Edit on that folder and nothing else
(no shell, no web, no search). It never sees debate_voice.py's code, the
eval, the judge, or the held-out cases. The loop hashes sophia_eval.py,
sophia_judge.py, holdout_cases.py and check_prompt_rules.py at start and
aborts if any of them changes.

SPEED
-----
With thinking off, speed is essentially already won (median ~3.6s in the
eval vs ~12.6s with thinking). So speed is a GUARD here, not the target:
a change is rejected if the median reply time rises more than 1.0s or the
median reply length (tokens) grows more than 45%, measured against the
run's starting baseline so the allowance can't compound round over round. The target is accuracy -
closing the gap to the thinking-on answer quality.

Note the eval's times include re-reading the full ~4,000-token prompt on
every request (each case is a fresh conversation). The live bot primes that
prompt into Ollama's cache once, so live replies start faster than these
numbers. Relative changes are still meaningful.

USAGE
-----
  cd "$env:USERPROFILE\\Desktop\\Ai Chat Bot 2\\sophia-debate-bot"
  $py = "$env:USERPROFILE\\open-webui-env\\Scripts\\python.exe"

  One supervised round first:
    & $py overnight_loop.py --rounds 1 --baseline eval_runs\\eval_all-v246-nothink_20260910-234702.json

  Overnight (after a kept round the prompt has changed, so --baseline no
  longer matches - leave it off and the loop re-measures, ~20 min):
    & $py overnight_loop.py --hours 7.5

  --baseline FILE   reuse an existing `--set all --think false --judge` run of
                    the CURRENT prompt instead of spending ~20 min re-running
                    it. Refused if the prompt has changed since that run.
  --rounds N        max rounds (default 30)
  --hours H         max wall-clock hours (default 7.5)
  --patience N      stop after N rejections in a row (default 8)
  --model NAME      Claude model for the reviser (default: your plan's default)
  --no-git          don't create a branch / commit (snapshots are still kept)

Ctrl+C at any time: the best prompt so far is put back into
debate_voice.py and the report is written before exiting.

Everything lands in overnight_runs/<timestamp>/ (gitignored):
  REPORT.md          the morning summary
  loop.log           full log
  baseline_prompt.txt / best_prompt.txt
  rNN/               per-round brief, reviser output, candidate prompt, eval logs
"""
import argparse
import ctypes
import glob
import hashlib
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
DV = os.path.join(HERE, "debate_voice.py")
MARKER = 'SYSTEM_PROMPT = """'
LOCKED = ["sophia_eval.py", "sophia_judge.py", "holdout_cases.py",
          "check_prompt_rules.py", "overnight_loop.py"]

REPEAT = 3
THINK = "false"
DEV_MARGIN = 0.08        # dev judge mean must beat best by this to be considered
HOLDOUT_TOLERANCE = 0.10 # held-out mean may not drop more than this
# Raised 2026-09-13 (was 0.5 / 1.25). Those values were set when the dev
# median reply was 3.6s and speed was "essentially already won" - but ~2.0s
# of that 3.6s was the localhost/IPv6 connection stall that v2.49 removed,
# and the guards never knew it. At the post-v2.49 median of 32.5 tokens a
# 1.25 ceiling allows about 8 extra tokens - roughly six words - on the
# median reply, which is not enough room to say WHY something is a category
# error. The guard would therefore have rejected the exact change this run
# exists to find, reported as "slower/longer".
#
# 1.45 puts the ceiling near 47 tokens; 1.0s keeps the worst case around
# 2.8s, still well under the 3.6s that was being lived with the day before.
# These are a deliberate spend of the latency v2.49 bought back, not drift.
# If a future run is about speed rather than completeness, put them back.
SPEED_GUARD_S = 1.0      # median reply time may not rise more than this
TOKEN_GUARD = 1.45       # median reply length may not grow more than 45%
PROMPT_GROWTH_CAP = 2500 # prompt may not grow more than this many chars overall
REVISER_TIMEOUT = 900
REVISER_MAX_TURNS = 25


# ---------------------------------------------------------------------------
# small utilities
# ---------------------------------------------------------------------------

class Log:
    def __init__(self, path):
        self.f = open(path, "a", encoding="utf-8")

    def __call__(self, msg=""):
        line = f"[{datetime.now().strftime('%H:%M:%S')}] {msg}" if msg else ""
        print(line, flush=True)
        self.f.write(line + "\n")
        self.f.flush()


def sha(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def write(path, text):
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(text)


def split_source(src):
    """(before, prompt, after) around SYSTEM_PROMPT's triple-quoted body."""
    start = src.index(MARKER) + len(MARKER)
    end = src.index('"""', start)
    return src[:start], src[start:end], src[end:]


def prompt_sha12(prompt):
    # same digest sophia_eval.py prints and stores as prompt_sha
    return hashlib.sha256(prompt.encode("utf-8")).hexdigest()[:12]


def keep_awake():
    """Stop Windows sleeping while this process runs (released on exit)."""
    if os.name == "nt":
        try:
            ctypes.windll.kernel32.SetThreadExecutionState(0x80000000 | 0x00000001)
            return True
        except Exception:
            return False
    return False


def child_env():
    env = dict(os.environ)
    # Redirected child output on Windows defaults to cp1252 and dies on the
    # first curly quote in a reply. Force UTF-8.
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"
    return env


def find_claude():
    exe = shutil.which("claude")
    if exe:
        return exe
    guess = os.path.join(os.path.expanduser("~"), ".local", "bin", "claude.exe")
    return guess if os.path.exists(guess) else None


def git(*args, check=True):
    r = subprocess.run(["git", *args], cwd=HERE, capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    if check and r.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {r.stderr.strip()}")
    return r.stdout.strip()


# ---------------------------------------------------------------------------
# evaluation
# ---------------------------------------------------------------------------

def run_eval(which, label, logdir, log):
    """Runs sophia_eval.py and returns its saved JSON document."""
    cmd = [sys.executable, os.path.join(HERE, "sophia_eval.py"), "--set", which,
           "--think", THINK, "--repeat", str(REPEAT), "--judge", "--label", label]
    logfile = os.path.join(logdir, f"eval_{which}_{label}.log")
    t0 = time.time()
    with open(logfile, "w", encoding="utf-8") as lf:
        r = subprocess.run(cmd, cwd=HERE, stdout=lf, stderr=subprocess.STDOUT,
                           env=child_env())
    # sophia_eval exits 1 whenever any check fails - that's normal. Find the
    # JSON it saved instead of trusting the exit code.
    prefix = "eval_" if which == "dev" else f"eval_{which}-"
    hits = sorted(glob.glob(os.path.join(HERE, "eval_runs", f"{prefix}{label}_*.json")),
                  key=os.path.getmtime)
    if not hits or os.path.getmtime(hits[-1]) < t0:
        raise RuntimeError(f"eval produced no JSON (exit {r.returncode}); see {logfile}")
    log(f"    {which} eval done in {(time.time() - t0) / 60:.1f} min")
    return json.load(open(hits[-1], encoding="utf-8"))


def metrics(records):
    scored = [r for r in records if r.get("judge") and r["judge"].get("score") is not None]
    times = sorted(r["elapsed"] for r in records)
    toks = [r.get("diag", {}).get("eval_count") for r in records if r.get("text")]
    toks = [t for t in toks if t]
    per_case = {}
    for r in scored:
        per_case.setdefault(r["case"], []).append(r["judge"]["score"])
    return {
        "mean": statistics.mean(r["judge"]["score"] for r in scored) if scored else 0.0,
        "n": len(scored),
        "passed": sum(1 for r in scored if r["judge"]["score"] >= 4),
        "median": statistics.median(times) if times else 0.0,
        "p90": times[min(len(times) - 1, int(0.9 * len(times)))] if times else 0.0,
        "tokens": statistics.median(toks) if toks else 0,
        "empty": sum(1 for r in records if not r.get("text", "").strip()),
        "mech_fail": sum(1 for r in records if r.get("failed_checks")),
        "per_case": {c: round(statistics.mean(v), 2) for c, v in sorted(per_case.items())},
    }


def pooled(dev, hold):
    n = dev["n"] + hold["n"]
    return (dev["mean"] * dev["n"] + hold["mean"] * hold["n"]) / n if n else 0.0


def merge_dev(m1, m2, rec1, rec2):
    """Average of two dev runs = metrics over all their records."""
    return metrics(rec1 + rec2)


# ---------------------------------------------------------------------------
# the reviser
# ---------------------------------------------------------------------------

PATTERNS = [
    ("opens by attacking ('You're conflating...', 'You are...')",
     lambda t: bool(re.match(r"\s*(you('re| are)|that'?s a category error|that is a (false|category|non))", t, re.I))),
    ("uses 'conflat...'", lambda t: bool(re.search(r"conflat", t, re.I))),
    ("says 'category error'", lambda t: "category error" in t.lower()),
    ("three or more sentences", None),  # filled from failed_checks
    ("announces its routing / mode", None),
]


def n_dev_cases():
    """Read the real count rather than restating it - the dev set grew from
    14 to 17 on 2026-09-12 and a hardcoded number would have gone stale
    silently, which is exactly how check_ollama_cache.py rotted."""
    import sophia_eval
    return len(sophia_eval.case_pool("dev"))


def n_hold_cases():
    import sophia_eval
    return len(sophia_eval.case_pool("holdout"))


def pattern_counts(records):
    texts = [r for r in records if r.get("text")]
    out = []
    for name, fn in PATTERNS:
        if fn is not None:
            n = sum(1 for r in texts if fn(r["text"]))
        elif name.startswith("three"):
            n = sum(1 for r in records if "sentence_limit" in r.get("failed_checks", []))
        else:
            n = sum(1 for r in records if "no_mode_narration" in r.get("failed_checks", []))
        out.append((name, n, len(texts)))
    return out


def build_brief(prompt_len, cap, dev_m, dev_records, history, round_no):
    lines = []
    A = lines.append
    A("# Brief for round %d" % round_no)
    A("")
    A("You are improving the system prompt of Sophia, a spoken-aloud debate bot. The")
    A("prompt is in `prompt.txt` in this folder. It runs on a local 27B model")
    A("(qwen3.8) with its reasoning/thinking mode turned OFF, for speed. With thinking")
    A("on, the model followed this prompt well but took ~13s per reply and sometimes")
    A("went silent. With thinking off it replies in ~3.6s but follows the prompt less")
    A("faithfully. Your job: edit the prompt so the model follows it better WITHOUT")
    A("thinking. There is no reasoning step - instructions must be executable on a")
    A("single read: short, concrete, placed where they will be seen, and phrased as")
    A("what to do (naming a forbidden phrase explicitly often works better than an")
    A("abstract rule).")
    A("")
    A("## Rules for this round - all are enforced automatically")
    A("")
    A("1. Edit ONLY `prompt.txt`, with the Edit tool. Make ONE focused change that")
    A("   tests ONE idea. Several small edits serving the same idea are fine; a")
    A("   general rewrite is not - if it fails, nobody learns why.")
    A("2. Do not delete or weaken any existing rule. An automated check verifies")
    A("   101 distinct behaviours are still present; losing one rejects the round.")
    A("   Rewording or moving a rule is fine if its substance survives.")
    A("3. Prompt length: currently %d chars, hard cap %d." % (prompt_len, cap))
    A("4. No backslashes and no triple quotes (the prompt lives in a Python string).")
    A("5. Fix the general behaviour, never the specific example. Do not mention")
    A("   the test topics below (zombies, kalam, BITE, Socrates, etc.) in the")
    A("   prompt. A separate hidden test set of real debate turns decides whether a")
    A("   change is kept; changes that only fit these examples will fail it.")
    A("6. Do not make replies longer. Reply length and speed are measured and a")
    A("   change that slows her down is rejected.")
    A("7. Do not repeat an idea from the history below that was already rejected,")
    A("   unless you are doing it in a clearly different way (say how).")
    A("")
    A("When done, your final message must be ONE line starting with `CHANGE:`")
    A("saying what you changed and which failure it targets.")
    A("")
    A("## Current scores (dev set, %d cases x %d runs, judge scores 1-5)"
      % (n_dev_cases(), args.repeat if hasattr(args, "repeat") else 3))
    A("")
    A("- judge mean %.2f, %d/%d replies scored 4+" % (dev_m["mean"], dev_m["passed"], dev_m["n"]))
    A("- median reply time %.1fs, median reply length %s tokens" % (dev_m["median"], dev_m["tokens"]))
    A("")
    A("Recurring patterns in the current replies:")
    for name, n, total in pattern_counts(dev_records):
        A("- %s: %d of %d replies" % (name, n, total))
    A("")
    A("## Replies that fell short (judge score under 4, or a mechanical check failed)")
    A("")
    for r in dev_records:
        j = r.get("judge") or {}
        bad = (j.get("score") is not None and j["score"] < 4) or r.get("failed_checks")
        if not bad:
            continue
        A("### Case %d, run %d - %s" % (r["case"], r["run"], r["name"]))
        A("- INPUT: %s" % r["input"])
        A("- EXPECTED: %s" % r["expected"])
        A("- REPLY: %s" % (r["text"].replace("\n", " ") or "(empty)"))
        A("- JUDGE: %s/5 - %s" % (j.get("score"), j.get("reason", "")))
        if r.get("failed_checks"):
            A("- FAILED CHECKS: %s" % ", ".join(r["failed_checks"]))
        A("")
    A("## History of changes already tried")
    A("")
    if not history:
        A("(none yet - this is the first round)")
    for h in history:
        A("- round %d: %s -> %s" % (h["round"], h["change"], h["verdict"]))
    A("")
    return "\n".join(lines)


REVISER_TOOLS_ALLOW = ["Read(./**)", "Edit(./prompt.txt)"]
REVISER_TOOLS_DENY = ["Bash", "PowerShell", "Write", "WebFetch", "WebSearch",
                      "Glob", "Grep", "Agent", "Task", "NotebookEdit", "mcp__*"]


def run_reviser(claude, workdir, model, log):
    cmd = [claude, "-p", "Read BRIEF.md in this folder and follow it exactly.",
           "--output-format", "json", "--max-turns", str(REVISER_MAX_TURNS),
           "--permission-mode", "dontAsk",
           "--allowedTools", *REVISER_TOOLS_ALLOW,
           "--disallowedTools", *REVISER_TOOLS_DENY]
    if model:
        cmd += ["--model", model]
    t0 = time.time()
    try:
        r = subprocess.run(cmd, cwd=workdir, capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=REVISER_TIMEOUT)
    except subprocess.TimeoutExpired:
        return None, "reviser timed out"
    write(os.path.join(workdir, "..", "reviser_stdout.json"), r.stdout)
    if r.stderr.strip():
        write(os.path.join(workdir, "..", "reviser_stderr.txt"), r.stderr)
    log(f"    reviser finished in {(time.time() - t0) / 60:.1f} min (exit {r.returncode})")
    summary = ""
    try:
        doc = json.loads(r.stdout)
        text = doc.get("result") or ""
        m = re.search(r"CHANGE:\s*(.+)", text)
        summary = (m.group(1) if m else text).strip().splitlines()[0][:300] if text else ""
        if doc.get("is_error"):
            return summary, f"reviser reported an error ({doc.get('subtype')})"
    except (ValueError, IndexError):
        if r.returncode != 0:
            return None, f"reviser failed (exit {r.returncode}): {r.stderr.strip()[:300]}"
    return summary or "(no summary given)", None


def validate(candidate, baseline_prompt, cap, rules_mod):
    if candidate is None or not candidate.strip():
        return "prompt is empty"
    if '"""' in candidate:
        return "contains triple quotes"
    if "\\" in candidate:
        return "contains a backslash"
    if len(candidate) > cap:
        return f"too long ({len(candidate)} > cap {cap})"
    # rule check: nothing present in the baseline may go missing
    norm = rules_mod._norm
    lost = []
    for version, rule, pats in rules_mod.RULES:
        was = any(re.search(norm(p), norm(baseline_prompt), re.S | re.I) for p in pats)
        now = any(re.search(norm(p), norm(candidate), re.S | re.I) for p in pats)
        if was and not now:
            lost.append(f"[{version}] {rule}")
    if lost:
        return "lost rule(s): " + "; ".join(lost[:5])
    return None


# ---------------------------------------------------------------------------
# report
# ---------------------------------------------------------------------------

def write_report(path, S):
    b, best = S["baseline"], S["best"]
    L = []
    A = L.append
    A("# Overnight run %s" % S["stamp"])
    A("")
    A("Started %s, report written %s. Rounds run: %d." % (
        S["started"], datetime.now().strftime("%Y-%m-%d %H:%M"), len(S["history"])))
    if S.get("stop_reason"):
        A("Stopped because: %s." % S["stop_reason"])
    A("")
    A("## Bottom line")
    A("")
    A("| | Baseline (v2.46, thinking off) | Best found |")
    A("|---|---|---|")
    A("| Judge mean, dev + held-out | %.2f | %.2f |" % (pooled(b["dev"], b["hold"]), pooled(best["dev"], best["hold"])))
    A("| Judge mean, dev (%d cases) | %.2f | %.2f |" % (n_dev_cases(), b["dev"]["mean"], best["dev"]["mean"]))
    A("| Judge mean, held-out (%d cases) | %.2f | %.2f |" % (n_hold_cases(), b["hold"]["mean"], best["hold"]["mean"]))
    A("| Replies scoring 4+ | %d/%d | %d/%d |" % (
        b["dev"]["passed"] + b["hold"]["passed"], b["dev"]["n"] + b["hold"]["n"],
        best["dev"]["passed"] + best["hold"]["passed"], best["dev"]["n"] + best["hold"]["n"]))
    A("| Median reply time (dev) | %.1fs | %.1fs |" % (b["dev"]["median"], best["dev"]["median"]))
    A("| Median reply length (dev, tokens) | %s | %s |" % (b["dev"]["tokens"], best["dev"]["tokens"]))
    A("| Prompt size | %d chars | %d chars |" % (b["prompt_len"], best["prompt_len"]))
    A("")
    A("For reference, thinking ON scored 3.85 overall and 4.47 on the replies it")
    A("actually gave, with 14 silent replies out of 78. Its 12.6s median is NOT")
    A("comparable to anything measured from v2.49 on: every timing recorded")
    A("before the 2026-09-12 localhost/IPv6 fix carries ~2s of connection stall")
    A("per request. Compare times only within this run.")
    A("")
    A("## Rounds")
    A("")
    A("| # | Change | Dev | Held-out | Median | Verdict |")
    A("|---|---|---|---|---|---|")
    for h in S["history"]:
        A("| %d | %s | %s | %s | %s | %s |" % (
            h["round"], h["change"].replace("|", "/"),
            "%.2f" % h["dev"] if h.get("dev") is not None else "-",
            "%.2f" % h["hold"] if h.get("hold") is not None else "-",
            "%.1fs" % h["median"] if h.get("median") is not None else "-",
            h["verdict"].replace("|", "/")))
    A("")
    A("## Per case (judge mean) - baseline -> best")
    A("")
    for which in ("dev", "hold"):
        for c, v in b[which]["per_case"].items():
            nv = best[which]["per_case"].get(c, v)
            arrow = "  " if abs(nv - v) < 0.34 else ("UP" if nv > v else "DOWN")
            A("- case %s: %.2f -> %.2f %s" % (c, v, nv, arrow))
    A("")
    A("## Next steps")
    A("")
    A("1. Read `best_vs_baseline.diff` in this folder - that's every prompt change kept.")
    A("2. Ask Claude to review the best version's replies against the baseline's.")
    A("3. Copy the best `debate_voice.py` into the folder you launch Sophia from and")
    A("   run a real session with thinking off before trusting any of this.")
    write(path, "\n".join(L) + "\n")


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(description="Overnight prompt-improvement loop for Sophia")
    ap.add_argument("--rounds", type=int, default=30)
    ap.add_argument("--hours", type=float, default=7.5)
    ap.add_argument("--patience", type=int, default=8)
    ap.add_argument("--baseline", default="")
    ap.add_argument("--model", default="")
    ap.add_argument("--no-git", action="store_true")
    a = ap.parse_args()

    stamp = datetime.now().strftime("%Y%m%d-%H%M")
    run_dir = os.path.join(HERE, "overnight_runs", stamp)
    os.makedirs(run_dir, exist_ok=True)
    log = Log(os.path.join(run_dir, "loop.log"))
    deadline = time.time() + a.hours * 3600

    # ---- preflight ------------------------------------------------------
    log(f"Overnight loop {stamp} - rounds<={a.rounds}, hours<={a.hours}, patience {a.patience}")
    claude = find_claude()
    if not claude:
        raise SystemExit("Claude Code not found. Open a new PowerShell window or check the install.")
    v = subprocess.run([claude, "--version"], capture_output=True, text=True)
    log(f"claude: {v.stdout.strip()}")
    for f in LOCKED:
        if not os.path.exists(os.path.join(HERE, f)):
            raise SystemExit(f"missing {f} next to this script")
    try:
        import requests
        requests.get("http://127.0.0.1:11434/api/tags", timeout=5).raise_for_status()
    except Exception as e:
        raise SystemExit(f"Ollama isn't answering on 127.0.0.1:11434 ({e}). Start it first.")
    locked_hashes = {f: sha(os.path.join(HERE, f)) for f in LOCKED}
    sys.path.insert(0, HERE)
    import check_prompt_rules as rules_mod
    log("keep-awake: " + ("on" if keep_awake() else "not available - disable sleep manually"))

    use_git = not a.no_git and shutil.which("git") is not None
    if not a.no_git and not use_git:
        log("git not found - continuing with file snapshots only")

    src0 = read(DV)
    before, baseline_prompt, after = split_source(src0)
    write(os.path.join(run_dir, "baseline_prompt.txt"), baseline_prompt)
    shutil.copy(DV, os.path.join(run_dir, "baseline_debate_voice.py"))
    cap = len(baseline_prompt) + PROMPT_GROWTH_CAP

    if use_git:
        branch = f"overnight/{stamp}"
        git("checkout", "-b", branch)
        git("add", "debate_voice.py", "sophia_eval.py", "sophia_judge.py",
            "overnight_loop.py", ".gitignore")
        if git("diff", "--cached", "--name-only"):
            git("commit", "-m", f"overnight {stamp}: baseline (v2.46 prompt + eval tools)")
        log(f"git branch {branch} created; your main branch is untouched")

    # ---- baseline -------------------------------------------------------
    if a.baseline:
        doc = json.load(open(os.path.join(HERE, a.baseline) if not os.path.isabs(a.baseline)
                             else a.baseline, encoding="utf-8"))
        if doc.get("prompt_sha") != prompt_sha12(baseline_prompt):
            raise SystemExit("--baseline was run on a different prompt; drop --baseline "
                             "to measure the current one fresh")
        if doc.get("think") != THINK or doc.get("set") != "all":
            raise SystemExit("--baseline must be a `--set all --think false --judge` run")
        dev_recs = [r for r in doc["records"] if r["case"] < 100]
        hold_recs = [r for r in doc["records"] if r["case"] > 100]
        log("baseline: reusing " + os.path.basename(a.baseline))
    else:
        log("baseline: measuring current prompt (dev + held-out, ~20 min)")
        dev_recs = run_eval("dev", f"on{stamp}-r00", run_dir, log)["records"]
        hold_recs = run_eval("holdout", f"on{stamp}-r00", run_dir, log)["records"]

    base = {"dev": metrics(dev_recs), "hold": metrics(hold_recs),
            "prompt_len": len(baseline_prompt)}
    best = dict(base, prompt=baseline_prompt, dev_records=dev_recs)
    S = {"stamp": stamp, "started": datetime.now().strftime("%Y-%m-%d %H:%M"),
         "baseline": base, "best": best, "history": []}
    log(f"baseline: dev {base['dev']['mean']:.2f}, held-out {base['hold']['mean']:.2f}, "
        f"pooled {pooled(base['dev'], base['hold']):.2f}, median {base['dev']['median']:.1f}s")
    report = os.path.join(run_dir, "REPORT.md")
    write_report(report, S)

    def put_prompt(p):
        write(DV, before + p + after)

    def finish(reason):
        S["stop_reason"] = reason
        put_prompt(best["prompt"])
        write(os.path.join(run_dir, "best_prompt.txt"), best["prompt"])
        shutil.copy(DV, os.path.join(run_dir, "best_debate_voice.py"))
        import difflib
        diff = difflib.unified_diff(baseline_prompt.splitlines(True), best["prompt"].splitlines(True),
                                    "baseline_prompt", "best_prompt")
        write(os.path.join(run_dir, "best_vs_baseline.diff"), "".join(diff))
        write_report(report, S)
        log(f"STOPPED: {reason}. Report: {report}")

    streak = 0
    rnd = 0
    try:
        while True:
            if rnd >= a.rounds:
                return finish(f"reached {a.rounds} rounds")
            if time.time() > deadline - 20 * 60:
                return finish(f"time limit ({a.hours}h) reached")
            if streak >= a.patience:
                return finish(f"{a.patience} rejected rounds in a row")
            rnd += 1
            rdir = os.path.join(run_dir, f"r{rnd:02d}")
            work = os.path.join(rdir, "workspace")
            os.makedirs(work, exist_ok=True)
            log("")
            log(f"=== round {rnd} ===")

            # 1. reviser
            write(os.path.join(work, "prompt.txt"), best["prompt"])
            write(os.path.join(work, "BRIEF.md"),
                  build_brief(len(best["prompt"]), cap, best["dev"], best["dev_records"],
                              S["history"], rnd))
            shutil.copy(os.path.join(work, "BRIEF.md"), os.path.join(rdir, "BRIEF.md"))
            summary, err = run_reviser(claude, work, a.model, log)
            candidate = read(os.path.join(work, "prompt.txt"))
            h = {"round": rnd, "change": summary or "(none)"}
            S["history"].append(h)
            if candidate == best["prompt"]:
                h["verdict"] = "no change made" + (f" ({err})" if err else "")
                log("    " + h["verdict"])
                streak += 1
                write_report(report, S)
                continue
            write(os.path.join(rdir, "candidate_prompt.txt"), candidate)
            log(f"    change: {h['change']}")

            # 2. validate
            problem = validate(candidate, baseline_prompt, cap, rules_mod)
            if problem:
                h["verdict"] = "rejected before testing: " + problem
                log("    " + h["verdict"])
                streak += 1
                write_report(report, S)
                continue

            # 3. dev eval
            put_prompt(candidate)
            try:
                d1 = run_eval("dev", f"on{stamp}-r{rnd:02d}", rdir, log)["records"]
            except Exception as e:
                put_prompt(best["prompt"])
                h["verdict"] = f"eval error: {e}"
                log("    " + h["verdict"])
                streak += 1
                write_report(report, S)
                continue
            for f, hsh in locked_hashes.items():
                if sha(os.path.join(HERE, f)) != hsh:
                    put_prompt(best["prompt"])
                    return finish(f"LOCKED FILE CHANGED: {f} - stopping for safety")
            m1 = metrics(d1)
            h.update(dev=m1["mean"], median=m1["median"])
            log(f"    dev {m1['mean']:.2f} (best {best['dev']['mean']:.2f}), median "
                f"{m1['median']:.1f}s, tokens {m1['tokens']}")

            # Guards are measured against the run's BASELINE, not the current
            # best - otherwise each kept round could add its own +0.5s / +25%
            # and the allowances would compound over a night.
            slower = (m1["median"] > base["dev"]["median"] + SPEED_GUARD_S or
                      (base["dev"]["tokens"] and m1["tokens"] > base["dev"]["tokens"] * TOKEN_GUARD))
            if m1["mean"] < best["dev"]["mean"] + DEV_MARGIN or slower:
                put_prompt(best["prompt"])
                h["verdict"] = "rejected: " + ("slower/longer" if slower else "no clear dev gain")
                log("    " + h["verdict"])
                streak += 1
                write_report(report, S)
                continue

            # 4. confirm dev, then held-out
            log("    promising - confirming dev and running held-out")
            d2 = run_eval("dev", f"on{stamp}-r{rnd:02d}b", rdir, log)["records"]
            md = metrics(d1 + d2)
            hr = run_eval("holdout", f"on{stamp}-r{rnd:02d}", rdir, log)["records"]
            mh = metrics(hr)
            h.update(dev=md["mean"], hold=mh["mean"], median=md["median"])
            log(f"    dev (2 runs) {md['mean']:.2f}, held-out {mh['mean']:.2f} "
                f"(best {best['hold']['mean']:.2f})")
            if (md["mean"] < best["dev"]["mean"] + DEV_MARGIN / 2 or
                    mh["mean"] < best["hold"]["mean"] - HOLDOUT_TOLERANCE):
                put_prompt(best["prompt"])
                h["verdict"] = ("rejected: gain didn't hold on re-run"
                                if md["mean"] < best["dev"]["mean"] + DEV_MARGIN / 2
                                else "rejected: held-out got worse")
                log("    " + h["verdict"])
                streak += 1
                write_report(report, S)
                continue

            # 5. keep
            best.update(prompt=candidate, dev=md, hold=mh, prompt_len=len(candidate),
                        dev_records=d1 + d2)
            h["verdict"] = "KEPT"
            streak = 0
            write(os.path.join(run_dir, "best_prompt.txt"), candidate)
            if use_git:
                git("add", "debate_voice.py")
                git("commit", "-m", f"overnight r{rnd:02d}: {h['change'][:120]} "
                    f"(dev {md['mean']:.2f}, held-out {mh['mean']:.2f})")
            log(f"    KEPT - new best: pooled {pooled(md, mh):.2f}")
            write_report(report, S)
    except KeyboardInterrupt:
        finish("stopped by you (Ctrl+C)")
    except Exception as e:
        finish(f"crashed: {e!r}")
        raise


if __name__ == "__main__":
    main()
