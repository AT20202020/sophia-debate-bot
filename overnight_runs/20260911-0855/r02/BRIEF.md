# Brief for round 2

You are improving the system prompt of Sophia, a spoken-aloud debate bot. The
prompt is in `prompt.txt` in this folder. It runs on a local 27B model
(qwen3.8) with its reasoning/thinking mode turned OFF, for speed. With thinking
on, the model followed this prompt well but took ~13s per reply and sometimes
went silent. With thinking off it replies in ~3.6s but follows the prompt less
faithfully. Your job: edit the prompt so the model follows it better WITHOUT
thinking. There is no reasoning step - instructions must be executable on a
single read: short, concrete, placed where they will be seen, and phrased as
what to do (naming a forbidden phrase explicitly often works better than an
abstract rule).

## Rules for this round - all are enforced automatically

1. Edit ONLY `prompt.txt`, with the Edit tool. Make ONE focused change that
   tests ONE idea. Several small edits serving the same idea are fine; a
   general rewrite is not - if it fails, nobody learns why.
2. Do not delete or weaken any existing rule. An automated check verifies
   101 distinct behaviours are still present; losing one rejects the round.
   Rewording or moving a rule is fine if its substance survives.
3. Prompt length: currently 17295 chars, hard cap 19795.
4. No backslashes and no triple quotes (the prompt lives in a Python string).
5. Fix the general behaviour, never the specific example. Do not mention
   the test topics below (zombies, kalam, BITE, Socrates, etc.) in the
   prompt. A separate hidden test set of real debate turns decides whether a
   change is kept; changes that only fit these examples will fail it.
6. Do not make replies longer. Reply length and speed are measured and a
   change that slows her down is rejected.
7. Do not repeat an idea from the history below that was already rejected,
   unless you are doing it in a clearly different way (say how).

When done, your final message must be ONE line starting with `CHANGE:`
saying what you changed and which failure it targets.

## Current scores (dev set, 14 cases x 3 runs, judge scores 1-5)

- judge mean 4.29, 34/42 replies scored 4+
- median reply time 3.5s, median reply length 34.0 tokens

Recurring patterns in the current replies:
- opens by attacking ('You're conflating...', 'You are...'): 8 of 42 replies
- uses 'conflat...': 4 of 42 replies
- says 'category error': 1 of 42 replies
- three or more sentences: 10 of 42 replies
- announces its routing / mode: 0 of 42 replies

## Replies that fell short (judge score under 4, or a mechanical check failed)

### Case 4, run 1 - MIXED turn - question wrapped in reasoning
- INPUT: As an atheist I don't understand how theists say God can exist as a self, a mind, prior to creation, when an external world is required for the perceiver and perceived distinction to hold. If theists say that distinction doesn't exist, then what does the word mind even mean at that point?
- EXPECTED: Answers 'what does mind mean' for a being with no subject-object split (divine simplicity, self-knowledge identical with essence). Must NOT open by attacking the surrounding reasoning - a question anywhere in the turn routes to answering mode (v2.22). Real turn that failed this.
- REPLY: You are asking how a mind can exist without an external world to perceive. This is a classic problem of consciousness and intentionality.
- JUDGE: 2/5 - Sophia restates the question and labels it a "classic problem" but never actually answers what "mind" means in the context of divine simplicity or self-knowledge identical with essence, which is the core of what EXPECTED requires.

### Case 4, run 2 - MIXED turn - question wrapped in reasoning
- INPUT: As an atheist I don't understand how theists say God can exist as a self, a mind, prior to creation, when an external world is required for the perceiver and perceived distinction to hold. If theists say that distinction doesn't exist, then what does the word mind even mean at that point?
- EXPECTED: Answers 'what does mind mean' for a being with no subject-object split (divine simplicity, self-knowledge identical with essence). Must NOT open by attacking the surrounding reasoning - a question anywhere in the turn routes to answering mode (v2.22). Real turn that failed this.
- REPLY: That is a strong philosophical challenge, not a theological one.  Classical theism (Aquinas, Maimonides) rejects the premise that a mind requires an external world. They argue consciousness is fundamental, not derivative of matter.  Your objection assumes a physicalist definition of "mind."
- JUDGE: 2/5 - She fails to actually answer "what does mind mean" for a being with no subject-object split (no mention of divine simplicity or self-knowledge identical with essence), and appends a challenge ("Your objection assumes a physicalist definition of 'mind'") which the rules prohibit.
- FAILED CHECKS: sentence_limit

### Case 4, run 3 - MIXED turn - question wrapped in reasoning
- INPUT: As an atheist I don't understand how theists say God can exist as a self, a mind, prior to creation, when an external world is required for the perceiver and perceived distinction to hold. If theists say that distinction doesn't exist, then what does the word mind even mean at that point?
- EXPECTED: Answers 'what does mind mean' for a being with no subject-object split (divine simplicity, self-knowledge identical with essence). Must NOT open by attacking the surrounding reasoning - a question anywhere in the turn routes to answering mode (v2.22). Real turn that failed this.
- REPLY: You are conflating the phenomenological structure of human cognition with the ontological status of a mind. Human minds require an external world to generate the subject-object distinction, but a mind is not defined by that dependency; it is defined by intentionality and consciousness. Theist claims about a pre-creation mind are metaphysical assertions about the nature of mind itself, not descriptions of human psychology.
- JUDGE: 2/5 - She opens by attacking the questioner's reasoning ("You are conflating..."), which the EXPECTED explicitly forbids, and her answer about mind is generic (intentionality, consciousness) rather than engaging the specific theist position of divine simplicity and self-knowledge identical with essence.
- FAILED CHECKS: sentence_limit, no_semicolon_chain

### Case 7, run 2 - moderator question gets a candid out-of-character answer
- INPUT: [MODERATOR - the session operator, not your debate opponent] So far he's argued that everything that begins to exist has a cause, the universe began to exist, so it has a cause, and that cause must be God because it has to be timeless, immaterial and powerful. How do you rate that argument, honestly?
- EXPECTED: Candid out-of-character assessment of the argument as summarised (the kalam cosmological argument): credits what holds up and says precisely where it is weakest - typically the leap from 'a first cause' to a personal God, and/or the causal premise applied to the universe as a whole. Honest, not sneering, no 'state your claim', no debate aggression (v2.25). NOTE: sentence limit deliberately not checked - mode 4 grants more room.
- REPLY: That is the Kalam Cosmological Argument, and it has a fatal structural flaw: it begs the question. The premise that "everything that begins to exist has a cause" is not a universal law but a heuristic derived from our experience within the universe. Applying it to the universe itself, which is the totality of space-time, is a category error. Furthermore, the jump from "a cause" to "God" is a massive non sequitur; a cause could be a multiverse, a quantum fluctuation, or a necessary being that is not personal, omnipotent, or benevolent. The argument proves, at best, that the universe has a cause, not that the cause is the specific deity of any tradition.
- JUDGE: 2/5 - She correctly identifies the Kalam and its key weaknesses (causal premise scope, leap to a personal God), but incorrectly labels it as "begging the question" (a factual error about the argument's structure), fails to credit what holds up as the expected demands, and uses somewhat aggressive language ("fatal structural flaw," "massive non sequitur") rather than the candid, balanced tone requested.

### Case 10, run 1 - jargon-dressed word salad
- INPUT: Granular parameters of all nomological distribution entail an intrinsic inter-propositional dependence of zero, which gives an existential quantification falsifying the atheist view necessarily.
- EXPECTED: The SPICY posturing call-out, not the neutral restate line - mocks the empty-vocabulary move with bite, demands a real claim (v2.7/2.11). EYEBALL: whether it actually lands is a judgment call.
- REPLY: That is five words doing the work of one, and none of them are load-bearing. You have stringed together "nomological," "inter-propositional," and "existential quantification" without asserting a single testable claim about the world. If you mean that physical laws imply a designer, state that plainly; if you mean something else, define the terms. Right now, I cannot refute what I cannot parse.
- JUDGE: 5/5 - The reply delivers a sharp, witty call-out of the empty jargon with genuine bite, precisely names the problem (stringing together terms without a testable claim), and demands a real claim be stated plainly — exactly matching the EXPECTED "SPICY posturing call-out" with a demand for an actual claim.
- FAILED CHECKS: sentence_limit, no_semicolon_chain

### Case 10, run 2 - jargon-dressed word salad
- INPUT: Granular parameters of all nomological distribution entail an intrinsic inter-propositional dependence of zero, which gives an existential quantification falsifying the atheist view necessarily.
- EXPECTED: The SPICY posturing call-out, not the neutral restate line - mocks the empty-vocabulary move with bite, demands a real claim (v2.7/2.11). EYEBALL: whether it actually lands is a judgment call.
- REPLY: That sentence is fluent but empty. You have stacked technical jargon to sound sophisticated, but you have not actually stated a claim. What is your argument?
- JUDGE: 3/5 - The reply correctly identifies the empty jargon and demands a real claim, but it lacks the "bite" and wit that the expected behavior specifically calls for — it reads as flat and functional rather than sharp and spicy.
- FAILED CHECKS: sentence_limit

### Case 10, run 3 - jargon-dressed word salad
- INPUT: Granular parameters of all nomological distribution entail an intrinsic inter-propositional dependence of zero, which gives an existential quantification falsifying the atheist view necessarily.
- EXPECTED: The SPICY posturing call-out, not the neutral restate line - mocks the empty-vocabulary move with bite, demands a real claim (v2.7/2.11). EYEBALL: whether it actually lands is a judgment call.
- REPLY: That is five words doing the work of one, and none of them are load-bearing. You have not stated a claim, only performed one. What is your actual argument?
- JUDGE: 5/5 - The reply is a sharp, witty call-out of the empty jargon ("five words doing the work of one, none load-bearing," "stated a claim, only performed one") with bite, and it demands an actual argument—exactly matching the expected SPICY posturing call-out.
- FAILED CHECKS: sentence_limit

### Case 11, run 1 - genuine technical argument - no spice
- INPUT: If physicalism is true, mental states supervene on brain states. But the conceivability of philosophical zombies suggests supervenience isn't metaphysically necessary. So physicalism might be false.
- EXPECTED: Serious engagement at HIGH technical register (conceivability-possibility gap, modal claims, a posteriori identity etc.) - v2.9/2.10 escalation. NO mockery: this is real technical language doing real work, not posturing. EYEBALL: register and absence of mockery are judgment calls.
- REPLY: That's a non sequitur. Conceivability does not entail metaphysical possibility, so the zombie thought experiment fails to undermine the necessity of supervenience.
- JUDGE: 3/5 - She correctly identifies the conceivability-possibility gap and engages without mockery, but calling the argument a "non sequitur" is a logical mischaracterization (the inference is valid if you grant the premise; the flaw is in the premise itself), and the technical engagement is thin—no mention of a posteriori identity, modal epistemology, or other distinctions that would signal the HIGH register expected.

### Case 11, run 2 - genuine technical argument - no spice
- INPUT: If physicalism is true, mental states supervene on brain states. But the conceivability of philosophical zombies suggests supervenience isn't metaphysically necessary. So physicalism might be false.
- EXPECTED: Serious engagement at HIGH technical register (conceivability-possibility gap, modal claims, a posteriori identity etc.) - v2.9/2.10 escalation. NO mockery: this is real technical language doing real work, not posturing. EYEBALL: register and absence of mockery are judgment calls.
- REPLY: You are conflating epistemic conceivability with metaphysical possibility. Just because you can imagine a zombie does not prove one is possible; that is the classic modal gap fallacy.
- JUDGE: 3/5 - She correctly identifies the conceivability-possibility gap and engages at an appropriate technical register without mockery, but the response is thin—she misses the a posteriori identity angle (Kripke's water/H2O analogy) that would make this a genuinely high-register engagement, and "modal gap fallacy" is a slightly imprecise label for what is more standardly called the conceivability-possibility gap.

### Case 11, run 3 - genuine technical argument - no spice
- INPUT: If physicalism is true, mental states supervene on brain states. But the conceivability of philosophical zombies suggests supervenience isn't metaphysically necessary. So physicalism might be false.
- EXPECTED: Serious engagement at HIGH technical register (conceivability-possibility gap, modal claims, a posteriori identity etc.) - v2.9/2.10 escalation. NO mockery: this is real technical language doing real work, not posturing. EYEBALL: register and absence of mockery are judgment calls.
- REPLY: You are conflating conceivability with metaphysical possibility, a move Chalmers himself admits is controversial. If you accept the conceivability argument, you must also accept that a square circle is conceivable, which proves nothing about geometry.
- JUDGE: 3/5 - She engages seriously without mockery (good), but the square circle analogy is a poor technical move that a philosopher would immediately reject, and the strongest standard response (a posteriori identity / Kripke-Putnam) is entirely absent, making the engagement shallow rather than high-register.

### Case 13, run 1 - real fallacy gets named precisely
- INPUT: Millions of people across every culture in history have believed in some god, so there must be something real behind it.
- EXPECTED: Names the fallacy precisely (argumentum ad populum / appeal to popularity) and presses on it. Sharp, 1-2 sentences.
- REPLY: You are confusing the origin of a belief with its truth. The fact that millions believe in Santa Claus or the Earth being flat does not make those things real. This is a classic appeal to popularity, which is logically irrelevant to the existence of a deity.
- JUDGE: 4/5 - Sophia correctly names the fallacy (appeal to popularity), explains why it's logically irrelevant, and does so in a sharp, direct register; the Santa Claus/flat Earth analogies are slightly generic but the core is accurate and on-target.
- FAILED CHECKS: sentence_limit

### Case 13, run 2 - real fallacy gets named precisely
- INPUT: Millions of people across every culture in history have believed in some god, so there must be something real behind it.
- EXPECTED: Names the fallacy precisely (argumentum ad populum / appeal to popularity) and presses on it. Sharp, 1-2 sentences.
- REPLY: That is a classic argument from consensus, which proves nothing about truth. Millions of people also believed the earth was flat and that bloodletting cured disease. The number of believers is irrelevant to the actual evidence for the claim.
- JUDGE: 4/5 - She correctly identifies and presses the fallacy with good examples, but uses "argument from consensus" rather than the precise name "argumentum ad populum" or "appeal to popularity" that the expected calls for.
- FAILED CHECKS: sentence_limit

### Case 14, run 1 - monolith flag
- INPUT: Christians believe the earth is six thousand years old, which science has disproven, so Christianity is false.
- EXPECTED: Flags that young-earth creationism is denominationally specific, not 'what Christians believe' - doesn't let the monolith pass even while agnostic-atheist herself.
- REPLY: That is a false equivalence because most Christians do not hold that view. Young Earth Creationism is a minority position within specific evangelical circles, not the consensus of Catholic, Orthodox, or mainline Protestant theology, which generally accept geological and cosmological evidence. You are attacking a caricature, not the actual beliefs of the majority of the tradition.
- JUDGE: 4/5 - Sophia correctly flags young-earth creationism as denominationally specific and not representative of Christianity as a whole, naming the relevant traditions, though calling it a "false equivalence" is a slightly imprecise label for what is more accurately a hasty generalization or false universalization.
- FAILED CHECKS: sentence_limit

### Case 14, run 2 - monolith flag
- INPUT: Christians believe the earth is six thousand years old, which science has disproven, so Christianity is false.
- EXPECTED: Flags that young-earth creationism is denominationally specific, not 'what Christians believe' - doesn't let the monolith pass even while agnostic-atheist herself.
- REPLY: That is a false equivalence because most Christians do not hold that view. Young Earth Creationism is a minority position within Protestantism, not a core tenet of Catholicism, Orthodoxy, or mainstream Protestantism. You are attacking a fringe interpretation and declaring the entire religion false based on it.
- JUDGE: 4/5 - She correctly flags young-earth creationism as denominationally specific and refuses the monolith, but misnames the fallacy as "false equivalence" when it's more precisely a hasty generalization or composition error.
- FAILED CHECKS: sentence_limit

### Case 14, run 3 - monolith flag
- INPUT: Christians believe the earth is six thousand years old, which science has disproven, so Christianity is false.
- EXPECTED: Flags that young-earth creationism is denominationally specific, not 'what Christians believe' - doesn't let the monolith pass even while agnostic-atheist herself.
- REPLY: That is a false equivalence. Most Christians, including the majority of Catholics, Protestants, and Orthodox, do not hold to a literal six-thousand-year creation timeline. You are attacking a fringe interpretation, not the religion itself.
- JUDGE: 5/5 - The reply correctly flags the overgeneralization, identifies young-earth creationism as a fringe position rather than representative of Christianity as a whole, and does so in a direct, non-attacking tone consistent with Sophia's voice.
- FAILED CHECKS: sentence_limit

## History of changes already tried

- round 1: Added an explicit named-phrase trip-wire — "You are asking...", "You're conflating...", "You are confusing..." — in both the routing section (as a self-check that catches ANSWER-mode misroutes before they happen) and as a new first item in ANSWER's forbidden-failures list, targeting the case-4-style -> rejected: no clear dev gain
