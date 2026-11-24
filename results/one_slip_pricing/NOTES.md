# B4 — error-tolerant Z13 fitting (one encoding slip), priced

**Claim.** Allowing one encoding slip (one position free) makes a "fit" cheap, and *how* cheap
depends on the reading's own repeat profile. Once the one-slip chance rate is priced into the
decision rule, **every** one-slip (and homophonic) fit seen in C1 v1 is chance. The naive rule
"any fit counts" flags 4; the priced, family-aware rule flags 0.

Reproduce: `python scripts/price_one_slip.py`
Tests: `python -m pytest tests/test_slip_rule.py` (8 pass; two fail under a naive rule).

## What one slip means

One slip = one **substitution** (a transcription or key error at a single position), not an
insertion/deletion. Length is preserved, so a candidate must still match the reading's length
(the length-12 `crosshair_null` reading tests 0 of the 13-letter lists, as in v1).

## The null must be per-reading

| reading | profile | #symbols | one-slip E (vocabcombo, n=5000) | one-slip max |
|---|---|---|---|---|
| canonical / reversed / bracket_is_perp | 3,2,2,2,1,1,1,1 | 8 | 0.037 | 1 |
| circles_distinct | 2,2,2,1,1,1,1,1,1,1 | 10 | **4.00** | **33** |
| crosshair_null | 3,2,2,2,1,1,1 (len 12) | 7 | n/a (length) | — |

`circles_distinct` is the loosest reading: its 10-symbol profile lets **1–4 candidates match a
random pattern by chance under one slip**, and up to 33 at the tail. A canonical-only baseline
(C1 v1's `decoys.py`) under-priced it by ~100×. Every v1 "fit" landed on exactly this reading;
none is above its own chance mean.

## Priced decision rule (for C1 v2)

For each declared (list × reading × key) cell:

1. Build the null by drawing `n_decoys` decoys with **that reading's** profile (exclude the
   reading's own isomorph and its reversal), and count how many candidates fit each decoy under
   the same key+tolerance → `null`.
2. `pval = (1 + #{null ≥ observed}) / (1 + n_decoys)` (add-one smoothed).
3. **Notable** iff `pval < α / n_tests` where `n_tests` is the declared family size (every
   evaluable list×reading cell for that key). α = 0.05, Bonferroni.
4. Report `family_expected = mean(null) × n_tests` alongside. When it is ≈1 or more, a handful
   of `k = 1` fits is exactly what chance predicts — the one-slip family here expects ~1 fit.

A lone one-slip fit is therefore **never** notable by itself; it must beat the per-reading null
tail after paying for the family.

## Observed vs priced (C1 v1), one-slip + homophonic hits only

| list | reading | key | observed | E | pval | verdict |
|---|---|---|---|---|---|---|
| persona | circles_distinct | one-slip | 1 | 1.23 | 0.48 | chance |
| taunt | circles_distinct | one-slip | 1 | 1.43 | 0.35 | chance |
| taunt | circles_distinct | homophonic | 2 | 0.49 | 0.07 | chance |
| vocabcombo | circles_distinct | one-slip | 2 | 4.00 | 0.49 | chance |

Full numbers: `slip_pricing.json`.

## For C1 v2

- Use `slip_rule.null_counts` + `slip_rule.decision` as the checker's verdict layer; pass the
  reading's own profile and the real family size `n_tests`.
- One-slip stays **exploratory / secondary** (the steer's instruction): it only ever downgrades,
  never promotes, a candidate — because the one-slip null swamps any single fit.
- `circles_distinct` is near-useless for discovery under relaxed tolerance; weight it accordingly
  or report it separately so its loose profile can't manufacture a headline.

## Follow-up (owner review — do not merge)

Folding slip tolerance + the per-profile priced null into zbot's fitting code is a
methodology/statistics change, so it ships to the fork as a PR that waits for the owner, not a
merge. This research artifact is self-contained and is what unblocks C1 v2.

**Guardrail honored:** no names of real people are fit, tested, or reported anywhere in B4.
