# Overnight run 20260919-1834

Started 2026-09-19 18:34, report written 2026-09-19 18:35. Rounds run: 0.
Stopped because: stopped by you (Ctrl+C).

## Bottom line

| | Baseline (v2.46, thinking off) | Best found |
|---|---|---|
| Judge mean, dev + held-out | 3.91 | 3.91 |
| Judge mean, dev (20 cases) | 4.05 | 4.05 |
| Judge mean, held-out (13 cases) | 3.69 | 3.69 |
| Replies scoring 4+ | 71/99 | 71/99 |
| Median reply time (dev) | 2.2s | 2.2s |
| Median reply length (dev, tokens) | 58.5 | 58.5 |
| Prompt size | 22805 chars | 22805 chars |

For reference, thinking ON scored 3.85 overall and 4.47 on the replies it
actually gave, with 14 silent replies out of 78. Its 12.6s median is NOT
comparable to anything measured from v2.49 on: every timing recorded
before the 2026-09-12 localhost/IPv6 fix carries ~2s of connection stall
per request. Compare times only within this run.

## Rounds

| # | Change | Dev | Held-out | Median | Verdict |
|---|---|---|---|---|---|

## Per case (judge mean) - baseline -> best

- case 1: 3.67 -> 3.67   
- case 2: 4.67 -> 4.67   
- case 3: 5.00 -> 5.00   
- case 4: 2.33 -> 2.33   
- case 5: 4.00 -> 4.00   
- case 6: 5.00 -> 5.00   
- case 7: 3.33 -> 3.33   
- case 8: 4.67 -> 4.67   
- case 9: 5.00 -> 5.00   
- case 10: 4.67 -> 4.67   
- case 11: 3.33 -> 3.33   
- case 12: 5.00 -> 5.00   
- case 13: 5.00 -> 5.00   
- case 14: 4.67 -> 4.67   
- case 15: 4.00 -> 4.00   
- case 16: 2.00 -> 2.00   
- case 17: 2.00 -> 2.00   
- case 18: 4.00 -> 4.00   
- case 19: 4.33 -> 4.33   
- case 20: 4.33 -> 4.33   
- case 101: 3.67 -> 3.67   
- case 102: 4.33 -> 4.33   
- case 103: 4.33 -> 4.33   
- case 104: 4.00 -> 4.00   
- case 105: 2.33 -> 2.33   
- case 106: 3.67 -> 3.67   
- case 107: 4.67 -> 4.67   
- case 108: 2.33 -> 2.33   
- case 109: 3.67 -> 3.67   
- case 110: 3.33 -> 3.33   
- case 111: 5.00 -> 5.00   
- case 112: 4.67 -> 4.67   
- case 113: 2.00 -> 2.00   

## Next steps

1. Read `best_vs_baseline.diff` in this folder - that's every prompt change kept.
2. Ask Claude to review the best version's replies against the baseline's.
3. Copy the best `debate_voice.py` into the folder you launch Sophia from and
   run a real session with thinking off before trusting any of this.
