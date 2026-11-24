# I1 results: Z13's three circled glyphs on the FBI photocopies

Protocol pre-registered on the fork before any new image was received (8aed1c8, 00:25Z); measurement code
sealed before it touched a real image (1f041bc, 01:24Z); boxes and deviations saved before measuring (47303ea).

## Images (FBI released Zodiac file, Part 09)

- **Primary:** p210, photocopy of the 20 Apr 1970 letter (lab item Qc46), bilevel ~150 ppi, circles 29-32 px wide
  (best public scan: ~12 px).
- **Replication:** p41, a second photocopy ("Bus Bomb Letter").

## Shape distance D (1 − best overlap after small rotation/scale; lower = more alike)

| | p210 (primary) | p41 (replication) |
|---|---|---|
| circles 5-7 / 5-9 / 7-9 | 0.307 / 0.254 / 0.283 | 0.388 / 0.327 / 0.333 |
| same symbol twice: A-A, N-N, M-M | 0.350, 0.301, 0.369 | 0.338, 0.364, 0.406 |
| same handwritten letter twice (h, i, s, e, a) | 0.636, 0.383, 0.378, 0.442, 0.728 | (not measured) |
| different symbols (36 pairs) | min 0.495, median 0.720 | min 0.477, median 0.753 |
| pre-registered decision | **one symbol** (Σ log10 LR −15.1; 90% −29.2 to −11.1) | **one symbol** (−8.7) |

## What this shows, and what it doesn't

- The three circles differ from each other **no more than Zodiac's repeats of a single letter** on the same page
  (on p210, less than any of them) and far less than any two different symbols. Both photocopies agree.
- **Limitation:** the "different symbols" reference is dissimilar letters (A vs E). The realistic alternative is three
  *look-alike but distinct* symbols. The likelihood ratios come from KDE tails far from the data and overstate the
  evidence against that alternative. Whether this metric can tell look-alike symbols apart at ~150 ppi is untested:
  that is I1b (Zodiac's own look-alike symbol families in his solved ciphers, from the same FBI photocopies).
- Until I1b, the honest reading is: **consistent with one symbol, and no sign of three; not yet decisive.**

## I1b: can the metric tell Zodiac's look-alike symbols apart? (pre-registered, fork b50fae8)

Data: FBI photocopies of all three Z408 parts (Part 09 pp. 176, 180, 171) and Z340 (p. 196, Qc32), same ~150 ppi
quality; 738 cells aligned to the transcriptions; B1's look-alike families. 242 same-symbol pairs, 439 look-alike
distinct pairs.

| | value | meaning |
|---|---|---|
| AUC (look-alike pair less alike than a same-symbol pair) | **0.758** | the metric only partly separates look-alikes |
| share of look-alike distinct pairs at D <= 0.31 (p210 circles' max) | **3.9%** | p210's circles are more alike than 96% of his distinct look-alikes |
| share at D <= 0.39 (p41 circles' max) | 30.8% | p41's blurrier copy is much less telling |
| realistic Σ log10 LR, p210 / p41 | **−1.83** / −0.45 | leans one symbol (~70:1 / ~3:1; pairs not independent, so upper bounds) |
| pre-registered label | **weak** | 0.65 <= AUC < 0.80 |

## Bottom line on the circles

The sharpest copy leans **one symbol**, weakly: the three circles are more alike than 96% of Zodiac's distinct look-alike
pairs, but the method is not sharp enough at 150 ppi to make that decisive, and the second copy barely moves.
The repeat pattern itself leans the other way (three distinct symbols favoured by 10^2 to 10^4.5, depending on the
key model; winchxyz 2026). Net: **still open**. Original photographs of item Qc46 (requested in the FBI FOIA draft)
are what can settle it.

## I1c: metric tournament (pre-registered, fork 59d9924; metrics sealed 0591b39)

Benchmark: Zodiac's ringed symbols from the FBI photocopies of Z408/Z340 (106 same-symbol, 451 look-alike pairs).
Winner by training AUC: **M7** (all measures combined), held-out AUC 0.979 on the sealed split (test symbols 1, 2, z).
Other held-out AUCs: whole shape 0.88, interior only 0.88, angular profile 0.84, ring geometry 0.80, topology 0.61,
Zernike 0.58. Applied once to the circles: **pre-registered verdict "one symbol" on p210 (Σ log10 LR −5.3) and p41 (−3.8).**

### Exploratory robustness (cannot change the verdict)
- 50 grouped splits: M7 wins all 50; held-out AUC median 0.92 (p10-p90 0.74-0.98): the sealed split was lucky.
- Circles, Σ log10 LR median −3.0 (p210) and −2.6 (p41); every split ≤ −1.37; **no split favours three**.
  Strict rule: "one symbol" in 76% / 70% of splits, else "weak" (20-26%) or "unresolved" (4%).
- Hardest look-alikes (plain-circle family, the Z13 case): AUC 0.76 (M7), 0.80 (whole shape). Leave-one-symbol-out:
  one symbol (`5`) separates poorly (0.67).

## Where the circles stand now
Every image analysis points the same way: **one symbol**, never three. Its strength is moderate, not decisive: the
method separates the most relevant look-alikes only moderately, and the summed ratios are upper bounds. Before today the
repeat pattern alone favoured three distinct symbols (~100:1 under the near-simple key Z13 most likely used); the
image evidence now roughly offsets that. Working reading: **one symbol, leaning**. Decisive: the FBI's original
photographs of item Qc46 (FOIA draft names it).
