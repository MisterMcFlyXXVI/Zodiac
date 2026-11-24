# K1: did Zodiac build his keys by a rule?

**Tested.** Among symbols that look like letters (glyph classes taken from descriptions plus B1's fixed
judgments, hashed before any statistic was computed), three tests per cipher:
- T1 shift: is the offset (encoded letter minus look-alike letter) constant? Statistic: most common offset count.
- T2 keyword order: sorting normal-orientation glyphs A..Z, do their encoded letters rise in order (as in a
  keyword-mixed alphabet)? Statistic: longest non-decreasing run.
- T3: same as T2 for mirrored/rotated glyphs.
Null: shuffle the encoded letters among the symbols in the set (keeps homophone counts), 100,000 shuffles,
seed 20261124. Bonferroni threshold 0.05/6 = 0.0083.

**Results** (set sizes: Z408 25 normal / 13 mirrored-rotated; Z340 28 / 12).

| | T1 shift (obs, p) | T2 order (obs, p) | T3 order (obs, p) |
|---|---|---|---|
| Z408 | 4, p=0.326 | 7, p=0.948 | 6, p=0.349 |
| Z340 | 3, p=0.968 | 9, p=0.660 | 5, p=0.736 |

Nothing is near the threshold; observed values are at or below what random assignment gives.
The most common offset is held by 3-4 symbols out of 25-28.

**Verdict.** No evidence that the glyph-to-letter assignment follows a constant shift or a keyword-mixed
alphabet, in either cipher or in either orientation class. Consistent with B1 (no look-alike tendency).

**Caveats.** Sets are small (12-28), so only a strong, near-complete rule would be detected; a rule applied
to only part of the key, or one broken by deliberate slips, would be missed. Ties between glyphs sharing a
letter (e.g. the serifed I variants) are ordered by ASCII symbol, an arbitrary but pre-declared choice.
Variant glyphs (| ! : ; &) follow B1's judgments and are debatable. Symbols with non-letter shapes (shapes,
strokes, crosshair) are excluded, so a rule over the full alphabet is not tested. The lack of a rule
among letter-shaped symbols does not exclude a rule among the others.
