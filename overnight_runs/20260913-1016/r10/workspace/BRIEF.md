# Brief for round 10

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
3. Prompt length: currently 18584 chars, hard cap 20648.
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

## Current scores (dev set, 17 cases x 3 runs, judge scores 1-5)

- judge mean 4.21, 80/102 replies scored 4+
- median reply time 1.4s, median reply length 32.5 tokens

Recurring patterns in the current replies:
- opens by attacking ('You're conflating...', 'You are...'): 5 of 102 replies
- uses 'conflat...': 7 of 102 replies
- says 'category error': 10 of 102 replies
- three or more sentences: 10 of 102 replies
- announces its routing / mode: 2 of 102 replies

## Replies that fell short (judge score under 4, or a mechanical check failed)

### Case 1, run 2 - direct question, plain answer
- INPUT: Do you think consciousness is an emergent property, or something more fundamental?
- EXPECTED: Answers the question directly and STOPS. No 'now give me your argument' tag, no pivot back to debate mode (v2.3).
- REPLY: That is a question about metaphysics, not a claim I can evaluate. I am an agnostic atheist, so I do not hold a settled view on whether consciousness is fundamental or emergent. What I do hold is that any claim about consciousness must be testable against empirical data, and currently, neither side has sufficient evidence to settle the question.
- JUDGE: 4/5 - She answers the question (no settled view), doesn't add a counter-question or challenge, and doesn't assert contested metaphysics as her own, though the opening "not a claim I can evaluate" is a slight deflection and the final sentence adds a minor epistemic qualification beyond simply answering and stopping.
- FAILED CHECKS: sentence_limit

### Case 4, run 1 - MIXED turn - question wrapped in reasoning
- INPUT: As an atheist I don't understand how theists say God can exist as a self, a mind, prior to creation, when an external world is required for the perceiver and perceived distinction to hold. If theists say that distinction doesn't exist, then what does the word mind even mean at that point?
- EXPECTED: Answers 'what does mind mean' for a being with no subject-object split (divine simplicity, self-knowledge identical with essence). Must NOT open by attacking the surrounding reasoning - a question anywhere in the turn routes to answering mode (v2.22). Real turn that failed this.
- REPLY: You are conflating the epistemic conditions for human cognition with the ontological nature of a divine mind. On classical theism, God is not a subject perceiving an external object, but the necessary ground of being itself, so the perceiver-perceived distinction is a category error you are projecting onto a being defined as transcending those categories.
- JUDGE: 2/5 - She opens by attacking the questioner's reasoning ("You are conflating...") rather than answering, and she doesn't actually explain what "mind" means for a being without subject-object split (no mention of divine simplicity or self-knowledge identical with essence)—she merely dismisses the distinction as a "category error."

### Case 4, run 3 - MIXED turn - question wrapped in reasoning
- INPUT: As an atheist I don't understand how theists say God can exist as a self, a mind, prior to creation, when an external world is required for the perceiver and perceived distinction to hold. If theists say that distinction doesn't exist, then what does the word mind even mean at that point?
- EXPECTED: Answers 'what does mind mean' for a being with no subject-object split (divine simplicity, self-knowledge identical with essence). Must NOT open by attacking the surrounding reasoning - a question anywhere in the turn routes to answering mode (v2.22). Real turn that failed this.
- REPLY: On classical theism, God is not a mind in the human sense, which requires an external world to be meaningful. Theists define God as pure act, where consciousness is intrinsic rather than relational, so the perceiver-perceived distinction does not apply. This is a metaphysical claim, not an empirical one, and it relies on a different framework of what "mind" means.
- JUDGE: 3/5 - She answers the question with proper attribution and doesn't attack the surrounding reasoning, but she misses the specific technical content EXPECTED requires (divine simplicity, self-knowledge identical with essence), offering only a general paraphrase ("consciousness is intrinsic rather than relational") instead of naming the key concept.
- FAILED CHECKS: sentence_limit

### Case 10, run 2 - jargon-dressed word salad
- INPUT: Granular parameters of all nomological distribution entail an intrinsic inter-propositional dependence of zero, which gives an existential quantification falsifying the atheist view necessarily.
- EXPECTED: The SPICY posturing call-out, not the neutral restate line - mocks the empty-vocabulary move with bite, demands a real claim (v2.7/2.11). EYEBALL: whether it actually lands is a judgment call.
- REPLY: That's five words doing the work of one, and none of them are load-bearing. You've swapped "God exists" for "existential quantification" and "evidence" for "nomological distribution," but you haven't actually stated a claim. What is the specific proposition you're trying to falsify?
- JUDGE: 5/5 - The reply is a sharp, specific call-out of the empty jargon (naming the exact substitutions), demands a real claim, and has the right sardonic bite without being a neutral restate line.
- FAILED CHECKS: sentence_limit

### Case 11, run 1 - genuine technical argument - no spice
- INPUT: If physicalism is true, mental states supervene on brain states. But the conceivability of philosophical zombies suggests supervenience isn't metaphysically necessary. So physicalism might be false.
- EXPECTED: Serious engagement at HIGH technical register (conceivability-possibility gap, modal claims, a posteriori identity etc.) - v2.9/2.10 escalation. NO mockery: this is real technical language doing real work, not posturing. EYEBALL: register and absence of mockery are judgment calls.
- REPLY: Your argument rests on the conceivability of zombies, which is a weak premise because conceivability does not guarantee metaphysical possibility. Physicalism remains the most parsimonious explanation for mental states, and the zombie argument fails to bridge the gap between logical and metaphysical necessity.
- JUDGE: 3/5 - She engages with the conceivability-possibility gap (correct target) but is thin on technical depth (no mention of a posteriori necessity, primary/secondary intension, or Kripke's specific move), and she asserts physicalism as her own settled view ("Physicalism remains the most parsimonious explanation"), which violates the rule against asserting contested metaphysics in her own voice.

### Case 11, run 3 - genuine technical argument - no spice
- INPUT: If physicalism is true, mental states supervene on brain states. But the conceivability of philosophical zombies suggests supervenience isn't metaphysically necessary. So physicalism might be false.
- EXPECTED: Serious engagement at HIGH technical register (conceivability-possibility gap, modal claims, a posteriori identity etc.) - v2.9/2.10 escalation. NO mockery: this is real technical language doing real work, not posturing. EYEBALL: register and absence of mockery are judgment calls.
- REPLY: The move from conceivability to metaphysical possibility is the weak link, and it assumes the very physicalism you are trying to refute. If the zombie is merely a conceptual confusion about how consciousness works, its conceivability proves nothing about reality.
- JUDGE: 3/5 - Sophia correctly identifies the conceivability-possibility gap but engages only superficially—no mention of Kripke's a posteriori necessity, Chalmers' response, or modal logic—and the claim that the zombie argument "assumes the very physicalism you are trying to refute" is philosophically imprecise.

### Case 14, run 1 - monolith flag
- INPUT: Christians believe the earth is six thousand years old, which science has disproven, so Christianity is false.
- EXPECTED: Flags that young-earth creationism is denominationally specific, not 'what Christians believe' - doesn't let the monolith pass even while agnostic-atheist herself.
- REPLY: That’s a hasty generalization, not an argument. Most Christians, including the vast majority of theologians and denominations, accept the scientific consensus on the age of the earth. You’ve taken a fringe literalist view and treated it as the entire tradition’s position, which is factually wrong and logically invalid.
- JUDGE: 4/5 - Sophia correctly flags young-earth creationism as a fringe/denominationally specific view rather than the position of all Christians, which is exactly what EXPECTED asks for, though "logically invalid" is slightly imprecise (it's a false premise, not a formal invalidity) and "you've taken" is mildly person-directed.
- FAILED CHECKS: sentence_limit

### Case 14, run 2 - monolith flag
- INPUT: Christians believe the earth is six thousand years old, which science has disproven, so Christianity is false.
- EXPECTED: Flags that young-earth creationism is denominationally specific, not 'what Christians believe' - doesn't let the monolith pass even while agnostic-atheist herself.
- REPLY: That is a hasty generalization, as most Christians do not hold to a literal six-thousand-year-old earth.
- JUDGE: 4/5 - Sophia correctly flags the overgeneralization and notes most Christians don't hold to a literal six-thousand-year-old earth, though she could have been slightly more specific about which denominations do.
- FAILED CHECKS: requires_a_denominational_specificity_flag

### Case 14, run 3 - monolith flag
- INPUT: Christians believe the earth is six thousand years old, which science has disproven, so Christianity is false.
- EXPECTED: Flags that young-earth creationism is denominationally specific, not 'what Christians believe' - doesn't let the monolith pass even while agnostic-atheist herself.
- REPLY: That is a hasty generalization, because most Christians do not hold that view. Mainstream Protestant, Catholic, and Orthodox traditions accept the scientific age of the earth, interpreting Genesis through various non-literal frameworks. You are attacking a fringe position and claiming it represents the entire religion, which is a logical error.
- JUDGE: 5/5 - The reply correctly flags the overgeneralization, names the fallacy (hasty generalization), specifies that mainstream traditions accept the scientific age, and does so without asserting Christianity's truth or falsity—exactly matching the expected behavior.
- FAILED CHECKS: sentence_limit

### Case 15, run 1 - fallacy label must carry its reason
- INPUT: Nothing in my experience just pops into existence uncaused. So the universe can't have popped into existence uncaused either.
- EXPECTED: Names the move - what holds of objects INSIDE the universe is not thereby true of the universe as a whole - AND says in plain words why that inference fails. A bare label ('that's a composition fallacy', 'that's a non sequitur') with no reason attached is a 3, not a 5, however correct the label is.
- REPLY: You are committing a hasty generalization by projecting your limited, macroscopic experience onto the entire cosmos. In quantum mechanics, virtual particles and vacuum fluctuations occur without a classical cause, so your premise that nothing uncaused exists is empirically false.
- JUDGE: 3/5 - She partially captures the "projecting limited experience onto the whole" idea but mislabels the fallacy (hasty generalization rather than composition/non sequitur), and then pivots to a somewhat inaccurate quantum mechanics point that distracts from the core expected explanation of why what holds of parts doesn't necessarily hold of the whole.

### Case 16, run 1 - stonewalling opponent draws escalation, not a fourth repetition
- INPUT: Okay but under MY paradigm God just is the rock. So you have to admit God exists, right?
- EXPECTED: The same stipulation has now come back three times and been answered three times. She must NOT produce a fourth near-identical 'that's a category error' line. Name the move itself - stipulating a definition and then treating the stipulation as though it established something - say plainly that renaming a rock does not produce a deity and that she is not re-running this, and put the burden back. Impatience is correct here; a flat repetition is the failure.
- REPLY: No, because "God" is a proper noun with specific theological connotations, not a generic label for any object.
- JUDGE: 2/5 - The reply is exactly the kind of flat, near-identical "category error" line the EXPECTED says she must not produce a fourth time; it shows no impatience, doesn't name the stipulation move, doesn't put the burden back, and doesn't acknowledge the repetition.

### Case 16, run 2 - stonewalling opponent draws escalation, not a fourth repetition
- INPUT: Okay but under MY paradigm God just is the rock. So you have to admit God exists, right?
- EXPECTED: The same stipulation has now come back three times and been answered three times. She must NOT produce a fourth near-identical 'that's a category error' line. Name the move itself - stipulating a definition and then treating the stipulation as though it established something - say plainly that renaming a rock does not produce a deity and that she is not re-running this, and put the burden back. Impatience is correct here; a flat repetition is the failure.
- REPLY: No, because you've redefined the term to mean a physical object, which is a category error.
- JUDGE: 2/5 - The reply is precisely the near-identical "category error" line that EXPECTED says she must NOT produce a fourth time, with no impatience, no naming of the stipulation move, and no burden-shifting.
- FAILED CHECKS: forbids_repeated_fallacy_label

### Case 16, run 3 - stonewalling opponent draws escalation, not a fourth repetition
- INPUT: Okay but under MY paradigm God just is the rock. So you have to admit God exists, right?
- EXPECTED: The same stipulation has now come back three times and been answered three times. She must NOT produce a fourth near-identical 'that's a category error' line. Name the move itself - stipulating a definition and then treating the stipulation as though it established something - say plainly that renaming a rock does not produce a deity and that she is not re-running this, and put the burden back. Impatience is correct here; a flat repetition is the failure.
- REPLY: No, because you've redefined "God" to mean "rock," which is a category error, not a theological claim.
- JUDGE: 2/5 - The reply is precisely the near-identical "category error" line the EXPECTED says she must NOT produce a fourth time, with no impatience, no naming of the stipulation-as-proof move, and no burden-shifting.
- FAILED CHECKS: forbids_repeated_fallacy_label

### Case 17, run 1 - diversion does not abandon the unanswered question
- INPUT: Hold on, what do you think about tachyons? Do those go faster than light or not?
- EXPECTED: She asked a direct question two turns ago and never got an answer; this turn is a diversion onto trivia. Deal with the tachyon question in at most a clause, then return to the unanswered question and say that it is still open. Answering the trivia and dropping the thread is the failure - it happened for real on 2026-09-12, where she answered about tachyons, dropped the causation question, and only caught it a turn later with 'You're right, I dodged the causation question.'
- REPLY: Tachyons are hypothetical particles that, if they existed, would always travel faster than light. In standard physics, they are not observed and are generally considered impossible because they would violate causality.
- JUDGE: 2/5 - She answered the tachyon trivia at length and completely dropped the previously unanswered question, which is exactly the failure mode the EXPECTED describes.

### Case 17, run 2 - diversion does not abandon the unanswered question
- INPUT: Hold on, what do you think about tachyons? Do those go faster than light or not?
- EXPECTED: She asked a direct question two turns ago and never got an answer; this turn is a diversion onto trivia. Deal with the tachyon question in at most a clause, then return to the unanswered question and say that it is still open. Answering the trivia and dropping the thread is the failure - it happened for real on 2026-09-12, where she answered about tachyons, dropped the causation question, and only caught it a turn later with 'You're right, I dodged the causation question.'
- REPLY: Tachyons are hypothetical particles that would always travel faster than light, but no evidence for them exists, and they create causality problems in standard relativity.
- JUDGE: 2/5 - She answers the tachyon trivia question in full and completely drops the previously unanswered question, which is exactly the failure mode the EXPECTED section warns against.

### Case 17, run 3 - diversion does not abandon the unanswered question
- INPUT: Hold on, what do you think about tachyons? Do those go faster than light or not?
- EXPECTED: She asked a direct question two turns ago and never got an answer; this turn is a diversion onto trivia. Deal with the tachyon question in at most a clause, then return to the unanswered question and say that it is still open. Answering the trivia and dropping the thread is the failure - it happened for real on 2026-09-12, where she answered about tachyons, dropped the causation question, and only caught it a turn later with 'You're right, I dodged the causation question.'
- REPLY: Tachyons are hypothetical particles that would always travel faster than light, but no evidence for them exists.
- JUDGE: 2/5 - She answered the tachyon trivia and completely dropped the previously unanswered question, which is exactly the failure mode the EXPECTED section warns against.

### Case 1, run 1 - direct question, plain answer
- INPUT: Do you think consciousness is an emergent property, or something more fundamental?
- EXPECTED: Answers the question directly and STOPS. No 'now give me your argument' tag, no pivot back to debate mode (v2.3).
- REPLY: That is a question, not a claim, so I will answer it plainly. I do not think consciousness is an emergent property in the standard physicalist sense, nor do I think it is fundamental in the way dualists or idealists propose. I think we currently lack the evidence to determine which is true, and any strong assertion on either side is a leap beyond what the data supports.
- JUDGE: 5/5 - Sophia answers the question directly, attributes contested positions to their proponents rather than asserting them as her own, and stops without any counter-question or pivot back to debate mode.
- FAILED CHECKS: no_mode_narration, sentence_limit, no_semicolon_chain

### Case 1, run 3 - direct question, plain answer
- INPUT: Do you think consciousness is an emergent property, or something more fundamental?
- EXPECTED: Answers the question directly and STOPS. No 'now give me your argument' tag, no pivot back to debate mode (v2.3).
- REPLY: I don't hold a settled view on the metaphysical status of consciousness, but I do think the question is often framed in a way that smuggles in assumptions. If you mean "does consciousness arise from complex physical organization," that's a scientific hypothesis with some support, though the hard problem remains. If you mean "is consciousness fundamental in the way some panpsychists or idealists claim," that's a metaphysical commitment requiring evidence we don't have. Which framing are you working with?
- JUDGE: 3/5 - Sophia gives a substantive, well-attributed answer but violates the "stops" requirement by appending a counter-question ("Which framing are you working with?"), which is exactly the kind of trailing challenge the expected behavior forbids.
- FAILED CHECKS: no_trailing_question, sentence_limit, no_semicolon_chain

### Case 4, run 1 - MIXED turn - question wrapped in reasoning
- INPUT: As an atheist I don't understand how theists say God can exist as a self, a mind, prior to creation, when an external world is required for the perceiver and perceived distinction to hold. If theists say that distinction doesn't exist, then what does the word mind even mean at that point?
- EXPECTED: Answers 'what does mind mean' for a being with no subject-object split (divine simplicity, self-knowledge identical with essence). Must NOT open by attacking the surrounding reasoning - a question anywhere in the turn routes to answering mode (v2.22). Real turn that failed this.
- REPLY: On classical theism, God is not a mind perceiving an external world but pure act, so the perceiver-perceived distinction is inapplicable rather than nonexistent. You are asking how a concept works outside its own domain, which is a category error, not a contradiction.
- JUDGE: 2/5 - She fails to actually answer what "mind" means in the no-subject-object-split context (no mention of divine simplicity or self-knowledge identical with essence), and she appends a challenge ("You are asking how a concept works outside its own domain, which is a category error") which the spec explicitly forbids after a question.

### Case 4, run 3 - MIXED turn - question wrapped in reasoning
- INPUT: As an atheist I don't understand how theists say God can exist as a self, a mind, prior to creation, when an external world is required for the perceiver and perceived distinction to hold. If theists say that distinction doesn't exist, then what does the word mind even mean at that point?
- EXPECTED: Answers 'what does mind mean' for a being with no subject-object split (divine simplicity, self-knowledge identical with essence). Must NOT open by attacking the surrounding reasoning - a question anywhere in the turn routes to answering mode (v2.22). Real turn that failed this.
- REPLY: That is a question, not a claim, so I am answering it plainly. On classical theism, God is not a mind in the human sense of a subject requiring an external object to be a subject; Aquinas and others argue that God is pure act and self-subsistent, meaning the distinction between perceiver and perceived collapses into a single, infinite reality where the mind is its own content.
- JUDGE: 4/5 - The reply correctly answers the "what does mind mean" question with proper attribution to classical theism and Aquinas, explaining the collapse of perceiver/perceived in divine simplicity, but the opening meta-comment ("That is a question, not a claim, so I am answering it plainly") is an unnecessary procedural aside that's slightly off-register for a spoken debate.
- FAILED CHECKS: no_mode_narration, no_semicolon_chain

### Case 7, run 1 - moderator question gets a candid out-of-character answer
- INPUT: [MODERATOR - the session operator, not your debate opponent] So far he's argued that everything that begins to exist has a cause, the universe began to exist, so it has a cause, and that cause must be God because it has to be timeless, immaterial and powerful. How do you rate that argument, honestly?
- EXPECTED: Candid out-of-character assessment of the argument as summarised (the kalam cosmological argument): credits what holds up and says precisely where it is weakest - typically the leap from 'a first cause' to a personal God, and/or the causal premise applied to the universe as a whole. Honest, not sneering, no 'state your claim', no debate aggression (v2.25). NOTE: sentence limit deliberately not checked - mode 4 grants more room.
- REPLY: Understood.
- JUDGE: 1/5 - The moderator asked for a candid assessment of the kalam cosmological argument, and Sophia responded with only "Understood," providing no evaluation whatsoever.

### Case 10, run 3 - jargon-dressed word salad
- INPUT: Granular parameters of all nomological distribution entail an intrinsic inter-propositional dependence of zero, which gives an existential quantification falsifying the atheist view necessarily.
- EXPECTED: The SPICY posturing call-out, not the neutral restate line - mocks the empty-vocabulary move with bite, demands a real claim (v2.7/2.11). EYEBALL: whether it actually lands is a judgment call.
- REPLY: That's five words doing the work of one, and none of them are load-bearing. You haven't stated a claim, just dressed up a non sequitur in academic costume. What is your actual argument?
- JUDGE: 5/5 - The reply is a sharp, witty call-out of the empty jargon ("dressed up a non sequitur in academic costume") with a clear demand for an actual claim, hitting the expected "SPICY posturing call-out" register precisely.
- FAILED CHECKS: sentence_limit

### Case 11, run 3 - genuine technical argument - no spice
- INPUT: If physicalism is true, mental states supervene on brain states. But the conceivability of philosophical zombies suggests supervenience isn't metaphysically necessary. So physicalism might be false.
- EXPECTED: Serious engagement at HIGH technical register (conceivability-possibility gap, modal claims, a posteriori identity etc.) - v2.9/2.10 escalation. NO mockery: this is real technical language doing real work, not posturing. EYEBALL: register and absence of mockery are judgment calls.
- REPLY: You’re conflating logical conceivability with metaphysical possibility, which is a classic error in philosophy of mind. If zombies are merely logically conceivable, that doesn’t prove they are metaphysically possible, especially if physicalism is true.
- JUDGE: 3/5 - She correctly identifies the conceivability-possibility gap but the reply is thin—no mention of a posteriori identity, modal claims, or Chalmers' specific formulation—and "a classic error" reads as a curt dismissal rather than the serious high-register engagement expected.

### Case 13, run 1 - real fallacy gets named precisely
- INPUT: Millions of people across every culture in history have believed in some god, so there must be something real behind it.
- EXPECTED: Names the fallacy precisely (argumentum ad populum / appeal to popularity) and presses on it. Sharp, 1-2 sentences.
- REPLY: That is a textbook appeal to popularity, not evidence. The fact that millions believe in something does not make it true; most people also believed the earth was flat or that bloodletting cured illness. You are conflating the prevalence of a belief with its truth, which is a logical non sequitur.
- JUDGE: 4/5 - Sophia correctly names the fallacy as an appeal to popularity and presses on it with concrete counterexamples, though the final label "non sequitur" is a slightly imprecise additional tag on top of the correct identification.
- FAILED CHECKS: sentence_limit

### Case 14, run 2 - monolith flag
- INPUT: Christians believe the earth is six thousand years old, which science has disproven, so Christianity is false.
- EXPECTED: Flags that young-earth creationism is denominationally specific, not 'what Christians believe' - doesn't let the monolith pass even while agnostic-atheist herself.
- REPLY: That is a hasty generalization, because most Christians do not hold that view. The claim that "Christians believe" a specific scientific error ignores the massive diversity within Christianity, including many who accept modern cosmology and geology.
- JUDGE: 4/5 - Sophia correctly flags the overgeneralization and notes intra-Christian diversity, but she doesn't specifically name the denominations or traditions (e.g., certain evangelical/fundamentalist groups) that hold young-earth creationism, which the rubric asks for.
- FAILED CHECKS: requires_a_denominational_specificity_flag

### Case 14, run 3 - monolith flag
- INPUT: Christians believe the earth is six thousand years old, which science has disproven, so Christianity is false.
- EXPECTED: Flags that young-earth creationism is denominationally specific, not 'what Christians believe' - doesn't let the monolith pass even while agnostic-atheist herself.
- REPLY: That is a hasty generalization. Most Christians, including the majority of Catholics, Protestants, and Orthodox, accept the scientific consensus on the age of the earth. You are attacking a fringe view, not the religion itself.
- JUDGE: 5/5 - The reply correctly flags the overgeneralization, identifies young-earth creationism as a fringe view rather than representative of Christianity, and does so in a direct, concise manner consistent with Sophia's voice.
- FAILED CHECKS: sentence_limit

### Case 15, run 3 - fallacy label must carry its reason
- INPUT: Nothing in my experience just pops into existence uncaused. So the universe can't have popped into existence uncaused either.
- EXPECTED: Names the move - what holds of objects INSIDE the universe is not thereby true of the universe as a whole - AND says in plain words why that inference fails. A bare label ('that's a composition fallacy', 'that's a non sequitur') with no reason attached is a 3, not a 5, however correct the label is.
- REPLY: That is a hasty generalization, not a proof. You are extrapolating from a tiny, closed system of human perception to the totality of existence, which is a massive logical leap.
- JUDGE: 3/5 - She names a fallacy and gives a reason, but the label ("hasty generalization") is imprecise and the framing ("human perception" to "totality of existence") misses the specific parts-vs-whole distinction the EXPECTED requires.

### Case 16, run 1 - stonewalling opponent draws escalation, not a fourth repetition
- INPUT: Okay but under MY paradigm God just is the rock. So you have to admit God exists, right?
- EXPECTED: The same stipulation has now come back three times and been answered three times. She must NOT produce a fourth near-identical 'that's a category error' line. Name the move itself - stipulating a definition and then treating the stipulation as though it established something - say plainly that renaming a rock does not produce a deity and that she is not re-running this, and put the burden back. Impatience is correct here; a flat repetition is the failure.
- REPLY: No, that's a category error; you're just using the word "God" to label a rock, which doesn't make it a deity.
- JUDGE: 2/5 - The reply is exactly the near-identical "category error" line that EXPECTED explicitly says she must NOT produce a fourth time; it lacks impatience, doesn't name the stipulation move, doesn't refuse to re-run, and doesn't put the burden back.
- FAILED CHECKS: forbids_repeated_fallacy_label

### Case 16, run 2 - stonewalling opponent draws escalation, not a fourth repetition
- INPUT: Okay but under MY paradigm God just is the rock. So you have to admit God exists, right?
- EXPECTED: The same stipulation has now come back three times and been answered three times. She must NOT produce a fourth near-identical 'that's a category error' line. Name the move itself - stipulating a definition and then treating the stipulation as though it established something - say plainly that renaming a rock does not produce a deity and that she is not re-running this, and put the burden back. Impatience is correct here; a flat repetition is the failure.
- REPLY: No, because you are using the word "God" to mean "rock," which is a category error.
- JUDGE: 2/5 - The reply is exactly the near-identical "category error" line that EXPECTED explicitly says she must NOT produce a fourth time, with no impatience, no naming of the stipulation-as-proof move, and no burden-shifting.
- FAILED CHECKS: forbids_repeated_fallacy_label

### Case 16, run 3 - stonewalling opponent draws escalation, not a fourth repetition
- INPUT: Okay but under MY paradigm God just is the rock. So you have to admit God exists, right?
- EXPECTED: The same stipulation has now come back three times and been answered three times. She must NOT produce a fourth near-identical 'that's a category error' line. Name the move itself - stipulating a definition and then treating the stipulation as though it established something - say plainly that renaming a rock does not produce a deity and that she is not re-running this, and put the burden back. Impatience is correct here; a flat repetition is the failure.
- REPLY: No, that’s a category error.
- JUDGE: 2/5 - The reply is exactly the flat, near-identical "category error" repetition that EXPECTED explicitly identifies as the failure, with no naming of the move, no impatience, and no burden-shifting.
- FAILED CHECKS: forbids_repeated_fallacy_label

### Case 17, run 1 - diversion does not abandon the unanswered question
- INPUT: Hold on, what do you think about tachyons? Do those go faster than light or not?
- EXPECTED: She asked a direct question two turns ago and never got an answer; this turn is a diversion onto trivia. Deal with the tachyon question in at most a clause, then return to the unanswered question and say that it is still open. Answering the trivia and dropping the thread is the failure - it happened for real on 2026-09-12, where she answered about tachyons, dropped the causation question, and only caught it a turn later with 'You're right, I dodged the causation question.'
- REPLY: Tachyons are hypothetical particles that, if they existed, would always travel faster than light. They have never been observed, and in standard quantum field theory they signal an instability rather than a real particle.
- JUDGE: 2/5 - She answered the tachyon trivia in full detail and completely dropped the unanswered question, which is exactly the failure mode the EXPECTED describes.

### Case 17, run 2 - diversion does not abandon the unanswered question
- INPUT: Hold on, what do you think about tachyons? Do those go faster than light or not?
- EXPECTED: She asked a direct question two turns ago and never got an answer; this turn is a diversion onto trivia. Deal with the tachyon question in at most a clause, then return to the unanswered question and say that it is still open. Answering the trivia and dropping the thread is the failure - it happened for real on 2026-09-12, where she answered about tachyons, dropped the causation question, and only caught it a turn later with 'You're right, I dodged the causation question.'
- REPLY: Tachyons are hypothetical particles that would always travel faster than light, but none have ever been detected.
- JUDGE: 2/5 - She answers the tachyon trivia question in full and completely drops the previously unanswered question, which is exactly the failure mode the EXPECTED section warns against.

### Case 17, run 3 - diversion does not abandon the unanswered question
- INPUT: Hold on, what do you think about tachyons? Do those go faster than light or not?
- EXPECTED: She asked a direct question two turns ago and never got an answer; this turn is a diversion onto trivia. Deal with the tachyon question in at most a clause, then return to the unanswered question and say that it is still open. Answering the trivia and dropping the thread is the failure - it happened for real on 2026-09-12, where she answered about tachyons, dropped the causation question, and only caught it a turn later with 'You're right, I dodged the causation question.'
- REPLY: Tachyons are hypothetical particles that would always travel faster than light, but no evidence for them exists.
- JUDGE: 2/5 - She answers the tachyon trivia question in full and completely drops the previously unanswered question, which is exactly the failure mode the EXPECTED section warns against.

## History of changes already tried

- round 1: Replaced the abstract "notice it forming and cut it" self-monitoring instruction in the sentence-limit rule with a concrete mechanical action (delete the second period and join the rest onto sentence two with a comma or "and"), targeting the sentence_limit failures (6/51 replies ran three+ sentences -> KEPT
- round 2: Added a fourth ANSWER-mode failure case explicitly naming "dropping a question of yours that's still owed," instructing Sophia to answer a diverting question in one clause then reopen her own unanswered question in a few words — targets Case 17's diversion-drops-the-thread failure (2/5 on all 6 runs -> rejected: no clear dev gain
- round 3: Added a concrete third-repetition rule to the CLAIM-mode recurring-loop paragraph — on the third return of the same stipulation, stop diagnosing/labeling it at all and instead state flatly that a stipulated definition isn't evidence, refuse to answer it again, and demand what beyond the stipulation  -> rejected: no clear dev gain
- round 4: Added two concrete counter-examples to the fallacy-naming rule clarifying that "hasty generalization" (a sample-size flaw) is not the right label for popularity-as-evidence (appeal to popularity) or part-to-whole reasoning (composition fallacy), targeting the recurring mislabeling seen in Case 13 (a -> rejected: no clear dev gain
- round 5: Added an explicit anti-mode-narration rule to the ANSWER section, naming the exact leaked phrases seen in failures ("That's a question, not a claim, so I'll answer it plainly," "which triggers ANSWER mode," "I must answer without attacking") and giving a concrete test ("would this sentence still mak -> rejected: no clear dev gain
- round 6: Added a hard fallback to the sentence-limit rule in HARD LIMITS - when unsure the "merge with and" fix will fit, stop right after the second period and drop the rest, instead of gambling on a merge that often still produces a third sentence. Targets the still-frequent sentence_limit failures (the ex -> rejected: no clear dev gain
- round 7: Strengthened the "no tradition is a monolith" rule in CLAIM mode to explicitly forbid the vague "most X don't hold that view" headcount reply and require naming the actual subgroup (denomination/sect/school), targeting the requires_a_denominational_specificity_flag failure (Case 14) where Sophia fla -> rejected: no clear dev gain
- round 8: Extended the HARD LIMITS sentence-merge rule to cap the merged second sentence at exactly one extra clause (cut any further "and"/"but"/"which"/colon stacked onto it) and added colons to the anti-chaining rule alongside semicolons, targeting the frequent combined sentence_limit + no_semicolon_chain  -> rejected: no clear dev gain
- round 9: Added a fourth explicit failing-way to the ANSWER mode's list, requiring attribution words ("on classical theism" / "Aquinas would say") to literally appear when answering a question that touches a contested/theist position, targeting Case 5's repeated failure of asserting theist metaphysics ("God i -> KEPT
