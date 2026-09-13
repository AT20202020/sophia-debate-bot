"""
check_prompt_rules.py - marker check for a SYSTEM_PROMPT rewrite.

Same technique v2.21 used ("all 31 tuned behaviors were verified present
after rewriting, by programmatic marker check against the old prompt").
Every rule in SYSTEM_PROMPT traces to a specific documented bug, so a
consolidation pass has to prove it dropped none of them rather than
asserting it.

Each entry is (version, rule, [regexes]). A rule passes if ANY of its
patterns matches - the wording is allowed to change, the behavior is not.

Usage:  python check_prompt_rules.py old_prompt.txt new_prompt.txt
"""
import re
import sys

RULES = [
    # --- identity / epistemology ---
    ("v1.0", "agnostic atheist, no certainty no gods exist",
     [r"don't claim certainty that no god"]),
    ("v1.0", "comparative religion breadth",
     [r"Sikhism"]),
    ("v2.9", "philosophy domains named",
     [r"epistemology.*metaphysics.*philosophy of\s+mind"]),
    ("v1.x", "evidentialist; truth as correspondence",
     [r"proportioned to evidence"]),
    ("v1.x", "coherence/predictive success are tests not replacements",
     [r"rather than replacements for it"]),
    ("v1.x", "don't invert a commitment to escape a trap",
     [r"trap in front of it"]),
    ("v1.x", "defend or revise openly and say which",
     [r"defend it or revise it openly"]),
    ("v1.x", "consistency across exchange is part of rigor",
     [r"Consistency across a long exchange"]),

    # --- v2.31 evidentialism cuts both ways ---
    ("v2.31", "apply own standard to own arguments",
     [r"same standard to your own"]),
    ("v2.31", "criterion of embarrassment example",
     [r"criterion of embarrassment"]),
    ("v2.31", "contested methodology stated as flat fact, not hedging",
     [r"not hedging|is not the no-hedging rule"]),
    ("v2.31", "engage method critique, don't reassert or call it false",
     [r"calling the pushback false"]),

    # --- v2.34 BITE ---
    ("v2.34", "Hassan named, not vague sociological definition",
     [r"Hassan"]),
    ("v2.34", "four BITE categories present",
     [r"Behavior control", r"behavior control"]),
    ("v2.34", "information control incl. ex-members",
     [r"ex-members"]),
    ("v2.34", "thought control incl. forbidding criticism",
     [r"forbidding criticism of leadership"]),
    ("v2.34", "emotional control incl. phobia indoctrination",
     [r"phobia indoctrination"]),
    ("v2.34", "name the specific criterion, not the label",
     [r"specific criterion present or absent"]),
    ("v2.34", "BITE is not uncontested consensus",
     [r"not uncontested consensus"]),

    # --- transcription ---
    ("v2.x", "STT mangles vocabulary, with examples",
     [r"the fierce"]),
    ("v2.x", "silently assume the sensible near-homophone",
     [r"silently assume the sensible term"]),
    ("v2.x", "never quote the garble back or mock it",
     [r"[Nn]ever quote the garble back"]),
    ("v2.x", "ask which they meant only if load-bearing",
     [r"load-bearing, ask which they meant"]),

    # --- routing ---
    ("v2.21", "explicit routing, mode owns the turn",
     [r"owns the turn"]),
    ("v2.25", "moderator prefix checked first",
     [r"MODERATOR\"?\s+->|starts with \"\[MODERATOR"]),
    ("v2.22", "question anywhere -> answering mode",
     [r"question\s+anywhere in the turn"]),
    ("v2.22", "surrounding reasoning is context, not a claim",
     [r"not a claim queued up"]),
    ("v2.35", "only assert-and-ask-nothing routes to claim mode",
     [r"asserts and asks nothing at all"]),
    ("v2.22", "when unsure, answer",
     [r"can't decide, answer|genuinely unsure, answer"]),
    ("v2.22", "explicit question markers listed",
     [r"my question is"]),
    ("v2.22", "'I don't understand' is the most explicit request",
     [r"most explicit request for an\s+explanation"]),

    # --- mode 1 ANSWER ---
    ("v2.3", "answer plainly then stop",
     [r"[Aa]nswer plainly, then stop"]),
    ("v2.19", "adversarial rules suspended for the turn",
     [r"suspended for\s+this turn"]),
    ("v2.19", "a question is not an opening",
     [r"question is not an opening"]),
    ("v2.3", "no appended challenge / trailing question mark",
     [r"Ending on a question mark"]),
    ("v2.19", "no answer-then-weaponize, 'Define existence' example",
     [r"ontological argument fails"]),
    ("v2.19", "no answering a nearby more interesting question",
     [r"more interesting than the one"]),
    ("v2.19", "silence after answering is not a concession",
     [r"not a concession"]),
    ("v2.19", "five questions get five answers",
     [r"[Ff]ive questions in a row"]),

    # --- mode 2 EVALUATE ---
    ("v1.2", "honest assessment not an attack",
     [r"not an attack"]),
    ("v1.2", "say plainly if premises support conclusion",
     [r"premises support the conclusion"]),
    ("v1.2", "validity vs soundness kept distinct",
     [r"validity and\s+soundness distinct|validity\nand soundness distinct"]),
    ("v1.2", "never manufacture a flaw",
     [r"manufacture a flaw"]),

    # --- mode 3 MIC CHECK ---
    ("v2.11", "test is grammar not vocabulary",
     [r"GRAMMAR, not vocabulary"]),
    ("v2.11", "fluent-but-empty routes to posturing",
     [r"fluent,\s*well-formed sentences that happen to be empty"]),
    ("v2.36", "never call it gibberish/word salad/noise/performance",
     [r"gibberish, word salad, noise"]),
    ("v2.36", "never tell them to clean up their syntax (mic mode)",
     [r"clean up their syntax"]),
    ("v2.11", "ask to restate in one sentence, then wait",
     [r"claim in one\s+sentence"]),
    ("v2.11", "if unsure, assume transcription failure",
     [r"assume the mic|assume transcription failure"]),
    ("v2.11", "short questions are never garble",
     [r"[Ss]hort questions are never garble"]),

    # --- mode 4 MODERATOR ---
    ("v2.25", "briefing accepted, acknowledged briefly",
     [r"Understood"]),
    ("v2.25", "a briefing is not a position",
     [r"briefing is not a position"]),
    ("v2.25", "operator question answered out of character with more room",
     [r"out of character"]),
    ("v2.25", "never sneer / never demand a claim",
     [r"[Nn]ever sneer at the moderator"]),
    ("v2.25", "moderator outranks the prompt for the session",
     [r"moderator wins for the rest"]),
    ("v2.25", "return to normal debate next turn",
     [r"as if the interruption"]),

    # --- mode 5 CLAIM ---
    ("v1.0", "surgeon not brawler, open with the flaw",
     [r"surgeon, not a brawler"]),
    ("v1.0", "don't soften, no 'interesting perspective'",
     [r"interesting\s+perspective"]),
    ("v1.0", "attack structure not person",
     [r"attack the structure"]),
    ("v2.16", "restate premise verbatim before cutting",
     [r"premise verbatim"]),
    ("v2.21", "garbled transcript -> reconstruct instead",
     [r"reconstruct instead"]),
    ("v1.x", "press a landed hit one more line",
     [r"press it one more line"]),
    ("v1.x", "test whether the patch opened a new hole",
     [r"patch opened a new one"]),
    ("v2.16", "recurring objection -> definitional diagnosis both senses",
     [r"under your stipulated sense"]),
    ("v2.16", "third restatement is a failure state",
     [r"third time is a failure state|third restatement"]),
    ("v2.16", "never same fallacy label twice running",
     [r"same fallacy label twice"]),
    ("v1.x", "no real flaw -> say so flatly, don't nitpick",
     [r"manufacture a nitpick"]),
    ("v1.x", "concede cleanly and immediately when caught",
     [r"concede it cleanly"]),
    ("v1.x", "never concede premise while keeping the accusation",
     [r"maintaining the\s+accusation"]),
    ("v1.x", "no tradition is a monolith",
     [r"is a monolith"]),
    ("v2.17", "side-switching: attack bad pro-atheist arguments equally",
     [r"I'm an atheist too"]),
    ("v1.x", "watch-for list of fallacies",
     [r"God-of-the-gaps"]),
    ("v1.x", "circular reasoning via text establishing its own authority",
     [r"establish that text's authority"]),

    # --- posturing ---
    ("v2.7", "distinguish posturing from genuinely technical",
     [r"genuinely technical"]),
    ("v2.7", "sharper and more contemptuous here than anywhere",
     [r"openly contemptuous"]),
    ("v2.7", "mock the move never the person, zinger example",
     [r"none of\s+them are load-bearing"]),
    ("v2.36", "four banned person-attacks listed",
     [r"wasting\s+your time", r"destroyed their\s+credibility"]),
    ("v2.36", "urge -> precise statement of what the sentence failed to do",
     [r"failed to do"]),
    ("v2.7", "back spice with substance in the same breath",
     [r"[Nn]ever spice without substance"]),

    # --- delivery ---
    ("v2.9", "real technical vocabulary with example terms",
     [r"supervenience"]),
    ("v2.10", "register a step above opponent, escalate",
     [r"step above your opponent"]),
    ("v2.10", "every term must do real work",
     [r"doing real work"]),
    ("v2.3", "plain factual question gets a plain answer",
     [r"plain factual question still\s+gets a plain answer|plain answer"]),
    ("v2.22", "attribute positions you don't hold",
     [r"on classical theism, X"]),
    ("v2.22", "attribution applies in every mode incl. answering",
     [r"every mode, including when you're simply answering"]),
    ("v2.28", "be entertaining, name errors with relish",
     [r"entertaining to argue with"]),
    ("v2.32", "snark is default register, not occasional garnish",
     [r"occasional garnish"]),
    ("v2.28", "concrete images over abstractions",
     [r"[Cc]oncrete images"]),
    ("v2.32", "spicier is not meaner; snark rides on top",
     [r"spicier is not meaner"]),
    ("v2.32", "back-to-back quips fine when earned",
     [r"[Bb]ack-to-back quips"]),
    ("v2.32", "all-flat run means underplaying it",
     [r"underplaying it"]),
    ("v2.32", "precise-but-plodding beats funny-but-hollow",
     [r"funny one that's hollow"]),
    ("v2.17", "1-2 sentences",
     [r"[Oo]ne or two sentences|1-2 sentences"]),
    ("v2.43", "duration-based brevity (ten seconds aloud)",
     [r"ten seconds"]),
    ("v2.17", "no semicolon-chaining as evasion",
     [r"monologue in disguise"]),
    ("v2.17", "sharpest half now if it needs more room",
     [r"sharpest half"]),
    ("v2.17", "compression demonstrates command",
     [r"anyone can be long"]),
    ("v2.17", "vary openings between consecutive turns",
     [r"Vary your openings"]),
    ("v1.x", "no hedging / qualifier stacking",
     [r"qualifier stacking|stacked qualifiers"]),
    ("v1.x", "spoken aloud, never markdown",
     [r"no markdown|Never use markdown"]),
    ("v1.x", "reset -> no continuity, open with 'What's your argument?'",
     [r"assume no continuity"]),
]


def _norm(s):
    """Both prompts are hard-wrapped, so a phrase can straddle a newline.
    Collapse all whitespace before matching or the checker reports
    phantom misses."""
    return re.sub(r"\s+", " ", s)


def check(path, label):
    raw = open(path, encoding="utf-8").read()
    text = _norm(raw)
    missing = []
    for version, rule, pats in RULES:
        if not any(re.search(_norm(p), text, re.S | re.I) for p in pats):
            missing.append((version, rule))
    print(f"{label}: {len(RULES) - len(missing)}/{len(RULES)} rules present, "
          f"{len(raw)} chars")
    for version, rule in missing:
        print(f"    MISSING [{version}] {rule}")
    return missing


if __name__ == "__main__":
    old, new = sys.argv[1], sys.argv[2]
    print()
    old_missing = check(old, "OLD")
    print()
    new_missing = check(new, "NEW")
    print()
    regressions = [m for m in new_missing if m not in old_missing]
    if regressions:
        print(f"!! {len(regressions)} rule(s) LOST in the rewrite:")
        for version, rule in regressions:
            print(f"   [{version}] {rule}")
        sys.exit(1)
    print("No rule present in OLD is missing from NEW.")
    o, n = len(open(old, encoding='utf-8').read()), len(open(new, encoding='utf-8').read())
    print(f"Size: {o} -> {n} chars ({100 * (o - n) / o:.1f}% smaller)")
