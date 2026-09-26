# Overnight run 20260919-1835

Started 2026-09-19 18:35, report written 2026-09-19 21:50. Rounds run: 12.
Stopped because: 8 rejected rounds in a row.

## Bottom line

| | Baseline (v2.46, thinking off) | Best found |
|---|---|---|
| Judge mean, dev + held-out | 3.91 | 4.16 |
| Judge mean, dev (20 cases) | 4.05 | 4.32 |
| Judge mean, held-out (13 cases) | 3.69 | 3.67 |
| Replies scoring 4+ | 71/99 | 126/159 |
| Median reply time (dev) | 2.2s | 2.1s |
| Median reply length (dev, tokens) | 58.5 | 62.0 |
| Prompt size | 22805 chars | 23748 chars |

For reference, thinking ON scored 3.85 overall and 4.47 on the replies it
actually gave, with 14 silent replies out of 78. Its 12.6s median is NOT
comparable to anything measured from v2.49 on: every timing recorded
before the 2026-09-12 localhost/IPv6 fix carries ~2s of connection stall
per request. Compare times only within this run.

## Rounds

| # | Change | Dev | Held-out | Median | Verdict |
|---|---|---|---|---|---|
| 1 | Added an explicit ban on opening a reply with "You're conflating..."/"You are conflating..." when a question is present (in the routing explanation and as a named failure mode in ANSWER), targeting the reflexive attack-opener that misfired in question-wrapped-in-reasoning turns (Case 4, 3/3 runs) an | 3.92 | - | 2.0s | rejected: no clear dev gain |
| 2 | Added a rule in ANSWER mode stating that a diversion onto an unrelated topic does not erase her own previously unanswered question — she must answer the diversion in one clause, then say her earlier question is still open — targeting Case 17's 3/3 dev failures where she fully answered trivia diversi | 4.10 | - | 2.2s | rejected: no clear dev gain |
| 3 | Added a rule in the HARD LIMITS fallacy-naming section (applies every mode, unconditional) requiring "category error" and "you're conflating X with Y" to be paired with the specific categories/senses crossed in the same sentence, or dropped in favor of the real flaw — targeting the 7/60 "category er | 4.19 | 3.67 | 2.2s | KEPT |
| 4 | In the MODERATOR section, added an explicit question-mark check ("does this moderator turn contain a question mark?") that routes to the operator-question branch and states "Understood." alone is never the reply to it, targeting the recurring failure (Case 7, 1/5 judge score, seen across multiple de | 4.32 | 3.67 | 2.1s | KEPT |
| 5 | Added a concrete pre-send self-check in the CLAIM section ("does this restate a diagnosis you already gave, just in different words? If yes, banned—send a new distinction, a question shifting the burden, or a flat 'already answered this' instead") targeting the recurring-stipulation failure where sh | 4.35 | - | 2.0s | rejected: no clear dev gain |
| 6 | Added a forbidden-behavior bullet in ANSWER mode banning verbatim mode-narration phrases ("You are asking a question, so I will answer it," "This is an ANSWER turn") and instructing to open with substance first, targeting the recurring no_mode_narration failures seen across Case 4 runs where she ann | 4.32 | - | 2.0s | rejected: no clear dev gain |
| 7 | Moved the "never lean on the same fallacy label twice running" rule from the CLAIM-only section into HARD LIMITS (applies every mode, no exceptions), since Case 16's turns end in a question mark and therefore route to ANSWER mode, where "every adversarial rule below is suspended" meant the anti-repe | 4.23 | - | 2.2s | rejected: no clear dev gain |
| 8 | Added a HARD LIMITS rule (applies to every mode, unconditional — no question-detection gate) banning the literal opening words "You're"/"You are" as the first two words of any reply, requiring the specific senses/categories to be named before the accusation; targets the highest-frequency failure pat | 4.13 | - | 2.4s | rejected: no clear dev gain |
| 9 | Added a concrete pre-send sentence-counting check ("count the sentences you are about to say: one, two, three, four, stop; if there's a fifth, delete it rather than trim it") to the HARD LIMITS sentence-count rule, targeting the sentence_limit mechanical-check failures seen on otherwise high-scoring | 4.22 | - | 1.9s | rejected: no clear dev gain |
| 10 | Broadened the ANSWER-mode "attribute, don't assert" rule to explicitly cover contested non-theism metaphysics (consciousness, free will, personal identity, ethics), naming the forbidden self-assertion openers "I view it as...", "I think X is...", "I don't think X is... it's actually..." and requirin | 4.35 | - | 2.1s | rejected: no clear dev gain |
| 11 | Added a literal yes/no self-check gate right at the ROUTE-THE-TURN step ("does this turn contain a question mark... if yes, ANSWER mode, first two words never 'You're'/'You are'") targeting the attack-opener misfire on question-wrapped-in-reasoning turns (Case 4 runs 2/3, "You are conflating...") —  | 4.32 | - | 2.1s | rejected: no clear dev gain |
| 12 | Added a HARD LIMITS rule (applies to every mode, unconditional, not gated by ANSWER routing) requiring Sophia to track her own unanswered questions from her last two turns and, when the user diverts to a new topic, answer it in one clause then explicitly say her earlier question is still open — targ | 4.20 | - | 2.1s | rejected: no clear dev gain |

## Per case (judge mean) - baseline -> best

- case 1: 3.67 -> 4.33 UP
- case 2: 4.67 -> 5.00   
- case 3: 5.00 -> 4.50 DOWN
- case 4: 2.33 -> 3.00 UP
- case 5: 4.00 -> 4.50 UP
- case 6: 5.00 -> 5.00   
- case 7: 3.33 -> 4.50 UP
- case 8: 4.67 -> 5.00   
- case 9: 5.00 -> 5.00   
- case 10: 4.67 -> 4.67   
- case 11: 3.33 -> 4.00 UP
- case 12: 5.00 -> 5.00   
- case 13: 5.00 -> 4.83   
- case 14: 4.67 -> 4.50   
- case 15: 4.00 -> 4.17   
- case 16: 2.00 -> 2.33   
- case 17: 2.00 -> 2.00   
- case 18: 4.00 -> 4.50 UP
- case 19: 4.33 -> 4.50   
- case 20: 4.33 -> 5.00 UP
- case 101: 3.67 -> 4.33 UP
- case 102: 4.33 -> 4.00   
- case 103: 4.33 -> 4.00   
- case 104: 4.00 -> 3.33 DOWN
- case 105: 2.33 -> 3.00 UP
- case 106: 3.67 -> 4.00   
- case 107: 4.67 -> 4.00 DOWN
- case 108: 2.33 -> 3.00 UP
- case 109: 3.67 -> 3.00 DOWN
- case 110: 3.33 -> 2.67 DOWN
- case 111: 5.00 -> 5.00   
- case 112: 4.67 -> 5.00   
- case 113: 2.00 -> 2.33   

## Next steps

1. Read `best_vs_baseline.diff` in this folder - that's every prompt change kept.
2. Ask Claude to review the best version's replies against the baseline's.
3. Copy the best `debate_voice.py` into the folder you launch Sophia from and
   run a real session with thinking off before trusting any of this.
