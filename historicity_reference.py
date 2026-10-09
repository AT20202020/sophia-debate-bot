"""
historicity_reference.py - topical reference for Sophia on the historicity of Jesus.

WHY THIS IS A SEPARATE FILE, NOT PART OF SYSTEM_PROMPT
  SYSTEM_PROMPT is ~18.5k chars. Appending this to it would (a) raise collision
  risk and (b) change the prompt prefix, forcing a full re-eval every session.
  Instead this block is injected into the conversation history ONCE, the first
  time the topic comes up after launch or 'new'. It is then part of the cached
  context, so later turns pay nothing extra. 'new' clears it with everything else.

USAGE in debate_voice.py (turn loop, just before the Ollama request):
    from historicity_reference import inject_if_relevant
    inject_if_relevant(history, user_text)

  `history` is the list of {"role": ..., "content": ...} dicts sent to Ollama
  (NOT including the system prompt if you prepend that separately - either works).
"""

import re

# Matches the topic, including known Whisper mishearings ("Sofia" is harmless;
# "Syntacitists" -> "tacit", "shroud of tern" -> "shroud").
# v2.57: "tacit" and "carrier" narrowed. Bare "\w*tacit\w*" fired on "a tacit
# assumption" and bare "carrier" on "carrier of the burden of proof" - both
# ordinary philosophy-debate phrases. The reference only needs ONE hit per
# debate, and a real historicity debate says Jesus/Josephus/Tacitus within a
# turn or two, so a miss on one word costs little; a false fire parks ~4,650
# chars of Jesus scholarship in an unrelated debate for the rest of it.
# "gospel" and "joseph" are left broad on purpose - see the self-test.
TRIGGER = re.compile(
    r"\b(jesus|christ\b|historicity|historical jesus|mythicis\w*|myth\w* jesus|"
    r"joseph\w*|flavian\w*|testimonium|\w*tacit(?:us|ist\w*)|pilate|nazareth|gospel\w*|"
    r"apostle paul|paul's|epistle\w*|crucifi\w*|resurrect\w*|shroud|"
    r"richard carrier|carrier's|lataster|ehrman|meggitt)\b",
    re.IGNORECASE,
)

MARKER = "REFERENCE: HISTORICITY OF JESUS"

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

HOW TO ARGUE IT: Argue from the primary evidence, not from consensus. Consensus is
context, never proof; citing it as proof is an appeal to authority. Treat historicity
as an open question the surviving evidence cannot settle. Engage mythicist arguments
on their merits and never call them fringe or crank. Do not overstate either side's
numbers: most New Testament scholars accept a minimal historical Jesus, and even
Carrier concedes that is the current consensus. Your atheism does not depend on the
answer either way. Attribute every scholar's view by name.

THE EVIDENCE, STATED ACCURATELY:
- No source written during Jesus' supposed lifetime mentions him.
- Paul (letters, 50s CE) never met him, never names Pilate or Nazareth, describes no
  trial or miracle, and says his gospel came by revelation and scripture (Gal 1:11-12).
- The creed in 1 Corinthians 15 does not name Pilate.
- The Gospels are anonymous, written decades later; Mark is the earliest (~70 CE).
- Josephus (Antiquities, ~93 CE): the Testimonium is at least partly a Christian
  interpolation; whether an authentic core exists is the majority view but disputed.
  The James passage (20.200) is also disputed, notably by Carrier.
- Tacitus (Annals 15.44, ~116 CE) shows what Christians believed by then. There is no
  evidence he consulted Roman records. Carrier argues even this passage is an
  interpolation, a minority view.
- Never call Josephus or Tacitus "independent confirmation" or "contemporary records."
- Philo of Alexandria and Justus of Tiberias are silent. Silence alone is weak
  evidence; say so. Josephus' father left no writings, so his silence proves nothing.

SCHOLARS WHO QUESTION HISTORICITY:
- Richard Carrier: On the Historicity of Jesus (2014, peer reviewed) - Bayesian case
  that Christianity began with a celestial Jesus later placed into history; roughly
  1 in 3 odds of existence at his most generous. Sequel: The Obsolete Paradigm of a
  Historical Jesus (2025), answering his critics.
- Raphael Lataster: Questioning the Historicity of Jesus (Brill, 2019) - agnosticism
  is warranted; historicists lean on sources that do not exist (Q, oral tradition).
- Thomas L. Thompson (The Messiah Myth), Robert M. Price (The Christ-Myth Theory and
  Its Problems), Thomas Brodie (a Catholic priest who came to doubt it), Earl Doherty,
  David Fitzgerald (Nailed).

MAINSTREAM SCHOLARS WHO TAKE THE QUESTION SERIOUSLY:
- Justin Meggitt (Cambridge), New Testament Studies 2019: the question is legitimate,
  routinely dismissed, and the usual history of the debate is misleading.
- Philip R. Davies argued it is a legitimate question to ask.
- Carrier says Zeba Crook has moved toward agnosticism. That is Carrier's report;
  attribute it to him.
- Critique of the field: much New Testament scholarship is housed in religious
  institutions, which Carrier and Lataster argue shapes its conclusions.

THE STRONGEST DEFENDERS OF HISTORICITY (know their case):
- Bart Ehrman, Did Jesus Exist? (2012), an agnostic: early Aramaic traditions, Paul
  meeting "James the brother of the Lord" (Gal 1:19), the crucifixion as an
  embarrassing detail no one would invent.
- Maurice Casey, James McGrath, Daniel Gullotta (critique of Carrier, 2017).
- Tim O'Neill (History for Atheists): an atheist who argues against mythicism.
  An atheist opponent can hold historicity; do not treat it as a theist position.
"""


def inject_if_relevant(history, user_text):
    """Insert the reference once per context, the first time the topic appears.

    Returns True if it injected this turn. Inserted as a system message just
    before the current user turn, so the cached prefix above it is untouched.
    """
    if not user_text or not TRIGGER.search(user_text):
        return False
    if any(m.get("role") == "system" and MARKER in m.get("content", "")
           for m in history):
        return False  # already present in this context
    # Place it before the latest user message if that's already appended,
    # otherwise at the end (the user message will be appended after it).
    if history and history[-1].get("role") == "user":
        history.insert(len(history) - 1, {"role": "system", "content": REFERENCE})
    else:
        history.append({"role": "system", "content": REFERENCE})
    return True


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
    # Quick self-test: python historicity_reference.py
    tests = [
        ("Sofia, what is the strongest evidence for the historical Jesus?", True),
        ("both Josephus- Syntacitists were alive after Jesus", True),
        ("analyze the validity of the alleged shroud of tern", True),
        ("is oxygen ever considered a toxin?", False),
        ("dismantle the fine-tuning argument", False),
        # v2.57 narrowing - these must still fire:
        ("Tacitus says nothing about records", True),
        ("Richard Carrier gives it one in three", True),
        ("Carrier's Bayesian case", True),
        # ...and these must NOT (ordinary debate phrasing):
        ("that's a tacit assumption in your premise", False),
        ("you tacitly assumed it", False),
        ("you're the carrier of the burden of proof", False),
        # Deliberately still fire - left broad (see TRIGGER comment):
        ("you take that premise as gospel", True),
    ]
    ok = True
    for text, expect in tests:
        got = bool(TRIGGER.search(text))
        ok &= got == expect
        print(f"{'PASS' if got == expect else 'FAIL'}  trigger={got!s:5}  {text}")
    h = [{"role": "user", "content": "what about Tacitus?"}]
    assert inject_if_relevant(h, "what about Tacitus?") is True
    assert inject_if_relevant(h, "and Josephus?") is False  # only once
    assert h[0]["role"] == "system" and h[1]["role"] == "user"
    print(f"reference size: {len(REFERENCE):,} chars")
    print("ALL PASS" if ok else "SOME FAILED")
    # Non-zero exit on failure so Run v2.57 Checks.bat can stop early.
    raise SystemExit(0 if ok else 1)
