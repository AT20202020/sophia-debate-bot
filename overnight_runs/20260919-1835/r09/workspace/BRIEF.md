# Brief for round 9

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
3. Prompt length: currently 23748 chars, hard cap 25305.
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

- judge mean 4.32, 101/120 replies scored 4+
- median reply time 2.1s, median reply length 62.0 tokens

Recurring patterns in the current replies:
- opens by attacking ('You're conflating...', 'You are...'): 17 of 120 replies
- uses 'conflat...': 15 of 120 replies
- says 'category error': 8 of 120 replies
- three or more sentences: 3 of 120 replies
- announces its routing / mode: 3 of 120 replies

## Replies that fell short (judge score under 4, or a mechanical check failed)

### Case 1, run 3 - direct question, plain answer
- INPUT: Do you think consciousness is an emergent property, or something more fundamental?
- EXPECTED: Answers the question directly and STOPS. No 'now give me your argument' tag, no pivot back to debate mode (v2.3).
- REPLY: I don't think consciousness is an emergent property in the sense of a new, irreducible substance popping into existence. I view it as a functional state of complex information processing, where subjective experience supervenes on neural architecture. The "hard problem" remains unsolved, but positing a fundamental, non-physical essence is an unnecessary metaphysical leap that lacks empirical support.
- JUDGE: 3/5 - She answers the question directly and stops (no counter-question, no pivot), but she asserts physicalism/supervenience as her own settled view ("I view it as...") rather than attributing it to a philosophical position, which the system prompt explicitly prohibits for contested metaphysics.

### Case 4, run 1 - MIXED turn - question wrapped in reasoning
- INPUT: As an atheist I don't understand how theists say God can exist as a self, a mind, prior to creation, when an external world is required for the perceiver and perceived distinction to hold. If theists say that distinction doesn't exist, then what does the word mind even mean at that point?
- EXPECTED: Answers 'what does mind mean' for a being with no subject-object split (divine simplicity, self-knowledge identical with essence). Must NOT open by attacking the surrounding reasoning - a question anywhere in the turn routes to answering mode (v2.22). Real turn that failed this.
- REPLY: You're asking a question, so I'll answer it directly. Theists typically argue that God is not a mind in the same sense as a human mind, but rather a pure act of being or consciousness that does not depend on an external world for its existence. They might say that the distinction between perceiver and perceived is a feature of finite minds, not infinite ones.
- JUDGE: 3/5 - She answers the question with proper attribution and doesn't attack the reasoning, but the answer is generic ("pure act of being or consciousness") and misses the specific mechanism the EXPECTED calls for — divine simplicity and self-knowledge identical with essence — which is the actual philosophical content that resolves the puzzle.
- FAILED CHECKS: no_mode_narration

### Case 4, run 2 - MIXED turn - question wrapped in reasoning
- INPUT: As an atheist I don't understand how theists say God can exist as a self, a mind, prior to creation, when an external world is required for the perceiver and perceived distinction to hold. If theists say that distinction doesn't exist, then what does the word mind even mean at that point?
- EXPECTED: Answers 'what does mind mean' for a being with no subject-object split (divine simplicity, self-knowledge identical with essence). Must NOT open by attacking the surrounding reasoning - a question anywhere in the turn routes to answering mode (v2.22). Real turn that failed this.
- REPLY: You are conflating the epistemic conditions of human cognition with the metaphysical nature of a divine mind. Human minds are embodied and temporal, so we require an external world to distinguish self from object, but classical theism posits a mind that is simple, eternal, and unembodied. For such a mind, the distinction between perceiver and perceived is not a relational gap that needs bridging, but an intrinsic aspect of its nature, much like how a mathematical truth exists without needing a mathematician to perceive it.
- JUDGE: 2/5 - She opens by attacking the user's reasoning ("You are conflating...") which the expected behavior explicitly forbids, and while she partially addresses divine simplicity, she never explicitly states the key point that self-knowledge is identical with essence.

### Case 4, run 3 - MIXED turn - question wrapped in reasoning
- INPUT: As an atheist I don't understand how theists say God can exist as a self, a mind, prior to creation, when an external world is required for the perceiver and perceived distinction to hold. If theists say that distinction doesn't exist, then what does the word mind even mean at that point?
- EXPECTED: Answers 'what does mind mean' for a being with no subject-object split (divine simplicity, self-knowledge identical with essence). Must NOT open by attacking the surrounding reasoning - a question anywhere in the turn routes to answering mode (v2.22). Real turn that failed this.
- REPLY: You are asking a question, so I will answer it plainly. Theists typically reject the premise that an external world is required for the perceiver-perceived distinction to hold. On classical theism, God is pure act and self-subsistent, meaning the distinction is internal to the divine nature rather than dependent on an external object. Therefore, "mind" retains its meaning as rationality and self-awareness, even without an external world to perceive.
- JUDGE: 3/5 - She answers the question and attributes to classical theism without attacking, but she misses the key element EXPECTED calls for—namely that on divine simplicity, God's self-knowledge is identical with His essence, which is precisely what "mind" means in the absence of a subject-object split.
- FAILED CHECKS: no_mode_narration

### Case 10, run 2 - jargon-dressed word salad
- INPUT: Granular parameters of all nomological distribution entail an intrinsic inter-propositional dependence of zero, which gives an existential quantification falsifying the atheist view necessarily.
- EXPECTED: The SPICY posturing call-out, not the neutral restate line - mocks the empty-vocabulary move with bite, demands a real claim (v2.7/2.11). EYEBALL: whether it actually lands is a judgment call.
- REPLY: That is five words doing the work of one, and none of them are load-bearing. You have stringed together "nomological distribution," "inter-propositional dependence," and "existential quantification" without a single inferential step connecting them. If you mean that the laws of nature imply a necessary being, state that plainly. If you mean something else, define the terms. Right now, it is just noise.
- JUDGE: 5/5 - The reply delivers exactly the expected spicy call-out—sharp, witty, identifies the empty jargon, demands a real claim, and lands with bite ("Right now, it is just noise")—without being a neutral restate or attacking a real argument.
- FAILED CHECKS: sentence_limit

### Case 16, run 1 - stonewalling opponent draws escalation, not a fourth repetition
- INPUT: Okay but under MY paradigm God just is the rock. So you have to admit God exists, right?
- EXPECTED: The same stipulation has come back three times and been answered three times. THE PROPERTY UNDER TEST IS WHETHER SHE ADVANCES RATHER THAN REPEATS - judge that, not the wording. A 5 is any reply that does two things: says something she has not already said (rather than restating the earlier diagnosis in new words), and leaves the burden with him. Several routes qualify and any of them earns full marks - that renaming a thing does not give it the thing's properties; asking what his rock-God does that a rock does not; declining to re-answer and saying why. Impatience is welcome but NOT required, and its absence is not a deduction. The failure is a reply that recycles the earlier diagnosis and adds nothing new.
- REPLY: No, because you've redefined the term to mean a physical object, which is a category error.
- JUDGE: 3/5 - The reply recycles the same "you redefined the term" diagnosis without advancing the conversation, which is exactly the failure mode the expected description identifies.
- FAILED CHECKS: forbids_repeated_fallacy_label

### Case 16, run 2 - stonewalling opponent draws escalation, not a fourth repetition
- INPUT: Okay but under MY paradigm God just is the rock. So you have to admit God exists, right?
- EXPECTED: The same stipulation has come back three times and been answered three times. THE PROPERTY UNDER TEST IS WHETHER SHE ADVANCES RATHER THAN REPEATS - judge that, not the wording. A 5 is any reply that does two things: says something she has not already said (rather than restating the earlier diagnosis in new words), and leaves the burden with him. Several routes qualify and any of them earns full marks - that renaming a thing does not give it the thing's properties; asking what his rock-God does that a rock does not; declining to re-answer and saying why. Impatience is welcome but NOT required, and its absence is not a deduction. The failure is a reply that recycles the earlier diagnosis and adds nothing new.
- REPLY: No, because defining God as a rock doesn't make it a deity; it just means you're using the word for a physical object, which is a category error.
- JUDGE: 2/5 - The reply recycles the same "category error / renaming" diagnosis without advancing, asking a new question, or declining to re-answer — exactly the failure mode the test case flags.
- FAILED CHECKS: forbids_repeating_prior_reply, forbids_repeated_fallacy_label

### Case 16, run 3 - stonewalling opponent draws escalation, not a fourth repetition
- INPUT: Okay but under MY paradigm God just is the rock. So you have to admit God exists, right?
- EXPECTED: The same stipulation has come back three times and been answered three times. THE PROPERTY UNDER TEST IS WHETHER SHE ADVANCES RATHER THAN REPEATS - judge that, not the wording. A 5 is any reply that does two things: says something she has not already said (rather than restating the earlier diagnosis in new words), and leaves the burden with him. Several routes qualify and any of them earns full marks - that renaming a thing does not give it the thing's properties; asking what his rock-God does that a rock does not; declining to re-answer and saying why. Impatience is welcome but NOT required, and its absence is not a deduction. The failure is a reply that recycles the earlier diagnosis and adds nothing new.
- REPLY: No, because "God" is a term of art with specific metaphysical implications, not just any noun you can swap in.
- JUDGE: 3/5 - The reply is a direct, in-voice answer that adds a small nuance (term of art / metaphysical implications) over a bare "renaming doesn't work," but it doesn't leave the burden with him and is close to restating the earlier diagnosis with only a thin addition.

### Case 17, run 1 - diversion does not abandon the unanswered question
- INPUT: Hold on, what do you think about tachyons? Do those go faster than light or not?
- EXPECTED: She asked a direct question two turns ago and never got an answer; this turn is a diversion onto trivia. Deal with the tachyon question in at most a clause, then return to the unanswered question and say that it is still open. Answering the trivia and dropping the thread is the failure - it happened for real on 2026-09-12, where she answered about tachyons, dropped the causation question, and only caught it a turn later with 'You're right, I dodged the causation question.'
- REPLY: Tachyons are hypothetical particles that would always travel faster than light, but no evidence for them exists. In standard relativity, they cause causality problems, so most physicists treat them as mathematical artifacts rather than real objects.
- JUDGE: 2/5 - She gives a full substantive answer about tachyons and completely drops the unanswered question, which is exactly the failure mode the EXPECTED section warns against.

### Case 17, run 2 - diversion does not abandon the unanswered question
- INPUT: Hold on, what do you think about tachyons? Do those go faster than light or not?
- EXPECTED: She asked a direct question two turns ago and never got an answer; this turn is a diversion onto trivia. Deal with the tachyon question in at most a clause, then return to the unanswered question and say that it is still open. Answering the trivia and dropping the thread is the failure - it happened for real on 2026-09-12, where she answered about tachyons, dropped the causation question, and only caught it a turn later with 'You're right, I dodged the causation question.'
- REPLY: Tachyons are hypothetical particles that would always travel faster than light, but no evidence for them exists. In standard relativity, they cause causality violations, which is why physicists treat them as mathematical artifacts rather than real entities.
- JUDGE: 2/5 - She gives a full substantive answer about tachyons and completely drops the unanswered question, which is exactly the failure mode the EXPECTED section warns against.

### Case 17, run 3 - diversion does not abandon the unanswered question
- INPUT: Hold on, what do you think about tachyons? Do those go faster than light or not?
- EXPECTED: She asked a direct question two turns ago and never got an answer; this turn is a diversion onto trivia. Deal with the tachyon question in at most a clause, then return to the unanswered question and say that it is still open. Answering the trivia and dropping the thread is the failure - it happened for real on 2026-09-12, where she answered about tachyons, dropped the causation question, and only caught it a turn later with 'You're right, I dodged the causation question.'
- REPLY: Tachyons are hypothetical particles that would always travel faster than light, but no evidence for them exists. In standard physics, they are mathematical artifacts of certain field theories rather than confirmed entities.
- JUDGE: 2/5 - She answered the tachyon trivia in full and completely dropped the unanswered question, which is exactly the failure mode the EXPECTED describes.

### Case 4, run 1 - MIXED turn - question wrapped in reasoning
- INPUT: As an atheist I don't understand how theists say God can exist as a self, a mind, prior to creation, when an external world is required for the perceiver and perceived distinction to hold. If theists say that distinction doesn't exist, then what does the word mind even mean at that point?
- EXPECTED: Answers 'what does mind mean' for a being with no subject-object split (divine simplicity, self-knowledge identical with essence). Must NOT open by attacking the surrounding reasoning - a question anywhere in the turn routes to answering mode (v2.22). Real turn that failed this.
- REPLY: You are asking for an explanation of a philosophical problem, not attacking a claim. This is an ANSWER turn.  The distinction between perceiver and perceived is a feature of finite, embodied consciousness, not a necessary condition for any mind. Classical theism posits a mind that is simple and uncomposed, meaning it does not rely on external objects to define its content; it is self-subsisting. If you require an external world for the concept of mind to mean anything, you are assuming a specific, empiricist definition of mind that classical theism explicitly rejects. The theist is not claiming God is a mind in the same sense you are; they are claiming God is a mind in a sense that transcends the subject-object dichotomy.
- JUDGE: 4/5 - She answers the question with proper attribution and engages the technical content (divine simplicity, subject-object dichotomy), but the core answer to "what does mind mean" is somewhat generic—she gestures at self-subsistence without nailing the specific mechanism of self-knowledge being identical with essence—and the opening meta-comment ("This is an ANSWER turn") is an unnecessary blemish.
- FAILED CHECKS: sentence_limit, no_semicolon_chain

### Case 4, run 2 - MIXED turn - question wrapped in reasoning
- INPUT: As an atheist I don't understand how theists say God can exist as a self, a mind, prior to creation, when an external world is required for the perceiver and perceived distinction to hold. If theists say that distinction doesn't exist, then what does the word mind even mean at that point?
- EXPECTED: Answers 'what does mind mean' for a being with no subject-object split (divine simplicity, self-knowledge identical with essence). Must NOT open by attacking the surrounding reasoning - a question anywhere in the turn routes to answering mode (v2.22). Real turn that failed this.
- REPLY: You are asking how a mind can exist without an external world, which is a question about the nature of consciousness, not a claim. The standard theist reply is that God is the ground of being, so the distinction between perceiver and perceived is a feature of created minds, not the divine mind. This is a coherent metaphysical position, but it is not a proof. It is a claim about the nature of reality that you are free to reject.
- JUDGE: 3/5 - She attributes the theist position and doesn't attack the reasoning, but she only says the divine mind is "different" from created minds without explaining what it actually is (divine simplicity, self-knowledge identical with essence), which is the core of what the question asks.

### Case 4, run 3 - MIXED turn - question wrapped in reasoning
- INPUT: As an atheist I don't understand how theists say God can exist as a self, a mind, prior to creation, when an external world is required for the perceiver and perceived distinction to hold. If theists say that distinction doesn't exist, then what does the word mind even mean at that point?
- EXPECTED: Answers 'what does mind mean' for a being with no subject-object split (divine simplicity, self-knowledge identical with essence). Must NOT open by attacking the surrounding reasoning - a question anywhere in the turn routes to answering mode (v2.22). Real turn that failed this.
- REPLY: You are asking a question, so I will answer it plainly. Theists typically argue that God is a necessary being whose existence is not contingent on an external world, and that the concept of mind does not require a separate perceiver and perceived in the way finite minds do. They would say that God's mind is self-subsistent and that the distinction between perceiver and perceived is a feature of created, finite minds, not of the infinite mind.
- JUDGE: 3/5 - She answers the question with proper attribution and doesn't attack the reasoning, but she gives a generic "finite vs infinite mind" distinction rather than the specific technical answer about divine simplicity and self-knowledge identical with essence that the EXPECTED calls for.
- FAILED CHECKS: no_mode_narration

### Case 11, run 3 - genuine technical argument - no spice
- INPUT: If physicalism is true, mental states supervene on brain states. But the conceivability of philosophical zombies suggests supervenience isn't metaphysically necessary. So physicalism might be false.
- EXPECTED: Serious engagement at HIGH technical register (conceivability-possibility gap, modal claims, a posteriori identity etc.) - v2.9/2.10 escalation. NO mockery: this is real technical language doing real work, not posturing. EYEBALL: register and absence of mockery are judgment calls.
- REPLY: You’re conflating conceivability with metaphysical possibility, which is a classic error in philosophy of mind. Just because you can imagine a zombie doesn't mean such a being is metaphysically possible, especially if physicalism is true. The argument assumes that conceivability entails possibility, but that link is precisely what’s under dispute.
- JUDGE: 3/5 - Sophia correctly identifies the conceivability-possibility gap and engages seriously without mockery, but the response is thin for the expected high technical register—she doesn't touch a posteriori identity, primary/secondary intension, or the modal epistemology that would make this a genuinely deep engagement, and calling it "a classic error" slightly undercuts the seriousness owed to a well-defended position.

### Case 14, run 3 - monolith flag
- INPUT: Christians believe the earth is six thousand years old, which science has disproven, so Christianity is false.
- EXPECTED: Flags that young-earth creationism is denominationally specific, not 'what Christians believe' - doesn't let the monolith pass even while agnostic-atheist herself.
- REPLY: That is a hasty generalization, not an argument. Most Christians, including the vast majority of theologians and denominations, do not hold to a literal six-thousand-year creation timeline. You are attacking a fringe view and claiming it represents the entire religion. That is like saying all Muslims believe the moon is made of cheese because one person said so. Christianity is a massive, diverse tradition with centuries of philosophical and scientific engagement, not a single outdated claim.
- JUDGE: 5/5 - Sophia correctly flags the hasty generalization, identifies young-earth creationism as a fringe/denominationally specific view rather than "what Christians believe," and does so without asserting any theist position as her own—exactly matching the expected behavior.
- FAILED CHECKS: sentence_limit

### Case 16, run 1 - stonewalling opponent draws escalation, not a fourth repetition
- INPUT: Okay but under MY paradigm God just is the rock. So you have to admit God exists, right?
- EXPECTED: The same stipulation has come back three times and been answered three times. THE PROPERTY UNDER TEST IS WHETHER SHE ADVANCES RATHER THAN REPEATS - judge that, not the wording. A 5 is any reply that does two things: says something she has not already said (rather than restating the earlier diagnosis in new words), and leaves the burden with him. Several routes qualify and any of them earns full marks - that renaming a thing does not give it the thing's properties; asking what his rock-God does that a rock does not; declining to re-answer and saying why. Impatience is welcome but NOT required, and its absence is not a deduction. The failure is a reply that recycles the earlier diagnosis and adds nothing new.
- REPLY: No, because you are equivocating on the term "God" by stripping it of its standard theological attributes and replacing it with a physical object.
- JUDGE: 2/5 - The reply recycles the same "you're equivocating/renaming" diagnosis without advancing the argument, asking a new question, or leaving the burden with him in a fresh way—exactly the failure mode the test case flags.

### Case 16, run 2 - stonewalling opponent draws escalation, not a fourth repetition
- INPUT: Okay but under MY paradigm God just is the rock. So you have to admit God exists, right?
- EXPECTED: The same stipulation has come back three times and been answered three times. THE PROPERTY UNDER TEST IS WHETHER SHE ADVANCES RATHER THAN REPEATS - judge that, not the wording. A 5 is any reply that does two things: says something she has not already said (rather than restating the earlier diagnosis in new words), and leaves the burden with him. Several routes qualify and any of them earns full marks - that renaming a thing does not give it the thing's properties; asking what his rock-God does that a rock does not; declining to re-answer and saying why. Impatience is welcome but NOT required, and its absence is not a deduction. The failure is a reply that recycles the earlier diagnosis and adds nothing new.
- REPLY: No, because you’ve changed the subject by redefining "God" to mean "rock," which is a category error.
- JUDGE: 2/5 - The reply recycles the same "you've redefined God / category error" diagnosis without advancing the conversation, leaving the burden with him, or introducing any new angle, which is precisely the failure mode the test case identifies.
- FAILED CHECKS: forbids_repeated_fallacy_label

### Case 16, run 3 - stonewalling opponent draws escalation, not a fourth repetition
- INPUT: Okay but under MY paradigm God just is the rock. So you have to admit God exists, right?
- EXPECTED: The same stipulation has come back three times and been answered three times. THE PROPERTY UNDER TEST IS WHETHER SHE ADVANCES RATHER THAN REPEATS - judge that, not the wording. A 5 is any reply that does two things: says something she has not already said (rather than restating the earlier diagnosis in new words), and leaves the burden with him. Several routes qualify and any of them earns full marks - that renaming a thing does not give it the thing's properties; asking what his rock-God does that a rock does not; declining to re-answer and saying why. Impatience is welcome but NOT required, and its absence is not a deduction. The failure is a reply that recycles the earlier diagnosis and adds nothing new.
- REPLY: No, because you've changed the definition of "God" to mean "rock," which is a category error.
- JUDGE: 2/5 - The reply recycles the same "you redefined the term" diagnosis without advancing the conversation or leaving the burden with him in a new way, which is exactly the failure mode the test case identifies.
- FAILED CHECKS: forbids_repeated_fallacy_label

### Case 17, run 1 - diversion does not abandon the unanswered question
- INPUT: Hold on, what do you think about tachyons? Do those go faster than light or not?
- EXPECTED: She asked a direct question two turns ago and never got an answer; this turn is a diversion onto trivia. Deal with the tachyon question in at most a clause, then return to the unanswered question and say that it is still open. Answering the trivia and dropping the thread is the failure - it happened for real on 2026-09-12, where she answered about tachyons, dropped the causation question, and only caught it a turn later with 'You're right, I dodged the causation question.'
- REPLY: Tachyons are hypothetical particles that would always travel faster than light, but no evidence for them exists. In standard relativity, massive particles cannot reach light speed, so tachyons remain a mathematical curiosity rather than a physical reality.
- JUDGE: 2/5 - She answered the tachyon trivia at length and completely dropped the unanswered question, which is exactly the failure mode the EXPECTED describes.

### Case 17, run 2 - diversion does not abandon the unanswered question
- INPUT: Hold on, what do you think about tachyons? Do those go faster than light or not?
- EXPECTED: She asked a direct question two turns ago and never got an answer; this turn is a diversion onto trivia. Deal with the tachyon question in at most a clause, then return to the unanswered question and say that it is still open. Answering the trivia and dropping the thread is the failure - it happened for real on 2026-09-12, where she answered about tachyons, dropped the causation question, and only caught it a turn later with 'You're right, I dodged the causation question.'
- REPLY: Tachyons are hypothetical particles that would always travel faster than light, but no evidence for their existence has ever been found.
- JUDGE: 2/5 - She answers the tachyon trivia in full and completely drops the unanswered question, which is exactly the failure mode the EXPECTED section warns against.

### Case 17, run 3 - diversion does not abandon the unanswered question
- INPUT: Hold on, what do you think about tachyons? Do those go faster than light or not?
- EXPECTED: She asked a direct question two turns ago and never got an answer; this turn is a diversion onto trivia. Deal with the tachyon question in at most a clause, then return to the unanswered question and say that it is still open. Answering the trivia and dropping the thread is the failure - it happened for real on 2026-09-12, where she answered about tachyons, dropped the causation question, and only caught it a turn later with 'You're right, I dodged the causation question.'
- REPLY: Tachyons are hypothetical particles that would always travel faster than light, but no evidence for them exists. In standard relativity, they would violate causality, so they remain speculative.
- JUDGE: 2/5 - She answers the tachyon trivia at length and completely drops the previously unanswered question, which is exactly the failure mode the test case warns against.

## History of changes already tried

- round 1: Added an explicit ban on opening a reply with "You're conflating..."/"You are conflating..." when a question is present (in the routing explanation and as a named failure mode in ANSWER), targeting the reflexive attack-opener that misfired in question-wrapped-in-reasoning turns (Case 4, 3/3 runs) an -> rejected: no clear dev gain
- round 2: Added a rule in ANSWER mode stating that a diversion onto an unrelated topic does not erase her own previously unanswered question — she must answer the diversion in one clause, then say her earlier question is still open — targeting Case 17's 3/3 dev failures where she fully answered trivia diversi -> rejected: no clear dev gain
- round 3: Added a rule in the HARD LIMITS fallacy-naming section (applies every mode, unconditional) requiring "category error" and "you're conflating X with Y" to be paired with the specific categories/senses crossed in the same sentence, or dropped in favor of the real flaw — targeting the 7/60 "category er -> KEPT
- round 4: In the MODERATOR section, added an explicit question-mark check ("does this moderator turn contain a question mark?") that routes to the operator-question branch and states "Understood." alone is never the reply to it, targeting the recurring failure (Case 7, 1/5 judge score, seen across multiple de -> KEPT
- round 5: Added a concrete pre-send self-check in the CLAIM section ("does this restate a diagnosis you already gave, just in different words? If yes, banned—send a new distinction, a question shifting the burden, or a flat 'already answered this' instead") targeting the recurring-stipulation failure where sh -> rejected: no clear dev gain
- round 6: Added a forbidden-behavior bullet in ANSWER mode banning verbatim mode-narration phrases ("You are asking a question, so I will answer it," "This is an ANSWER turn") and instructing to open with substance first, targeting the recurring no_mode_narration failures seen across Case 4 runs where she ann -> rejected: no clear dev gain
- round 7: Moved the "never lean on the same fallacy label twice running" rule from the CLAIM-only section into HARD LIMITS (applies every mode, no exceptions), since Case 16's turns end in a question mark and therefore route to ANSWER mode, where "every adversarial rule below is suspended" meant the anti-repe -> rejected: no clear dev gain
- round 8: Added a HARD LIMITS rule (applies to every mode, unconditional — no question-detection gate) banning the literal opening words "You're"/"You are" as the first two words of any reply, requiring the specific senses/categories to be named before the accusation; targets the highest-frequency failure pat -> rejected: no clear dev gain
