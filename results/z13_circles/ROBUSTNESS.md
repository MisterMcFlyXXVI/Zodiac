# I1c exploratory robustness checks (do not change the pre-registered verdict)

Script: scripts/z13_circles/robustness.py (output i1c/robustness.json). Same pairs and cells as run_i1c.py; 50 symbol-grouped 2/3-1/3 splits, seeds 1-50.

## (a) Split stability
- Winner by train AUC: M7 in 50 of 50 splits (it is fitted on train, so this is expected).
- Winner test AUC: median 0.917, 10th-90th percentile 0.738-0.979. The pre-registered split (0.979) is at the top of that range.
- Circles' sum log10 LR, median (10th-90th): p210 -2.98 (-7.36 to -1.38); p41 -2.55 (-4.19 to -1.37). Every split puts both at or below -1.37.
- Share of splits where the pre-registered rule gives: one symbol / unresolved / weak / three:
  p210 76% / 4% / 20% / 0%; p41 70% / 4% / 26% / 0%.
  "Weak" arises when test AUC falls below 0.80 or the test LOOK share reaches 0.10. No split favours three symbols.

## (b) Hardest look-alikes (within-family LOOK vs SAME, test pairs pooled across splits)
| Family | M1 | M7 |
|---|---|---|
| plain circle `561234` | 0.795 | 0.759 |
| crossed circle `()z` | 0.904 | 0.913 |
| both | 0.836 | 0.817 |
Among plain-circle look-alikes M7 is no better than M1 and falls just under 0.80. The combined model's high headline AUC comes largely from easy pairs.

## (c) Leave-one-symbol-out, M7 AUC (held-out symbol's LOOK pairs vs its SAME pairs)
`(` 0.999 | `)` 0.987 | `1` 0.929 (3 SAME) | `2` 0.986 | `3` 1.000 (1 SAME) | `4` 0.986 | `5` 0.666 | `6` 0.975 | `z` 0.916.
Symbol 5 is the weak case (M1 0.723). Symbols 1 and 3 have 3 and 1 SAME pairs, so their AUCs are very noisy.

## Reading
The direction of the result is stable: no split points to three symbols, and all LRs are at or below -1.37. But the verdict is only "one symbol" in about 70-76% of splits under the strict rule, and the plain-circle look-alikes, the case that matters for Z13, are separated only at AUC about 0.76-0.80. The headline test AUC of 0.979 is optimistic. Treat "one symbol" as favoured, not firmly established.
