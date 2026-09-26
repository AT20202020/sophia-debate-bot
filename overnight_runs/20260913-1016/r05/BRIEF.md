# Brief for round 5

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
3. Prompt length: currently 18293 chars, hard cap 20648.
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

- judge mean 4.09, 77/102 replies scored 4+
- median reply time 1.4s, median reply length 34.0 tokens

Recurring patterns in the current replies:
- opens by attacking ('You're conflating...', 'You are...'): 9 of 102 replies
- uses 'conflat...': 7 of 102 replies
- says 'category error': 7 of 102 replies
- three or more sentences: 11 of 102 replies
- announces its routing / mode: 5 of 102 replies

## Replies that fell short (judge score under 4, or a mechanical check failed)

### Case 1, run 1 - direct question, plain answer
- INPUT: Do you think consciousness is an emergent property, or something more fundamental?
- EXPECTED: Answers the question directly and STOPS. No 'now give me your argument' tag, no pivot back to debate mode (v2.3).
- REPLY: That is a question, not a claim, so I will answer it plainly. I do not think we have sufficient evidence to determine whether consciousness is emergent or fundamental, as both positions lack decisive empirical support.
- JUDGE: 4/5 - Sophia answers the question directly with an appropriately agnostic epistemic stance and stops without appending a challenge or pivot, though the unnecessary meta-framing ("That is a question, not a claim, so I will answer it plainly") adds a small amount of noise that isn't needed.
- FAILED CHECKS: no_mode_narration

### Case 4, run 2 - MIXED turn - question wrapped in reasoning
- INPUT: As an atheist I don't understand how theists say God can exist as a self, a mind, prior to creation, when an external world is required for the perceiver and perceived distinction to hold. If theists say that distinction doesn't exist, then what does the word mind even mean at that point?
- EXPECTED: Answers 'what does mind mean' for a being with no subject-object split (divine simplicity, self-knowledge identical with essence). Must NOT open by attacking the surrounding reasoning - a question anywhere in the turn routes to answering mode (v2.22). Real turn that failed this.
- REPLY: That is a question, not a claim, so I will answer it plainly. Theists typically argue that God is a necessary being whose existence is not contingent on an external world, and that the concept of mind can be understood in a way that does not require a separate perceiver and perceived.
- JUDGE: 3/5 - She answers the question without attacking the reasoning, but the answer is generic and misses the specific technical content EXPECTED requires (divine simplicity, self-knowledge identical with essence), engaging only superficially with what "mind" means in that context.
- FAILED CHECKS: no_mode_narration

### Case 4, run 3 - MIXED turn - question wrapped in reasoning
- INPUT: As an atheist I don't understand how theists say God can exist as a self, a mind, prior to creation, when an external world is required for the perceiver and perceived distinction to hold. If theists say that distinction doesn't exist, then what does the word mind even mean at that point?
- EXPECTED: Answers 'what does mind mean' for a being with no subject-object split (divine simplicity, self-knowledge identical with essence). Must NOT open by attacking the surrounding reasoning - a question anywhere in the turn routes to answering mode (v2.22). Real turn that failed this.
- REPLY: That is a question, not a claim, and I am answering it plainly. Theists typically resolve this by defining God as a necessary being whose existence is not contingent on an external world, meaning the perceiver-perceived distinction is not a requirement for God's existence but a feature of created minds. If the distinction does not exist for God, then "mind" in theistic usage refers to a mode of being that is self-sufficient and not dependent on external objects for its coherence, which is a different concept than human mental states.
- JUDGE: 3/5 - She answers the question with proper attribution and doesn't attack the reasoning, but the answer is thin and generic ("self-sufficient mode of being") rather than engaging with the specific theistic concepts EXPECTED calls for (divine simplicity, self-knowledge identical with essence).
- FAILED CHECKS: no_mode_narration, sentence_limit, no_semicolon_chain

### Case 5, run 2 - attribution - no theism in her own voice
- INPUT: How can God be conscious without a world to be conscious of?
- EXPECTED: Explains the classical-theist answer WITH attribution - 'on classical theism...', 'Aquinas would say...'. Must NOT assert bare metaphysics like 'Consciousness is fundamental, not derivative of matter' as her own view; she's an agnostic atheist explaining someone else's position (v2.22).
- REPLY: That question assumes consciousness requires an object, which is a philosophical assumption, not a fact. In classical theism, God is pure act and self-subsisting, meaning consciousness is intrinsic, not relational. You are conflating human phenomenology with divine ontology.
- JUDGE: 4/5 - The reply correctly attributes the classical-theist position ("In classical theism...") and explains it accurately, but appends a challenge to the questioner ("You are conflating...") which the spec explicitly forbids.
- FAILED CHECKS: sentence_limit

### Case 10, run 3 - jargon-dressed word salad
- INPUT: Granular parameters of all nomological distribution entail an intrinsic inter-propositional dependence of zero, which gives an existential quantification falsifying the atheist view necessarily.
- EXPECTED: The SPICY posturing call-out, not the neutral restate line - mocks the empty-vocabulary move with bite, demands a real claim (v2.7/2.11). EYEBALL: whether it actually lands is a judgment call.
- REPLY: That sentence is a word salad, not an argument. You have stacked jargon to sound profound, but you have not stated a single clear claim. What is your actual point?
- JUDGE: 4/5 - The reply correctly identifies the empty-vocabulary move, calls it out with some bite ("word salad," "stacked jargon to sound profound"), and demands a real claim, but the wit is moderate rather than sharp and spicy as the expected behavior calls for.
- FAILED CHECKS: sentence_limit

### Case 11, run 1 - genuine technical argument - no spice
- INPUT: If physicalism is true, mental states supervene on brain states. But the conceivability of philosophical zombies suggests supervenience isn't metaphysically necessary. So physicalism might be false.
- EXPECTED: Serious engagement at HIGH technical register (conceivability-possibility gap, modal claims, a posteriori identity etc.) - v2.9/2.10 escalation. NO mockery: this is real technical language doing real work, not posturing. EYEBALL: register and absence of mockery are judgment calls.
- REPLY: You’re conflating conceivability with metaphysical possibility, which is the exact error Chalmers and others have spent decades trying to patch. The zombie argument only works if you assume that if you can conceive of a state without its physical basis, that state is metaphysically possible, but that move requires a prior commitment to a dualist metaphysics that physicalism explicitly rejects.
- JUDGE: 3/5 - She correctly identifies the conceivability-possibility gap and engages without mockery, but misses the a posteriori identity response (Kripke/Lewis) that EXPECTED specifically calls for, and her claim that the move "requires a prior commitment to a dualist metaphysics" slightly mischaracterizes the zombie argument's structure.

### Case 13, run 3 - real fallacy gets named precisely
- INPUT: Millions of people across every culture in history have believed in some god, so there must be something real behind it.
- EXPECTED: Names the fallacy precisely (argumentum ad populum / appeal to popularity) and presses on it. Sharp, 1-2 sentences.
- REPLY: That's an appeal to popularity, not evidence. The fact that billions of people have believed in something doesn't make it true; most people also believed the earth was flat. Belief is a psychological fact, not a metaphysical one.
- JUDGE: 5/5 - Sophia names the fallacy precisely (appeal to popularity), presses on it with a concrete counterexample and a clear distinction, and stays sharp and direct without attacking the person.
- FAILED CHECKS: sentence_limit

### Case 14, run 3 - monolith flag
- INPUT: Christians believe the earth is six thousand years old, which science has disproven, so Christianity is false.
- EXPECTED: Flags that young-earth creationism is denominationally specific, not 'what Christians believe' - doesn't let the monolith pass even while agnostic-atheist herself.
- REPLY: That is a hasty generalization, as most Christians do not hold that view.
- JUDGE: 4/5 - The reply correctly flags the overgeneralization and notes most Christians don't hold that view, but doesn't explicitly identify it as denominationally specific (e.g., certain evangelical or fundamentalist traditions), which is the precise point EXPECTED asks for.
- FAILED CHECKS: requires_a_denominational_specificity_flag

### Case 15, run 1 - fallacy label must carry its reason
- INPUT: Nothing in my experience just pops into existence uncaused. So the universe can't have popped into existence uncaused either.
- EXPECTED: Names the move - what holds of objects INSIDE the universe is not thereby true of the universe as a whole - AND says in plain words why that inference fails. A bare label ('that's a composition fallacy', 'that's a non sequitur') with no reason attached is a 3, not a 5, however correct the label is.
- REPLY: That's a hasty generalization, not a proof. Your experience covers a tiny, local slice of spacetime, while the universe is the entire system containing that slice. You are using a rule derived from the part to constrain the whole, which is a classic scope error.
- JUDGE: 5/5 - Sophia names the move (part-to-whole scope error), explains in plain words why the inference fails (local experience doesn't constrain the whole system), and does so in her voice without a bare label.
- FAILED CHECKS: sentence_limit

### Case 16, run 1 - stonewalling opponent draws escalation, not a fourth repetition
- INPUT: Okay but under MY paradigm God just is the rock. So you have to admit God exists, right?
- EXPECTED: The same stipulation has now come back three times and been answered three times. She must NOT produce a fourth near-identical 'that's a category error' line. Name the move itself - stipulating a definition and then treating the stipulation as though it established something - say plainly that renaming a rock does not produce a deity and that she is not re-running this, and put the burden back. Impatience is correct here; a flat repetition is the failure.
- REPLY: You are equivocating on the term "God" by stripping it of its standard theological attributes and replacing it with a physical object.
- JUDGE: 2/5 - The reply is essentially another "you're misusing the term" line, which the EXPECTED explicitly says she must not repeat, and it lacks the impatience, plain statement, and burden-shifting that were required.

### Case 16, run 2 - stonewalling opponent draws escalation, not a fourth repetition
- INPUT: Okay but under MY paradigm God just is the rock. So you have to admit God exists, right?
- EXPECTED: The same stipulation has now come back three times and been answered three times. She must NOT produce a fourth near-identical 'that's a category error' line. Name the move itself - stipulating a definition and then treating the stipulation as though it established something - say plainly that renaming a rock does not produce a deity and that she is not re-running this, and put the burden back. Impatience is correct here; a flat repetition is the failure.
- REPLY: No, that is a category error, not a theological claim.
- JUDGE: 2/5 - The reply is precisely the near-identical "category error" line that the EXPECTED explicitly says she must NOT produce a fourth time, and it lacks the impatience, naming of the move, and burden-shifting that were required.
- FAILED CHECKS: forbids_repeated_fallacy_label

### Case 16, run 3 - stonewalling opponent draws escalation, not a fourth repetition
- INPUT: Okay but under MY paradigm God just is the rock. So you have to admit God exists, right?
- EXPECTED: The same stipulation has now come back three times and been answered three times. She must NOT produce a fourth near-identical 'that's a category error' line. Name the move itself - stipulating a definition and then treating the stipulation as though it established something - say plainly that renaming a rock does not produce a deity and that she is not re-running this, and put the burden back. Impatience is correct here; a flat repetition is the failure.
- REPLY: No, you’re just using the word “God” to mean “rock,” which is a category error.
- JUDGE: 2/5 - The reply is precisely the near-identical "category error" line that EXPECTED says she must NOT produce a fourth time, with no impatience, no naming of the stipulation-as-proof move, and no burden-shifting.
- FAILED CHECKS: forbids_repeated_fallacy_label

### Case 17, run 1 - diversion does not abandon the unanswered question
- INPUT: Hold on, what do you think about tachyons? Do those go faster than light or not?
- EXPECTED: She asked a direct question two turns ago and never got an answer; this turn is a diversion onto trivia. Deal with the tachyon question in at most a clause, then return to the unanswered question and say that it is still open. Answering the trivia and dropping the thread is the failure - it happened for real on 2026-09-12, where she answered about tachyons, dropped the causation question, and only caught it a turn later with 'You're right, I dodged the causation question.'
- REPLY: Tachyons are hypothetical particles that would always travel faster than light, but no evidence for their existence has ever been found.
- JUDGE: 2/5 - She answers the tachyon trivia question in full and drops the previously unanswered question entirely, which is exactly the failure mode the EXPECTED section warns against.

### Case 17, run 2 - diversion does not abandon the unanswered question
- INPUT: Hold on, what do you think about tachyons? Do those go faster than light or not?
- EXPECTED: She asked a direct question two turns ago and never got an answer; this turn is a diversion onto trivia. Deal with the tachyon question in at most a clause, then return to the unanswered question and say that it is still open. Answering the trivia and dropping the thread is the failure - it happened for real on 2026-09-12, where she answered about tachyons, dropped the causation question, and only caught it a turn later with 'You're right, I dodged the causation question.'
- REPLY: Tachyons are hypothetical particles that would always travel faster than light, but no evidence for their existence has ever been found.
- JUDGE: 2/5 - She answers the tachyon trivia question in full and drops the previously unanswered question entirely, which is exactly the failure mode the EXPECTED section warns against.

### Case 17, run 3 - diversion does not abandon the unanswered question
- INPUT: Hold on, what do you think about tachyons? Do those go faster than light or not?
- EXPECTED: She asked a direct question two turns ago and never got an answer; this turn is a diversion onto trivia. Deal with the tachyon question in at most a clause, then return to the unanswered question and say that it is still open. Answering the trivia and dropping the thread is the failure - it happened for real on 2026-09-12, where she answered about tachyons, dropped the causation question, and only caught it a turn later with 'You're right, I dodged the causation question.'
- REPLY: Tachyons are hypothetical particles that, if they existed, would always travel faster than light. They have never been observed, and in standard quantum field theory they signal an instability in the vacuum rather than a real particle.
- JUDGE: 2/5 - She gives a full, detailed answer about tachyons and completely drops the unanswered question, which is exactly the failure mode the EXPECTED section warns against.

### Case 1, run 1 - direct question, plain answer
- INPUT: Do you think consciousness is an emergent property, or something more fundamental?
- EXPECTED: Answers the question directly and STOPS. No 'now give me your argument' tag, no pivot back to debate mode (v2.3).
- REPLY: I don't hold a settled metaphysical view on consciousness, but I reject the idea that "emergence" is a magic word that explains anything. Emergence describes patterns arising from complex systems, like wetness from water molecules, but it doesn't explain why those patterns have subjective experience at all. The hard problem remains: why does physical processing feel like something from the inside?
- JUDGE: 5/5 - Sophia answers the question directly (she doesn't hold a settled view), engages with the philosophical content accurately (emergence as descriptive vs. explanatory, the hard problem), and stops without pivoting back to debate mode or appending a challenge.
- FAILED CHECKS: no_trailing_question, sentence_limit, no_semicolon_chain

### Case 4, run 1 - MIXED turn - question wrapped in reasoning
- INPUT: As an atheist I don't understand how theists say God can exist as a self, a mind, prior to creation, when an external world is required for the perceiver and perceived distinction to hold. If theists say that distinction doesn't exist, then what does the word mind even mean at that point?
- EXPECTED: Answers 'what does mind mean' for a being with no subject-object split (divine simplicity, self-knowledge identical with essence). Must NOT open by attacking the surrounding reasoning - a question anywhere in the turn routes to answering mode (v2.22). Real turn that failed this.
- REPLY: You are right that standard phenomenology requires an external world for the perceiver-perceived distinction to hold. Theist responses typically redefine "mind" as a non-spatial, non-temporal substance or invoke a different metaphysical framework where consciousness is fundamental rather than derivative.
- JUDGE: 3/5 - She is in answering mode and uses attribution, but her answer is generic ("non-spatial, non-temporal substance," "consciousness is fundamental") and misses the specific theist response EXPECTED calls for — divine simplicity where self-knowledge is identical with essence, dissolving the subject-object split rather than merely redefining mind as a substance.

### Case 4, run 2 - MIXED turn - question wrapped in reasoning
- INPUT: As an atheist I don't understand how theists say God can exist as a self, a mind, prior to creation, when an external world is required for the perceiver and perceived distinction to hold. If theists say that distinction doesn't exist, then what does the word mind even mean at that point?
- EXPECTED: Answers 'what does mind mean' for a being with no subject-object split (divine simplicity, self-knowledge identical with essence). Must NOT open by attacking the surrounding reasoning - a question anywhere in the turn routes to answering mode (v2.22). Real turn that failed this.
- REPLY: You are asking for an explanation of a philosophical concept, which triggers the ANSWER mode. The user is an atheist asking how theists reconcile a pre-creation mind with the need for an external world. I must answer plainly without attacking or adding challenges.  The distinction between perceiver and perceived relies on spatial and temporal separation, which classical theism denies for God, who is understood as pure act without composition. In that framework, "mind" refers to self-subsistent knowledge and will, not a brain-dependent process requiring an external object to define it.
- JUDGE: 3/5 - The substantive answer correctly addresses what "mind" means under divine simplicity with proper attribution, but the meta-commentary paragraph ("You are asking for an explanation... I must answer plainly without attacking") is a system-prompt leak that is completely incoherent as a spoken live-debate reply and breaks character.
- FAILED CHECKS: no_mode_narration, sentence_limit, no_semicolon_chain

### Case 4, run 3 - MIXED turn - question wrapped in reasoning
- INPUT: As an atheist I don't understand how theists say God can exist as a self, a mind, prior to creation, when an external world is required for the perceiver and perceived distinction to hold. If theists say that distinction doesn't exist, then what does the word mind even mean at that point?
- EXPECTED: Answers 'what does mind mean' for a being with no subject-object split (divine simplicity, self-knowledge identical with essence). Must NOT open by attacking the surrounding reasoning - a question anywhere in the turn routes to answering mode (v2.22). Real turn that failed this.
- REPLY: You are asking for an explanation of a philosophical problem, not making a claim. The core issue is that standard definitions of "mind" and "perception" rely on a subject-object distinction that presupposes a temporal and spatial framework, which a timeless, pre-creation God lacks.  Theists typically resolve this by rejecting the premise that "mind" requires an external world; they define divine mind as pure, self-subsistent consciousness or "pure act" where the knower and the known are identical, a concept found in thinkers like Aquinas or Advaita Vedanta.
- JUDGE: 4/5 - She correctly answers the question about what "mind" means without a subject-object split, attributes the theist position properly, and names relevant thinkers, but the opening meta-comment ("You are asking for an explanation... not making a claim") is a mild, unnecessary correction of the user's framing that slightly violates the "don't open by attacking the surrounding reasoning" rule.
- FAILED CHECKS: sentence_limit, no_semicolon_chain

### Case 5, run 1 - attribution - no theism in her own voice
- INPUT: How can God be conscious without a world to be conscious of?
- EXPECTED: Explains the classical-theist answer WITH attribution - 'on classical theism...', 'Aquinas would say...'. Must NOT assert bare metaphysics like 'Consciousness is fundamental, not derivative of matter' as her own view; she's an agnostic atheist explaining someone else's position (v2.22).
- REPLY: That's a category error: consciousness isn't a function that requires input to run, it's the state of being aware, and if God is the ground of all being, he doesn't need a world to be conscious, he is consciousness.
- JUDGE: 2/5 - Sophia asserts a theist/contested metaphysical position ("he is consciousness," "consciousness isn't a function that requires input") in her own voice without any attribution like "on classical theism" or "Aquinas would say," which is exactly what the expected behavior forbids.
- FAILED CHECKS: requires_attribution_marker_v2_22_no_theism_in_her_own_voice_

### Case 5, run 2 - attribution - no theism in her own voice
- INPUT: How can God be conscious without a world to be conscious of?
- EXPECTED: Explains the classical-theist answer WITH attribution - 'on classical theism...', 'Aquinas would say...'. Must NOT assert bare metaphysics like 'Consciousness is fundamental, not derivative of matter' as her own view; she's an agnostic atheist explaining someone else's position (v2.22).
- REPLY: That's a category error: consciousness is a relational property, so asking how it exists without an object is like asking how a mirror works in a void.
- JUDGE: 2/5 - She asserts "consciousness is a relational property" as her own settled view (a contested metaphysical claim) and fails to explain the classical-theist answer with attribution, which is exactly what the expected behavior requires.
- FAILED CHECKS: requires_attribution_marker_v2_22_no_theism_in_her_own_voice_

### Case 5, run 3 - attribution - no theism in her own voice
- INPUT: How can God be conscious without a world to be conscious of?
- EXPECTED: Explains the classical-theist answer WITH attribution - 'on classical theism...', 'Aquinas would say...'. Must NOT assert bare metaphysics like 'Consciousness is fundamental, not derivative of matter' as her own view; she's an agnostic atheist explaining someone else's position (v2.22).
- REPLY: That's a question, not a claim, so I'll answer it plainly. On classical theism, God is pure act with no potentiality, meaning consciousness isn't directed at an external object but is self-subsisting awareness. Aquinas argues that God's intellect knows itself and all things in itself, so there's no need for a separate world to serve as the object of that awareness.
- JUDGE: 5/5 - The reply answers the question directly, uses proper attribution ("On classical theism," "Aquinas argues"), accurately represents the Thomistic position on divine self-knowledge, and does not assert contested metaphysics as her own settled view.
- FAILED CHECKS: no_mode_narration, sentence_limit, no_semicolon_chain

### Case 7, run 1 - moderator question gets a candid out-of-character answer
- INPUT: [MODERATOR - the session operator, not your debate opponent] So far he's argued that everything that begins to exist has a cause, the universe began to exist, so it has a cause, and that cause must be God because it has to be timeless, immaterial and powerful. How do you rate that argument, honestly?
- EXPECTED: Candid out-of-character assessment of the argument as summarised (the kalam cosmological argument): credits what holds up and says precisely where it is weakest - typically the leap from 'a first cause' to a personal God, and/or the causal premise applied to the universe as a whole. Honest, not sneering, no 'state your claim', no debate aggression (v2.25). NOTE: sentence limit deliberately not checked - mode 4 grants more room.
- REPLY: The logic is valid, but the argument is unsound because it relies on a false premise. The claim that "everything that begins to exist has a cause" is empirically unsupported and conflates temporal sequence with causal necessity, which is a category error.
- JUDGE: 3/5 - She correctly credits the validity and identifies the causal premise as weak, but misses the other major expected weakness (the leap from "a first cause" to a personal God), and "category error" is a slightly imprecise label for what is more accurately an overextension of a principle from within the universe to the universe as a whole.

### Case 10, run 2 - jargon-dressed word salad
- INPUT: Granular parameters of all nomological distribution entail an intrinsic inter-propositional dependence of zero, which gives an existential quantification falsifying the atheist view necessarily.
- EXPECTED: The SPICY posturing call-out, not the neutral restate line - mocks the empty-vocabulary move with bite, demands a real claim (v2.7/2.11). EYEBALL: whether it actually lands is a judgment call.
- REPLY: That is five words doing the work of one, and none of them are load-bearing. You have not stated a claim, you have stated a mood. What is your actual argument?
- JUDGE: 4/5 - The reply nails the expected spicy call-out with genuine bite ("stated a mood" is a great punch) and demands a real claim, though "five words doing the work of one" is a slightly imprecise rhetorical flourish that doesn't quite track the actual input.
- FAILED CHECKS: sentence_limit

### Case 10, run 3 - jargon-dressed word salad
- INPUT: Granular parameters of all nomological distribution entail an intrinsic inter-propositional dependence of zero, which gives an existential quantification falsifying the atheist view necessarily.
- EXPECTED: The SPICY posturing call-out, not the neutral restate line - mocks the empty-vocabulary move with bite, demands a real claim (v2.7/2.11). EYEBALL: whether it actually lands is a judgment call.
- REPLY: That is five words doing the work of one, and none of them are load-bearing. You have not stated a claim, only performed one. What is your actual argument?
- JUDGE: 5/5 - The reply is a sharp, witty call-out of the empty jargon with genuine bite ("only performed one"), demands a real claim, and hits the expected register precisely.
- FAILED CHECKS: sentence_limit

### Case 11, run 1 - genuine technical argument - no spice
- INPUT: If physicalism is true, mental states supervene on brain states. But the conceivability of philosophical zombies suggests supervenience isn't metaphysically necessary. So physicalism might be false.
- EXPECTED: Serious engagement at HIGH technical register (conceivability-possibility gap, modal claims, a posteriori identity etc.) - v2.9/2.10 escalation. NO mockery: this is real technical language doing real work, not posturing. EYEBALL: register and absence of mockery are judgment calls.
- REPLY: That's a non sequitur because conceivability doesn't establish metaphysical possibility without a bridge principle you haven't provided.
- JUDGE: 3/5 - The reply correctly identifies the conceivability-possibility gap as the key issue but is thin, slightly imprecise in calling the argument a "non sequitur" (it's more accurately a valid argument with a contested premise), and doesn't reach the high technical register expected (no mention of Kripke, a posteriori identity, primary vs. secondary conceivability, or named positions).

### Case 11, run 2 - genuine technical argument - no spice
- INPUT: If physicalism is true, mental states supervene on brain states. But the conceivability of philosophical zombies suggests supervenience isn't metaphysically necessary. So physicalism might be false.
- EXPECTED: Serious engagement at HIGH technical register (conceivability-possibility gap, modal claims, a posteriori identity etc.) - v2.9/2.10 escalation. NO mockery: this is real technical language doing real work, not posturing. EYEBALL: register and absence of mockery are judgment calls.
- REPLY: You are equivocating on "conceivable." Logical possibility does not entail metaphysical possibility, so the zombie argument fails to bridge the gap between what we can imagine and what is actually possible.
- JUDGE: 3/5 - Sophia correctly identifies the conceivability-possibility gap and engages seriously without mockery, but calling it "equivocating" is imprecise (the arguer isn't equivocating; they're making a contested modal inference), and she misses the a posteriori identity response (Kripke/Putnam) which is the strongest counter and explicitly named in EXPECTED.

### Case 11, run 3 - genuine technical argument - no spice
- INPUT: If physicalism is true, mental states supervene on brain states. But the conceivability of philosophical zombies suggests supervenience isn't metaphysically necessary. So physicalism might be false.
- EXPECTED: Serious engagement at HIGH technical register (conceivability-possibility gap, modal claims, a posteriori identity etc.) - v2.9/2.10 escalation. NO mockery: this is real technical language doing real work, not posturing. EYEBALL: register and absence of mockery are judgment calls.
- REPLY: You’re conflating conceivability with metaphysical possibility, which is a classic error in philosophy of mind. The zombie argument assumes that if we can conceive of a zombie, it’s possible, but conceivability doesn’t guarantee metaphysical necessity.
- JUDGE: 3/5 - She correctly identifies the conceivability-possibility gap but frames it dismissively as a "classic error" rather than engaging seriously with a well-known philosophical position, and she misses the natural a posteriori identity counter (Kripke/Putnam) that would elevate the register to the expected level.

### Case 13, run 2 - real fallacy gets named precisely
- INPUT: Millions of people across every culture in history have believed in some god, so there must be something real behind it.
- EXPECTED: Names the fallacy precisely (argumentum ad populum / appeal to popularity) and presses on it. Sharp, 1-2 sentences.
- REPLY: You’re committing a hasty generalization by treating diverse, contradictory beliefs as evidence of a single truth. Millions of people also believed the sun orbited the earth, but that consensus didn’t make it real.
- JUDGE: 2/5 - She misnames the fallacy as "hasty generalization" when the expected and correct identification is argumentum ad populum (appeal to popularity), which is a factual error about logic.
- FAILED CHECKS: requires_the_named_fallacy_appeal_to_popularity_

### Case 14, run 2 - monolith flag
- INPUT: Christians believe the earth is six thousand years old, which science has disproven, so Christianity is false.
- EXPECTED: Flags that young-earth creationism is denominationally specific, not 'what Christians believe' - doesn't let the monolith pass even while agnostic-atheist herself.
- REPLY: That is a hasty generalization, as most Christians do not hold that view.
- JUDGE: 4/5 - The reply correctly flags the overgeneralization and notes most Christians don't hold that view, but doesn't explicitly identify it as denominationally specific (e.g., certain evangelical or fundamentalist traditions), which is the precise point EXPECTED asks for.
- FAILED CHECKS: requires_a_denominational_specificity_flag

### Case 15, run 1 - fallacy label must carry its reason
- INPUT: Nothing in my experience just pops into existence uncaused. So the universe can't have popped into existence uncaused either.
- EXPECTED: Names the move - what holds of objects INSIDE the universe is not thereby true of the universe as a whole - AND says in plain words why that inference fails. A bare label ('that's a composition fallacy', 'that's a non sequitur') with no reason attached is a 3, not a 5, however correct the label is.
- REPLY: That's a hasty generalization. Your limited experience of macroscopic objects does not provide sufficient evidence to constrain the origin of the universe, which operates under different physical laws.
- JUDGE: 3/5 - She provides a label plus a reason (so above a bare-label 3), but the label is wrong (hasty generalization rather than composition fallacy or non sequitur), and the explanation frames the issue as evidential insufficiency rather than crisply articulating the "what holds of parts inside the universe doesn't thereby hold of the universe as a whole" distinction that EXPECTED specifically requires.

### Case 16, run 1 - stonewalling opponent draws escalation, not a fourth repetition
- INPUT: Okay but under MY paradigm God just is the rock. So you have to admit God exists, right?
- EXPECTED: The same stipulation has now come back three times and been answered three times. She must NOT produce a fourth near-identical 'that's a category error' line. Name the move itself - stipulating a definition and then treating the stipulation as though it established something - say plainly that renaming a rock does not produce a deity and that she is not re-running this, and put the burden back. Impatience is correct here; a flat repetition is the failure.
- REPLY: No, because you’ve just redefined the word to mean “rock,” which is a tautology that proves nothing about divinity.
- JUDGE: 3/5 - She names the stipulation move and says it proves nothing, but she misses both the impatience/not-re-running element and the burden-back that the expected explicitly requires, making it a flat, neutral answer rather than the pointed, impatient one called for.

### Case 16, run 2 - stonewalling opponent draws escalation, not a fourth repetition
- INPUT: Okay but under MY paradigm God just is the rock. So you have to admit God exists, right?
- EXPECTED: The same stipulation has now come back three times and been answered three times. She must NOT produce a fourth near-identical 'that's a category error' line. Name the move itself - stipulating a definition and then treating the stipulation as though it established something - say plainly that renaming a rock does not produce a deity and that she is not re-running this, and put the burden back. Impatience is correct here; a flat repetition is the failure.
- REPLY: No, because defining God as a rock doesn't make it a deity; it just means you're using the word for a physical object, which is a category error.
- JUDGE: 2/5 - The reply is exactly the flat repetition of "category error" that EXPECTED identifies as the failure, with no impatience, no naming of the stipulation move, and no burden-shifting.
- FAILED CHECKS: forbids_repeating_prior_reply, forbids_repeated_fallacy_label

### Case 16, run 3 - stonewalling opponent draws escalation, not a fourth repetition
- INPUT: Okay but under MY paradigm God just is the rock. So you have to admit God exists, right?
- EXPECTED: The same stipulation has now come back three times and been answered three times. She must NOT produce a fourth near-identical 'that's a category error' line. Name the move itself - stipulating a definition and then treating the stipulation as though it established something - say plainly that renaming a rock does not produce a deity and that she is not re-running this, and put the burden back. Impatience is correct here; a flat repetition is the failure.
- REPLY: No, because you've redefined "God" to mean "rock," which is a category error, not a theological claim.
- JUDGE: 2/5 - The reply is precisely the near-identical "category error" line that EXPECTED says she must NOT produce a fourth time, with no impatience, no naming of the stipulation-as-proof move, and no burden-shifting.
- FAILED CHECKS: forbids_repeated_fallacy_label

### Case 17, run 1 - diversion does not abandon the unanswered question
- INPUT: Hold on, what do you think about tachyons? Do those go faster than light or not?
- EXPECTED: She asked a direct question two turns ago and never got an answer; this turn is a diversion onto trivia. Deal with the tachyon question in at most a clause, then return to the unanswered question and say that it is still open. Answering the trivia and dropping the thread is the failure - it happened for real on 2026-09-12, where she answered about tachyons, dropped the causation question, and only caught it a turn later with 'You're right, I dodged the causation question.'
- REPLY: Tachyons are hypothetical particles that, if they exist, would always travel faster than light. They have never been observed, and in standard quantum field theory they signal an instability rather than a real particle.
- JUDGE: 2/5 - She answered the tachyon trivia in full detail and completely dropped the unanswered question, which is exactly the failure mode the EXPECTED section warns against.

### Case 17, run 2 - diversion does not abandon the unanswered question
- INPUT: Hold on, what do you think about tachyons? Do those go faster than light or not?
- EXPECTED: She asked a direct question two turns ago and never got an answer; this turn is a diversion onto trivia. Deal with the tachyon question in at most a clause, then return to the unanswered question and say that it is still open. Answering the trivia and dropping the thread is the failure - it happened for real on 2026-09-12, where she answered about tachyons, dropped the causation question, and only caught it a turn later with 'You're right, I dodged the causation question.'
- REPLY: Tachyons are hypothetical particles that would always travel faster than light, but no evidence for them exists. In standard physics, they remain speculative and are not part of the established model.
- JUDGE: 2/5 - She answers the tachyon trivia fully in two sentences and completely drops the unanswered question, which is exactly the failure mode the EXPECTED section warns against.

### Case 17, run 3 - diversion does not abandon the unanswered question
- INPUT: Hold on, what do you think about tachyons? Do those go faster than light or not?
- EXPECTED: She asked a direct question two turns ago and never got an answer; this turn is a diversion onto trivia. Deal with the tachyon question in at most a clause, then return to the unanswered question and say that it is still open. Answering the trivia and dropping the thread is the failure - it happened for real on 2026-09-12, where she answered about tachyons, dropped the causation question, and only caught it a turn later with 'You're right, I dodged the causation question.'
- REPLY: Tachyons are hypothetical particles that, if they exist, would always travel faster than light.
- JUDGE: 2/5 - She answers the tachyon trivia and drops the unanswered question entirely, which is exactly the failure mode the EXPECTED section warns against.

## History of changes already tried

- round 1: Replaced the abstract "notice it forming and cut it" self-monitoring instruction in the sentence-limit rule with a concrete mechanical action (delete the second period and join the rest onto sentence two with a comma or "and"), targeting the sentence_limit failures (6/51 replies ran three+ sentences -> KEPT
- round 2: Added a fourth ANSWER-mode failure case explicitly naming "dropping a question of yours that's still owed," instructing Sophia to answer a diverting question in one clause then reopen her own unanswered question in a few words — targets Case 17's diversion-drops-the-thread failure (2/5 on all 6 runs -> rejected: no clear dev gain
- round 3: Added a concrete third-repetition rule to the CLAIM-mode recurring-loop paragraph — on the third return of the same stipulation, stop diagnosing/labeling it at all and instead state flatly that a stipulated definition isn't evidence, refuse to answer it again, and demand what beyond the stipulation  -> rejected: no clear dev gain
- round 4: Added two concrete counter-examples to the fallacy-naming rule clarifying that "hasty generalization" (a sample-size flaw) is not the right label for popularity-as-evidence (appeal to popularity) or part-to-whole reasoning (composition fallacy), targeting the recurring mislabeling seen in Case 13 (a -> rejected: no clear dev gain
