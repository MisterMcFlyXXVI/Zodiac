# I1b pre-registration: can the circles metric tell Zodiac's look-alike symbols apart?

Written after I1 (verdict "one symbol" on two FBI photocopies) and BEFORE any look-alike glyph is measured.
Purpose: I1's "different symbols" reference was dissimilar letters. The realistic alternative for Z13's circles is
three look-alike but distinct symbols. This measures the metric's power against that alternative.

## Data
- FBI released Zodiac file photocopies of the solved ciphers: Z408 (three parts, Aug 1969) and Z340 (Nov 1969),
  from FBI file Parts 08/09 (the highest-resolution copy of each; ~150 ppi bilevel, the same kind as I1's images).
- Glyphs located by grid segmentation (17 columns; Z408 parts 8 rows each, Z340 20 rows) and aligned to the known
  transcriptions (data/ciphers/z408.json, z340.json). A part is used only if its segmented count equals the expected
  count and its row/column structure matches; otherwise it is excluded and reported.

## Look-alike families (fixed in research/B1/census.py long before this test)
triangle `987`, square `#_%@*`, circle `561234`, crossed circle `()z`, serif-I `I!|:;` (transcription codes).

## Pairs (per cipher, seeds 20261124)
- SAME: two instances of the same family symbol (up to 10 random pairs per symbol).
- LOOK: two instances of different symbols in the same family (up to 10 random pairs per symbol pair).
- Distance: the sealed `measure.shape_distance` (sha256 7c0b6bbb…), unchanged.

## Statistics and decision (written now)
1. AUC = P(D_LOOK > D_SAME).
2. q = P(D_LOOK <= 0.39), the largest circle-pair distance seen in I1 (p41); also reported at 0.31 (p210 max).
3. Realistic likelihood ratio for the circles: I1's three circle distances re-scored with LOOK as the "different" set and
   I1's p210 same-symbol set (8 pairs) pooled with this SAME set as the "same" set (Gaussian KDE, Silverman).
- **Metric separates look-alikes** if AUC >= 0.80 and q <= 0.10: then report the realistic LR as the evidence for one
  symbol vs three (one symbol if Σ log10 LR <= −1, three if >= +1, else unresolved).
- **Metric cannot separate** if AUC < 0.65: I1 shows only that the circles look alike; verdict for the circles
  becomes "unresolved at this resolution".
- In between: report the realistic LR, labelled "weak".
