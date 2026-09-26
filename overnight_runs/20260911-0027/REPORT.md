# Overnight run 20260911-0027

Started 2026-09-11 00:27, report written 2026-09-11 01:00. Rounds run: 1.
Stopped because: reached 1 rounds.

## Bottom line

| | Baseline (v2.46, thinking off) | Best found |
|---|---|---|
| Judge mean, dev + held-out | 3.85 | 4.16 |
| Judge mean, dev (14 cases) | 4.17 | 4.27 |
| Judge mean, held-out (12 cases) | 3.47 | 3.89 |
| Replies scoring 4+ | 51/78 | 89/120 |
| Median reply time (dev) | 3.6s | 3.5s |
| Median reply length (dev, tokens) | 36.0 | 39.0 |
| Prompt size | 17050 chars | 17295 chars |

For reference, thinking ON scored 3.85 overall and 4.47 on the replies it
actually gave, at a 12.6s median with 14 silent replies out of 78.

## Rounds

| # | Change | Dev | Held-out | Median | Verdict |
|---|---|---|---|---|---|
| 1 | Expanded the "One or two sentences. Never three." hard limit to explicitly name the three shapes the forbidden third sentence takes (a follow-up demand, a tacked-on question, or a restated point) and instruct cutting it before speaking it — targets the dominant sentence_limit failure seen across ANS | 4.27 | 3.89 | 3.5s | KEPT |

## Per case (judge mean) - baseline -> best

- case 1: 3.33 -> 3.67   
- case 2: 5.00 -> 5.00   
- case 3: 4.33 -> 4.50   
- case 4: 2.67 -> 2.83   
- case 5: 3.00 -> 3.50 UP
- case 6: 5.00 -> 5.00   
- case 7: 4.00 -> 3.83   
- case 8: 5.00 -> 5.00   
- case 9: 5.00 -> 5.00   
- case 10: 4.00 -> 4.33   
- case 11: 3.33 -> 3.00   
- case 12: 5.00 -> 5.00   
- case 13: 4.67 -> 5.00   
- case 14: 4.00 -> 4.17   
- case 101: 4.67 -> 4.33   
- case 102: 3.00 -> 3.33   
- case 103: 4.00 -> 3.67   
- case 104: 3.00 -> 3.33   
- case 105: 2.67 -> 3.67 UP
- case 106: 4.00 -> 4.33   
- case 107: 4.67 -> 5.00   
- case 108: 3.00 -> 2.67   
- case 109: 2.67 -> 3.00   
- case 110: 2.00 -> 3.67 UP
- case 111: 3.33 -> 4.67 UP
- case 112: 4.67 -> 5.00   

## Next steps

1. Read `best_vs_baseline.diff` in this folder - that's every prompt change kept.
2. Ask Claude to review the best version's replies against the baseline's.
3. Copy the best `debate_voice.py` into the folder you launch Sophia from and
   run a real session with thinking off before trusting any of this.
