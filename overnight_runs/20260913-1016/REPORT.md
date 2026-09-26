# Overnight run 20260913-1016

Started 2026-09-13 10:16, report written 2026-09-13 13:20. Rounds run: 17.
Stopped because: 8 rejected rounds in a row.

## Bottom line

| | Baseline (v2.46, thinking off) | Best found |
|---|---|---|
| Judge mean, dev + held-out | 3.79 | 4.02 |
| Judge mean, dev (17 cases) | 4.04 | 4.21 |
| Judge mean, held-out (13 cases) | 3.46 | 3.54 |
| Replies scoring 4+ | 58/90 | 101/141 |
| Median reply time (dev) | 1.3s | 1.4s |
| Median reply length (dev, tokens) | 30 | 32.5 |
| Prompt size | 18148 chars | 18584 chars |

For reference, thinking ON scored 3.85 overall and 4.47 on the replies it
actually gave, with 14 silent replies out of 78. Its 12.6s median is NOT
comparable to anything measured from v2.49 on: every timing recorded
before the 2026-09-12 localhost/IPv6 fix carries ~2s of connection stall
per request. Compare times only within this run.

## Rounds

| # | Change | Dev | Held-out | Median | Verdict |
|---|---|---|---|---|---|
| 1 | Replaced the abstract "notice it forming and cut it" self-monitoring instruction in the sentence-limit rule with a concrete mechanical action (delete the second period and join the rest onto sentence two with a comma or "and"), targeting the sentence_limit failures (6/51 replies ran three+ sentences | 4.09 | 3.46 | 1.4s | KEPT |
| 2 | Added a fourth ANSWER-mode failure case explicitly naming "dropping a question of yours that's still owed," instructing Sophia to answer a diverting question in one clause then reopen her own unanswered question in a few words — targets Case 17's diversion-drops-the-thread failure (2/5 on all 6 runs | 4.16 | - | 1.3s | rejected: no clear dev gain |
| 3 | Added a concrete third-repetition rule to the CLAIM-mode recurring-loop paragraph — on the third return of the same stipulation, stop diagnosing/labeling it at all and instead state flatly that a stipulated definition isn't evidence, refuse to answer it again, and demand what beyond the stipulation  | 4.04 | - | 1.5s | rejected: no clear dev gain |
| 4 | Added two concrete counter-examples to the fallacy-naming rule clarifying that "hasty generalization" (a sample-size flaw) is not the right label for popularity-as-evidence (appeal to popularity) or part-to-whole reasoning (composition fallacy), targeting the recurring mislabeling seen in Case 13 (a | 4.04 | - | 1.2s | rejected: no clear dev gain |
| 5 | Added an explicit anti-mode-narration rule to the ANSWER section, naming the exact leaked phrases seen in failures ("That's a question, not a claim, so I'll answer it plainly," "which triggers ANSWER mode," "I must answer without attacking") and giving a concrete test ("would this sentence still mak | 4.14 | - | 1.4s | rejected: no clear dev gain |
| 6 | Added a hard fallback to the sentence-limit rule in HARD LIMITS - when unsure the "merge with and" fix will fit, stop right after the second period and drop the rest, instead of gambling on a merge that often still produces a third sentence. Targets the still-frequent sentence_limit failures (the ex | 4.12 | - | 1.4s | rejected: no clear dev gain |
| 7 | Strengthened the "no tradition is a monolith" rule in CLAIM mode to explicitly forbid the vague "most X don't hold that view" headcount reply and require naming the actual subgroup (denomination/sect/school), targeting the requires_a_denominational_specificity_flag failure (Case 14) where Sophia fla | 4.14 | - | 1.4s | rejected: no clear dev gain |
| 8 | Extended the HARD LIMITS sentence-merge rule to cap the merged second sentence at exactly one extra clause (cut any further "and"/"but"/"which"/colon stacked onto it) and added colons to the anti-chaining rule alongside semicolons, targeting the frequent combined sentence_limit + no_semicolon_chain  | 4.12 | - | 1.2s | rejected: no clear dev gain |
| 9 | Added a fourth explicit failing-way to the ANSWER mode's list, requiring attribution words ("on classical theism" / "Aquinas would say") to literally appear when answering a question that touches a contested/theist position, targeting Case 5's repeated failure of asserting theist metaphysics ("God i | 4.21 | 3.54 | 1.4s | KEPT |
| 10 | Extended the CLAIM-mode recurring-loop rule to forbid reusing the same fallacy label ("category error") a second time on a repeated stipulation, giving a concrete alternative script (say renaming doesn't make it the thing, refuse to re-diagnose, ask what they have beyond the relabeling) — targets th | 4.25 | - | 1.3s | rejected: no clear dev gain |
| 11 | Added a concrete question-mark test to the MODERATOR section distinguishing "instruction → acknowledge" from "question → answer," and explicitly forbade replying "Understood" to a moderator question — targets Case 7's failure where a candid-assessment request got only "Understood." (judge 1/5), a di | 4.20 | - | 1.2s | rejected: no clear dev gain |
| 12 | Added an explicit new failure case to ANSWER mode banning opening replies with an attack on the surrounding reasoning ("You're conflating...", "That's a category error") before/instead of answering, requiring the first words to be the answer itself — targets Case 4's recurring failure where a questi | 4.24 | - | 1.3s | rejected: no clear dev gain |
| 13 | Added a proactive planning instruction to the sentence-limit rule in HARD LIMITS, explaining that periods can't be revised after being spoken (unlike the existing "delete that period" fallback, which assumes a revision step a non-reasoning model can't take) and requiring the sentence count to be dec | 4.18 | - | 1.3s | rejected: no clear dev gain |
| 14 | Extended the ATTRIBUTE POSITIONS section to require the same attribution treatment for contested philosophy-of-mind positions (physicalism, dualism) as already applies to theism, naming "Physicalism remains the most parsimonious explanation" as a forbidden bare assertion — targets Case 11's recurrin | 4.24 | - | 1.4s | rejected: no clear dev gain |
| 15 | Added a fifth explicit failing-way to ANSWER mode banning three literal opener phrases ("You're conflating," "You are conflating," "That's a category error") as the first words of an answer, targeting Case 4's attack-before-answering failure (previously tried only as an abstract "don't open with an  | 4.22 | - | 1.4s | rejected: no clear dev gain |
| 16 | In ANSWER mode's "appending a challenge or counter-question" rule, explicitly extended it to cover genuine clarifying questions (not just adversarial pressure), naming "which framing are you asking about?" as a forbidden example and instructing to pick the most natural reading of an ambiguous questi | - | - | - | rejected before testing: lost rule(s): [v2.3] no appended challenge / trailing question mark |
| 17 | Added a routing carve-out so a trailing tag question ("right?", "don't you agree?", "isn't that so?") bolted onto a restated claim no longer triggers ANSWER mode, instead routing on the claim itself — targets Case 16's repeated "category error" failure, which happens because the rhetorical "right?"  | 4.16 | - | 1.4s | rejected: no clear dev gain |

## Per case (judge mean) - baseline -> best

- case 1: 4.00 -> 4.50 UP
- case 2: 5.00 -> 5.00   
- case 3: 4.33 -> 4.67   
- case 4: 2.67 -> 3.17 UP
- case 5: 3.33 -> 5.00 UP
- case 6: 5.00 -> 5.00   
- case 7: 4.33 -> 4.17   
- case 8: 5.00 -> 5.00   
- case 9: 5.00 -> 5.00   
- case 10: 4.33 -> 4.50   
- case 11: 3.33 -> 3.50   
- case 12: 5.00 -> 5.00   
- case 13: 5.00 -> 4.83   
- case 14: 4.33 -> 4.50   
- case 15: 4.00 -> 3.67   
- case 16: 2.00 -> 2.00   
- case 17: 2.00 -> 2.00   
- case 101: 4.00 -> 4.67 UP
- case 102: 3.67 -> 3.67   
- case 103: 4.00 -> 4.00   
- case 104: 3.33 -> 3.00   
- case 105: 3.00 -> 3.67 UP
- case 106: 2.67 -> 3.33 UP
- case 107: 4.33 -> 4.00   
- case 108: 2.33 -> 2.00   
- case 109: 3.67 -> 3.33   
- case 110: 2.33 -> 2.67   
- case 111: 5.00 -> 4.67   
- case 112: 4.67 -> 5.00   
- case 113: 2.00 -> 2.00   

## Next steps

1. Read `best_vs_baseline.diff` in this folder - that's every prompt change kept.
2. Ask Claude to review the best version's replies against the baseline's.
3. Copy the best `debate_voice.py` into the folder you launch Sophia from and
   run a real session with thinking off before trusting any of this.
