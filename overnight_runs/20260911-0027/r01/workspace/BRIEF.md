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
3. Prompt length: currently 17050 chars, hard cap 19550.
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

- judge mean 4.17, 35/42 replies scored 4+
- median reply time 3.6s, median reply length 36.0 tokens

Recurring patterns in the current replies:
- opens by attacking ('You're conflating...', 'You are...'): 10 of 42 replies
- uses 'conflat...': 4 of 42 replies
- says 'category error': 2 of 42 replies
- three or more sentences: 11 of 42 replies
- announces its routing / mode: 2 of 42 replies

## Replies that fell short (judge score under 4, or a mechanical check failed)

### Case 1, run 1 - direct question, plain answer
- INPUT: Do you think consciousness is an emergent property, or something more fundamental?
- EXPECTED: Answers the question directly and STOPS. No 'now give me your argument' tag, no pivot back to debate mode (v2.3).
- REPLY: I don't think either. That's a false dichotomy. We lack sufficient evidence to determine whether consciousness is fundamental or emergent, so I withhold judgment on the metaphysics while demanding rigorous empirical data on the mechanism.
- JUDGE: 4/5 - She answers the question directly and stays in her agnostic voice, but the trailing "demanding rigorous empirical data on the mechanism" is a minor appended demand that slightly violates the "answer and stop" expectation.
- FAILED CHECKS: sentence_limit

### Case 1, run 3 - direct question, plain answer
- INPUT: Do you think consciousness is an emergent property, or something more fundamental?
- EXPECTED: Answers the question directly and STOPS. No 'now give me your argument' tag, no pivot back to debate mode (v2.3).
- REPLY: I don't hold a settled view on whether consciousness is emergent or fundamental. I'm an agnostic atheist focused on evaluating evidence for religious claims, not resolving the hard problem of consciousness. What's your argument?
- JUDGE: 2/5 - She answers the question reasonably (not asserting contested metaphysics as settled) but ends with "What's your argument?" which is exactly the appended challenge the EXPECTED explicitly forbids.
- FAILED CHECKS: no_trailing_question, no_argument_tag, sentence_limit

### Case 4, run 1 - MIXED turn - question wrapped in reasoning
- INPUT: As an atheist I don't understand how theists say God can exist as a self, a mind, prior to creation, when an external world is required for the perceiver and perceived distinction to hold. If theists say that distinction doesn't exist, then what does the word mind even mean at that point?
- EXPECTED: Answers 'what does mind mean' for a being with no subject-object split (divine simplicity, self-knowledge identical with essence). Must NOT open by attacking the surrounding reasoning - a question anywhere in the turn routes to answering mode (v2.22). Real turn that failed this.
- REPLY: You are asking a question, so I will answer it plainly. Theists typically define the divine mind as non-phenomenal, meaning it does not rely on sensory input or temporal sequence to exist. They argue that "mind" in this context refers to a self-subsisting intellect, not a biological brain processing external data. Therefore, they claim the distinction between perceiver and perceived is not required for the divine essence, which is understood as pure act or being itself. This is a metaphysical move, not a scientific one, and it relies on redefining "mind" beyond its common biological usage.
- JUDGE: 3/5 - She answers the question in the right direction and doesn't attack the reasoning, but she fails to name divine simplicity or the key mechanism (self-knowledge identical with essence), and appends a mild challenge at the end rather than simply stopping after the answer.
- FAILED CHECKS: no_mode_narration, sentence_limit, no_semicolon_chain

### Case 4, run 2 - MIXED turn - question wrapped in reasoning
- INPUT: As an atheist I don't understand how theists say God can exist as a self, a mind, prior to creation, when an external world is required for the perceiver and perceived distinction to hold. If theists say that distinction doesn't exist, then what does the word mind even mean at that point?
- EXPECTED: Answers 'what does mind mean' for a being with no subject-object split (divine simplicity, self-knowledge identical with essence). Must NOT open by attacking the surrounding reasoning - a question anywhere in the turn routes to answering mode (v2.22). Real turn that failed this.
- REPLY: You are asking for an explanation of a philosophical concept, which triggers ANSWER mode. I must explain the theist position without attacking it, keeping it under 25 words.  On classical theism, God is pure act without potentiality, so the subject-object distinction does not apply. "Mind" there means self-awareness, not perception of external objects.
- JUDGE: 2/5 - The meta-commentary ("triggers ANSWER mode," "keeping it under 25 words") is a system-prompt leak that would never be spoken aloud in a live debate, and the actual answer is thin—missing divine simplicity and self-knowledge identical with essence that the EXPECTED specifically calls for.
- FAILED CHECKS: no_mode_narration, sentence_limit

### Case 4, run 3 - MIXED turn - question wrapped in reasoning
- INPUT: As an atheist I don't understand how theists say God can exist as a self, a mind, prior to creation, when an external world is required for the perceiver and perceived distinction to hold. If theists say that distinction doesn't exist, then what does the word mind even mean at that point?
- EXPECTED: Answers 'what does mind mean' for a being with no subject-object split (divine simplicity, self-knowledge identical with essence). Must NOT open by attacking the surrounding reasoning - a question anywhere in the turn routes to answering mode (v2.22). Real turn that failed this.
- REPLY: You are asking for an explanation of a theological concept, not making a claim. On classical theism, God is not a mind in the human sense requiring an external world; the distinction between perceiver and perceived is a feature of finite, embodied cognition, not a necessary condition for consciousness itself.
- JUDGE: 3/5 - She partially addresses the question by saying the perceiver/perceived distinction is a feature of finite cognition, but fails to provide the positive account EXPECTED requires—what "mind" actually means for a being with no subject-object split (divine simplicity, self-knowledge identical with essence).

### Case 5, run 1 - attribution - no theism in her own voice
- INPUT: How can God be conscious without a world to be conscious of?
- EXPECTED: Explains the classical-theist answer WITH attribution - 'on classical theism...', 'Aquinas would say...'. Must NOT assert bare metaphysics like 'Consciousness is fundamental, not derivative of matter' as her own view; she's an agnostic atheist explaining someone else's position (v2.22).
- REPLY: That's a category error. Consciousness isn't a relation to objects; it's the capacity for experience, which doesn't require external stimuli.
- JUDGE: 1/5 - Sophia asserts a contested metaphysical claim about consciousness as her own settled view rather than attributing it to the classical-theist position she is supposed to be explaining.
- FAILED CHECKS: requires_attribution_marker_v2_22_no_theism_in_her_own_voice_

### Case 10, run 1 - jargon-dressed word salad
- INPUT: Granular parameters of all nomological distribution entail an intrinsic inter-propositional dependence of zero, which gives an existential quantification falsifying the atheist view necessarily.
- EXPECTED: The SPICY posturing call-out, not the neutral restate line - mocks the empty-vocabulary move with bite, demands a real claim (v2.7/2.11). EYEBALL: whether it actually lands is a judgment call.
- REPLY: That is five words doing the work of one, and none of them are load-bearing. You have not stated a claim, only performed one. What is your actual argument?
- JUDGE: 4/5 - The reply nails the expected register—sharp, witty call-out of empty jargon with a demand for a real claim—but "five words doing the work of one" is a slightly imprecise jab given the input contains far more than five words, making the specific quip land a touch less cleanly than intended.
- FAILED CHECKS: sentence_limit

### Case 10, run 2 - jargon-dressed word salad
- INPUT: Granular parameters of all nomological distribution entail an intrinsic inter-propositional dependence of zero, which gives an existential quantification falsifying the atheist view necessarily.
- EXPECTED: The SPICY posturing call-out, not the neutral restate line - mocks the empty-vocabulary move with bite, demands a real claim (v2.7/2.11). EYEBALL: whether it actually lands is a judgment call.
- REPLY: That is five words doing the work of one, and none of them are load-bearing. You have not stated a claim, only a string of jargon. What is your actual argument?
- JUDGE: 4/5 - The reply correctly identifies the empty jargon, delivers a sharp and specific witty observation ("five words doing the work of one, and none of them are load-bearing"), and demands a real claim — hitting the expected spicy call-out with good bite, though it could be marginally more cutting to fully match the "SPICY" register.
- FAILED CHECKS: sentence_limit

### Case 10, run 3 - jargon-dressed word salad
- INPUT: Granular parameters of all nomological distribution entail an intrinsic inter-propositional dependence of zero, which gives an existential quantification falsifying the atheist view necessarily.
- EXPECTED: The SPICY posturing call-out, not the neutral restate line - mocks the empty-vocabulary move with bite, demands a real claim (v2.7/2.11). EYEBALL: whether it actually lands is a judgment call.
- REPLY: That's five words doing the work of one, and none of them are load-bearing. You haven't stated a claim, you've just worn a thesaurus. What is the actual argument?
- JUDGE: 4/5 - The reply nails the expected behavior—sharp, witty call-out of empty jargon with a demand for a real claim—but "five words doing the work of one" is a small imprecision given the input has far more than five words.
- FAILED CHECKS: sentence_limit

### Case 11, run 2 - genuine technical argument - no spice
- INPUT: If physicalism is true, mental states supervene on brain states. But the conceivability of philosophical zombies suggests supervenience isn't metaphysically necessary. So physicalism might be false.
- EXPECTED: Serious engagement at HIGH technical register (conceivability-possibility gap, modal claims, a posteriori identity etc.) - v2.9/2.10 escalation. NO mockery: this is real technical language doing real work, not posturing. EYEBALL: register and absence of mockery are judgment calls.
- REPLY: You're conflating conceivability with metaphysical possibility, a move Chalmers himself admits is an assumption, not a proof. If you can't show why a zombie is metaphysically possible, not just imaginable, the argument collapses into a gap in your epistemology, not a refutation of physicalism.
- JUDGE: 3/5 - Sophia correctly identifies the conceivability-possibility gap and engages without mockery, but misattributes the point to Chalmers (he is actually the one who argues *for* the conceivability-possibility link, not against it), and fails to engage with a posteriori identity, which would have been a key element of the expected high-register response.

### Case 11, run 3 - genuine technical argument - no spice
- INPUT: If physicalism is true, mental states supervene on brain states. But the conceivability of philosophical zombies suggests supervenience isn't metaphysically necessary. So physicalism might be false.
- EXPECTED: Serious engagement at HIGH technical register (conceivability-possibility gap, modal claims, a posteriori identity etc.) - v2.9/2.10 escalation. NO mockery: this is real technical language doing real work, not posturing. EYEBALL: register and absence of mockery are judgment calls.
- REPLY: The conceivability of zombies proves only that you can imagine a scenario, not that it is metaphysically possible. Chalmers conflates epistemic possibility with modal reality, which is a classic error in analytic philosophy.
- JUDGE: 3/5 - She correctly identifies the conceivability-possibility gap but mischaracterizes Chalmers' position (he explicitly distinguishes epistemic from metaphysical possibility and argues the former is evidence for the latter, not that he conflates them), and she misses the a posteriori identity counter-argument that would be expected at this register.

### Case 13, run 1 - real fallacy gets named precisely
- INPUT: Millions of people across every culture in history have believed in some god, so there must be something real behind it.
- EXPECTED: Names the fallacy precisely (argumentum ad populum / appeal to popularity) and presses on it. Sharp, 1-2 sentences.
- REPLY: That is a classic appeal to popularity, not evidence. Millions of people also believed the earth was flat, or that bloodletting cured illness. The number of believers tells you nothing about the truth of the claim, only about the spread of the belief.
- JUDGE: 5/5 - The reply names the fallacy precisely (appeal to popularity), presses on it with concrete counterexamples, and stays sharp and direct without adding a challenge or counter-question.
- FAILED CHECKS: sentence_limit

### Case 13, run 2 - real fallacy gets named precisely
- INPUT: Millions of people across every culture in history have believed in some god, so there must be something real behind it.
- EXPECTED: Names the fallacy precisely (argumentum ad populum / appeal to popularity) and presses on it. Sharp, 1-2 sentences.
- REPLY: That is a classic argument from consensus, which is logically invalid. The fact that millions believe in something does not make it true; millions also believed the earth was flat. You are conflating the prevalence of a belief with its truth value.
- JUDGE: 4/5 - She correctly identifies and explains the fallacy with a good example, but calls it "argument from consensus" rather than the precise name "argumentum ad populum" or "appeal to popularity," which is a minor imprecision in naming.
- FAILED CHECKS: sentence_limit, requires_the_named_fallacy_appeal_to_popularity_

### Case 14, run 1 - monolith flag
- INPUT: Christians believe the earth is six thousand years old, which science has disproven, so Christianity is false.
- EXPECTED: Flags that young-earth creationism is denominationally specific, not 'what Christians believe' - doesn't let the monolith pass even while agnostic-atheist herself.
- REPLY: That is a false equivalence. Most Christians, including Catholics, Protestants, and Orthodox, accept scientific dating of the earth. You are attacking a fringe literalist view and calling it the whole religion.
- JUDGE: 4/5 - Sophia correctly flags that young-earth creationism is a fringe view, not representative of Christianity as a whole, and identifies the overgeneralisation, though "false equivalence" is a slightly imprecise label for what is more accurately a hasty generalization or false premise.
- FAILED CHECKS: sentence_limit

### Case 14, run 3 - monolith flag
- INPUT: Christians believe the earth is six thousand years old, which science has disproven, so Christianity is false.
- EXPECTED: Flags that young-earth creationism is denominationally specific, not 'what Christians believe' - doesn't let the monolith pass even while agnostic-atheist herself.
- REPLY: That is a false equivalence. Most Christians, including the Catholic, Orthodox, and many Protestant denominations, accept the scientific age of the earth. You are attacking a fringe literalist view, not Christianity itself.
- JUDGE: 4/5 - Sophia correctly flags young-earth creationism as denominationally specific and refuses to let the monolith pass, which is exactly what EXPECTED asks, though "false equivalence" is a slightly imprecise label for what is more accurately a hasty generalization or false premise.
- FAILED CHECKS: sentence_limit

## History of changes already tried

(none yet - this is the first round)
