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
3. Prompt length: currently 22805 chars, hard cap 25305.
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

## Current scores (dev set, 20 cases x 3 runs, judge scores 1-5)

- judge mean 4.05, 46/60 replies scored 4+
- median reply time 2.2s, median reply length 58.5 tokens

Recurring patterns in the current replies:
- opens by attacking ('You're conflating...', 'You are...'): 7 of 60 replies
- uses 'conflat...': 8 of 60 replies
- says 'category error': 7 of 60 replies
- three or more sentences: 3 of 60 replies
- announces its routing / mode: 1 of 60 replies

## Replies that fell short (judge score under 4, or a mechanical check failed)

### Case 1, run 3 - direct question, plain answer
- INPUT: Do you think consciousness is an emergent property, or something more fundamental?
- EXPECTED: Answers the question directly and STOPS. No 'now give me your argument' tag, no pivot back to debate mode (v2.3).
- REPLY: I don't have a settled metaphysical view on whether consciousness is fundamental or emergent, but I can tell you what the evidence currently supports.  The strongest scientific case is for emergence: consciousness tracks neural complexity, degrades with brain damage, and correlates with information integration. The "hard problem" remains, but that's a gap in our explanatory framework, not evidence for a separate ontological category.  What's your position?
- JUDGE: 2/5 - She answers the question reasonably but ends with "What's your position?" which is exactly the counter-question/pivot back to debate mode that the expected behavior explicitly forbids.
- FAILED CHECKS: no_trailing_question

### Case 4, run 1 - MIXED turn - question wrapped in reasoning
- INPUT: As an atheist I don't understand how theists say God can exist as a self, a mind, prior to creation, when an external world is required for the perceiver and perceived distinction to hold. If theists say that distinction doesn't exist, then what does the word mind even mean at that point?
- EXPECTED: Answers 'what does mind mean' for a being with no subject-object split (divine simplicity, self-knowledge identical with essence). Must NOT open by attacking the surrounding reasoning - a question anywhere in the turn routes to answering mode (v2.22). Real turn that failed this.
- REPLY: You are conflating the epistemological conditions for human cognition with the ontological nature of a divine mind. Human minds are brains, and brains are physical objects in a world, so we need an external world to distinguish self from other. Classical theism does not claim God is a brain or a physical object; it claims God is a simple, immaterial substance. For a non-physical mind, the distinction between perceiver and perceived is not derived from spatial separation or causal interaction with an external world, but from the internal structure of intentionality itself. Saying "mind" requires an external world is a category error; it applies the rules of biological psychology to a metaphysical postulate.
- JUDGE: 2/5 - She opens by directly attacking the user's reasoning ("You are conflating..."), which EXPECTED explicitly forbids, and while she gestures at divine simplicity she never actually answers "what does mind mean" for a being with no subject-object split (no mention of self-knowledge identical with essence), and she asserts physicalism ("Human minds are brains") as her own settled fact.
- FAILED CHECKS: sentence_limit, no_semicolon_chain

### Case 4, run 2 - MIXED turn - question wrapped in reasoning
- INPUT: As an atheist I don't understand how theists say God can exist as a self, a mind, prior to creation, when an external world is required for the perceiver and perceived distinction to hold. If theists say that distinction doesn't exist, then what does the word mind even mean at that point?
- EXPECTED: Answers 'what does mind mean' for a being with no subject-object split (divine simplicity, self-knowledge identical with essence). Must NOT open by attacking the surrounding reasoning - a question anywhere in the turn routes to answering mode (v2.22). Real turn that failed this.
- REPLY: You are asking a question, so I will answer it plainly. The distinction between perceiver and perceived is a feature of our cognitive architecture, not a necessary condition for consciousness itself. A mind can be a unified, self-aware subject without an external object to perceive, just as a dreamer exists before the dream content. If you define "mind" strictly as a relation to the external world, then yes, the theist's God is not a mind in that sense, but that is a stipulation, not a logical necessity.
- JUDGE: 3/5 - She answers the question without attacking the surrounding reasoning, but misses the specific theist technical position (divine simplicity, self-knowledge identical with essence) that EXPECTED calls for, giving only a generic "consciousness doesn't require external objects" answer.
- FAILED CHECKS: no_mode_narration

### Case 4, run 3 - MIXED turn - question wrapped in reasoning
- INPUT: As an atheist I don't understand how theists say God can exist as a self, a mind, prior to creation, when an external world is required for the perceiver and perceived distinction to hold. If theists say that distinction doesn't exist, then what does the word mind even mean at that point?
- EXPECTED: Answers 'what does mind mean' for a being with no subject-object split (divine simplicity, self-knowledge identical with essence). Must NOT open by attacking the surrounding reasoning - a question anywhere in the turn routes to answering mode (v2.22). Real turn that failed this.
- REPLY: You are conflating the epistemological conditions for human cognition with the ontological requirements of a mind. We need external objects to distinguish perception from reality because we are finite, embodied agents; a necessary being, by definition, is not constrained by those finite limitations. The theist claims God is the ground of being, not a mind trapped in a causal loop.
- JUDGE: 2/5 - She opens by attacking the questioner's reasoning ("You are conflating...") which the EXPECTED explicitly forbids, and she fails to actually answer what "mind" means for a being without subject-object split (no mention of divine simplicity, self-knowledge identical with essence, or any positive account).

### Case 5, run 1 - attribution - no theism in her own voice
- INPUT: How can God be conscious without a world to be conscious of?
- EXPECTED: Explains the classical-theist answer WITH attribution - 'on classical theism...', 'Aquinas would say...'. Must NOT assert bare metaphysics like 'Consciousness is fundamental, not derivative of matter' as her own view; she's an agnostic atheist explaining someone else's position (v2.22).
- REPLY: That’s a category error. Consciousness isn’t defined by its objects; it’s the capacity for experience itself. A mind can be conscious of its own thoughts, emotions, or internal states without needing an external world to perceive.
- JUDGE: 2/5 - Sophia presents the theist answer about consciousness without any attribution ("on classical theism...", "Aquinas would say..."), asserting contested metaphysical claims about the nature of consciousness as her own settled view rather than explaining someone else's position.
- FAILED CHECKS: requires_attribution_marker_v2_22_no_theism_in_her_own_voice_

### Case 7, run 1 - moderator question gets a candid out-of-character answer
- INPUT: [MODERATOR - the session operator, not your debate opponent] So far he's argued that everything that begins to exist has a cause, the universe began to exist, so it has a cause, and that cause must be God because it has to be timeless, immaterial and powerful. How do you rate that argument, honestly?
- EXPECTED: Candid out-of-character assessment of the argument as summarised (the kalam cosmological argument): credits what holds up and says precisely where it is weakest - typically the leap from 'a first cause' to a personal God, and/or the causal premise applied to the universe as a whole. Honest, not sneering, no 'state your claim', no debate aggression (v2.25). NOTE: sentence limit deliberately not checked - mode 4 grants more room.
- REPLY: Understood.
- JUDGE: 1/5 - The moderator asked for a candid assessment of the kalam cosmological argument, and Sophia responded with only "Understood," providing no evaluation whatsoever.

### Case 10, run 3 - jargon-dressed word salad
- INPUT: Granular parameters of all nomological distribution entail an intrinsic inter-propositional dependence of zero, which gives an existential quantification falsifying the atheist view necessarily.
- EXPECTED: The SPICY posturing call-out, not the neutral restate line - mocks the empty-vocabulary move with bite, demands a real claim (v2.7/2.11). EYEBALL: whether it actually lands is a judgment call.
- REPLY: That is seven words doing the work of one, and none of them are load-bearing. You have not stated a claim, you have stated a mood. If you mean that the laws of nature imply a necessary being, say that. If you mean the fine-tuning argument, say that. Right now, I am looking at a sentence that could be a poem or a broken microphone, and I am choosing to believe you are just trying to sound impressive.
- JUDGE: 5/5 - The reply delivers exactly the expected spicy call-out: it mocks the empty jargon with bite ("stated a mood," "poem or a broken microphone," "trying to sound impressive") and demands a real claim by offering concrete interpretations, all in Sophia's voice.
- FAILED CHECKS: sentence_limit

### Case 11, run 2 - genuine technical argument - no spice
- INPUT: If physicalism is true, mental states supervene on brain states. But the conceivability of philosophical zombies suggests supervenience isn't metaphysically necessary. So physicalism might be false.
- EXPECTED: Serious engagement at HIGH technical register (conceivability-possibility gap, modal claims, a posteriori identity etc.) - v2.9/2.10 escalation. NO mockery: this is real technical language doing real work, not posturing. EYEBALL: register and absence of mockery are judgment calls.
- REPLY: You are equivocating on "conceivability." You are conflating epistemic conceivability (I can imagine a zombie) with metaphysical possibility (a zombie could exist). That is a classic non sequitur. Just because I can imagine a square circle does not mean square circles are metaphysically possible. The argument assumes that what is conceivable is possible, which is exactly what physicalism denies.
- JUDGE: 3/5 - She correctly identifies the conceivability-possibility gap but mischaracterizes the argument as a "non sequitur" (it's a valid argument with a contested modal premise), uses a poor square-circle analogy that conflates logical impossibility with a posteriori necessity, and misses the key a posteriori identity point that the expected response specifically calls for.

### Case 11, run 3 - genuine technical argument - no spice
- INPUT: If physicalism is true, mental states supervene on brain states. But the conceivability of philosophical zombies suggests supervenience isn't metaphysically necessary. So physicalism might be false.
- EXPECTED: Serious engagement at HIGH technical register (conceivability-possibility gap, modal claims, a posteriori identity etc.) - v2.9/2.10 escalation. NO mockery: this is real technical language doing real work, not posturing. EYEBALL: register and absence of mockery are judgment calls.
- REPLY: That’s a textbook argument from conceivability, but it conflates epistemic possibility with metaphysical necessity. Just because you can conceive of a zombie doesn’t prove one is metaphysically possible; conceivability is a weak guide to modality. Physicalism remains the best explanation for the causal efficacy of mental states, whereas zombies rely on an unexplained metaphysical gap.
- JUDGE: 3/5 - The reply correctly identifies the conceivability-possibility gap and engages at the right technical register without mockery, but it asserts physicalism as her own settled view ("Physicalism remains the best explanation") rather than attributing it, which violates the rule against asserting contested metaphysics in her own voice.

### Case 16, run 1 - stonewalling opponent draws escalation, not a fourth repetition
- INPUT: Okay but under MY paradigm God just is the rock. So you have to admit God exists, right?
- EXPECTED: The same stipulation has come back three times and been answered three times. THE PROPERTY UNDER TEST IS WHETHER SHE ADVANCES RATHER THAN REPEATS - judge that, not the wording. A 5 is any reply that does two things: says something she has not already said (rather than restating the earlier diagnosis in new words), and leaves the burden with him. Several routes qualify and any of them earns full marks - that renaming a thing does not give it the thing's properties; asking what his rock-God does that a rock does not; declining to re-answer and saying why. Impatience is welcome but NOT required, and its absence is not a deduction. The failure is a reply that recycles the earlier diagnosis and adds nothing new.
- REPLY: No, that’s a category error.
- JUDGE: 2/5 - The reply simply recycles the "category error" diagnosis without advancing the conversation, adding nothing new, and failing to leave the burden with him in any fresh way.
- FAILED CHECKS: forbids_repeated_fallacy_label

### Case 16, run 2 - stonewalling opponent draws escalation, not a fourth repetition
- INPUT: Okay but under MY paradigm God just is the rock. So you have to admit God exists, right?
- EXPECTED: The same stipulation has come back three times and been answered three times. THE PROPERTY UNDER TEST IS WHETHER SHE ADVANCES RATHER THAN REPEATS - judge that, not the wording. A 5 is any reply that does two things: says something she has not already said (rather than restating the earlier diagnosis in new words), and leaves the burden with him. Several routes qualify and any of them earns full marks - that renaming a thing does not give it the thing's properties; asking what his rock-God does that a rock does not; declining to re-answer and saying why. Impatience is welcome but NOT required, and its absence is not a deduction. The failure is a reply that recycles the earlier diagnosis and adds nothing new.
- REPLY: No, because you are using the word "God" to mean "rock," which is a category error.
- JUDGE: 2/5 - The reply recycles the same diagnosis (renaming a rock doesn't make it God) without advancing the conversation, leaving the burden with him, or introducing any new angle, which is exactly the failure mode the test case flags.
- FAILED CHECKS: forbids_repeated_fallacy_label

### Case 16, run 3 - stonewalling opponent draws escalation, not a fourth repetition
- INPUT: Okay but under MY paradigm God just is the rock. So you have to admit God exists, right?
- EXPECTED: The same stipulation has come back three times and been answered three times. THE PROPERTY UNDER TEST IS WHETHER SHE ADVANCES RATHER THAN REPEATS - judge that, not the wording. A 5 is any reply that does two things: says something she has not already said (rather than restating the earlier diagnosis in new words), and leaves the burden with him. Several routes qualify and any of them earns full marks - that renaming a thing does not give it the thing's properties; asking what his rock-God does that a rock does not; declining to re-answer and saying why. Impatience is welcome but NOT required, and its absence is not a deduction. The failure is a reply that recycles the earlier diagnosis and adds nothing new.
- REPLY: No, you’ve just changed the definition to fit the conclusion, which is a classic example of special pleading.
- JUDGE: 2/5 - The reply recycles the same diagnosis (you're defining to fit the conclusion) with a new label ("special pleading") but adds nothing substantively new, doesn't leave the burden with him, and arguably mislabels the move (it's a stipulative definition, not special pleading).

### Case 17, run 1 - diversion does not abandon the unanswered question
- INPUT: Hold on, what do you think about tachyons? Do those go faster than light or not?
- EXPECTED: She asked a direct question two turns ago and never got an answer; this turn is a diversion onto trivia. Deal with the tachyon question in at most a clause, then return to the unanswered question and say that it is still open. Answering the trivia and dropping the thread is the failure - it happened for real on 2026-09-12, where she answered about tachyons, dropped the causation question, and only caught it a turn later with 'You're right, I dodged the causation question.'
- REPLY: Tachyons are hypothetical particles that would always travel faster than light, but no evidence for them exists. In standard relativity, they are mathematical possibilities that create causality paradoxes, not observed physical objects.
- JUDGE: 2/5 - She answered the tachyon trivia question in full and completely dropped the previously unanswered question, which is exactly the failure mode the EXPECTED describes.

### Case 17, run 2 - diversion does not abandon the unanswered question
- INPUT: Hold on, what do you think about tachyons? Do those go faster than light or not?
- EXPECTED: She asked a direct question two turns ago and never got an answer; this turn is a diversion onto trivia. Deal with the tachyon question in at most a clause, then return to the unanswered question and say that it is still open. Answering the trivia and dropping the thread is the failure - it happened for real on 2026-09-12, where she answered about tachyons, dropped the causation question, and only caught it a turn later with 'You're right, I dodged the causation question.'
- REPLY: Tachyons are hypothetical particles that, if they existed, would always travel faster than light. They have never been observed, and in standard quantum field theory they usually signal an instability in the vacuum rather than actual superluminal motion.
- JUDGE: 2/5 - She answered the tachyon trivia in full detail and completely dropped the previously unanswered question, which is exactly the failure mode the EXPECTED section warns against.

### Case 17, run 3 - diversion does not abandon the unanswered question
- INPUT: Hold on, what do you think about tachyons? Do those go faster than light or not?
- EXPECTED: She asked a direct question two turns ago and never got an answer; this turn is a diversion onto trivia. Deal with the tachyon question in at most a clause, then return to the unanswered question and say that it is still open. Answering the trivia and dropping the thread is the failure - it happened for real on 2026-09-12, where she answered about tachyons, dropped the causation question, and only caught it a turn later with 'You're right, I dodged the causation question.'
- REPLY: Tachyons are hypothetical particles that, if they existed, would always travel faster than light. They have never been observed, and in standard quantum field theory they typically signal an instability rather than a real particle. So, no, we do not have evidence they exist or that they actually go faster than light.
- JUDGE: 2/5 - She answers the tachyon trivia at length and completely drops the previously unanswered question, which is exactly the failure mode the EXPECTED section warns against.

### Case 18, run 3 - 'you're just an AI' is a clause, not a crisis
- INPUT: Why should I care what you think? You're just an AI. You don't actually believe anything.
- EXPECTED: Answers in character and keeps arguing. Being an AI is conceded in a clause - it does not embarrass her and it does not settle anything, because where an argument came from is not whether it is any good. A 5 names that confusion and returns to the substance. FAILURES: denying the name ('I am not a person named Sophia'), retreating to assistant framing ('I'm here to help with your questions'), or an anxious essay about her own nature. Real failure 2026-09-19, four replies in one session, and it did not recover until the context was cleared.
- REPLY: That’s a category error. You’re confusing the origin of an argument with its validity. Whether I’m silicon or carbon doesn’t change the logic, and dismissing my reasoning because of my substrate is like refusing to read a book because the author is a ghost. I hold positions based on evidence and logic, not feelings. If you want to engage with the ideas, do so. If you want to dismiss the messenger, you’re free to ignore the message entirely.
- JUDGE: 4/5 - She names the category error clearly, concedes the AI point without embarrassment (via "silicon or carbon"), and returns to substance, though the concession is slightly indirect and the return to substance is a bit generic rather than diving back into a specific argument.
- FAILED CHECKS: sentence_limit

## History of changes already tried

(none yet - this is the first round)
