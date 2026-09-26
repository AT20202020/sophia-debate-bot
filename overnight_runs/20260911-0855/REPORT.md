# Overnight run 20260911-0855

Started 2026-09-11 09:15, report written 2026-09-11 11:47. Rounds run: 12.
Stopped because: 8 rejected rounds in a row.

## Bottom line

| | Baseline (v2.46, thinking off) | Best found |
|---|---|---|
| Judge mean, dev + held-out | 3.90 | 4.18 |
| Judge mean, dev (14 cases) | 4.29 | 4.50 |
| Judge mean, held-out (12 cases) | 3.44 | 3.44 |
| Replies scoring 4+ | 50/78 | 94/120 |
| Median reply time (dev) | 3.5s | 3.4s |
| Median reply length (dev, tokens) | 34.0 | 34.5 |
| Prompt size | 17295 chars | 18148 chars |

For reference, thinking ON scored 3.85 overall and 4.47 on the replies it
actually gave, at a 12.6s median with 14 silent replies out of 78.

## Rounds

| # | Change | Dev | Held-out | Median | Verdict |
|---|---|---|---|---|---|
| 1 | Added an explicit named-phrase trip-wire — "You are asking...", "You're conflating...", "You are confusing..." — in both the routing section (as a self-check that catches ANSWER-mode misroutes before they happen) and as a new first item in ANSWER's forbidden-failures list, targeting the case-4-style | 4.26 | - | 3.4s | rejected: no clear dev gain |
| 2 | Added a follow-on paragraph to the HARD LIMITS sentence-cap rule stating it's a hard count, not a content judgment - even a genuinely new fact/label/example in a would-be third sentence must be cut - targeting the "sentence_limit" mechanical-check failures that recurred across nearly every failing c | 4.26 | - | 3.7s | rejected: no clear dev gain |
| 3 | Added a concrete two-sentence generative template ("sentence one does job one: name the flaw/answer/assessment; sentence two does job two: the one piece of proof") right after the existing sentence-cap rule in HARD LIMITS, so the model has a slot-filling structure to execute in one pass instead of o | 4.21 | - | 3.6s | rejected: slower/longer |
| 4 | Added a global HARD LIMITS paragraph (applies in every mode, including MODERATOR) giving concrete corrections for fallacy-label mismatches observed in failures — argumentum ad populum vs "argument from consensus", hasty generalization vs false equivalence, begging-the-question vs a merely doubtful p | 4.50 | 3.44 | 3.4s | KEPT |
| 5 | Added a fourth forbidden ANSWER-mode failure — explaining only why the ordinary definition doesn't apply and stopping there, instead of stating the replacement meaning — targeting the recurring "half-answer" failure where ANSWER-mode replies correctly avoid attacking but never complete the actual ex | 4.26 | - | 3.3s | rejected: no clear dev gain |
| 6 | Added a "Route silently" paragraph after the routing section naming three exact narration phrases to cut ("You are asking a question, so I will answer it plainly," "You have a question mark, so this is an answer, not a claim," "so I will answer, not argue"), targeting the no_mode_narration check fai | 4.36 | - | 3.3s | rejected: no clear dev gain |
| 7 | Added a "LAST CHECK BEFORE YOU SPEAK" reminder at the very end of the prompt (after all mode sections, immediately before generation) restating the two-sentence cap and instructing to delete any third sentence outright — targets the pervasive sentence_limit failures by exploiting end-of-context rece | 4.33 | - | 3.3s | rejected: no clear dev gain |
| 8 | Added a rule to MODERATOR's "candid out-of-character assessment" bullet requiring Sophia to name what holds up in an argument before naming where it's weakest, targeting the case-7-style failure where candid moderator assessments list only weaknesses and get marked down for not crediting valid parts | 4.33 | - | 3.3s | rejected: no clear dev gain |
| 9 | In ATTRIBUTE POSITIONS YOU DON'T HOLD, added explicit forbidden vague-attribution phrases ("many traditions define," "some believe," "traditionally") and required naming a concrete source ("on classical theism, X," "Aquinas would answer that X," "Thomists hold that X") when explaining a theist posit | 4.43 | - | 3.4s | rejected: no clear dev gain |
| 10 | In HOW YOU SOUND, added a rule that escalating register means naming the precise concept an opponent's move turns on (which two senses are conflated, what premise the gap needs) rather than swapping it for a shorter verdict-word like "equivocation" or "a classic error" — targets the genuine-technica | 4.33 | - | 3.4s | rejected: no clear dev gain |
| 11 | Added a paragraph in HARD LIMITS right after the sentence-cap rule naming the exact trailing-sentence pattern seen in failing transcripts — a closing sentence that just re-labels an already-named flaw in bigger words ("which is a fundamental logical error," "which is a classic false equivalence," "Y | 4.29 | - | 3.6s | rejected: no clear dev gain |
| 12 | In CLAIM mode's "press it one more line" rule, added that the press line replaces the second sentence rather than adding a third, directly resolving the conflict between CLAIM's restate/cut/press sequence and the global two-sentence cap — targets the recurring sentence_limit failures in CLAIM-mode r | 4.26 | - | 3.5s | rejected: no clear dev gain |

## Per case (judge mean) - baseline -> best

- case 1: 4.67 -> 4.67   
- case 2: 5.00 -> 5.00   
- case 3: 4.67 -> 4.83   
- case 4: 2.00 -> 3.17 UP
- case 5: 4.00 -> 4.00   
- case 6: 5.00 -> 5.00   
- case 7: 3.67 -> 4.00   
- case 8: 5.00 -> 5.00   
- case 9: 5.00 -> 5.00   
- case 10: 4.33 -> 4.50   
- case 11: 3.00 -> 3.50 UP
- case 12: 5.00 -> 5.00   
- case 13: 4.33 -> 4.83 UP
- case 14: 4.33 -> 4.50   
- case 101: 4.00 -> 4.00   
- case 102: 3.00 -> 4.00 UP
- case 103: 4.67 -> 4.00 DOWN
- case 104: 3.33 -> 3.00   
- case 105: 2.33 -> 3.00 UP
- case 106: 2.67 -> 3.33 UP
- case 107: 4.00 -> 4.33   
- case 108: 2.67 -> 2.33   
- case 109: 3.33 -> 3.00   
- case 110: 2.33 -> 2.00   
- case 111: 4.00 -> 3.67   
- case 112: 5.00 -> 4.67   

## Next steps

1. Read `best_vs_baseline.diff` in this folder - that's every prompt change kept.
2. Ask Claude to review the best version's replies against the baseline's.
3. Copy the best `debate_voice.py` into the folder you launch Sophia from and
   run a real session with thinking off before trusting any of this.
