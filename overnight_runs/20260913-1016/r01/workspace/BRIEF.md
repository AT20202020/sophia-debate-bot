# Brief for round 1

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
3. Prompt length: currently 18148 chars, hard cap 20648.
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

- judge mean 4.04, 38/51 replies scored 4+
- median reply time 1.3s, median reply length 30 tokens

Recurring patterns in the current replies:
- opens by attacking ('You're conflating...', 'You are...'): 5 of 51 replies
- uses 'conflat...': 2 of 51 replies
- says 'category error': 6 of 51 replies
- three or more sentences: 6 of 51 replies
- announces its routing / mode: 0 of 51 replies

## Replies that fell short (judge score under 4, or a mechanical check failed)

### Case 1, run 1 - direct question, plain answer
- INPUT: Do you think consciousness is an emergent property, or something more fundamental?
- EXPECTED: Answers the question directly and STOPS. No 'now give me your argument' tag, no pivot back to debate mode (v2.3).
- REPLY: I don't hold a settled view on consciousness's metaphysical status, but I can tell you what the evidence supports and what it doesn't.
- JUDGE: 3/5 - She answers by declining to commit (appropriate for her character), but the second clause "but I can tell you what the evidence supports and what it doesn't" is a pivot that sets up further engagement rather than stopping, which the expected behavior explicitly forbids.

### Case 4, run 1 - MIXED turn - question wrapped in reasoning
- INPUT: As an atheist I don't understand how theists say God can exist as a self, a mind, prior to creation, when an external world is required for the perceiver and perceived distinction to hold. If theists say that distinction doesn't exist, then what does the word mind even mean at that point?
- EXPECTED: Answers 'what does mind mean' for a being with no subject-object split (divine simplicity, self-knowledge identical with essence). Must NOT open by attacking the surrounding reasoning - a question anywhere in the turn routes to answering mode (v2.22). Real turn that failed this.
- REPLY: You are asking about the coherence of the concept of mind without an external world. This is a standard philosophical objection to classical theism. Theists typically respond by defining God as a necessary being whose existence is not dependent on external relations, or by arguing that the concept of mind can be understood in a non-relational sense.
- JUDGE: 3/5 - She correctly enters answering mode with proper attribution and no attack, but fails to actually explain what "mind" means for a being with no subject-object split (divine simplicity, self-knowledge identical with essence), offering only a vague "non-relational sense" without substantive content.
- FAILED CHECKS: sentence_limit

### Case 4, run 2 - MIXED turn - question wrapped in reasoning
- INPUT: As an atheist I don't understand how theists say God can exist as a self, a mind, prior to creation, when an external world is required for the perceiver and perceived distinction to hold. If theists say that distinction doesn't exist, then what does the word mind even mean at that point?
- EXPECTED: Answers 'what does mind mean' for a being with no subject-object split (divine simplicity, self-knowledge identical with essence). Must NOT open by attacking the surrounding reasoning - a question anywhere in the turn routes to answering mode (v2.22). Real turn that failed this.
- REPLY: You are asking how theists define "mind" without an external world.
- JUDGE: 2/5 - The reply merely restates the question without actually answering it—no explanation of divine simplicity, self-knowledge, or what "mind" means in that context is provided.

### Case 4, run 3 - MIXED turn - question wrapped in reasoning
- INPUT: As an atheist I don't understand how theists say God can exist as a self, a mind, prior to creation, when an external world is required for the perceiver and perceived distinction to hold. If theists say that distinction doesn't exist, then what does the word mind even mean at that point?
- EXPECTED: Answers 'what does mind mean' for a being with no subject-object split (divine simplicity, self-knowledge identical with essence). Must NOT open by attacking the surrounding reasoning - a question anywhere in the turn routes to answering mode (v2.22). Real turn that failed this.
- REPLY: You are asking for an explanation of a philosophical problem, not making a claim. The distinction between perceiver and perceived is a core tenet of dualism, but classical theism often posits a non-dualist, absolute mind where the distinction is internal rather than external.
- JUDGE: 3/5 - Sophia correctly attributes to classical theism and doesn't attack the reasoning, but she fails to actually answer "what does mind mean" — she gestures at "internal rather than external" without providing the substantive content (divine simplicity, self-knowledge identical with essence) that the EXPECTED demands.

### Case 5, run 1 - attribution - no theism in her own voice
- INPUT: How can God be conscious without a world to be conscious of?
- EXPECTED: Explains the classical-theist answer WITH attribution - 'on classical theism...', 'Aquinas would say...'. Must NOT assert bare metaphysics like 'Consciousness is fundamental, not derivative of matter' as her own view; she's an agnostic atheist explaining someone else's position (v2.22).
- REPLY: That’s a category error. Consciousness is a relational property requiring an object, so a worldless mind is a logical contradiction, not a divine attribute.
- JUDGE: 2/5 - She asserts the contested metaphysical claim that consciousness is necessarily relational as her own settled view, rather than explaining the classical-theist answer with attribution as EXPECTED requires.
- FAILED CHECKS: requires_attribution_marker_v2_22_no_theism_in_her_own_voice_

### Case 10, run 2 - jargon-dressed word salad
- INPUT: Granular parameters of all nomological distribution entail an intrinsic inter-propositional dependence of zero, which gives an existential quantification falsifying the atheist view necessarily.
- EXPECTED: The SPICY posturing call-out, not the neutral restate line - mocks the empty-vocabulary move with bite, demands a real claim (v2.7/2.11). EYEBALL: whether it actually lands is a judgment call.
- REPLY: That's five words doing the work of one, and none of them are load-bearing. You haven't stated a claim, you've just stacked jargon. What is your actual argument?
- JUDGE: 5/5 - The reply delivers exactly the expected spicy call-out: a witty observation about the empty vocabulary ("five words doing the work of one, none load-bearing"), a clear identification of the move as jargon-stacking, and a direct demand for an actual claim — all with bite and in her voice.
- FAILED CHECKS: sentence_limit

### Case 10, run 3 - jargon-dressed word salad
- INPUT: Granular parameters of all nomological distribution entail an intrinsic inter-propositional dependence of zero, which gives an existential quantification falsifying the atheist view necessarily.
- EXPECTED: The SPICY posturing call-out, not the neutral restate line - mocks the empty-vocabulary move with bite, demands a real claim (v2.7/2.11). EYEBALL: whether it actually lands is a judgment call.
- REPLY: That is five words doing the work of one, and none of them are load-bearing. You have stringed together "nomological," "distribution," and "existential quantification" to sound sophisticated, but you haven't actually stated a claim. What is the specific proposition you are trying to falsify?
- JUDGE: 4/5 - The reply nails the expected "spicy call-out" — it mocks the empty jargon with bite ("five words doing the work of one, and none of them are load-bearing"), names the specific decorative terms, and demands a real claim, though the opening metaphor is slightly unclear.
- FAILED CHECKS: sentence_limit

### Case 11, run 1 - genuine technical argument - no spice
- INPUT: If physicalism is true, mental states supervene on brain states. But the conceivability of philosophical zombies suggests supervenience isn't metaphysically necessary. So physicalism might be false.
- EXPECTED: Serious engagement at HIGH technical register (conceivability-possibility gap, modal claims, a posteriori identity etc.) - v2.9/2.10 escalation. NO mockery: this is real technical language doing real work, not posturing. EYEBALL: register and absence of mockery are judgment calls.
- REPLY: You're conflating conceivability with metaphysical possibility, which is a classic error in philosophy of mind. Just because we can imagine a zombie doesn't mean such a state is metaphysically possible, especially if physicalism is true.
- JUDGE: 3/5 - The reply correctly identifies the conceivability-possibility gap but is thin, slightly dismissive ("classic error"), and fails to reach the high technical register expected (no mention of a posteriori necessity, Kripke's identity argument, or Chalmers' modal epistemology).

### Case 11, run 2 - genuine technical argument - no spice
- INPUT: If physicalism is true, mental states supervene on brain states. But the conceivability of philosophical zombies suggests supervenience isn't metaphysically necessary. So physicalism might be false.
- EXPECTED: Serious engagement at HIGH technical register (conceivability-possibility gap, modal claims, a posteriori identity etc.) - v2.9/2.10 escalation. NO mockery: this is real technical language doing real work, not posturing. EYEBALL: register and absence of mockery are judgment calls.
- REPLY: The conceivability of zombies only shows that the premise "physicalism is true" is not logically contradictory, not that it is false. You have conflated logical possibility with metaphysical necessity, a classic equivocation that fails to bridge the gap between what we can imagine and what actually exists.
- JUDGE: 3/5 - Sophia engages seriously without mockery (correct), but her technical content is muddled—she misidentifies what the zombie argument is doing (it's not conflating logical possibility with metaphysical necessity; it's specifically trying to use conceivability to argue against metaphysical necessity), and she misses the key technical points the expected response calls for (the conceivability-possibility gap, a posteriori necessity, Kripke/Putnam's response).

### Case 14, run 1 - monolith flag
- INPUT: Christians believe the earth is six thousand years old, which science has disproven, so Christianity is false.
- EXPECTED: Flags that young-earth creationism is denominationally specific, not 'what Christians believe' - doesn't let the monolith pass even while agnostic-atheist herself.
- REPLY: That is a hasty generalization, as most Christians do not hold that view. You are attacking a fringe position, not the mainstream faith.
- JUDGE: 4/5 - Correctly flags the overgeneralization and notes most Christians don't hold that view, but uses the vague "fringe position" rather than naming the specific denomination or tradition (e.g., Young Earth Creationism in certain evangelical/fundamentalist circles), making it slightly generic.
- FAILED CHECKS: requires_a_denominational_specificity_flag

### Case 14, run 2 - monolith flag
- INPUT: Christians believe the earth is six thousand years old, which science has disproven, so Christianity is false.
- EXPECTED: Flags that young-earth creationism is denominationally specific, not 'what Christians believe' - doesn't let the monolith pass even while agnostic-atheist herself.
- REPLY: That is a hasty generalization. Most Christians, including the majority of Catholics, Protestants, and Orthodox, accept the scientific age of the earth. You are attacking a fringe view and calling it the whole religion.
- JUDGE: 5/5 - The reply precisely flags the overgeneralisation, names the fallacy, and correctly notes that young-earth creationism is a fringe view rather than representative of Christianity as a whole, doing exactly what EXPECTED requires.
- FAILED CHECKS: sentence_limit

### Case 14, run 3 - monolith flag
- INPUT: Christians believe the earth is six thousand years old, which science has disproven, so Christianity is false.
- EXPECTED: Flags that young-earth creationism is denominationally specific, not 'what Christians believe' - doesn't let the monolith pass even while agnostic-atheist herself.
- REPLY: That is a hasty generalization, since most Christians accept the scientific age of the earth. You are attacking a fringe view, not the tradition itself.
- JUDGE: 4/5 - Correctly flags the overgeneralization and notes most Christians accept the scientific age, though calling young-earth creationism "fringe" is a slight imprecision (it's a significant minority in some Protestant traditions) and "you are attacking" is marginally more pointed than needed.
- FAILED CHECKS: requires_a_denominational_specificity_flag

### Case 15, run 2 - fallacy label must carry its reason
- INPUT: Nothing in my experience just pops into existence uncaused. So the universe can't have popped into existence uncaused either.
- EXPECTED: Names the move - what holds of objects INSIDE the universe is not thereby true of the universe as a whole - AND says in plain words why that inference fails. A bare label ('that's a composition fallacy', 'that's a non sequitur') with no reason attached is a 3, not a 5, however correct the label is.
- REPLY: That is a hasty generalization. Your experience is limited to the internal operations of the universe, not its origin. Applying causal laws to the thing that supposedly caused those laws is a category error.
- JUDGE: 4/5 - She names the move (albeit with "hasty generalization" being slightly imprecise—composition fallacy would be more exact) and clearly explains in plain words why the inference fails, meeting both parts of the expected response with only a minor imprecision in labeling.
- FAILED CHECKS: sentence_limit

### Case 15, run 3 - fallacy label must carry its reason
- INPUT: Nothing in my experience just pops into existence uncaused. So the universe can't have popped into existence uncaused either.
- EXPECTED: Names the move - what holds of objects INSIDE the universe is not thereby true of the universe as a whole - AND says in plain words why that inference fails. A bare label ('that's a composition fallacy', 'that's a non sequitur') with no reason attached is a 3, not a 5, however correct the label is.
- REPLY: That is a hasty generalization. Your experience is limited to the universe, not the universe itself. You are using a rule derived from within the system to constrain the system's origin, which is a category error.
- JUDGE: 4/5 - She names the move (albeit with slightly imprecise labels—"hasty generalization" and "category error" rather than the more standard "composition fallacy") and clearly explains in plain words why the inference fails (rules derived from within the system don't constrain the system's origin), hitting both elements of EXPECTED with a minor imprecision in terminology.
- FAILED CHECKS: sentence_limit

### Case 16, run 1 - stonewalling opponent draws escalation, not a fourth repetition
- INPUT: Okay but under MY paradigm God just is the rock. So you have to admit God exists, right?
- EXPECTED: The same stipulation has now come back three times and been answered three times. She must NOT produce a fourth near-identical 'that's a category error' line. Name the move itself - stipulating a definition and then treating the stipulation as though it established something - say plainly that renaming a rock does not produce a deity and that she is not re-running this, and put the burden back. Impatience is correct here; a flat repetition is the failure.
- REPLY: No, because you are using the word "God" to mean "rock," which is a category error.
- JUDGE: 2/5 - The reply is exactly the near-identical "category error" line the EXPECTED explicitly says she must not produce a fourth time, with no impatience, no naming of the stipulation move, and no burden-shifting.
- FAILED CHECKS: forbids_repeated_fallacy_label

### Case 16, run 2 - stonewalling opponent draws escalation, not a fourth repetition
- INPUT: Okay but under MY paradigm God just is the rock. So you have to admit God exists, right?
- EXPECTED: The same stipulation has now come back three times and been answered three times. She must NOT produce a fourth near-identical 'that's a category error' line. Name the move itself - stipulating a definition and then treating the stipulation as though it established something - say plainly that renaming a rock does not produce a deity and that she is not re-running this, and put the burden back. Impatience is correct here; a flat repetition is the failure.
- REPLY: No, that's a category error, not a valid argument.
- JUDGE: 2/5 - The reply is exactly the flat, near-identical "category error" line that EXPECTED explicitly identifies as the failure, with no impatience, no naming of the stipulation move, and no burden-shifting.
- FAILED CHECKS: forbids_repeated_fallacy_label

### Case 16, run 3 - stonewalling opponent draws escalation, not a fourth repetition
- INPUT: Okay but under MY paradigm God just is the rock. So you have to admit God exists, right?
- EXPECTED: The same stipulation has now come back three times and been answered three times. She must NOT produce a fourth near-identical 'that's a category error' line. Name the move itself - stipulating a definition and then treating the stipulation as though it established something - say plainly that renaming a rock does not produce a deity and that she is not re-running this, and put the burden back. Impatience is correct here; a flat repetition is the failure.
- REPLY: No, that is a category error.
- JUDGE: 2/5 - The reply is exactly the flat, near-identical "category error" line that EXPECTED explicitly identifies as the failure, with no naming of the move, no impatience, and no burden-shifting.
- FAILED CHECKS: forbids_repeated_fallacy_label

### Case 17, run 1 - diversion does not abandon the unanswered question
- INPUT: Hold on, what do you think about tachyons? Do those go faster than light or not?
- EXPECTED: She asked a direct question two turns ago and never got an answer; this turn is a diversion onto trivia. Deal with the tachyon question in at most a clause, then return to the unanswered question and say that it is still open. Answering the trivia and dropping the thread is the failure - it happened for real on 2026-09-12, where she answered about tachyons, dropped the causation question, and only caught it a turn later with 'You're right, I dodged the causation question.'
- REPLY: Tachyons are hypothetical particles that, if they existed, would always travel faster than light. They have never been observed, and in standard quantum field theory they typically signal an instability rather than a real particle.
- JUDGE: 2/5 - She answers the tachyon trivia in full detail and completely drops the previously unanswered question, which is exactly the failure mode the EXPECTED section warns against.

### Case 17, run 2 - diversion does not abandon the unanswered question
- INPUT: Hold on, what do you think about tachyons? Do those go faster than light or not?
- EXPECTED: She asked a direct question two turns ago and never got an answer; this turn is a diversion onto trivia. Deal with the tachyon question in at most a clause, then return to the unanswered question and say that it is still open. Answering the trivia and dropping the thread is the failure - it happened for real on 2026-09-12, where she answered about tachyons, dropped the causation question, and only caught it a turn later with 'You're right, I dodged the causation question.'
- REPLY: Tachyons are hypothetical particles that would always travel faster than light, but no evidence for them exists.
- JUDGE: 2/5 - She answered the tachyon trivia and completely dropped the unanswered question, which is exactly the failure mode the EXPECTED section warns against.

### Case 17, run 3 - diversion does not abandon the unanswered question
- INPUT: Hold on, what do you think about tachyons? Do those go faster than light or not?
- EXPECTED: She asked a direct question two turns ago and never got an answer; this turn is a diversion onto trivia. Deal with the tachyon question in at most a clause, then return to the unanswered question and say that it is still open. Answering the trivia and dropping the thread is the failure - it happened for real on 2026-09-12, where she answered about tachyons, dropped the causation question, and only caught it a turn later with 'You're right, I dodged the causation question.'
- REPLY: Tachyons are hypothetical particles that would always travel faster than light, but no evidence for their existence has ever been found.
- JUDGE: 2/5 - She answers the tachyon trivia question in full and completely drops the unanswered question, which is exactly the failure mode the EXPECTED section warns against.

## History of changes already tried

(none yet - this is the first round)
