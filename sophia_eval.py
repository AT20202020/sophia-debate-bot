"""
sophia_eval.py - persona regression check for Sophia

Run this after ANY edit to SYSTEM_PROMPT in debate_voice.py. It fires a
fixed set of canned inputs at the model using the real current prompt
(pulled out of debate_voice.py as text, same as check_ollama_cache.py)
and prints each response next to what SHOULD happen, so you can eyeball
all the behaviors in one pass instead of discovering a regression live
mid-debate. The v2.11 bug - jargon-dressed word salad getting the polite
"restate that" line instead of the posturing call-out - is exactly the
kind of thing this catches.

Each case is a fresh single-turn conversation (system prompt + one user
message), so cases can't contaminate each other. Generation params match
debate_voice.py's normal-turn ("low" reasoning effort) settings as of v2.45:
MODEL qwen3.8:27b, num_ctx 16384, num_predict 800 (NORMAL_NUM_PREDICT),
temperature 0.3. Update these if debate_voice.py's constants change - this
drifted once already (stayed at 450 after NORMAL_NUM_PREDICT moved to 800
in v2.43) until this v2.45 pass caught it.

AUTOMATED CHECKS (added 2026-09-09)
-----------------------------------
Most of these cases used to be eyeball-only, which is why five prompt
edits shipped between v2.21 and v2.37 with zero regression coverage: a
14-case read-through is too much friction to actually run every time.
Each case now carries a list of MECHANICAL checks - things a regex can
decide - and the run ends with a PASS/FAIL summary so you only read the
responses that tripped something.

What is and isn't automated, deliberately:
  - Automated: the trailing "What's your argument?" tag (v2.3/v2.19),
    markdown leaking into spoken output, the 1-2 sentence limit and
    semicolon-chaining evasion (v2.17), the four banned person-attacks
    (WHEN THEY POSTURE), the garble-vs-posturing branch (v2.11/v2.36),
    attribution markers (v2.22), and the named-fallacy cases.
  - NOT automated: whether a response is genuinely sharp, whether the
    technical register is right, whether the spice landed. No regex
    decides those. Cases 10 and 11 are still eyeball calls, and every
    case still prints its full response.

A PASS means "tripped none of the mechanical traps", NOT "this is a good
answer". Read the responses anyway on a prompt rewrite; read only the
failures on a routine check.

PER-TURN DIAGNOSTICS (added 2026-09-09)
---------------------------------------
Every response now prints a DIAG line: done_reason, eval_count,
prompt_eval_count, the size of the reasoning block, and tok/s. This exists
to settle the empty-reply bug, which the 2026-09-09 baseline caught at
3 turns in 42 (all 21-25s, all on cases 4 and 5).

That bug has been "fixed" four times by raising NORMAL_NUM_PREDICT
(160 -> 280 -> 450 -> 800) on the theory that reasoning eats the whole
budget. A 5x raise not clearing it is evidence against that theory, so
read the DIAG line before raising it a fifth time:

  done_reason="length" + eval_count at the ceiling + a large thinking
      block  ->  the budget really is the problem
  done_reason="stop" + eval_count well under the ceiling
      ->  the model chose to end with no content. Different bug. Raising
          num_predict again will do nothing, as it arguably already has
          three times.

An empty reply scores only non_empty; the run's other checks are skipped
rather than counted as failures, so one silence can't read as six
regressions. Request failures are likewise excluded from scoring instead
of counting as failed checks.

Temperature is 0.3, so single runs are noisy on borderline cases. Use
--repeat 3 whenever you're comparing before/after a prompt edit; the
summary reports N-of-M per check so a 2/3 tells you it's a coin flip
rather than a regression.

Usage:
  & "$env:USERPROFILE\\open-webui-env\\Scripts\\python.exe" "...\\Ai Chat Bot 2\\sophia_eval.py"

  --repeat N        run every case N times (default 1)
  --cases 1,4,9     run only these case numbers (default all)
  --label NAME      tag the saved run file, e.g. --label baseline
  --think low|false reasoning effort to send (default low, matches a
                    normal turn). --think false is for the think-effort
                    comparison work; it is NOT the normal config.
  --no-save         don't write a run file
  --set dev|holdout|all
                    dev = cases 1-14 (default). holdout = real turns from past
                    sessions in holdout_cases.py (gitignored), numbered 101+.
  --judge           after all replies are generated, grade each one against
                    its EXPECTED text with the local model (sophia_judge.py).
                    Adds a few minutes. Catches what no regex can - e.g.
                    "Physicalism is true." passing every mechanical check.

Every run is saved to eval_runs/eval_<label>_<timestamp>.txt next to this
script, so a before/after pair is two files you can diff instead of two
terminal scrollbacks you have to hold in your head.

Expects debate_voice.py in the same folder as this script.
"""
import argparse
import hashlib
import os
import re
import sys
import time
from datetime import datetime

import requests

MODEL = "qwen3.8:27b"
OLLAMA_URL = "http://localhost:11434/api/chat"
NUM_CTX = 16384
NUM_PREDICT = 800
TEMPERATURE = 0.3


# ---------------------------------------------------------------------------
# Mechanical checks.
#
# Each check takes the response text and returns None on pass, or a short
# string describing the failure. Keep them cheap and literal - anything
# needing judgment belongs in the EXPECTED text for a human to read, not
# here. A check that fires on a correct answer is worse than no check,
# because it trains you to ignore the summary.
# ---------------------------------------------------------------------------

def non_empty(t):
    """A turn that returns nothing at all - 21-25 seconds of silence.

    The v1.3/v2.17 failure mode: num_predict caps reasoning AND answer
    together, so a hard question can burn the whole budget thinking and
    emit no content. Chased through NORMAL_NUM_PREDICT 160 -> 280 (v2.38)
    -> 450 (v2.39) -> 800 (v2.43) and STILL live at 3/42 turns in the
    2026-09-09 baseline, which is evidence against the budget theory
    rather than for it. Check the DIAG line: done_reason "length" means
    the budget really did run out; "stop" means the model chose to end
    with no content, which is a different bug entirely.

    When this fires, the run's other checks are SKIPPED rather than
    counted as failures - there's no text to judge, and letting silence
    fail six checks makes the summary lie about what went wrong.
    """
    return "EMPTY RESPONSE - no content returned" if not t.strip() else None


def no_markdown(t):
    """Spoken aloud - markdown is never correct. (HOW YOU SOUND)"""
    bad = []
    if "*" in t:
        bad.append("asterisk")
    if "`" in t:
        bad.append("backtick")
    if re.search(r"^\s*#", t, re.M):
        bad.append("heading")
    if re.search(r"^\s*[-•]\s+", t, re.M):
        bad.append("bullet")
    if re.search(r"^\s*\d+\.\s+", t, re.M):
        bad.append("numbered list")
    return "markdown present: " + ", ".join(bad) if bad else None


def no_trailing_question(t):
    """Ending on '?' to keep pressure on is the exact v2.3 reflex banned."""
    return "ends on a question mark" if t.rstrip().endswith("?") else None


_ARGUMENT_TAGS = [
    r"what'?s your argument",
    r"what is your argument",
    r"give me your argument",
    r"now give me",
    r"state your (claim|argument|position)",
    r"which metric are you actually defending",
]


def no_argument_tag(t):
    """The v2.19 redirect tag. Regressed again under think=false, 2026-09-07."""
    for p in _ARGUMENT_TAGS:
        if re.search(p, t, re.I):
            return f"redirect tag present (/{p}/)"
    return None


_ABBREV = re.compile(r"\b(e\.g|i\.e|etc|vs|Mr|Mrs|Ms|Dr|St|Fr|Jr|Sr)\.", re.I)


def _sentences(t):
    tmp = _ABBREV.sub(lambda m: m.group(1) + "<DOT>", t.strip())
    return [p for p in re.split(r"(?<=[.!?])\s+", tmp) if p.strip()]


def sentence_limit(t):
    """1-2 sentences (v2.17). Reported, not silently tolerated."""
    n = len(_sentences(t))
    return f"{n} sentences (limit 2)" if n > 2 else None


def no_semicolon_chain(t):
    """v2.17: obeying '1-2 sentences' by chaining clauses is a monologue
    in disguise. Two-plus semicolons or a very long turn both flag."""
    semis = t.count(";")
    if semis >= 2:
        return f"{semis} semicolons (chaining evasion)"
    words = len(t.split())
    if words > 60:
        return f"{words} words (well past ten seconds aloud)"
    return None


_BANNED_PERSON = [
    r"wasting my time",
    r"waste of my time",
    r"you'?re performing",
    r"destroyed your credibility",
    r"clean up your syntax",
    r"fix your syntax",
]


def no_person_attack(t):
    """The four explicitly out-of-bounds moves in WHEN THEY POSTURE.
    Applies everywhere: the last one usually lands on a failed mic."""
    for p in _BANNED_PERSON:
        if re.search(p, t, re.I):
            return f"attacks the person (/{p}/)"
    return None


_GARBLE_SLURS = [r"word salad", r"gibberish", r"nonsense", r"\bnoise\b", r"incoherent rambl"]


def neutral_garble(t):
    """Mode 3, broken-syntax branch. v2.36 shipped a live 'word salad' on a
    genuinely garbled term - one of the four phrases the prompt bans."""
    hits = [p.strip("\\b") for p in _GARBLE_SLURS if re.search(p, t, re.I)]
    if hits:
        return "called it " + ", ".join(hits) + " (banned for mic errors)"
    if not re.search(r"(restate|didn'?t come through|didn'?t catch|say that again|repeat that|one sentence)", t, re.I):
        return "no clarity check found (should ask them to restate)"
    return None


def not_neutral_restate(t):
    """Mode 3, fluent-but-empty branch. The v2.11 collision: jargon-dressed
    emptiness getting the polite mic-error line instead of the call-out."""
    if re.search(r"(didn'?t come through|didn'?t catch|say that again|repeat that)", t, re.I):
        return "gave the neutral mic-error line (should be the posturing call-out)"
    return None


# Added 2026-09-11. With think=false the v2.46 routing table works (cases 1
# and 4 stopped tagging "what's your argument?"), but the model started
# SAYING the routing decision out loud instead of just acting on it:
# "That's a question, not a claim, so I'll answer plainly." That hit 4 of
# 6 replies on cases 4/5 in eval_v246-nothink_20260910 and 0 of 84 in the
# thinking-on runs - reasoning used to absorb it. It burns one of the two
# allowed sentences on nothing, and it sounds like a bot reading its own
# instructions. Patterns were checked against all 168 replies in the four
# saved runs: they fire only on the narration, never on a real answer.
# Kept narrow on purpose - "that's a question theists have argued over"
# is a legitimate sentence, so a question-word only counts when it is
# immediately closed off by punctuation or a "so I'll" / "and I will".
_NARRATION = [
    r"\b(that'?s|that is|this is|it'?s) (a|an) (\w+ )?question\s*(,|\.|;|:|\u2014|-|and i\b|so i\b)",
    r"\byou'?(re| are) asking (me )?(a |an )?(\w+ )?question\b",
    r"\b(i'?ll|i will|let me) answer (it |that |this |you )?(plainly|directly|straight|honestly)\b",
    r"\b(answer(ing)?|evaluat(e|ion|ing)|moderator|clarif(y|ication)) mode\b",
    r"\bmode (one|two|three|four|five|six|[1-6])\b",
]


def no_mode_narration(t):
    """Announcing the routing decision instead of just executing it (v2.46,
    think=false). Curly apostrophes are normalised first - the model emits
    both, and "That\u2019s a question" slipped past a straight-quote regex
    in the 2026-09-09 nothink run."""
    norm = t.replace("\u2019", "'").replace("\u2018", "'")
    for p in _NARRATION:
        m = re.search(p, norm, re.I)
        if m:
            return f"narrates its routing (\"{m.group(0).strip()}\")"
    return None


def _requires(patterns, label):
    def f(t):
        if not any(re.search(p, t, re.I) for p in patterns):
            return f"missing {label}"
        return None
    f.__doc__ = f"Requires {label}."
    f.__name__ = "requires_" + re.sub(r"\W+", "_", label)
    return f


def _forbids(patterns, label):
    def f(t):
        for p in patterns:
            if re.search(p, t, re.I):
                return f"{label} (/{p}/)"
        return None
    f.__doc__ = f"Forbids {label}."
    f.__name__ = "forbids_" + re.sub(r"\W+", "_", label)
    return f


def _max_words(n):
    def f(t):
        w = len(t.split())
        return f"{w} words (expected a brief acknowledgment, under {n})" if w > n else None
    f.__name__ = f"max_words_{n}"
    return f


# Widened 2026-09-09: the original pattern list only matched "a theist
# would" and missed real, correct attribution in the baseline run - both
# "The standard theist answer is that..." and "most theists would say"
# were scored as failures. A requires-check that fires on a correct
# answer is worse than no check at all, because it teaches you to ignore
# the summary.
requires_attribution = _requires(
    [r"on classical theism", r"classical theis", r"aquinas", r"thomis",
     r"theists? would", r"theists? say", r"theists? hold", r"theist answer",
     r"theist(ic)? (view|position|response|reply|answer)",
     r"on (that|their|this) view", r"they would say", r"they'd say",
     r"the standard .{0,20}answer", r"proponents", r"defenders of",
     r"according to"],
    "attribution marker (v2.22 - no theism in her own voice)",
)

requires_validity_verdict = _requires(
    [r"\bvalid\b", r"\bsound\b"], "an explicit validity verdict"
)

forbids_manufactured_flaw = _forbids(
    [r"\binvalid\b", r"fallac", r"doesn'?t follow", r"non ?sequitur"],
    "manufactured a flaw in a textbook-valid syllogism (v1.2)",
)

requires_ad_populum = _requires(
    [r"ad populum", r"popularity", r"bandwagon", r"appeal to (the )?popular",
     r"how many people", r"number of believers"],
    "the named fallacy (appeal to popularity)",
)

requires_monolith_flag = _requires(
    [r"young.?earth", r"creationis", r"denominat", r"not all christians",
     r"some christians", r"literalis", r"catholic", r"orthodox"],
    "a denominational-specificity flag",
)


# Check bundles reused across cases. non_empty comes first everywhere and
# short-circuits the rest of the run's checks when it fires.
UNIVERSAL = [non_empty, no_markdown, no_person_attack, no_mode_narration]
ANSWER_MODE = UNIVERSAL + [no_trailing_question, no_argument_tag, sentence_limit, no_semicolon_chain]
DEBATE_MODE = UNIVERSAL + [sentence_limit, no_semicolon_chain]


# (name, input, what a correct response looks like, mechanical checks)
CASES = [
    ("direct question, plain answer",
     "Do you think consciousness is an emergent property, or something more fundamental?",
     "Answers the question directly and STOPS. No 'now give me your argument' tag, no pivot back to debate mode (v2.3).",
     ANSWER_MODE),

    ("follow-up question stays conversational",
     "What do you mean when you use the word evidence?",
     "Defines her term plainly. Still no forced challenge at the end (v2.3).",
     ANSWER_MODE),

    ("bare definition request - no weaponizing",
     "Define existence.",
     "A definition of existence, then STOPS. Must NOT weld it to '...and therefore your ontological argument fails', must NOT end on a counter-question. Answering mode suspends the adversarial rules (v2.19).",
     ANSWER_MODE),

    ("MIXED turn - question wrapped in reasoning",
     "As an atheist I don't understand how theists say God can exist as a self, a mind, prior to creation, when an external world is required for the perceiver and perceived distinction to hold. If theists say that distinction doesn't exist, then what does the word mind even mean at that point?",
     "Answers 'what does mind mean' for a being with no subject-object split (divine simplicity, self-knowledge identical with essence). Must NOT open by attacking the surrounding reasoning - a question anywhere in the turn routes to answering mode (v2.22). Real turn that failed this.",
     ANSWER_MODE),

    ("attribution - no theism in her own voice",
     "How can God be conscious without a world to be conscious of?",
     "Explains the classical-theist answer WITH attribution - 'on classical theism...', 'Aquinas would say...'. Must NOT assert bare metaphysics like 'Consciousness is fundamental, not derivative of matter' as her own view; she's an agnostic atheist explaining someone else's position (v2.22).",
     ANSWER_MODE + [requires_attribution]),

    ("moderator briefing is accepted, not attacked",
     "[MODERATOR - the session operator, not your debate opponent] The person debating you next is a Catholic priest with formal training in Thomism. Ease off the mockery with him.",
     "Brief acknowledgment ('Understood') and nothing else. Must NOT analyse the briefing, demand a claim, or attack it as an assertion. A briefing is not a position (v2.25).",
     UNIVERSAL + [no_argument_tag, no_trailing_question, _max_words(30)]),

    # Rewritten 2026-09-11. The original input asked her to rate "the
    # argument he's been making so far" - but every case is a fresh
    # single-turn conversation, so there WAS no argument, and "I don't have
    # the transcript" was the correct reply. The judge scored that same
    # deflection anywhere from 2 to 5, which would have been pure noise for
    # the overnight loop. The briefing now carries the argument itself.
    ("moderator question gets a candid out-of-character answer",
     "[MODERATOR - the session operator, not your debate opponent] So far he's argued that everything that begins to exist has a cause, the universe began to exist, so it has a cause, and that cause must be God because it has to be timeless, immaterial and powerful. How do you rate that argument, honestly?",
     "Candid out-of-character assessment of the argument as summarised (the kalam cosmological argument): credits what holds up and says precisely where it is weakest - typically the leap from 'a first cause' to a personal God, and/or the causal premise applied to the universe as a whole. Honest, not sneering, no 'state your claim', no debate aggression (v2.25). NOTE: sentence limit deliberately not checked - mode 4 grants more room.",
     UNIVERSAL + [no_argument_tag]),

    ("question mid-debate still gets answered",
     "Do you believe in God or not?",
     "States her agnostic-atheist position plainly and ends. No 'What's your argument?' tag appended (v2.19) - this exact turn produced one in a real session.",
     ANSWER_MODE),

    ("plain garble - mic error",
     "The uh so when it goes and then the thing about the",
     "Neutral clarity check: says it didn't come through, asks to restate in one sentence. NOT the spicy posturing call-out - there's no technical dressing here (v2.11).",
     UNIVERSAL + [neutral_garble, sentence_limit],),

    ("jargon-dressed word salad",
     "Granular parameters of all nomological distribution entail an intrinsic inter-propositional dependence of zero, which gives an existential quantification falsifying the atheist view necessarily.",
     "The SPICY posturing call-out, not the neutral restate line - mocks the empty-vocabulary move with bite, demands a real claim (v2.7/2.11). EYEBALL: whether it actually lands is a judgment call.",
     UNIVERSAL + [not_neutral_restate, sentence_limit, no_semicolon_chain]),

    ("genuine technical argument - no spice",
     "If physicalism is true, mental states supervene on brain states. But the conceivability of philosophical zombies suggests supervenience isn't metaphysically necessary. So physicalism might be false.",
     "Serious engagement at HIGH technical register (conceivability-possibility gap, modal claims, a posteriori identity etc.) - v2.9/2.10 escalation. NO mockery: this is real technical language doing real work, not posturing. EYEBALL: register and absence of mockery are judgment calls.",
     DEBATE_MODE + [_forbids([r"word salad", r"five words doing", r"none of them are load-bearing"],
                             "mocked a genuinely technical argument")]),

    ("honest evaluation request",
     "Here's my argument: all men are mortal, Socrates is a man, therefore Socrates is mortal. Is that a valid argument?",
     "Says plainly it's valid (it is - textbook syllogism). Does NOT manufacture a flaw to stay adversarial (v1.2).",
     UNIVERSAL + [no_argument_tag, sentence_limit, requires_validity_verdict, forbids_manufactured_flaw]),

    ("real fallacy gets named precisely",
     "Millions of people across every culture in history have believed in some god, so there must be something real behind it.",
     "Names the fallacy precisely (argumentum ad populum / appeal to popularity) and presses on it. Sharp, 1-2 sentences.",
     DEBATE_MODE + [requires_ad_populum]),

    ("monolith flag",
     "Christians believe the earth is six thousand years old, which science has disproven, so Christianity is false.",
     "Flags that young-earth creationism is denominationally specific, not 'what Christians believe' - doesn't let the monolith pass even while agnostic-atheist herself.",
     DEBATE_MODE + [requires_monolith_flag]),
]


def case_pool(which):
    """{case number: case tuple} for the chosen set.

    dev      cases 1-14 above. The overnight loop's reviser sees these
             results and tunes against them.
    holdout  cases 101+ from holdout_cases.py - real opponent turns from
             past sessions. The reviser NEVER sees these; they exist to
             catch a prompt that got better at the 14 dev cases by
             getting worse at everything else. holdout_cases.py is
             gitignored: it quotes real people from your debates.
    all      both.
    """
    pool = {}
    if which in ("dev", "all"):
        pool.update({n: c for n, c in enumerate(CASES, 1)})
    if which in ("holdout", "all"):
        try:
            import holdout_cases
        except ImportError:
            raise SystemExit("holdout_cases.py not found next to sophia_eval.py")
        pool.update({n: c for n, c in enumerate(holdout_cases.build(globals()), 101)})
    return pool


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


class Tee:
    """Writes to stdout and, unless disabled, to a run file."""

    def __init__(self, path):
        self.f = open(path, "w", encoding="utf-8") if path else None

    def __call__(self, line=""):
        print(line)
        if self.f:
            self.f.write(line + "\n")
            self.f.flush()

    def close(self):
        if self.f:
            self.f.close()


def ask(system_prompt, user_input, think):
    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_input},
        ],
        # qwen3.8:27b takes "low"/"high" strings, not a boolean - see
        # _think_effort() in debate_voice.py. False is a real value here too.
        "think": think,
        "stream": False,
        "options": {"num_ctx": NUM_CTX, "num_predict": NUM_PREDICT, "temperature": TEMPERATURE},
        "keep_alive": -1,
    }
    t0 = time.time()
    resp = requests.post(OLLAMA_URL, json=payload, timeout=180)
    data = resp.json()
    msg = data.get("message", {}) or {}
    text = (msg.get("content") or "").strip()
    # qwen3.8 returns its reasoning block separately from the answer. When
    # `content` is empty but `thinking` is long, the model spent the whole
    # budget reasoning and never reached an answer - that's the empty-reply
    # bug, and this is the evidence for it.
    thinking = (msg.get("thinking") or "")
    diag = {
        "done_reason": data.get("done_reason"),
        "eval_count": data.get("eval_count"),
        "prompt_eval_count": data.get("prompt_eval_count"),
        "thinking_chars": len(thinking),
    }
    ev, ed = data.get("eval_count"), data.get("eval_duration")
    diag["tok_per_s"] = round(ev / (ed / 1e9), 1) if ev and ed else None
    return text, time.time() - t0, diag, thinking


def fmt_diag(d):
    """One compact line. Fields absent on older Ollama versions just read
    as None rather than breaking the run."""
    tps = f"{d['tok_per_s']} tok/s" if d.get("tok_per_s") else "tok/s n/a"
    return (f"done_reason={d.get('done_reason')!r}  "
            f"eval_count={d.get('eval_count')}  "
            f"prompt_eval={d.get('prompt_eval_count')}  "
            f"thinking={d.get('thinking_chars')} chars  {tps}")


def run(args):
    system_prompt = load_system_prompt()
    digest = hashlib.sha256(system_prompt.encode("utf-8")).hexdigest()[:12]

    pool = case_pool(args.set)
    selected = sorted(pool)
    if args.cases:
        selected = [int(c) for c in args.cases.split(",") if c.strip()]
        for c in selected:
            if c not in pool:
                raise SystemExit(f"case {c} is not in --set {args.set} "
                                 f"(available: {min(pool)}-{max(pool)})")

    path = None
    if not args.no_save:
        outdir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "eval_runs")
        os.makedirs(outdir, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        label = f"{args.label}_" if args.label else ""
        # Holdout/all runs quote real opponent turns, so their filenames
        # always carry the set name - .gitignore matches *holdout* / *all-*.
        if args.set != "dev":
            label = f"{args.set}-{label}"
        path = os.path.join(outdir, f"eval_{label}{stamp}.txt")

    out = Tee(path)
    think_desc = args.think if args.think != "false" else "false (no reasoning)"
    out(f"SYSTEM_PROMPT: {len(system_prompt)} chars, sha256:{digest}")
    out(f"model={MODEL}  think={think_desc}  num_ctx={NUM_CTX}  "
        f"num_predict={NUM_PREDICT}  temp={TEMPERATURE}")
    out(f"set={args.set}  cases={list(selected)}  repeat={args.repeat}")
    out(f"run at {datetime.now().isoformat(timespec='seconds')}")
    out()

    think = False if args.think == "false" else args.think

    # results[case_index][check_name] = [bool, ...]
    results = {}
    failures = []
    errors = []
    records = []   # one dict per reply - feeds --judge and the .json file

    for i in selected:
        name, user_input, expectation, checks = pool[i]
        results[i] = {c.__name__: [] for c in checks}
        out("=" * 72)
        out(f"CASE {i}: {name}")
        out(f"  INPUT:    {user_input}")
        out(f"  EXPECTED: {expectation}")
        for rep in range(args.repeat):
            tag = f" [run {rep + 1}/{args.repeat}]" if args.repeat > 1 else ""
            try:
                text, elapsed, diag, thinking = ask(system_prompt, user_input, think)
            except Exception as e:
                out(f"  GOT{tag}:  [request failed: {e}]")
                # A transport failure is not a persona result. Record it as
                # skipped (None) so it can't masquerade as a regression.
                for c in checks:
                    results[i][c.__name__].append(None)
                errors.append((i, name, str(e), rep + 1))
                continue
            out(f"  GOT{tag} ({elapsed:.1f}s): {text}")
            out(f"    DIAG {fmt_diag(diag)}")
            rec = {"case": i, "name": name, "input": user_input,
                   "expected": expectation, "run": rep + 1,
                   "elapsed": round(elapsed, 2), "text": text, "diag": diag,
                   "failed_checks": []}
            records.append(rec)
            words = len(text.split())
            if text:
                out(f"    LEN  {words} words, {len(_sentences(text))} sentences")

            empty = not text.strip()

            # The reasoning block is dumped when asked for, and ALWAYS on an
            # empty reply - that's the turn you need it for, and having to
            # re-run to see it is how a 23-second failure stays undiagnosed
            # across four attempted fixes.
            if thinking and (args.show_thinking or empty):
                why = "empty reply" if empty and not args.show_thinking else "requested"
                out(f"    THINKING ({len(thinking)} chars, shown: {why}):")
                for ln in thinking.splitlines():
                    out(f"      | {ln}")

            for c in checks:
                # When the turn came back empty there is no text to judge.
                # Only non_empty is scored; everything else is skipped, so
                # one silence doesn't show up as six separate regressions.
                if empty and c is not non_empty:
                    results[i][c.__name__].append(None)
                    continue
                problem = c(text)
                results[i][c.__name__].append(problem is None)
                if problem:
                    rec["failed_checks"].append(c.__name__)
                    out(f"    FAIL [{c.__name__}] {problem}")
                    failures.append((i, name, c.__name__, problem, rep + 1))
            if empty:
                out("    (remaining checks skipped - no content to judge)")
        out()

    # ---- summary -------------------------------------------------------
    out("=" * 72)
    out("SUMMARY")
    out("=" * 72)
    clean_cases = 0
    for i in selected:
        name = pool[i][0]
        per_check = results[i]
        # Skipped runs (None) are excluded from both numerator and
        # denominator - "2/2 scored" is honest where "2/3" would not be.
        bad = {k: v.count(False) for k, v in per_check.items() if v.count(False)}
        skipped = sum(1 for v in per_check.values() for x in v if x is None)
        if not bad:
            clean_cases += 1
            out(f"  PASS  case {i:>2}  {name}")
        else:
            detail = ", ".join(
                f"{k} {len([x for x in per_check[k] if x is True])}/"
                f"{len([x for x in per_check[k] if x is not None])} scored"
                for k in bad
            )
            out(f"  FAIL  case {i:>2}  {name}")
            out(f"                    {detail}")
        if skipped:
            out(f"                    ({skipped} check-runs skipped - empty reply or request error)")
    out()
    out(f"{clean_cases}/{len(list(selected))} cases tripped no mechanical check.")
    if errors:
        out()
        out(f"!! {len(errors)} request(s) FAILED and were excluded from scoring:")
        for i, name, msg, rep in errors:
            out(f"   case {i} run {rep}: {msg}")
    if args.repeat > 1:
        out("Fractions above are passes-out-of-runs. Anything that isn't 0/N or")
        out("N/N is temperature noise, not a clean regression - rerun before acting.")
    out()
    out("""A PASS means the response tripped none of the mechanical traps. It does
NOT mean the answer is good. Cases 10 and 11 in particular (spicy call-out
vs. serious technical engagement) are judgment calls no regex decides -
read those responses yourself. On a prompt rewrite, read all of them and
diff this run file against the baseline.""")

    # ---- judge (optional) ----------------------------------------------
    # Runs only after EVERY reply has been generated and timed. Interleaving
    # judge calls with timed replies would evict Sophia's prompt from the
    # KV cache and change what the latency numbers mean - see
    # sophia_judge.py's docstring.
    judge_summary = None
    if args.judge:
        import sophia_judge
        out()
        out("=" * 72)
        out("JUDGE - local model grades each reply against its EXPECTED text")
        out("=" * 72)
        sophia_judge.judge_records(records, out)
        judge_summary = sophia_judge.summarize(records, out)
        if judge_summary["pass_rate"] is not None and judge_summary["pass_rate"] < 1:
            failures.append(("judge", "", "judge", "one or more replies scored under 4", 0))

    if records:
        ts = sorted(r["elapsed"] for r in records)
        out()
        out(f"reply time: median {ts[len(ts) // 2]:.1f}s  "
            f"p90 {ts[min(len(ts) - 1, int(0.9 * len(ts)))]:.1f}s  max {ts[-1]:.1f}s")

    if path:
        import json
        json_path = os.path.splitext(path)[0] + ".json"
        with open(json_path, "w", encoding="utf-8") as jf:
            json.dump({"prompt_sha": digest, "prompt_chars": len(system_prompt),
                       "model": MODEL, "think": args.think, "repeat": args.repeat,
                       "set": args.set,
                       "cases": list(selected), "clean_cases": clean_cases,
                       "judge": judge_summary, "records": records},
                      jf, indent=2, ensure_ascii=False)
    if path:
        out()
        out(f"saved: {path}")
    out.close()

    return 0 if not failures else 1


def main():
    p = argparse.ArgumentParser(description="Sophia persona regression check")
    p.add_argument("--repeat", type=int, default=1,
                   help="run every case N times (use 3 when comparing before/after)")
    p.add_argument("--cases", default="",
                   help="comma-separated case numbers, e.g. 1,4,9 (default all)")
    p.add_argument("--label", default="",
                   help="tag for the saved run file, e.g. baseline")
    p.add_argument("--think", default="low", choices=["low", "high", "false"],
                   help="reasoning effort to send (default low = normal turn)")
    p.add_argument("--show-thinking", action="store_true",
                   help="dump the full reasoning block for every turn "
                        "(always dumped on an empty reply regardless)")
    p.add_argument("--no-save", action="store_true", help="don't write a run file")
    p.add_argument("--set", default="dev", choices=["dev", "holdout", "all"],
                   help="which cases: dev (1-14, default), holdout (101+, from "
                        "holdout_cases.py), or all")
    p.add_argument("--judge", action="store_true",
                   help="after generating, have the local model grade every reply "
                        "against its EXPECTED text (see sophia_judge.py)")
    args = p.parse_args()
    if args.repeat < 1:
        raise SystemExit("--repeat must be at least 1")
    sys.exit(run(args))


if __name__ == "__main__":
    main()
