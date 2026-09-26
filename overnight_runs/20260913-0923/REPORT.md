# Overnight run 20260913-0923

Started 2026-09-13 09:23, report written 2026-09-13 09:23. Rounds run: 0.
Stopped because: crashed: NameError("name 'args' is not defined").

## Bottom line

| | Baseline (v2.46, thinking off) | Best found |
|---|---|---|
| Judge mean, dev + held-out | 3.79 | 3.79 |
| Judge mean, dev (17 cases) | 4.04 | 4.04 |
| Judge mean, held-out (13 cases) | 3.46 | 3.46 |
| Replies scoring 4+ | 58/90 | 58/90 |
| Median reply time (dev) | 1.3s | 1.3s |
| Median reply length (dev, tokens) | 30 | 30 |
| Prompt size | 18148 chars | 18148 chars |

For reference, thinking ON scored 3.85 overall and 4.47 on the replies it
actually gave, with 14 silent replies out of 78. Its 12.6s median is NOT
comparable to anything measured from v2.49 on: every timing recorded
before the 2026-09-12 localhost/IPv6 fix carries ~2s of connection stall
per request. Compare times only within this run.

## Rounds

| # | Change | Dev | Held-out | Median | Verdict |
|---|---|---|---|---|---|

## Per case (judge mean) - baseline -> best

- case 1: 4.00 -> 4.00   
- case 2: 5.00 -> 5.00   
- case 3: 4.33 -> 4.33   
- case 4: 2.67 -> 2.67   
- case 5: 3.33 -> 3.33   
- case 6: 5.00 -> 5.00   
- case 7: 4.33 -> 4.33   
- case 8: 5.00 -> 5.00   
- case 9: 5.00 -> 5.00   
- case 10: 4.33 -> 4.33   
- case 11: 3.33 -> 3.33   
- case 12: 5.00 -> 5.00   
- case 13: 5.00 -> 5.00   
- case 14: 4.33 -> 4.33   
- case 15: 4.00 -> 4.00   
- case 16: 2.00 -> 2.00   
- case 17: 2.00 -> 2.00   
- case 101: 4.00 -> 4.00   
- case 102: 3.67 -> 3.67   
- case 103: 4.00 -> 4.00   
- case 104: 3.33 -> 3.33   
- case 105: 3.00 -> 3.00   
- case 106: 2.67 -> 2.67   
- case 107: 4.33 -> 4.33   
- case 108: 2.33 -> 2.33   
- case 109: 3.67 -> 3.67   
- case 110: 2.33 -> 2.33   
- case 111: 5.00 -> 5.00   
- case 112: 4.67 -> 4.67   
- case 113: 2.00 -> 2.00   

## Next steps

1. Read `best_vs_baseline.diff` in this folder - that's every prompt change kept.
2. Ask Claude to review the best version's replies against the baseline's.
3. Copy the best `debate_voice.py` into the folder you launch Sophia from and
   run a real session with thinking off before trusting any of this.
