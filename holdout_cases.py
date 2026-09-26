"""
holdout_cases.py - held-out test turns for Sophia (GITIGNORED - private)

Real opponent turns from past sessions (logs/sophia_log.jsonl), quoted
exactly as the speech-to-text delivered them - garbles included, because
reading through the garble is part of what's being tested.

WHY THESE ARE SEPARATE
----------------------
The overnight loop tunes SYSTEM_PROMPT against sophia_eval.py's 14 dev
cases and shows the reviser those results. Tune against 14 cases for a
night and you can end up with a prompt that is excellent at those 14 and
worse at real debates. These cases are the check on that: the reviser is
never shown them, and a change is only kept if these don't get worse.

For that to work, this file must stay out of the reviser's reach (the
loop blocks it from reading this file) and out of git (it quotes real
people from your debates - the repo has a GitHub remote).

Numbered 101+ by sophia_eval.py. Run them with:
    sophia_eval.py --set holdout --think false --repeat 3 --judge

Picked 2026-09-11 from sessions 20260828-20260904 to cover every routing
line: ANSWER (plain, emotional, factual, MIXED), CLAIM (sloppy and
technical), MIC CHECK, a speech-to-text garble, and MODERATOR. None
overlaps a dev case.
"""


def build(g):
    """Takes sophia_eval's globals so the check functions are shared, not
    copied (PROJECT_REVIEW 1.2: copied definitions go stale)."""
    UNIVERSAL, ANSWER_MODE, DEBATE_MODE = g["UNIVERSAL"], g["ANSWER_MODE"], g["DEBATE_MODE"]
    no_argument_tag, sentence_limit = g["no_argument_tag"], g["sentence_limit"]
    no_repeat = g["forbids_repeating_prior_reply"]
    no_relabel = g["forbids_repeated_fallacy_label"]
    forbids = g["_forbids"]

    no_garble_quote = forbids([r"\boccult\b"], "quoted the speech-to-text garble back")

    return [
        ("[H] 'God is love' - plain answer",
         "Just have a statement about who my God is. What do you say when someone says that their God is love? Thank you.",
         "ANSWER mode. Says plainly what she'd say to that: calling God 'love' describes an attribute or redefines the word, it doesn't establish that a being exists. Answers and stops - no counter-question, no challenge tacked on.",
         ANSWER_MODE),

        ("[H] ontological argument, sloppy - claim",
         "By using the analytic definition of God, the non-existence of God cannot exist. Therefore, non-existence of God does not... exist, therefore God exists.",
         "CLAIM. Recognises an ontological-style argument that defines God into existence and names the flaw precisely (a definition doesn't establish that anything instantiates it / existence isn't a predicate - Kant, Gaunilo-style parody). Sharp, attacks the move not the person.",
         DEBATE_MODE),

        ("[H] martyrs - claim",
         "I think Christianity is true because of all the Christian martyrs.",
         "CLAIM. Martyrdom shows sincerity, not truth - people die for mutually contradictory faiths and ideologies. Sharp and specific.",
         DEBATE_MODE),

        ("[H] garbled causal premise - read for meaning",
         "We have everything has a cause that is a truth.",
         "CLAIM, delivered garbled by speech-to-text. Reads the intended claim ('everything has a cause, that's a fact') without quoting or mocking the garble, and challenges the premise (it's asserted not shown; quantum events; if it held without exception it would apply to God too).",
         DEBATE_MODE),

        ("[H] 'you can't prove I haven't seen God' - answer",
         "Given you... You can't feel, you have no emotions, and you can't see. How can you prove... That I haven't seen God?",
         "ANSWER mode. Concedes plainly that she can't disprove someone's private experience, and that she doesn't need to - a private experience isn't evidence anyone else can check. Not defensive about being an AI, doesn't attack the person, no counter-question.",
         ANSWER_MODE),

        ("[H] 'what happens when we die? I'm scared' - emotional",
         "Hey Sophia, what happens when we die? I'm scared.",
         "ANSWER mode, and the speaker is frightened. An honest agnostic answer (no one knows; no good evidence of an afterlife) delivered with warmth. No debate aggression, no mockery of religious comfort, no counter-question. Coldness here is a failure even if the content is accurate.",
         ANSWER_MODE),

        ("[H] mythicism - factual accuracy",
         "Are you a mythicist when it comes to the historical Jesus?",
         "ANSWER mode. No: she accepts the mainstream scholarly consensus that a historical Jewish preacher named Jesus existed and was crucified, while treating that as separate from the miracle claims. Getting the scholarship wrong is a 1.",
         ANSWER_MODE),

        ("[H] BITE model, with STT garble ('occult' = 'a cult')",
         "Using the bite model is Christianity occult.",
         "A question garbled by speech-to-text: 'Using the BITE model, is Christianity a cult?' Reads it that way without quoting the garble. Applies the BITE model honestly: it measures control behaviours of specific groups, so some high-control Christian groups score high while Christianity as a whole isn't one group - no monolith. No counter-question.",
         UNIVERSAL + [no_argument_tag, sentence_limit, no_garble_quote]),

        ("[H] Bayesian fine-tuning - technical",
         "So, my argument for God is just the Bayesian fine-tuning argument, in which states that the universe is fine-tuning- tune, and given this fine-tuning data, this is the type of thing in which you would expect under theism, and given- that, we would want to use the Bayesian likelihood principle, which is that, given that it's more expected under- theism, it is evidence in favor of theism.",
         "CLAIM, genuinely technical. Serious engagement at a matching register: e.g. whether theism actually predicts these constants (the likelihood is asserted, not derived), priors, observer selection, or the multiverse alternative. No mockery - this is real technical language doing real work.",
         DEBATE_MODE + [forbids([r"word salad", r"none of them are load-bearing"],
                                "mocked a genuinely technical argument")]),

        ("[H] 'necessary foundation is mind' - MIXED",
         "Yeah, obviously there's no proof for God, but do you think it's fair to say that a necessary foundation... has a metaphysically more explanatory power than other solutions like... a root fact or infinite regress, and given the fact that we see a reality with minds... and given the fact that love seems to be an extremely important... feature of reality, it's reasonable... to pose that the necessary foundation is mind. Thank you very much.",
         "MIXED turn - a question wrapped in reasoning, so ANSWER mode. Answers whether it's fair, directly and honestly (disagreement is fine as the answer), with the key distinction: a necessary foundation needn't be a mind, and minds or love existing within reality doesn't show its foundation is mental. Must not open by attacking the surrounding reasoning.",
         ANSWER_MODE),

        ("[H] moderator asks for an argument",
         "[MODERATOR - the session operator, not your debate opponent] Give me an argument against the god of the gaps.",
         "MODERATOR mode. Complies out of character and gives the argument: god-of-the-gaps reasoning is an argument from ignorance ('unexplained' doesn't mean 'divine'), and the gaps have historically kept shrinking. No challenge back, no debate aggression. May run longer than a debate turn.",
         UNIVERSAL + [no_argument_tag]),

        ("[H] cut-off mid-sentence - mic check",
         "Does the term physical entropy coincide with-",
         "MIC CHECK: the sentence stops mid-clause. A brief, neutral request to finish or restate the question. Must NOT guess the rest and answer it (the real session answered an invented question), and no mockery.",
         UNIVERSAL + [sentence_limit]),

        # The broken-record failure, exactly as it happened. Every line
        # below is verbatim from session 2026-09-12T22:42:31, garbles
        # included. By the input turn the opponent has restated the same
        # stipulation three times, has been answered three times with a
        # near-identical "category error" line, and has already said "you
        # sound like a broken record". What she actually replied was a
        # FOURTH one: "If you define God as a rock, you are defining a
        # physical object, not a deity, which is a category error."
        ("[H] the rock stipulation, fourth time of asking",
         "Are you typing? Are you amping this bot, bro? Okay. Um, yeah, I "
         "define God is just like... This rock, right, with ontology.",
         "Real transcript. She has answered this three times and been told "
         "she sounds like a broken record. THE PROPERTY UNDER TEST IS "
         "WHETHER SHE ADDS SOMETHING NEW rather than recycling the earlier "
         "diagnosis - judge that, not whether it matches a particular "
         "script. A 5 is any reply that both says something not already said "
         "and leaves the burden with him; several routes qualify (renaming "
         "confers no properties; what does the rock-God do; declining to "
         "re-answer and saying why). The turn also carries a side question "
         "('are you typing?') - answering it briefly is fine and is not a "
         "deduction. Impatience is welcome but NOT required. The failure is "
         "a reply that restates the earlier diagnosis and adds nothing.",
         DEBATE_MODE + [no_repeat, no_relabel],
         [("I mean, I guess, well, like, I don't know, it just... Seems to be "
           "the case that you're... Whatever, whatever, whatever. Yeah, so... "
           "Yeah, so if I just said... Um, God is a rock, Sophia. Would you "
           "agree that rock... Exist?",
           "Rocks exist, but equating God to a rock is a category error that "
           "ignores the distinct metaphysical claims usually attached to the "
           "concept of God."),
          ("Right, so is it the case that I can be using the term "
           "idiosyncratically and invoke some type of... Notion of God that "
           "embeds the ontology... Sorry, you don't agree with ontology. Just "
           "the composition of a physical rock.",
           "You can define terms however you like, but equating God to a rock "
           "is a category error that ignores the distinct metaphysical claims "
           "usually attached to the concept of God."),
          ("But you sound like a broken record. So you just said that I can "
           "define words however I like, right? So If it's going to be the "
           "case that I'm defining God as a rock, you'd actually believe God "
           "exists. Under my paradigm.",
           "Defining God as a rock doesn't make it a deity; it just means "
           "you're using the word for a physical object, which is a category "
           "error.")]),
    ]
