# Audit of two published Z32 claims

Papers read in full (text and figures):
- Foxon, "On the 32-Character Zodiac Cipher", IACR ePrint 2023/982 [read]
- Allen, SSRN 4715713, v1.0 of 3 Feb 2024 [read]

The second paper's reading presupposes that a specific real person was the Zodiac. Per this project's rule
that person is not named and nothing is fitted or tested against them; the claim is described generically,
and only its cipher reading is evaluated.

Our bar: (1) the reading and every free choice fixed before checking; (2) expected chance fits across
everything tried well below 1; (3) independent backing. Both claims fail it; the first calls itself preliminary.

## 1. Foxon (ePrint 2023/982)

**Claim.** A "possible new approach", self-described as preliminary and "not particularly convincing". With
Mt. Diablo as the pole, "set to Mag. N." means setting a watch to the magnetic declination (~16.9 deg E),
read as 12:03 or 00:03, i.e. polar coordinates (12, 3), radius in inches and angle in radians. Z32 is
proposed to encode a phrase naming them ("TWELVE INCHES ALONG THE THREE RADIANS" or similar), after a
Z340-style transposition, or the map point itself.

**Method.** Declination 16 deg 53 min E for 26 Jun 1970 (IGRF-13; 16.3-17.7 deg over the map area);
hour = floor(decl/30), minute = round(decl/6); four candidate coordinates pruned to one; two 32-letter
phrases that do not fit Z32's repeats in reading order, so a transposition (bottom row shifted two places,
knight-move read order) is added; the fit needs two misspellings; the point is plotted for 8 axis and
direction combinations.

**Free choices.** Hand rule (floor vs round); 12 vs 24 hour; which number is radius and which angle;
dropping (3,0) as "unlikely"; reference axis (4) and direction (2); phrase wording and word order; the
transposition; up to 2 spelling slips; the map scale used for plotting.

**Null model.** None. Sensitivity checks cover only the declination, which is too coarse to move the answer.
No expected chance count, no pre-registration.

**Look-elsewhere.** About 4 coordinate branches x 8 maps x 10 phrasings x 5 transposition variants, each
tolerating 2 slips: at least 10^3 tries. In our own measurement 15.3% of random 32-letter English windows
fit Z32 with at most 2 slips on that read order, so hundreds of chance fits are expected. **Verdict:
does not survive** (fails 1, 2, 3). The author does not claim otherwise.

**Conflicts with our facts.**
- Scale: the figure places (12 in, 3 rad) about 11-12 miles from the summit, about 1 mile per "inch". The
  map's real scale is 7.0-7.2 ground miles per inch, so 12 inches is ~84 miles and 3 inches ~21 miles. The
  map-location part does not apply to the actual map.
- A watch cannot show "12:03" from one angle: both hands set to 16.9 deg would show about 00:34 on the hour
  hand with the minute hand at :03. It is an arithmetic convention.
- With the map's own skew (true north ~4.6 deg clockwise of map-up) magnetic north is ~21.5 deg clockwise of
  map-up (our inference, sign convention as measured), and round(21.5/6) = 4, not 3: the surviving coordinate
  becomes (12,4). The rounding is brittle.

**Useful to us.** Declination at Mt. Diablo, 16 deg 53 min E (IGRF model value, not an observation);
a catalogue of earlier attempts with their free choices.

## 2. Allen (SSRN 4715713)

**Claim.** Z32 decrypts to "TOWNSHIP THREE NORTH RANGE THREE WEST", the US land-survey designation of a
township about 6x6 miles on the Mt. Diablo Meridian that contains the home of the person the paper presupposes
to be the Zodiac. Supported by a motive theory and by a claim that the writer "confused radian with meridian".

**Method.** Six words, 32 letters exactly, put in a non-natural order with two words reversed (NORTH and one
THREE): `HTRONEERHTTHREERANGETOWNSHIPWEST`. A homophonic key is read off afterwards; 29 symbols map onto 12
letters, so only the three repeat pairs test anything. Appeals to Z340's reversed words as precedent.

**Free choices.** The identity premise; the grid system and the township; the wording (spelled out vs "T3N
R3W"); the order of the six words (6!/2 orders); which words are reversed; the split across the line break; the
key, fitted afterwards. Not used: the map, the number of inches, the radian angle, any scale.

**Null model.** None. One footnote concedes spurious homophonic decryptions are "relatively easy"; no count
is given. Nothing fixed in advance.

**Look-elsewhere (computed).** `scripts/audit_z32_word_orders.py` takes the paper's own six words and
counts every order and every reversal pattern: 23,040 distinct 32-letter strings, of which **20 (0.087%)** fit
Z32's repeat pairs, read from `data/ciphers/z32.json`. The published arrangement is one of the 20. Chance
alone supplies about 20 fitting arrangements of this word list, and the author needs one; across other word
lists, grid systems and phrasings the expected chance count is in the thousands. 0.087% is the same order as
our 157 of 713,360 (0.022%) for free English. **Verdict: does not survive** (fails 1, 2). The land-survey
facts are real but describe a place; they do not test the reading, and the identity premise is outside our
rules.

**Errors and conflicts.**
- It ignores the "# inches along the radians" instruction, which we treat as the content clue.
- "Meridians run toward magnetic north" is wrong: principal meridians are true-north lines. With true north
  ~4.6 deg clockwise of map-up and magnetic north ~17 deg E of true, the two readings differ by ~17 deg.
- Corner arithmetic slips (a township corner at 6 N, 6 W is the south-east corner, not north-east; the north-east
  corner of T3N R3W is 18 N, 12 W). Not verified that the township covers what the paper says.
- The letter says the map and code tell where the bomb is, not a 36 square mile region.
- A natural unpadded 32-letter instruction cannot fit Z32 in reading order (the 2nd and 32nd symbols are
  equal); the paper avoids this only by scrambling and partly reversing the words, an order chosen afterwards.

**Useful to us.** Mt. Diablo is the origin of the Mount Diablo Meridian and Base Line, a map-relevant fact.
At our measured scale one map inch is slightly more than one 6-mile township; reading "inches" in township
units is an untested idea that would be post hoc if applied to Z32.

## Summary

| | Foxon | Allen |
|---|---|---|
| Status of claim | Hypothesis, self-described unconvincing | Asserted solution |
| Null model | none | none |
| Free choices | about 9 | about 8, plus the identity premise |
| Chance expectation | hundreds (at least 10^3 tries, 15% per try at 2 slips) | about 20 for its own word list; thousands overall |
| Survives our bar | no | no |

Reproduce the count: `python scripts/audit_z32_word_orders.py`.
