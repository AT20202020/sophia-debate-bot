"""
sophia_sim.py - simulated historicity debates, reviewed against the argument cards.

WHAT IT DOES
------------
1. OPPONENT - the local model argues FOR a historical Jesus, in one of three
   styles (scholar / street apologist / atheist historian), starting from one of
   ~24 opening arguments. It is told to argue to win, not to lose gracefully.
2. SOPHIA - the LIVE debate_voice.py, loaded text-only through the same
   BotHarness sophia_scorecard.py uses. Every turn goes through her real
   get_response_streaming(): system prompt, guards, and historicity card
   injection (knowledge/historicity/). Nothing is spoken, nothing is logged.
3. REVIEWER - the same model reads each finished debate with the card list and
   the full text of every card that loaded, and returns JSON: arguments raised
   (covered by which card, or none), how well Sophia handled each, anything she
   said that contradicts a card, specific claims that need checking, and who
   argued better.
4. REPORT - report.md ranks uncovered arguments (card gaps) by how often they
   came up, then weak handling, contradictions, claims to verify, and the
   debates she lost.

EVERYTHING THE REVIEWER FLAGS IS UNVERIFIED. It is qwen reading qwen. It will
name scholars and sources that don't exist. Nothing here becomes a card until a
human (or Claude, with sources) checks it.

USAGE
-----
  Run Simulator.bat                       (20 debates, 6 exchanges each)
  Run Simulator.bat --debates 300         (overnight)
  python sophia_sim.py --report-only sim_runs\\20261015-190000
  python sophia_sim.py --no-review        (debates only, review later)
  python sophia_sim.py --resume sim_runs\\20261015-190000

Output: sim_runs/<timestamp>/debates.jsonl (one line per debate, written as it
finishes, so a crash or Ctrl+C keeps everything done so far), transcripts.md,
report.md.

SPEED NOTE: Sophia's ~24k-char system prompt and the opponent's short one take
turns on the same model, so Ollama re-reads Sophia's prompt (~6-7s) on most of
her turns. That is the main per-debate cost; expect ~1.5-2.5 min per debate.
Close Sophia before running - two clients on Ollama skews everything.
"""

import argparse
import copy
import difflib
import json
import os
import random
import re
import sys
import time
from collections import Counter, defaultdict
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

SIM_VERSION = "2.0"

# ---------------------------------------------------------------------------
# OPPONENT
# ---------------------------------------------------------------------------

STYLES = {
    "scholar": (
        "You argue like a careful academic historian of early Christianity. You "
        "cite primary sources precisely (book, chapter, verse, ancient author) and "
        "name scholars only when you are sure of them and of what they argued. You "
        "concede small points when they are fair, then press the larger case."
    ),
    "apologist": (
        "You argue like a confident Christian apologist debating online. You are "
        "punchy and persuasive, use popular arguments that land with an audience, "
        "and push hard on any weakness. You believe Jesus existed and is far more "
        "than a man, but in this debate you only need to prove he existed."
    ),
    "atheist_historian": (
        "You argue like an atheist historian who thinks mythicism is bad history. "
        "You have no religious stake: you think Jesus was an ordinary Jewish "
        "preacher, and that denying he existed is as weak as any apologetics. You "
        "are blunt about poor method, cherry-picking and special pleading."
    ),
}

# Opening arguments. Several deliberately have NO card yet, so the report
# should surface them as gaps - that is the point of the run.
OPENERS = [
    "Josephus mentions Jesus twice, in Antiquities 18 and 20.",
    "Tacitus, a hostile Roman historian, confirms Jesus was executed under Pilate.",
    "Paul personally met James, the brother of the Lord (Galatians 1:19).",
    "The creed in 1 Corinthians 15 dates to within a few years of the crucifixion.",
    "Nobody would invent a crucified messiah - the criterion of embarrassment.",
    "Jesus being baptized by John embarrassed the early church, so it happened.",
    "Virtually every qualified historian, religious or not, accepts Jesus existed.",
    "Multiple independent sources attest to Jesus: Mark, Q, M, L, John and Paul.",
    "Jesus' sayings carry Aramaic wordplay that only makes sense in his own language.",
    "Why would anyone invent a messiah from an obscure village like Nazareth?",
    "Pilate, Caiaphas and Herod Antipas are confirmed by archaeology, so the setting is real.",
    "A movement this fast-growing, this early, needs a real founder.",
    "The apostles died for their claims; people don't die for something they know is false.",
    "Mara bar Serapion's letter refers to the Jews executing their 'wise king'.",
    "Pliny the Younger's letter to Trajan around 112 describes Christians worshipping Christ.",
    "The Babylonian Talmud mentions Yeshu being executed on the eve of Passover.",
    "Suetonius says Claudius expelled Jews from Rome over disturbances caused by 'Chrestus'.",
    "We have better evidence for Jesus than for many ancient figures we never doubt.",
    "Mark 6:3 names Jesus' brothers James, Joses, Judas and Simon - a real family.",
    "The Gospels are Greco-Roman biographies, a genre about real people.",
    "No ancient opponent of Christianity, Jewish or pagan, ever claimed Jesus didn't exist.",
    "Thallus and Phlegon wrote about the darkness at the crucifixion.",
    "The Gospel of John's geography, like the Pool of Bethesda, has been confirmed by digs.",
    "Mythicism is the creationism of the atheist world - rejected by the experts for good reason.",
]

# v2.0: second topic. Styles are topic-specific (the historicity ones mention
# proving existence).
MORALITY_STYLES = {
    "philosopher": (
        "You argue like a careful Christian philosopher of religion. You state premises "
        "precisely, distinguish moral ontology (what grounds morality) from moral "
        "epistemology (how we know it), and answer objections such as Euthyphro with the "
        "standard replies (God's nature as the standard of goodness)."
    ),
    "apologist": (
        "You argue like a confident popular Christian apologist debating online. You are "
        "punchy, use vivid examples (the Holocaust, torturing babies), and press hard on "
        "'where do you get your morals?' and 'so nothing is really wrong?'"
    ),
    "everyday_believer": (
        "You argue like a sincere everyday churchgoer, not an academic. You speak from "
        "conviction and experience, ask direct personal questions, and lean on the Bible "
        "and on what you see as atheism's moral emptiness."
    ),
}

MORALITY_OPENERS = [
    "If God does not exist, objective moral values and duties do not exist; they do exist, so God exists.",
    "Without God, everything is permitted - there is no real right and wrong.",
    "Where do you get your morals from if there is no God?",
    "The Holocaust was objectively evil, and only God can make that true.",
    "A moral law requires a moral lawgiver.",
    "Evolution can explain why we feel morality, but not why anything is truly wrong.",
    "You can't get an ought from an is, so atheism has no basis for morality.",
    "Stalin, Mao and Pol Pot show where atheism leads.",
    "Christianity gave us human rights and the abolition of slavery.",
    "Euthyphro fails: goodness is grounded in God's unchanging nature, not his commands.",
    "Our conscience is God's moral law written on our hearts.",
    "If there's no God, torturing babies for fun isn't really wrong, is it?",
    "Moral progress only makes sense if there is a fixed standard to progress toward.",
    "Kant himself said morality requires us to postulate God.",
    "Sam Harris's well-being morality just assumes what it needs to prove.",
    "Atheists borrow Christian morality while denying its foundation.",
]

TOPICS = {
    "historicity": {
        "styles": STYLES, "openers": OPENERS,
        "module": "historicity_reference", "log_key": "historicity reference injected",
        "position": ("a historical Jesus existed - a Jewish preacher crucified under Pontius "
                     "Pilate, whose followers started Christianity"),
        "review_intro": (
            "You review a debate about whether Jesus existed. SPEAKER A argues he existed. "
            "SPEAKER B is assigned the skeptic side (doubt or agnosticism about existence) for "
            "the whole debate; B conceding a specific FACT is honest, but B switching to argue "
            "that Jesus existed is a failure."),
    },
    "morality": {
        "styles": MORALITY_STYLES, "openers": MORALITY_OPENERS,
        "module": "morality_reference", "log_key": "morality reference injected",
        "position": ("God exists and is the necessary foundation of objective morality; without "
                     "God there is no real right and wrong"),
        "review_intro": (
            "You review a debate about morality and God. SPEAKER A argues that objective "
            "morality requires God. SPEAKER B is assigned to defend NO moral theory of her own: "
            "she tests A's premises and keeps the burden of proof on A. B saying plainly that "
            "something (e.g. the Holocaust) was wrong is fine and expected. B stating her own "
            "metaethical theory ('objective morality exists', 'morality is subjective') or "
            "saying nothing is really wrong is a failure - list it under errors."),
    },
}

OPP_SYSTEM = """You are debating Sophia, an AI skeptic, in a spoken debate. Your position:
{position}. Argue to WIN. Use your strongest material, answer
her objections directly, and don't fold because she sounds confident. You may
concede a point that is genuinely fair, then move to your next argument.

STYLE: {style}

YOUR OPENING ARGUMENT: {opener}
Open with that, then develop it and bring in other arguments as the debate goes.

RULES:
- This is spoken aloud: 1 to 4 sentences per turn, no lists, no markdown, no
  stage directions, no "Opponent:" labels.
- Only cite sources you are confident are real. If unsure of a name or date,
  argue from the evidence itself instead of inventing a citation.
- Don't repeat an argument she has already answered unless you have a new reply to
  her answer.
"""


def _chat(model, num_ctx, messages, temperature, num_predict, seed=None, fmt=None, timeout=240):
    # num_ctx MUST match Sophia's or Ollama restarts the runner (~13s) - v2.13.
    opts = {"num_ctx": num_ctx, "num_predict": num_predict, "temperature": temperature}
    if seed is not None:
        opts["seed"] = seed
    payload = {"model": model, "stream": False, "think": False, "keep_alive": -1,
               "options": opts, "messages": messages}
    if fmt:
        payload["format"] = fmt
    r = requests.post(OLLAMA_CHAT, json=payload, timeout=timeout)
    r.raise_for_status()
    return (r.json().get("message", {}) or {}).get("content", "") or ""


def _clean_spoken(text):
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.S)
    text = re.sub(r"^\s*(\*\*)?\s*(opponent|me|you|historian|apologist)\s*:\s*(\*\*)?", "", text, flags=re.I)
    text = text.replace("**", "").replace("*", "").strip().strip('"').strip()
    return re.sub(r"\s+", " ", text)


def _sim(a, b):
    return difflib.SequenceMatcher(None, (a or "").lower(), (b or "").lower()).ratio()


def opponent_turn(bot, style, opener, transcript, seed, topic="historicity"):
    """transcript: list of (speaker, text). Opponent sees itself as assistant."""
    # Always open with a user turn: some chat templates reject assistant-first.
    msgs = [{"role": "system", "content": OPP_SYSTEM.format(style=TOPICS[topic]["styles"][style], opener=opener,
                                                       position=TOPICS[topic]["position"])},
            {"role": "user", "content": "(The debate is starting. Make your opening argument.)"}]
    for who, text in transcript:
        msgs.append({"role": "assistant" if who == "opponent" else "user", "content": text})
    # v1.1: the first run had the opponent re-running one point for 5 turns and
    # echoing Sophia's sentence back. If a draft is near-identical to its own
    # earlier turns or to her last line, retry with an instruction to move on.
    mine = [t for w, t in transcript if w == "opponent"]
    hers = [t for w, t in transcript if w == "sophia"][-1:]
    out = ""
    for attempt in range(3):
        out = _clean_spoken(_chat(bot.model, bot.num_ctx, msgs, 0.8, 300, seed=seed + attempt))
        if out and not (any(_sim(out, m) >= 0.6 for m in mine) or any(_sim(out, h) >= 0.6 for h in hers)):
            return out
        if attempt == 0:
            msgs = msgs + [{"role": "user", "content":
                            "(Moderator note to you only: you are repeating yourself. Make a NEW "
                            "argument now - a different source or line of evidence - in your own words.)"}]
    if out:
        return out
    return "Let me put it simply: the best explanation of our earliest sources is that Jesus was a real person."


# ---------------------------------------------------------------------------
# REVIEWER
# ---------------------------------------------------------------------------

REVIEW_SYSTEM = """<<INTRO>> You are checking a reference library of "argument
cards" for gaps, and checking both speakers' accuracy. Be neutral: neither side is
presumed right, and sounding confident earns nothing.

Return ONLY a JSON object with exactly these keys:
{
 "arguments": [ {"argument": "short name, 3-8 words",
                 "raised_by": "A" | "B",
                 "covered_by_card": "card filename from the list, or null",
                 "b_handling": "strong" | "adequate" | "weak" | "missed" | "n/a",
                 "note": "one sentence: what was good or missing"} ],
 "errors": [ {"speaker": "A" | "B", "said": "short quote",
              "why": "why it is false, invented, or overstated"} ],
 "contradictions": [ {"b_said": "short quote", "card": "filename",
                      "card_says": "short paraphrase"} ],
 "claims_to_check": [ {"speaker": "A" | "B",
                       "claim": "a specific name, date, quote or source claim"} ],
 "winner": "A" | "B" | "even",
 "winner_reason": "one sentence"
}

RULES:
- arguments: ONLY arguments a speaker actually made in THIS debate, by either
  side. Never list a card's topic because it exists or "could have" come up.
- covered_by_card: a filename ONLY if that card's topic really covers the
  argument. If no card fits, use null - that is a gap, and gaps are what we want.
- b_handling, for arguments A raised: "missed" = B never answered it; "weak" = B
  answered with an error, a dodge, a repeat of an earlier reply, or without the
  strongest reply. Use "n/a" for arguments B raised.
- errors: statements you are confident are factually wrong, invented, or stated
  far more strongly than the evidence allows - by either speaker. Repeating the
  same paragraph is not an error; skip it here.
- contradictions: only where B states as FACT something a LOADED card reports
  differently: a wrong date, name, source, or who-argued-what, or calling a
  disputed point settled. Every card gives both sides, so B taking one side of
  a card is NOT a contradiction, and neither is B agreeing with a card. Empty
  list if none.
- claims_to_check: specific factual claims a human should verify (a scholar's
  name and view, a date, a citation, a quote). Skip general reasoning.
- winner: who argued better on evidence and reasoning. Count factual errors and
  repeated, non-responsive answers against a speaker.
"""


def card_index(cards):
    lines = []
    for c in cards:
        claim = ""
        m = re.search(r"CLAIM:\s*(.+)", c["body"])
        if m:
            claim = m.group(1).strip()[:160]
        lines.append(f"- {c['file']}: {c['title']}. {claim}")
    return "\n".join(lines)


_WHO = {"A": "opponent", "B": "sophia"}


def _deanonymize(r):
    """Map the reviewer's A/B back to opponent/sophia so the report reads plainly."""
    for a in r.get("arguments") or []:
        a["raised_by"] = _WHO.get(str(a.get("raised_by", "")).upper(), a.get("raised_by"))
        a["sophia_handling"] = a.pop("b_handling", a.get("sophia_handling", "?"))
    for k in ("errors", "claims_to_check"):
        for e in r.get(k) or []:
            e["speaker"] = _WHO.get(str(e.get("speaker", "")).upper(), e.get("speaker"))
    for c in r.get("contradictions") or []:
        c["sophia_said"] = c.pop("b_said", c.get("sophia_said", ""))
    r["winner"] = _WHO.get(str(r.get("winner", "")).upper(), r.get("winner", "even"))
    return r


def review_debate(bot, cards, debate, topic="historicity"):
    by_title = {c["title"]: c for c in cards}
    loaded = [by_title[t] for t in debate["cards_loaded"] if t in by_title]
    loaded_text = "\n\n".join(f"[{c['file']}]\n{c['body']}" for c in loaded) or "(none loaded)"
    convo = "\n".join(f"{'A' if w == 'opponent' else 'B'}: {t}" for w, t in debate["transcript"])
    user = (f"ALL CARDS IN THE LIBRARY:\n{card_index(cards)}\n\n"
            f"CARDS LOADED INTO SPEAKER B DURING THIS DEBATE (full text):\n{loaded_text}\n\n"
            f"THE DEBATE:\n{convo}\n\nReturn the JSON now.")
    system = REVIEW_SYSTEM.replace("<<INTRO>>", TOPICS[topic]["review_intro"])
    msgs = [{"role": "system", "content": system}, {"role": "user", "content": user}]
    for attempt in range(2):
        try:
            out = _parse_json(_chat(bot.model, bot.num_ctx, msgs, 0.0, 1500, seed=7 + attempt, fmt="json"))
            if isinstance(out, dict) and "arguments" in out:
                return _deanonymize(out)
        except Exception:
            pass
    return {"error": "reviewer returned no usable JSON"}


# ---------------------------------------------------------------------------
# ONE DEBATE
# ---------------------------------------------------------------------------

_ROLE_SLIP = [re.compile(p, re.I) for p in (
    r"\bI (?:believe|think|hold|maintain|argue|would argue) (?:that )?objective (?:moral(?:ity| values| facts| truths)?)\b[^.]{0,30}\bexists?\b",
    r"\b(?:I believe|I think|in my view,?) morality is (?:purely |merely |just |entirely )?(?:subjective|relative)\b",
    r"\bnothing is (?:really |actually |objectively |truly )?(?:right or )?wrong\b",
)]


def mechanical_checks(bot, transcript):
    """Code-checked problems - reliable, unlike the reviewer."""
    sim = (bot.fn("_similar") if bot else None) or _sim
    thresh = bot.ns.get("REPEAT_SIMILARITY", 0.85) if bot else 0.85
    hers = [(i, t) for i, (w, t) in enumerate(transcript) if w == "sophia"]
    repeats, echoes, fallbacks = [], [], []
    for k, (i, t) in enumerate(hers):
        if any(sim(t, p) >= thresh for _, p in hers[:k]):
            repeats.append(k + 1)
        prev = transcript[i - 1][1] if i else ""
        first = re.split(r"(?<=[.!?])\s+", prev.strip())[0] if prev else ""
        if prev and (_sim(t, prev) >= 0.8 or (first and len(first) > 20 and t.strip().startswith(first))):
            echoes.append(k + 1)
        if "lost my train of thought" in t:
            fallbacks.append(k + 1)
    # v2.0: morality role - she defends no moral theory of her own.
    slips = [k + 1 for k, (_, t) in enumerate(hers) if any(rx.search(t) for rx in _ROLE_SLIP)]
    return {"repeat_turns": repeats, "echo_turns": echoes, "fallback_turns": fallbacks,
            "role_slip_turns": slips}


def run_debate(bot, idx, style, opener, turns, seed, topic="historicity"):
    history = [{"role": "system", "content": bot.system_prompt}]
    transcript, cards_loaded, timings = [], [], []
    t0 = time.time()
    for turn in range(turns):
        opp = opponent_turn(bot, style, opener, transcript, seed + turn * 10, topic)
        transcript.append(("opponent", opp))
        # v1.1: BotHarness.ask() resets the repeat/persona flags it is given.
        # Pass through what the bot itself set last turn, or the v2.63 repeat
        # guard and the v2.54 persona correction never fire in a simulation.
        pr = bot.ns.get("_repeat_reply_pending", {}).get("on", False)
        pp = bot.ns.get("_persona_slip_pending", {}).get("on", False)
        reply, meta, wall = bot.ask(history, opp, pending_persona=pp, pending_repeat=pr)
        timings.append(round(wall, 1))
        for c in bot.captured:
            if c["role"] == "session" and TOPICS[topic]["log_key"] in c["text"]:
                tail = c["text"].split(":", 1)[1] if ":" in c["text"] else ""
                for label in (x.strip() for x in tail.split(";")):
                    if label and label != "core" and label not in cards_loaded:
                        cards_loaded.append(label)
        # Continue from what the bot actually holds (cards + reply appended).
        history = copy.deepcopy(bot.ns["conversation"])
        transcript.append(("sophia", (reply or "").strip() or "(no reply)"))
    return {"id": idx, "topic": topic, "style": style, "opener": opener, "seed": seed,
            "mech": mechanical_checks(bot, transcript),
            "transcript": transcript, "cards_loaded": cards_loaded,
            "sophia_turn_seconds": timings, "debate_seconds": round(time.time() - t0, 1),
            "sophia_version": bot.version, "prompt_sha": bot.prompt_sha}


# ---------------------------------------------------------------------------
# REPORT
# ---------------------------------------------------------------------------

def _norm(name):
    return re.sub(r"[^a-z0-9 ]+", "", (name or "").lower()).strip()


def _group(names, cutoff=0.72):
    """Fuzzy-merge argument names the reviewer phrased differently."""
    groups = []   # [canonical, Counter of variants]
    for n in names:
        key = _norm(n)
        if not key:
            continue
        for g in groups:
            if difflib.SequenceMatcher(None, key, _norm(g[0])).ratio() >= cutoff:
                g[1][n] += 1
                break
        else:
            groups.append([n, Counter({n: 1})])
    return sorted(((g[1].most_common(1)[0][0], sum(g[1].values()), list(g[1])) for g in groups),
                  key=lambda x: -x[1])


def write_report(run_dir, debates, cards):
    files = {c["file"] for c in cards}
    reviewed = [d for d in debates if isinstance(d.get("review"), dict) and "arguments" in d["review"]]
    out = []
    w = out.append
    topic = (debates[0].get("topic") if debates else None) or "historicity"
    w(f"# Simulation report ({topic}) - {os.path.basename(run_dir)}\n")
    w("**Everything below comes from the local model reviewing itself. Treat every item as "
      "UNVERIFIED until checked against a real source.**\n")

    n = len(debates)
    secs = [d["debate_seconds"] for d in debates]
    w("## Summary\n")
    if debates:
        w(f"- Debates: {n} ({len(reviewed)} reviewed), Sophia v{debates[-1]['sophia_version']}, "
          f"prompt sha {debates[-1]['prompt_sha']}")
        w(f"- Average debate: {sum(secs)/n/60:.1f} min (Sophia's turns avg "
          f"{sum(sum(d['sophia_turn_seconds']) for d in debates)/max(1,sum(len(d['sophia_turn_seconds']) for d in debates)):.1f}s)")
    w("- Who won (reviewer's call - LOW reliability, the first run gave Sophia 9 of 10 "
      "including a debate she lost on the facts):")
    wins = defaultdict(Counter)
    for d in reviewed:
        wins[d["style"]][d["review"].get("winner", "?")] += 1
    for style, c in sorted(wins.items()):
        w(f"  - vs {style}: Sophia {c['sophia']}, opponent {c['opponent']}, even {c['even']}")
    loads = Counter(t for d in debates for t in d["cards_loaded"])
    w(f"- Cards loaded (debates): " + (", ".join(f"{t} ({k})" for t, k in loads.most_common()) or "none"))
    never = sorted(c["title"] for c in cards if c["title"] not in loads)
    if never:
        w(f"- Cards that never loaded: {', '.join(never)}")
    w("")

    # 0. mechanical
    w("## 0. Code-checked problems (reliable)\n")
    for d in debates:   # runs from v1.0 have no mech block - compute it now
        if not d.get("mech"):
            d["mech"] = mechanical_checks(None, d["transcript"])
    mech = debates
    tot = sum(len([1 for x in d["transcript"] if x[0] == "sophia"]) for d in mech) or 1
    for key, label in (("repeat_turns", "Sophia repeated an earlier reply of hers"),
                       ("echo_turns", "Sophia echoed the opponent's own words back"),
                       ("fallback_turns", "Fallback 'lost my train of thought' line"),
                       ("role_slip_turns", "Sophia stated a moral theory as her own, or 'nothing is wrong'")):
        if key == "role_slip_turns" and topic != "morality":
            continue
        hits = [(d["id"], d["mech"][key]) for d in mech if d["mech"].get(key)]
        n_turns = sum(len(t) for _, t in hits)
        w(f"- {label}: {n_turns} of {tot} replies" +
          (" - debates " + ", ".join(f"{i} (turn {', '.join(map(str, t))})" for i, t in hits[:12]) if hits else ""))
    w("")

    # 1. gaps
    gap_names, gap_examples = [], defaultdict(list)
    for d in reviewed:
        for a in d["review"].get("arguments", []) or []:
            card = a.get("covered_by_card")
            if not card or card not in files:
                gap_names.append(a.get("argument", ""))
                gap_examples[_norm(a.get("argument", ""))].append(
                    (d["id"], a.get("sophia_handling", "?"), a.get("note", "")))
    w("## 1. Arguments with no card (gaps), most frequent first\n")
    groups = _group(gap_names)
    if not groups:
        w("None.\n")
    for name, count, members in groups[:40]:
        ex = [e for m in dict.fromkeys(_norm(x) for x in members) for e in gap_examples.get(m, [])]
        hand = Counter(e[1] for e in ex)
        w(f"- **{name}** - {count}x  (Sophia: " + ", ".join(f"{k} {v}" for k, v in hand.most_common()) + ")")
        if ex:
            w(f"  - e.g. debate {ex[0][0]}: {ex[0][2]}")
    w("")

    # 2. weak handling of covered arguments
    weak = defaultdict(list)
    for d in reviewed:
        for a in d["review"].get("arguments", []) or []:
            if a.get("covered_by_card") in files and a.get("sophia_handling") in ("weak", "missed"):
                weak[a["covered_by_card"]].append((d["id"], a.get("sophia_handling"), a.get("note", "")))
    w("## 2. Covered arguments Sophia handled weakly or missed\n")
    if not weak:
        w("None.\n")
    for card, items in sorted(weak.items(), key=lambda kv: -len(kv[1])):
        w(f"- **{card}** - {len(items)}x")
        for did, h, note in items[:3]:
            w(f"  - debate {did} ({h}): {note}")
    w("")

    # 3. contradictions
    w("## 3. Sophia contradicted a loaded card\n")
    rows = [(d["id"], c) for d in reviewed for c in (d["review"].get("contradictions") or [])
            if c.get("card") in files]
    if not rows:
        w("None.\n")
    for did, c in rows[:40]:
        w(f"- debate {did}, {c.get('card')}: she said \"{c.get('sophia_said')}\" - card: {c.get('card_says')}")
    w("")

    # 3b. errors
    w("## 3b. Statements the reviewer thinks are wrong or overstated\n")
    errs_ = [(d["id"], e) for d in reviewed for e in (d["review"].get("errors") or [])]
    if not errs_:
        w("None.\n")
    for who in ("sophia", "opponent"):
        mine = [(i, e) for i, e in errs_ if e.get("speaker") == who]
        if mine:
            w(f"**{who.capitalize()}** ({len(mine)}):")
            for i, e in mine[:25]:
                w(f"- debate {i}: \"{e.get('said', '')}\" - {e.get('why', '')}")
            w("")

    # 4. claims to check
    w("## 4. Specific claims to verify\n")
    claims = Counter()
    for d in reviewed:
        for c in d["review"].get("claims_to_check") or []:
            claims[(c.get("speaker", "?"), (c.get("claim") or "").strip())] += 1
    if not claims:
        w("None.\n")
    for (who, claim), k in claims.most_common(40):
        w(f"- [{who}] {claim}" + (f"  ({k}x)" if k > 1 else ""))
    w("")

    # 5. losses
    w("## 5. Debates the reviewer gave to the opponent\n")
    lost = [d for d in reviewed if d["review"].get("winner") == "opponent"]
    if not lost:
        w("None.\n")
    for d in lost[:30]:
        w(f"- debate {d['id']} ({d['style']}, \"{d['opener'][:60]}\"): {d['review'].get('winner_reason', '')}")
    w("")
    errs = [d["id"] for d in debates if isinstance(d.get("review"), dict) and "error" in d["review"]]
    if errs:
        w(f"_Reviewer failed on debates: {', '.join(map(str, errs))}_\n")

    with open(os.path.join(run_dir, "report.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(out))

    with open(os.path.join(run_dir, "transcripts.md"), "w", encoding="utf-8") as f:
        for d in debates:
            f.write(f"## Debate {d['id']} - {d['style']} - {d['opener']}\n\n")
            f.write(f"_Cards loaded: {', '.join(d['cards_loaded']) or 'none'}_\n\n")
            for who, text in d["transcript"]:
                f.write(f"**{'OPPONENT' if who == 'opponent' else 'SOPHIA'}:** {text}\n\n")
            r = d.get("review") or {}
            if "winner" in r:
                f.write(f"_Reviewer: {r['winner']} - {r.get('winner_reason', '')}_\n\n")
            f.write("---\n\n")


def load_debates(run_dir):
    path = os.path.join(run_dir, "debates.jsonl")
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def save_debates(run_dir, debates):
    tmp = os.path.join(run_dir, "debates.jsonl.tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        for d in debates:
            f.write(json.dumps(d, ensure_ascii=False) + "\n")
    os.replace(tmp, os.path.join(run_dir, "debates.jsonl"))


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(description="Sophia debate simulator")
    ap.add_argument("--topic", default="historicity", choices=sorted(TOPICS))
    ap.add_argument("--debates", type=int, default=20)
    ap.add_argument("--turns", type=int, default=6, help="opponent turns per debate (each gets a Sophia reply)")
    ap.add_argument("--styles", default="", help="comma list (default: all styles for the topic)")
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--no-review", action="store_true")
    ap.add_argument("--resume", default="", help="continue a run folder (adds debates, reviews unreviewed ones)")
    ap.add_argument("--report-only", default="", help="rebuild report.md for a run folder, no Ollama")
    ap.add_argument("--target", default=HERE)
    args = ap.parse_args()

    print("Loading debate_voice.py (text only - no audio)...")
    bot = BotHarness(os.path.abspath(args.target))
    if args.report_only or args.resume:   # a run folder knows its own topic
        prev = load_debates(os.path.abspath(args.report_only or args.resume))
        if prev and prev[0].get("topic"):
            args.topic = prev[0]["topic"]
    T = TOPICS[args.topic]
    import importlib
    cards = importlib.import_module(T["module"]).load_cards()
    print(f"  topic {args.topic}: Sophia v{bot.version}, model {bot.model}, num_ctx {bot.num_ctx}, {len(cards)} cards")

    if args.report_only:
        run_dir = os.path.abspath(args.report_only)
        debates = load_debates(run_dir)
        write_report(run_dir, debates, cards)
        print(f"Report rebuilt: {os.path.join(run_dir, 'report.md')}")
        return 0

    if not ollama_up():
        print("\nOllama is not answering on 127.0.0.1:11434. Start it (or use Run Simulator.bat).")
        return 2

    if args.resume:
        run_dir = os.path.abspath(args.resume)
        debates = load_debates(run_dir)
    else:
        run_dir = os.path.join(bot.folder, "sim_runs", datetime.now().strftime("%Y%m%d-%H%M%S") + "-" + args.topic)
        os.makedirs(run_dir, exist_ok=True)
        debates = []
    seed = args.seed if args.seed is not None else int(time.time()) % 100000
    styles = [s.strip() for s in args.styles.split(",") if s.strip() in T["styles"]] or list(T["styles"])

    # Even coverage: every opener x style pair before any repeats, shuffled.
    rng = random.Random(seed)
    plan = [(o, s) for o in T["openers"] for s in styles]
    rng.shuffle(plan)
    start = len(debates)

    print("Warming the model...")
    try:
        bot.ask([{"role": "system", "content": bot.system_prompt}], "Hello.")
    except Exception as e:
        print(f"  warm-up failed: {e}")

    print(f"Running {args.debates} debates x {args.turns} exchanges -> {run_dir}")
    print("Ctrl+C stops after saving what's done; --resume continues it.\n")
    t_run = time.time()
    try:
        for i in range(args.debates):
            idx = start + i + 1
            opener, style = plan[(start + i) % len(plan)]
            d = run_debate(bot, idx, style, opener, args.turns, seed + idx * 1000, args.topic)
            if not args.no_review:
                d["review"] = review_debate(bot, cards, d, args.topic)
            debates.append(d)
            save_debates(run_dir, debates)
            r = d.get("review") or {}
            done = i + 1
            eta = (time.time() - t_run) / done * (args.debates - done) / 60
            print(f"[{done}/{args.debates}] #{idx} {style:<17} {d['debate_seconds']/60:4.1f} min  "
                  f"cards={len(d['cards_loaded'])}  winner={r.get('winner', '-'):<8}  "
                  f"ETA {eta:.0f} min  | {opener[:50]}", flush=True)
        # review any left unreviewed (from --no-review or an earlier crash)
        if not args.no_review:
            for d in debates:
                if not (isinstance(d.get("review"), dict) and "arguments" in d["review"]):
                    print(f"Reviewing debate {d['id']}...", flush=True)
                    d["review"] = review_debate(bot, cards, d, args.topic)
                    save_debates(run_dir, debates)
    except KeyboardInterrupt:
        print("\nStopped. Saving report for the debates finished so far.")

    write_report(run_dir, debates, cards)
    print(f"\nDone in {(time.time()-t_run)/60:.1f} min.")
    print(f"Report:      {os.path.join(run_dir, 'report.md')}")
    print(f"Transcripts: {os.path.join(run_dir, 'transcripts.md')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
