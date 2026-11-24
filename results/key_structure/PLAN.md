# K1 pre-registration: keyword/shift structure in solved Zodiac keys

Data: z408.json, z340.json ("symbols"; encoded letter = symbol's "letter"). Glyph classes: glyph_table.json
(built from description text only, B1's judgments for non-capital shapes; hashed in PLAN.sha256).
Sets per cipher: NORMAL = transform "normal" with a glyph_letter; NONNORMAL = "reversed" or "rotated/upside-down" with a glyph_letter.
Letters A-Z = 0..25.

- T1 (shift, NORMAL): d = (encoded - glyph_letter) mod 26 per symbol; statistic = max count of any single d.
- T2 (keyword order, NORMAL): sort symbols by (glyph_letter, symbol ascii); statistic = length of the longest
  non-decreasing subsequence (LNDS) of encoded positions in that order.
- T3 (NONNORMAL): same as T2 on NONNORMAL.
- Null (each test): permute the encoded letters among the symbols of the set (multiset preserved);
  N = 100,000 permutations; numpy default_rng(20261124), one generator per cipher consumed in order T1, T2, T3
  (each test draws N permutations of its set via rng.permutation).
- p = (1 + #null >= observed) / (1 + N). Right tail only.
- 6 tests (2 ciphers x T1-T3), Bonferroni alpha = 0.05/6 = 0.00833. Pooled results are descriptive only.
