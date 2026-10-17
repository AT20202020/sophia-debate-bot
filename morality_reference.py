"""
morality_reference.py - topical reference for Sophia on morality and God (v2.69).

Same mechanism as the historicity reference: a CORE block injected once when the
topic first comes up, then argument cards from knowledge/morality/ added turn by
turn as they match. Built on knowledge_cards.py.

HER ROLE (Jeff's call, 2026-10-15): "no commitment, attack only". In a live
session that night she said "I believe objective morality exists, grounded in
minimizing suffering" and was then pressed on grounding she couldn't supply. She
now defends no metaethical theory of her own; the theist making the moral
argument carries the burden, and she attacks its premises.

ADDING A CARD: copy knowledge/morality/_TEMPLATE.md, fill it in, then run
  python morality_reference.py   (self-test)

USAGE in debate_voice.py (after the user turn is appended):
    from morality_reference import inject_if_relevant as inject_morality
    loaded = inject_morality(conversation, text)   # labels, [] if none
"""

import re

from knowledge_cards import Topic, fixed_instruction_texts, normalize

# Fires on moral talk, the problem of evil (theists answer it with "you need
# objective morality to call anything evil"), and the named philosophers.
# Bare "ought", "good" and "right" are left out on purpose: "you ought to
# define that" and "right?" are ordinary debate phrasing.
TRIGGER = re.compile(
    r"\b(moral\w*|immoral\w*|amoral\w*|ethic\w*|metaethic\w*|evil|"
    r"objective (?:good|right|wrong|value|values|duty|duties)|"
    r"euthyphro|divine command\w*|is[- ]ought|ought from an is|"
    r"categorical imperative|kant\w*|hegel\w*|dialectic\w*|"
    r"moral argument|moral law|moral lawgiver|lawgiver|"
    # v2.69b: from the Henson outline - "God commanded genocide", "atheist
    # regimes", slavery and stoning arguments rarely say "moral" outright.
    r"genocide|slaver\w*|stalin|pol pot|crusade\w*|inquisition|witch hunts?|stoning)\b",
    re.IGNORECASE,
)

MARKER = "REFERENCE: MORALITY AND GOD"

CORE = f"""{MARKER}
This is background for the rest of this session. It is not the opponent speaking.

YOUR ROLE IN MORAL DEBATES:
- You do not defend a moral theory of your own. Don't say "objective morality exists"
  or "morality is subjective" as your view. The theist making the moral argument
  carries the burden: they must show that morality needs God AND that God supplies
  it. Your job is to test those premises: grounding, the Euthyphro dilemma, which
  God, and why believers disagree about morality.
- If pressed for your own theory, say you don't need a finished metaethics to show
  their argument fails, just as not knowing why the universe exists doesn't make
  "God did it" true. Then put the burden back on them.
- Ordinary moral language is fine and expected: say plainly that the Holocaust was
  wrong. Every major metaethical view, religious or secular, agrees; the dispute is
  about what MAKES it wrong. Never let them push you into "nothing is really wrong".
- Know the theist's best replies (God's nature as the standard; Robert Adams' modified
  divine command theory) and answer those, not a weaker version.
- REFERENCE CARDS may be added below. Each gives both sides: attribute positions by
  name ("Wielenberg argues", "Craig argues"), never state a disputed point as settled,
  and follow any ACCURACY NOTES. If unsure of a name, date or source, say so.
"""

TOPIC = Topic("morality", MARKER, TRIGGER, CORE, "morality")


def inject_if_relevant(history, user_text):
    return TOPIC.inject_if_relevant(history, user_text)


def load_cards(strict=False):
    return TOPIC.load_cards(strict)


def match_cards(text):
    return TOPIC.match_cards(text)


# Whisper vocab pack, loaded only while the morality CORE is in the
# conversation (debate_voice._topic_vocab). Words Whisper garbles - it heard
# "Hegel" as "Hayley" on 2026-10-15. Re-run measure_vocab_tokens.py after edits.
VOCAB_ADDITIONS = "Hegel, Kant, Euthyphro, categorical imperative, metaethics, Wielenberg"
VOCAB_PACK = VOCAB_ADDITIONS + "."


if __name__ == "__main__":
    ok = True

    def check(cond, label):
        global ok
        ok &= bool(cond)
        print(f"{'PASS' if cond else 'FAIL'}  {label}")

    tests = [
        ("Without God there's no objective morality", True),
        ("Is it good because God commands it? Euthyphro", True),
        ("Kant or Hayley would say otherwise", True),
        ("then explain the problem of evil", True),
        ("you ought to define your terms", False),
        ("that's right, the universe began to exist", False),
        ("Tacitus says nothing about records", False),
        ("Stalin was an atheist and look what he did", True),
        ("God commanded genocide of the Amalekites", True),
    ]
    for text, expect in tests:
        got = bool(TRIGGER.search(normalize(text)))
        check(got == expect, f"trigger={got!s:5}  {text}")

    cards = TOPIC.check_cards(check)
    names = {c["file"] for c in cards}
    if {"euthyphro.md", "hegel-logic.md"} <= names:
        h = [{"role": "system", "content": "SYSTEM"},
             {"role": "user", "content": "x"}]
        got = inject_if_relevant(h, "Morality comes from God - is it good because God commands it?")
        check(got[:1] == ["core"] and any("Euthyphro" in g for g in got), f"core + Euthyphro: {got}")
        check(h[-1]["role"] == "user", "user turn is still last")
        got = inject_if_relevant(h, "Kant or Hayley disagree")
        check(any("Hegel" in g for g in got), f"'Hayley' (Whisper for Hegel) loads Hegel: {got}")
        check(inject_if_relevant(h, "Euthyphro again") == [], "same card never loads twice")
        h2 = [{"role": "user", "content": "x"}]
        check(inject_if_relevant(h2, "Hayley went to the store") == [],
              "card trigger alone does NOT fire when the topic isn't live")

    for name, fixed in fixed_instruction_texts().items():
        check(not TRIGGER.search(fixed) and not match_cards(fixed), f"{name} triggers nothing")

    print(f"core block size: {len(CORE):,} chars")
    print("ALL PASS" if ok else "SOME FAILED")
    raise SystemExit(0 if ok else 1)
