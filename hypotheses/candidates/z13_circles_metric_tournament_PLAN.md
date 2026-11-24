# I1c pre-registration: a metric tournament on Zodiac's own symbols, then one application to the circles

Written after I1/I1b and BEFORE any new metric is computed on anything. I1b found the whole-glyph overlap metric
only partly separates look-alike symbols (AUC 0.758). Likely cause: for ringed symbols the outer ring dominates the
overlap. This tests interior-focused metrics, chooses one on Zodiac's solved-cipher symbols, and applies only that one
to Z13's circles.

## Benchmark (no Z13 data)
I1b's aligned cells from the FBI photocopies of Z408 (3 parts) and Z340. Restricted to ringed symbols: B1 families
circle `561234` and crossed circle `()z`. SAME = two instances of one ringed symbol; LOOK = instances of two different
ringed symbols (up to 10 random pairs per symbol / symbol pair, seed 20261124). If either set has < 40 pairs, all
five B1 families are used instead (reported).

## Candidate metrics (fixed list)
- M1 whole-glyph D (I1's sealed metric; baseline).
- M2 interior D: fit a circle to the outer ring (least squares on the outermost contour), remove an annulus of the
  measured ring thickness, then the same overlap search on the interior only.
- M3 angular profile: unwrap around the fitted centre; ink fraction in 36 angle bins for r/R in [0.15, 0.65];
  distance = 1 − max circular cross-correlation over shifts within ±15°.
- M4 topology: inside the ring, the number of enclosed background regions, skeleton junctions and skeleton endpoints;
  distance = sum of absolute differences, each count divided by its benchmark standard deviation.
- M5 interior Zernike moment magnitudes up to order 8; Euclidean distance on z-scored magnitudes.
- M6 ring geometry: width/height ratio, ring thickness, diameter relative to cell height, circularity 4πA/P²;
  Euclidean distance on z-scored features.
- M7 combined: logistic regression on M1-M6 distances, fitted on the training split only.

## Selection and honest score
Split the benchmark by symbol (grouped: no symbol in both splits), 2/3 train, 1/3 test, seed 20261124. The winner is the
metric with the highest TRAIN AUC = P(D_LOOK > D_SAME). Report every metric's train and test AUC; the winner's TEST AUC
is its honest score.

## One application to the circles, and the decision
Apply only the winner to Z13 positions 5, 7, 9 on FBI Part 09 p210 (primary) and p41 (replication), using I1's crops.
LR per circle pair from Gaussian KDEs (Silverman) of the winner's TEST-split SAME vs LOOK distances; Σ log10 LR over
the three pairs (an upper bound: pairs are not independent).
- test AUC >= 0.80 and the share of TEST LOOK pairs at or below the largest circle-pair distance <= 0.10:
  one symbol if Σ log10 LR <= −1; three if >= +1; else unresolved.
- test AUC < 0.65: unresolved at this resolution.
- otherwise: report the LR, labelled weak.
No other metric is ever applied to the circles under this plan.
