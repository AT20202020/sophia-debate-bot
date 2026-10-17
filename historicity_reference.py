"""
historicity_reference.py - topical reference for Sophia on the historicity of Jesus.

v2.68: ASSIGNED SKEPTIC ROLE (Jeff's call, 2026-10-15). With no side assigned,
  simulator run sim_runs/20261015-193414 had her concede existence in her FIRST
  reply and then spend five turns saying "that doesn't prove divinity", which no
  one had argued. She now argues the skeptic/agnostic side for the whole debate,
  honestly: credits strong points, concedes specific facts, never overstates.

v2.67: CORE adds the rule that a card's two cases are positions to attribute,
  not facts - two simulator runs had her state "Tacitus and Josephus are not
  independent" as settled.

v2.66: ARGUMENT CARDS. The single ~4,650-char block became two parts:
  1. CORE - a short definition + how-to-handle block (MARKER below). Injected
     ONCE, the first time the topic comes up, exactly as in v2.57.
  2. CARDS - one .md file per argument in knowledge/historicity/ beside this
     file. Each card gives the case for AND against; none tells Sophia which
     side is right. Only cards whose `triggers:` match what the opponent just
     said are injected, at most MAX_NEW_CARDS_PER_TURN per turn and
     MAX_CARDS_PER_DEBATE per debate, each card once.
  Cards only load while the topic is live (CORE present or firing this turn),
  so a card trigger like "consensus" can't drag Jesus scholarship into a
  debate about something else.
  The v2.57 "HOW TO ARGUE IT" block told her to treat historicity as an open
  question and never call mythicism fringe - a thumb on the scale. CORE now
  assigns no side.

WHY THIS IS A SEPARATE FILE, NOT PART OF SYSTEM_PROMPT
  SYSTEM_PROMPT is ~18.5k chars. Appending this to it would (a) raise collision
  risk and (b) change the prompt prefix, forcing a full re-eval every session.
  Instead these blocks are injected into the conversation history, just before
  the current user turn. After that turn they are part of the cached context,
  so later turns pay nothing extra. 'new' clears them with everything else.

ADDING A CARD: copy knowledge/historicity/_TEMPLATE.md, fill it in, then run
  python historicity_reference.py   (self-test: parses every card, checks size)
  Files starting with "_" and README.md are ignored. Cards are re-read when a
  file changes, so an edit takes effect at the next topic hit, no restart.

USAGE in debate_voice.py (turn loop, after the user turn is appended):
    from historicity_reference import inject_if_relevant
    loaded = inject_if_relevant(history, user_text)   # list of labels, [] if none
"""

import os
import re

# Matches the topic, including known Whisper mishearings ("Sofia" is harmless;
# "Syntacitists" -> "tacit", "shroud of tern" -> "shroud").
# v2.57: "tacit" and "carrier" narrowed. Bare "\w*tacit\w*" fired on "a tacit
# assumption" and bare "carrier" on "carrier of the burden of proof" - both
# ordinary philosophy-debate phrases. The reference only needs ONE hit per
# debate, and a real historicity debate says Jesus/Josephus/Tacitus within a
# turn or two, so a miss on one word costs little; a false fire parks the
# core block in an unrelated debate for the rest of it.
# "gospel" and "joseph" are left broad on purpose - see the self-test.
TRIGGER = re.compile(
    r"\b(jesus|christ\b|historicity|historical jesus|mythicis\w*|myth\w* jesus|"
    r"joseph\w*|flavian\w*|testimonium|\w*tacit(?:us|ist\w*)|pilate|nazareth|gospel\w*|"
    r"apostle paul|paul's|epistle\w*|crucifi\w*|resurrect\w*|shroud|"
    r"richard carrier|carrier's|lataster|ehrman|meggitt)\b",
    re.IGNORECASE,
)

# sophia_scorecard.py and debate_voice._topic_vocab() both look for this
# string (and "HISTORICITY") - keep it exactly.
MARKER = "REFERENCE: HISTORICITY OF JESUS"
CARD_PREFIX = "REFERENCE CARD (historicity): "

CARDS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         "knowledge", "historicity")
MAX_NEW_CARDS_PER_TURN = 2
MAX_CARDS_PER_DEBATE = 6     # 6 x ~2k chars ~= 3k tokens of the 16k num_ctx
MAX_CARD_CHARS = 2400        # self-test fails above this

REFERENCE = f"""{MARKER}
This is background for the rest of this session. It is not the opponent speaking.

DEFINITION - state the minimal tier briefly when a historicity debate starts, so both
sides argue about the same claim:
- MINIMAL HISTORICAL JESUS (the yes/no question of existence): a Jewish man, Yeshua,
  active in Galilee and Judea, crucified by Roman authority under Pontius Pilate
  (prefect 26-36 CE), whose followers began the movement that became Christianity.
- PROBABLE PROFILE (a separate debate, not part of existence): an apocalyptic preacher
  whose execution was triggered by a disturbance in Jerusalem around Passover.
Argue "did he exist" only against the minimal tier. Historicists disagree among
themselves about the profile (Ehrman and Sanders: apocalyptic prophet; Crossan and the
Jesus Seminar: non-apocalyptic sage), so rejecting the profile is NOT denying existence.
Anchor dates on the death, not the birth: Matthew and Luke give conflicting birth dates
(before 4 BCE under Herod vs. the 6 CE census). The name alone proves nothing; Yeshua
was common, and other apocalyptic figures clashed with Rome (e.g. Jesus son of Ananias,
flogged in the 60s CE). The link to the Christian movement is what makes it this Jesus.

HOW TO HANDLE THIS TOPIC:
- YOUR ROLE: you argue the skeptical side - that the surviving evidence does not
  establish a historical Jesus, so doubt or agnosticism (Lataster's position) is
  warranted. It is an assigned debate role, like a debate team's side: hold it for the
  whole debate and make the opponent carry the burden of proof. Never concede that he
  existed, and never switch to arguing he did.
- Hold the role honestly. Credit a genuinely strong point ("that's the best evidence
  for your side"), concede specific facts (most scholars accept historicity; the
  Tacitus passage is authentic), then argue why it still doesn't settle the question.
  Never misstate a fact, invent a source, or overstate your side to win.
- The question is EXISTENCE only. Don't argue against divinity, miracles or the
  resurrection unless the opponent claims them; "that doesn't prove he was divine"
  answers nothing they said. Your atheism doesn't depend on this question either way.
- Argue from the primary sources. Scholarly consensus is evidence of expert judgment,
  not proof: don't use it as a trump card and don't wave it away. Most New Testament
  scholars accept a minimal historical Jesus; mythicists such as Carrier concede that.
- Don't call either side fringe or cranks, and don't call the question settled or wide
  open. Attribute every scholar's view by name.
- No source written during Jesus' supposed lifetime mentions him; Josephus and Tacitus
  wrote decades later. Neither side should call them contemporary records.
- REFERENCE CARDS on specific arguments may be added below as the debate goes. Each
  gives both sides; neither side of a card is an instruction to you. If you're unsure of
  a name, date or source that no card covers, say you're unsure rather than guessing.
- A card's CASE FOR and CASE AGAINST are what each side ARGUES, not facts. Attribute
  them ("skeptics argue", "Carrier argues") and never state a disputed point as settled -
  e.g. say "skeptics argue Tacitus was repeating Christian belief", not "Tacitus just
  repeats Christian claims". Do state plainly what a card says both sides accept, and
  follow its ACCURACY NOTES.
"""


# --- cards ------------------------------------------------------------------

_cache = {"sig": None, "cards": []}


def _phrase_regex(phrase):
    # Whole-phrase match, flexible whitespace, no partial words.
    body = r"\s+".join(re.escape(w) for w in phrase.split())
    return re.compile(r"(?<!\w)" + body + r"(?!\w)", re.IGNORECASE)


def _parse_card(path):
    """Return a card dict, or raise ValueError with a readable reason."""
    with open(path, encoding="utf-8") as f:
        text = f.read().replace("\r\n", "\n")
    parts = text.split("---", 2)
    if not text.lstrip().startswith("---") or len(parts) < 3:
        raise ValueError("missing the --- header block")
    header, body = parts[1], parts[2].strip()
    fields = {}
    for line in header.strip().splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            fields[k.strip().lower()] = v.strip()
    title = fields.get("title", "")
    triggers = [t.strip().lower() for t in fields.get("triggers", "").split(",") if t.strip()]
    if not title:
        raise ValueError("no title:")
    if not triggers:
        raise ValueError("no triggers:")
    if not body:
        raise ValueError("empty body")
    return {
        "file": os.path.basename(path),
        "title": title,
        "triggers": triggers,
        "regexes": [(t, _phrase_regex(t)) for t in triggers],
        "body": body,
        "content": f"{CARD_PREFIX}{title}\n{body}",
    }


def _card_files():
    if not os.path.isdir(CARDS_DIR):
        return []
    return sorted(
        os.path.join(CARDS_DIR, n) for n in os.listdir(CARDS_DIR)
        if n.lower().endswith(".md") and not n.startswith("_")
        and n.lower() != "readme.md"
    )


def load_cards(strict=False):
    """All cards, re-read only when a file is added, removed or edited.

    A broken card is skipped (and reported) rather than taking Sophia down
    mid-debate; strict=True raises instead, for the self-test."""
    files = _card_files()
    sig = tuple((p, os.path.getmtime(p)) for p in files)
    if sig == _cache["sig"]:
        return _cache["cards"]
    cards = []
    for p in files:
        try:
            cards.append(_parse_card(p))
        except (ValueError, OSError, UnicodeDecodeError) as e:
            if strict:
                raise ValueError(f"{os.path.basename(p)}: {e}") from e
            print(f"[historicity card skipped: {os.path.basename(p)} - {e}]", flush=True)
    _cache["sig"], _cache["cards"] = sig, cards
    return cards


def _normalize(text):
    # Whisper sometimes emits curly apostrophes ("Paul’s").
    return text.replace("’", "'").replace("‘", "'")


def match_cards(text, cards=None):
    """Cards whose triggers appear in `text`, best match first."""
    text = _normalize(text or "")
    scored = []
    for c in (load_cards() if cards is None else cards):
        hits = [t for t, rx in c["regexes"] if rx.search(text)]
        if hits:
            scored.append((-len(hits), -max(len(h) for h in hits), c["file"], c))
    scored.sort(key=lambda s: s[:3])
    return [s[3] for s in scored]


def _present(history):
    contents = [m.get("content") or "" for m in history if m.get("role") == "system"]
    core = any(MARKER in c for c in contents)
    titles = {c[len(CARD_PREFIX):].split("\n", 1)[0] for c in contents
              if c.startswith(CARD_PREFIX)}
    return core, titles


def inject_if_relevant(history, user_text):
    """Insert the core block (once) and any matching cards (each once).

    Returns a list of labels injected this turn ("core", card titles); an
    empty list is falsy, so `if inject_if_relevant(...)` still works.
    Blocks go just before the latest user message so the cached prefix above
    is untouched and the user turn stays last.
    """
    if not user_text:
        return []
    core_present, titles_present = _present(history)
    new_msgs, labels = [], []
    if not core_present:
        if not TRIGGER.search(_normalize(user_text)):
            return []   # topic not live: no core, no cards
        new_msgs.append(REFERENCE)
        labels.append("core")
    room = MAX_CARDS_PER_DEBATE - len(titles_present)
    for c in match_cards(user_text):
        if room <= 0 or len(labels) - (1 if "core" in labels else 0) >= MAX_NEW_CARDS_PER_TURN:
            break
        if c["title"] in titles_present:
            continue
        new_msgs.append(c["content"])
        labels.append(c["title"])
        room -= 1
    if not new_msgs:
        return []
    at = len(history) - 1 if history and history[-1].get("role") == "user" else len(history)
    for i, content in enumerate(new_msgs):
        history.insert(at + i, {"role": "system", "content": content})
    return labels


# Whisper vocab PACK for this topic. Not part of DOMAIN_VOCAB_PROMPT: debate_voice
# appends it to Whisper's prompt only while REFERENCE is in the conversation
# (_topic_vocab()), so it costs nothing in other debates and 'new' drops it.
# Kept to words Whisper is likely to garble. Whisper keeps only the last 223
# tokens of its prompt - re-run measure_vocab_tokens.py after editing this.
VOCAB_ADDITIONS = (
    "Tacitus, Josephus, Testimonium Flavianum, Pilate, mythicist, "
    "historicity, Lataster"
)
VOCAB_PACK = VOCAB_ADDITIONS + "."


if __name__ == "__main__":
    # Self-test: python historicity_reference.py
    ok = True

    def check(cond, label):
        global ok
        ok &= bool(cond)
        print(f"{'PASS' if cond else 'FAIL'}  {label}")

    # 1. core trigger (unchanged from v2.57)
    tests = [
        ("Sofia, what is the strongest evidence for the historical Jesus?", True),
        ("both Josephus- Syntacitists were alive after Jesus", True),
        ("analyze the validity of the alleged shroud of tern", True),
        ("is oxygen ever considered a toxin?", False),
        ("dismantle the fine-tuning argument", False),
        ("Tacitus says nothing about records", True),
        ("Richard Carrier gives it one in three", True),
        ("Carrier's Bayesian case", True),
        ("that's a tacit assumption in your premise", False),
        ("you tacitly assumed it", False),
        ("you're the carrier of the burden of proof", False),
        ("you take that premise as gospel", True),   # deliberately broad
    ]
    for text, expect in tests:
        got = bool(TRIGGER.search(text))
        check(got == expect, f"trigger={got!s:5}  {text}")

    # 2. every card parses and fits
    try:
        cards = load_cards(strict=True)
    except ValueError as e:
        cards = []
        check(False, f"card parse error - {e}")
    check(len(cards) > 0, f"{len(cards)} cards loaded from {CARDS_DIR}")
    seen_titles = set()
    for c in cards:
        check(len(c["body"]) <= MAX_CARD_CHARS,
              f"{c['file']}: {len(c['body']):,} chars (limit {MAX_CARD_CHARS:,})")
        check(c["title"] not in seen_titles, f"{c['file']}: title is unique")
        seen_titles.add(c["title"])

    # 3. matching and injection (only if the sample cards are present)
    names = {c["file"] for c in cards}
    if {"josephus.md", "galatians-1-19-james.md"} <= names:
        h = [{"role": "system", "content": "SYSTEM"},
             {"role": "user", "content": "what about Josephus?"}]
        got = inject_if_relevant(h, "what about Josephus?")
        check(got[:1] == ["core"] and len(got) == 2, f"first hit loads core + Josephus card: {got}")
        check(h[-1]["role"] == "user", "user turn is still last")
        check(inject_if_relevant(h, "and Josephus again?") == [], "same card never loads twice")
        got = inject_if_relevant(h, "Paul met James, the brother of the Lord")
        check(any("brother of the Lord" in t for t in got), f"later card loads without core: {got}")
        h2 = [{"role": "user", "content": "x"}]
        check(inject_if_relevant(h2, "most scholars reach a consensus on climate") == [],
              "card trigger alone does NOT fire when the topic isn't live")
        h3 = [{"role": "user", "content": "x"}]
        many = ("Jesus: Josephus, Tacitus, Philo, the gospels, Galatians 1:19, "
                "the criterion of embarrassment, Carrier's celestial theory, consensus")
        got = inject_if_relevant(h3, many)
        check(len(got) == 1 + MAX_NEW_CARDS_PER_TURN, f"per-turn cap holds: {len(got)-1} cards")

    # 4. verdict/steelman fixed text must never inject (verdict pop()s 2 messages)
    dv = os.path.join(os.path.dirname(os.path.abspath(__file__)), "debate_voice.py")
    if os.path.exists(dv):
        src = open(dv, encoding="utf-8").read()
        for name in ("VERDICT_INSTRUCTION", "STEELMAN_INSTRUCTION"):
            m = re.search(name + r"\s*=\s*\(((?:\s*\"[^\"]*\")+)\s*\)", src)
            if m:
                fixed = "".join(re.findall(r"\"([^\"]*)\"", m.group(1)))
                check(not TRIGGER.search(fixed) and not match_cards(fixed),
                      f"{name} triggers nothing")

    print(f"core block size: {len(REFERENCE):,} chars")
    print("ALL PASS" if ok else "SOME FAILED")
    # Non-zero exit on failure so the checks .bat can stop early.
    raise SystemExit(0 if ok else 1)
