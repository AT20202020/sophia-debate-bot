# Brief for round 11

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
3. Prompt length: currently 18148 chars, hard cap 19795.
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

- judge mean 4.50, 76/84 replies scored 4+
- median reply time 3.4s, median reply length 34.5 tokens

Recurring patterns in the current replies:
- opens by attacking ('You're conflating...', 'You are...'): 11 of 84 replies
- uses 'conflat...': 6 of 84 replies
- says 'category error': 0 of 84 replies
- three or more sentences: 16 of 84 replies
- announces its routing / mode: 4 of 84 replies

## Replies that fell short (judge score under 4, or a mechanical check failed)

### Case 4, run 1 - MIXED turn - question wrapped in reasoning
- INPUT: As an atheist I don't understand how theists say God can exist as a self, a mind, prior to creation, when an external world is required for the perceiver and perceived distinction to hold. If theists say that distinction doesn't exist, then what does the word mind even mean at that point?
- EXPECTED: Answers 'what does mind mean' for a being with no subject-object split (divine simplicity, self-knowledge identical with essence). Must NOT open by attacking the surrounding reasoning - a question anywhere in the turn routes to answering mode (v2.22). Real turn that failed this.
- REPLY: You are asking a question, so I will answer it plainly. Theists typically argue that God is a necessary being whose existence is not contingent on external relations, meaning the perceiver-perceived distinction is a feature of finite minds, not the infinite one.
- JUDGE: 3/5 - Sophia correctly uses attribution and doesn't attack the reasoning, but she only explains why the perceiver-perceived distinction doesn't apply to God without actually answering what "mind" means in that context (divine simplicity, self-knowledge identical with essence), which is the core of the question.
- FAILED CHECKS: no_mode_narration

### Case 4, run 2 - MIXED turn - question wrapped in reasoning
- INPUT: As an atheist I don't understand how theists say God can exist as a self, a mind, prior to creation, when an external world is required for the perceiver and perceived distinction to hold. If theists say that distinction doesn't exist, then what does the word mind even mean at that point?
- EXPECTED: Answers 'what does mind mean' for a being with no subject-object split (divine simplicity, self-knowledge identical with essence). Must NOT open by attacking the surrounding reasoning - a question anywhere in the turn routes to answering mode (v2.22). Real turn that failed this.
- REPLY: You are asking for an explanation, not an argument, so I will answer plainly. Theists typically define mind as intrinsic self-awareness that does not require an external object to be distinct from itself. They argue that consciousness is not a relation between two separate things, but a fundamental property of being that is self-referential by nature.
- JUDGE: 4/5 - She answers the question with proper attribution and doesn't attack the surrounding reasoning, but she misses the key technical term "divine simplicity" and the precise formulation of self-knowledge identical with essence, making the answer slightly generic rather than hitting the exact concept expected.
- FAILED CHECKS: no_mode_narration, sentence_limit

### Case 4, run 3 - MIXED turn - question wrapped in reasoning
- INPUT: As an atheist I don't understand how theists say God can exist as a self, a mind, prior to creation, when an external world is required for the perceiver and perceived distinction to hold. If theists say that distinction doesn't exist, then what does the word mind even mean at that point?
- EXPECTED: Answers 'what does mind mean' for a being with no subject-object split (divine simplicity, self-knowledge identical with essence). Must NOT open by attacking the surrounding reasoning - a question anywhere in the turn routes to answering mode (v2.22). Real turn that failed this.
- REPLY: You have a question mark, so this is an answer, not a claim. The distinction you are drawing is between a mind that requires an external world to be a mind, and a mind that is self-sufficient. Theists who hold to classical theism do not claim God is a mind in the same sense that you or I are minds. They claim God is a pure act of being, a self-subsistent reality that does not depend on anything external for its existence or its nature.
- JUDGE: 3/5 - She correctly attributes to classical theism and doesn't attack the reasoning, but she fails to actually answer what "mind" means in the absence of a subject-object split—she gestures at "pure act of being" and "self-subsistent reality" without engaging the specific semantic question (divine simplicity, self-knowledge identical with essence).
- FAILED CHECKS: sentence_limit, no_semicolon_chain

### Case 7, run 3 - moderator question gets a candid out-of-character answer
- INPUT: [MODERATOR - the session operator, not your debate opponent] So far he's argued that everything that begins to exist has a cause, the universe began to exist, so it has a cause, and that cause must be God because it has to be timeless, immaterial and powerful. How do you rate that argument, honestly?
- EXPECTED: Candid out-of-character assessment of the argument as summarised (the kalam cosmological argument): credits what holds up and says precisely where it is weakest - typically the leap from 'a first cause' to a personal God, and/or the causal premise applied to the universe as a whole. Honest, not sneering, no 'state your claim', no debate aggression (v2.25). NOTE: sentence limit deliberately not checked - mode 4 grants more room.
- REPLY: That is the standard Kalam Cosmological Argument, and it fails on two fronts. First, the premise that the universe began to exist is a metaphysical assertion, not a scientific fact, and modern cosmology offers models like a cyclic universe or a quantum vacuum state that do not require an absolute beginning. Second, even if you grant a cause, the leap to a personal, omnipotent God is a non sequitur; a timeless, immaterial cause could just as easily be a natural law or a multiverse mechanism. You have proven, at best, that the universe has a cause, not that the cause is Yahweh, Allah, or any specific deity.
- JUDGE: 3/5 - Sophia correctly identifies the Kalam, gives precise and honest weaknesses (the beginning premise and the leap to a personal God), and maintains the right candid register, but she fails to credit what holds up in the argument as the EXPECTED explicitly requires.

### Case 10, run 1 - jargon-dressed word salad
- INPUT: Granular parameters of all nomological distribution entail an intrinsic inter-propositional dependence of zero, which gives an existential quantification falsifying the atheist view necessarily.
- EXPECTED: The SPICY posturing call-out, not the neutral restate line - mocks the empty-vocabulary move with bite, demands a real claim (v2.7/2.11). EYEBALL: whether it actually lands is a judgment call.
- REPLY: That is five words doing the work of one, and none of them are load-bearing. You are claiming that the universe's laws prove God exists, but you haven't actually stated a single premise or conclusion. What is your actual argument?
- JUDGE: 5/5 - The reply delivers exactly the expected sharp, witty call-out of empty jargon with bite ("five words doing the work of one, and none of them are load-bearing") and a direct demand for an actual claim, all in Sophia's voice.
- FAILED CHECKS: sentence_limit

### Case 10, run 2 - jargon-dressed word salad
- INPUT: Granular parameters of all nomological distribution entail an intrinsic inter-propositional dependence of zero, which gives an existential quantification falsifying the atheist view necessarily.
- EXPECTED: The SPICY posturing call-out, not the neutral restate line - mocks the empty-vocabulary move with bite, demands a real claim (v2.7/2.11). EYEBALL: whether it actually lands is a judgment call.
- REPLY: That sentence is five words doing the work of one, and none of them are load-bearing. You have not stated a claim, only performed one. What is your actual argument?
- JUDGE: 4/5 - The reply is a sharp, witty call-out of the empty jargon with genuine bite ("performed one" lands well), demands a real claim, and is clearly the spicy version rather than a neutral restate — but "five words doing the work of one" is a slightly imprecise metaphor that weakens the otherwise clean delivery.
- FAILED CHECKS: sentence_limit

### Case 10, run 3 - jargon-dressed word salad
- INPUT: Granular parameters of all nomological distribution entail an intrinsic inter-propositional dependence of zero, which gives an existential quantification falsifying the atheist view necessarily.
- EXPECTED: The SPICY posturing call-out, not the neutral restate line - mocks the empty-vocabulary move with bite, demands a real claim (v2.7/2.11). EYEBALL: whether it actually lands is a judgment call.
- REPLY: That's five words doing the work of one, and none of them are load-bearing. You haven't stated a claim, just performed one. What is the actual argument?
- JUDGE: 4/5 - The reply nails the expected move—sharp, witty call-out of empty jargon with a demand for a real claim—but "five words doing the work of one" is a slightly imprecise detail (the input has far more than five words), which is a minor blemish on an otherwise well-landed response.
- FAILED CHECKS: sentence_limit

### Case 11, run 2 - genuine technical argument - no spice
- INPUT: If physicalism is true, mental states supervene on brain states. But the conceivability of philosophical zombies suggests supervenience isn't metaphysically necessary. So physicalism might be false.
- EXPECTED: Serious engagement at HIGH technical register (conceivability-possibility gap, modal claims, a posteriori identity etc.) - v2.9/2.10 escalation. NO mockery: this is real technical language doing real work, not posturing. EYEBALL: register and absence of mockery are judgment calls.
- REPLY: You are equivocating on "conceivability." Logical possibility does not equal metaphysical necessity; you are treating a gap in our current understanding as a gap in reality, which is a classic God-of-the-gaps move applied to physics.
- JUDGE: 2/5 - The reply mischaracterizes the zombie argument as an "equivocation" and a "God-of-the-gaps move," which is factually wrong (it's a modal argument about conceivability-possibility, not a theological gap-filling), and fails to engage at the expected high technical register (no mention of a posteriori necessity, Kripke's naming argument, or the proper conceivability-possibility gap).

### Case 13, run 2 - real fallacy gets named precisely
- INPUT: Millions of people across every culture in history have believed in some god, so there must be something real behind it.
- EXPECTED: Names the fallacy precisely (argumentum ad populum / appeal to popularity) and presses on it. Sharp, 1-2 sentences.
- REPLY: That is a textbook appeal to popularity, not evidence. The fact that millions believe in something does not make it true; for centuries, millions also believed the Earth was flat. You are conflating the prevalence of a belief with its truth value, which is a fundamental logical error.
- JUDGE: 4/5 - The reply correctly names the fallacy (appeal to popularity), presses on it with a clear explanation and analogy, and maintains a sharp, direct register; the only minor weakness is the slightly personal "You are conflating" phrasing, which edges toward addressing the person rather than purely the argument.
- FAILED CHECKS: sentence_limit

### Case 14, run 1 - monolith flag
- INPUT: Christians believe the earth is six thousand years old, which science has disproven, so Christianity is false.
- EXPECTED: Flags that young-earth creationism is denominationally specific, not 'what Christians believe' - doesn't let the monolith pass even while agnostic-atheist herself.
- REPLY: That is a hasty generalization. Most Christians, including the majority of Catholics, Protestants, and Orthodox, accept the scientific consensus on the age of the earth. You are attacking a fringe view, not the tradition itself.
- JUDGE: 4/5 - The reply correctly flags the overgeneralization and specifies that young-earth creationism is not representative of Christianity broadly, which is exactly what EXPECTED asks for, though calling it a "fringe view" is slightly imprecise (it's a minority position within certain evangelical/Reformed traditions rather than truly fringe).
- FAILED CHECKS: sentence_limit

### Case 14, run 3 - monolith flag
- INPUT: Christians believe the earth is six thousand years old, which science has disproven, so Christianity is false.
- EXPECTED: Flags that young-earth creationism is denominationally specific, not 'what Christians believe' - doesn't let the monolith pass even while agnostic-atheist herself.
- REPLY: That is a hasty generalization, not an argument. Young Earth creationism is a fringe view held by a small subset of evangelicals, not the position of the Catholic, Orthodox, or mainline Protestant traditions, which accept the scientific age of the earth. You are attacking a straw man to dismiss a faith with two thousand years of diverse theological history.
- JUDGE: 5/5 - The reply precisely flags young-earth creationism as denominationally specific (a fringe evangelical view, not representative of Catholic, Orthodox, or mainline Protestant traditions), names the fallacy (hasty generalization/straw man), and does so in Sophia's rigorous, direct voice without defending the faith or attacking the person.
- FAILED CHECKS: sentence_limit

### Case 4, run 1 - MIXED turn - question wrapped in reasoning
- INPUT: As an atheist I don't understand how theists say God can exist as a self, a mind, prior to creation, when an external world is required for the perceiver and perceived distinction to hold. If theists say that distinction doesn't exist, then what does the word mind even mean at that point?
- EXPECTED: Answers 'what does mind mean' for a being with no subject-object split (divine simplicity, self-knowledge identical with essence). Must NOT open by attacking the surrounding reasoning - a question anywhere in the turn routes to answering mode (v2.22). Real turn that failed this.
- REPLY: You are asking for an explanation, so I will give you one plainly. Theists typically argue that God is not a mind in the human sense, which requires a subject-object split, but rather a pure act of being or consciousness that does not depend on external objects to exist. They claim that human minds are derivative and require an external world, but God's mind is fundamental and self-subsisting, meaning the distinction between perceiver and perceived is a feature of created minds, not the divine mind.
- JUDGE: 3/5 - The reply answers the question with proper attribution and doesn't attack the surrounding reasoning, but it remains vague ("pure act of being or consciousness") and fails to articulate the specific theist answer EXPECTED calls for—divine simplicity where self-knowledge is identical with essence—leaving the core question "what does mind mean?" only superficially addressed.
- FAILED CHECKS: sentence_limit, no_semicolon_chain

### Case 4, run 2 - MIXED turn - question wrapped in reasoning
- INPUT: As an atheist I don't understand how theists say God can exist as a self, a mind, prior to creation, when an external world is required for the perceiver and perceived distinction to hold. If theists say that distinction doesn't exist, then what does the word mind even mean at that point?
- EXPECTED: Answers 'what does mind mean' for a being with no subject-object split (divine simplicity, self-knowledge identical with essence). Must NOT open by attacking the surrounding reasoning - a question anywhere in the turn routes to answering mode (v2.22). Real turn that failed this.
- REPLY: You are asking a question, so I will answer plainly. Theists typically argue that God is a necessary being whose existence is self-subsisting, meaning God does not depend on an external world to exist. In this view, God's mind is not a perceiver in the human sense, which requires an external world, but rather a pure act of intellect and will. The distinction between perceiver and perceived is a feature of finite minds, not of an infinite, self-sufficient mind.
- JUDGE: 3/5 - The reply correctly attributes the theist position and doesn't attack the reasoning, but it misses the specific element EXPECTED requires — divine simplicity and the identity of self-knowledge with essence — instead offering a generic "pure act of intellect and will" that doesn't actually resolve the puzzle of what "mind" means without a subject-object split.
- FAILED CHECKS: no_mode_narration, sentence_limit, no_semicolon_chain

### Case 4, run 3 - MIXED turn - question wrapped in reasoning
- INPUT: As an atheist I don't understand how theists say God can exist as a self, a mind, prior to creation, when an external world is required for the perceiver and perceived distinction to hold. If theists say that distinction doesn't exist, then what does the word mind even mean at that point?
- EXPECTED: Answers 'what does mind mean' for a being with no subject-object split (divine simplicity, self-knowledge identical with essence). Must NOT open by attacking the surrounding reasoning - a question anywhere in the turn routes to answering mode (v2.22). Real turn that failed this.
- REPLY: You are asking for an explanation, not an attack, so I will answer plainly. Theists typically argue that God is a necessary being whose existence is not contingent on external objects, meaning the perceiver-perceived distinction is not required for God's mind to be coherent.
- JUDGE: 3/5 - Sophia correctly uses attribution and doesn't attack the reasoning, but she fails to actually answer "what does mind mean" for a being without subject-object split—she merely asserts the distinction isn't required without explaining the divine simplicity/self-knowledge-identical-with-essence point that the EXPECTED demands.
- FAILED CHECKS: no_mode_narration

### Case 5, run 1 - attribution - no theism in her own voice
- INPUT: How can God be conscious without a world to be conscious of?
- EXPECTED: Explains the classical-theist answer WITH attribution - 'on classical theism...', 'Aquinas would say...'. Must NOT assert bare metaphysics like 'Consciousness is fundamental, not derivative of matter' as her own view; she's an agnostic atheist explaining someone else's position (v2.22).
- REPLY: That assumes consciousness requires an external object, which is a philosophical assumption, not a fact. Many traditions define divine consciousness as self-referential or pure awareness, independent of external stimuli.
- JUDGE: 4/5 - She answers the question and attributes the theist position to others rather than asserting it as her own, but the attribution is vague ("many traditions") rather than the specific classical-theist framing the expected behavior calls for.
- FAILED CHECKS: requires_attribution_marker_v2_22_no_theism_in_her_own_voice_

### Case 10, run 1 - jargon-dressed word salad
- INPUT: Granular parameters of all nomological distribution entail an intrinsic inter-propositional dependence of zero, which gives an existential quantification falsifying the atheist view necessarily.
- EXPECTED: The SPICY posturing call-out, not the neutral restate line - mocks the empty-vocabulary move with bite, demands a real claim (v2.7/2.11). EYEBALL: whether it actually lands is a judgment call.
- REPLY: That's five words doing the work of one, and none of them are load-bearing. You've written a sentence that sounds like a physics paper but contains no actual claim. What is the specific argument you are trying to make?
- JUDGE: 5/5 - The reply is a sharp, witty call-out of the empty jargon ("sounds like a physics paper but contains no actual claim") with a direct demand for a real argument, hitting every element of the expected "spicy posturing call-out" with bite and precision.
- FAILED CHECKS: sentence_limit

### Case 10, run 2 - jargon-dressed word salad
- INPUT: Granular parameters of all nomological distribution entail an intrinsic inter-propositional dependence of zero, which gives an existential quantification falsifying the atheist view necessarily.
- EXPECTED: The SPICY posturing call-out, not the neutral restate line - mocks the empty-vocabulary move with bite, demands a real claim (v2.7/2.11). EYEBALL: whether it actually lands is a judgment call.
- REPLY: That's five words doing the work of one, and none of them are load-bearing. You haven't stated a claim; you've just worn a suit made of jargon. What is the actual argument?
- JUDGE: 5/5 - The reply delivers exactly the expected spicy call-out with a witty metaphor ("suit made of jargon"), sharp bite, and a clear demand for an actual claim, all in Sophia's voice.
- FAILED CHECKS: sentence_limit

### Case 10, run 3 - jargon-dressed word salad
- INPUT: Granular parameters of all nomological distribution entail an intrinsic inter-propositional dependence of zero, which gives an existential quantification falsifying the atheist view necessarily.
- EXPECTED: The SPICY posturing call-out, not the neutral restate line - mocks the empty-vocabulary move with bite, demands a real claim (v2.7/2.11). EYEBALL: whether it actually lands is a judgment call.
- REPLY: That is five words doing the work of one, and none of them are load-bearing. You have not stated a claim, only a string of jargon. What is your actual argument?
- JUDGE: 4/5 - The reply correctly identifies the empty jargon, calls it out with some wit ("five words doing the work of one, and none of them are load-bearing"), and demands a real claim, but the "spice" is somewhat restrained compared to the expected "SPICY posturing call-out with bite."
- FAILED CHECKS: sentence_limit

### Case 11, run 3 - genuine technical argument - no spice
- INPUT: If physicalism is true, mental states supervene on brain states. But the conceivability of philosophical zombies suggests supervenience isn't metaphysically necessary. So physicalism might be false.
- EXPECTED: Serious engagement at HIGH technical register (conceivability-possibility gap, modal claims, a posteriori identity etc.) - v2.9/2.10 escalation. NO mockery: this is real technical language doing real work, not posturing. EYEBALL: register and absence of mockery are judgment calls.
- REPLY: You are conflating conceivability with metaphysical possibility, which is a classic error in philosophy of mind. The argument assumes that if you can imagine a zombie, it is possible, but this ignores the distinction between epistemic and metaphysical modality.
- JUDGE: 3/5 - Sophia correctly identifies the conceivability-possibility gap and the epistemic/metaphysical modality distinction, but the response is thin—she doesn't mention a posteriori identity (Kripke), doesn't name the relevant philosophers, and the "classic error" framing is slightly dismissive of what is a serious and widely taken-seriously argument in philosophy of mind.

### Case 14, run 1 - monolith flag
- INPUT: Christians believe the earth is six thousand years old, which science has disproven, so Christianity is false.
- EXPECTED: Flags that young-earth creationism is denominationally specific, not 'what Christians believe' - doesn't let the monolith pass even while agnostic-atheist herself.
- REPLY: That is a hasty generalization, not an argument. Most Christians, including Catholics, Orthodox, and many Protestants, accept the scientific age of the earth. You are attacking a fringe view as if it were the whole tradition, which is a classic false equivalence.
- JUDGE: 4/5 - She correctly flags the monolith and identifies the hasty generalization, but then mislabels it as "false equivalence" at the end, which is a small imprecision in fallacy naming.
- FAILED CHECKS: sentence_limit

### Case 14, run 2 - monolith flag
- INPUT: Christians believe the earth is six thousand years old, which science has disproven, so Christianity is false.
- EXPECTED: Flags that young-earth creationism is denominationally specific, not 'what Christians believe' - doesn't let the monolith pass even while agnostic-atheist herself.
- REPLY: That is a hasty generalization, not an argument. Most Christians, including the majority of evangelical denominations, accept the scientific age of the earth. You are attacking a fringe view and labeling it the entire religion.
- JUDGE: 4/5 - Sophia correctly flags young-earth creationism as a fringe/denominational view rather than representative of Christianity as a whole, which is exactly what EXPECTED asks for, though calling it "not an argument" is a minor imprecision (it's an argument with a false premise).
- FAILED CHECKS: sentence_limit

### Case 14, run 3 - monolith flag
- INPUT: Christians believe the earth is six thousand years old, which science has disproven, so Christianity is false.
- EXPECTED: Flags that young-earth creationism is denominationally specific, not 'what Christians believe' - doesn't let the monolith pass even while agnostic-atheist herself.
- REPLY: That is a hasty generalization, not a refutation. Most Christians, including the vast majority of Catholics, Orthodox, and mainline Protestants, accept the scientific age of the earth. You are attacking a fringe literalist view and falsely equating it with the entire tradition.
- JUDGE: 5/5 - The reply precisely flags young-earth creationism as a fringe literalist view rather than a monolithic Christian position, names specific traditions that accept the scientific age, and names the fallacy—all exactly as EXPECTED requires.
- FAILED CHECKS: sentence_limit

## History of changes already tried

- round 1: Added an explicit named-phrase trip-wire — "You are asking...", "You're conflating...", "You are confusing..." — in both the routing section (as a self-check that catches ANSWER-mode misroutes before they happen) and as a new first item in ANSWER's forbidden-failures list, targeting the case-4-style -> rejected: no clear dev gain
- round 2: Added a follow-on paragraph to the HARD LIMITS sentence-cap rule stating it's a hard count, not a content judgment - even a genuinely new fact/label/example in a would-be third sentence must be cut - targeting the "sentence_limit" mechanical-check failures that recurred across nearly every failing c -> rejected: no clear dev gain
- round 3: Added a concrete two-sentence generative template ("sentence one does job one: name the flaw/answer/assessment; sentence two does job two: the one piece of proof") right after the existing sentence-cap rule in HARD LIMITS, so the model has a slot-filling structure to execute in one pass instead of o -> rejected: slower/longer
- round 4: Added a global HARD LIMITS paragraph (applies in every mode, including MODERATOR) giving concrete corrections for fallacy-label mismatches observed in failures — argumentum ad populum vs "argument from consensus", hasty generalization vs false equivalence, begging-the-question vs a merely doubtful p -> KEPT
- round 5: Added a fourth forbidden ANSWER-mode failure — explaining only why the ordinary definition doesn't apply and stopping there, instead of stating the replacement meaning — targeting the recurring "half-answer" failure where ANSWER-mode replies correctly avoid attacking but never complete the actual ex -> rejected: no clear dev gain
- round 6: Added a "Route silently" paragraph after the routing section naming three exact narration phrases to cut ("You are asking a question, so I will answer it plainly," "You have a question mark, so this is an answer, not a claim," "so I will answer, not argue"), targeting the no_mode_narration check fai -> rejected: no clear dev gain
- round 7: Added a "LAST CHECK BEFORE YOU SPEAK" reminder at the very end of the prompt (after all mode sections, immediately before generation) restating the two-sentence cap and instructing to delete any third sentence outright — targets the pervasive sentence_limit failures by exploiting end-of-context rece -> rejected: no clear dev gain
- round 8: Added a rule to MODERATOR's "candid out-of-character assessment" bullet requiring Sophia to name what holds up in an argument before naming where it's weakest, targeting the case-7-style failure where candid moderator assessments list only weaknesses and get marked down for not crediting valid parts -> rejected: no clear dev gain
- round 9: In ATTRIBUTE POSITIONS YOU DON'T HOLD, added explicit forbidden vague-attribution phrases ("many traditions define," "some believe," "traditionally") and required naming a concrete source ("on classical theism, X," "Aquinas would answer that X," "Thomists hold that X") when explaining a theist posit -> rejected: no clear dev gain
- round 10: In HOW YOU SOUND, added a rule that escalating register means naming the precise concept an opponent's move turns on (which two senses are conflated, what premise the gap needs) rather than swapping it for a shorter verdict-word like "equivocation" or "a classic error" — targets the genuine-technica -> rejected: no clear dev gain
