# C1 Pre-registration: Z13 candidate lists from the letters' own vocabulary

STATUS: NO LIST HAS BEEN CHECKED AGAINST Z13. Lists and hashes are fixed before any check.
The only Z13 data read while building this was the isomorph, to EXCLUDE it (and its reversal)
from the decoy set. No fit was computed with it.

No names of real people (no surnames, no given names) appear in any list or word pool.
Proper nouns found in the letters (people, places, papers) were removed by hand. A name
fitting Z13 would say nothing about anyone. A fit is never evidence about a person.

## Lists (regenerate: `python research/C1/generate.py`, deterministic)
Words are drawn only from `zbot.words.zodiac_vocab()`; templates are mine. Each list is
deduplicated against the owner's mikado/persona list, an approximation of the owner's
letter-window passages (all word-aligned 13-letter runs of consecutive words), and earlier
lists here. Over-size lists are cut to the cap by log-frequency of the words in his letters.

| list | size | sha256 | rationale |
|---|---|---|---|
| persona_v1 | 1500 | c72ea1ef9d5fa5e66802b9b5997c4ecb9654ce69005c322086d8faf969c7b536 | "My name is"/"This is ... speaking" self-description: I AM (THE) adj noun |
| taunt_v1 | 2500 | b15b55f91b26f0ea76a28d2f41be262effe0ea6fc710b74aed65dc5d6b19251e | Short sentences from his verbs, modals (WILL SHALL WONT DONT), pronouns |
| vocabcombo_v1 | 5000 | 454134e860612aa4093bc2ac0d8614c42231fd573b480c9918da1fa722625b1d | 2-5 word det/adj/noun/prep/verb templates of his own nouns, adjectives, verbs |

Total 9000 (budget 10,000). Expected chance fits at the measured upper-bound rate
(<4.2e-6 per passage, simple key): 9000 x 4.2e-6 = 0.038 per reading and key.
Caveat: my templates are looser than real English prose (e.g. "THE BUS OF A NAME"), so the
measured English rate is only a rough guide. The decoy baseline below is the reference.

## Decoy baseline (`python research/C1/decoys.py`, 2,000 decoys, seed 20261123)
Decoys: random 13-symbol patterns with Z13's profile (one x3, three x2, four x1), Z13 isomorph
and reversal excluded. Full numbers: `decoy_baseline.json`.

| list | exact mean/p95/p99/max | one-slip mean/p95/p99/max | homophonic mean/p99/max |
|---|---|---|---|
| persona_v1 | 0 / 0 / 0 / 0 | 0.0090 / 0 / 0 / 3 | 0 / 0 / 0 |
| taunt_v1 | 0 / 0 / 0 / 0 | 0.0315 / 0 / 1 / 7 | 0.0015 / 0 / 2 |
| vocabcombo_v1 | 0 / 0 / 0 / 0 | 0.0370 / 0 / 1 / 9 | 0 / 0 / 0 |
| TOTAL | 0 / 0 / 0 / 0 | 0.0775 / 0 / 2 / 9 | 0.0015 / 0 / 2 |

Exact fits on 2,000 decoys: 0, so the per-decoy rate is under about 1.5e-3 (95% bound).
That is a weak bound; the English-passage rate above is the sharper one for exact fits.
One slip fits about 4% of decoys at least once, so a one-slip fit is common by chance.

## What will be checked (multiple tests, declared now)
Readings: the 5 files `z13.{canonical, reversed, bracket_is_perp, circles_distinct,
crosshair_null}.txt`. Keys: simple (isomorph equality) and homophonic (equal symbols give
equal letters), plus one-slip as a secondary, labelled exploratory.
- Primary family: 5 readings x 2 keys = 10 tests per pooled list of 9000. Per-list reporting
  gives 30 sub-tests; all 30 are reported, none dropped.
- One-slip: 5 readings x 3 lists, exploratory, never used alone.
The 10 primary tests are not independent (the readings differ by a few symbols).

## PRE-REGISTERED DECISION RULE (written before checking)
1. A list is notable only if its real-pattern fit count exceeds the 99th percentile of its
   decoy counts for the same key (exact and homophonic: more than 0; one slip: more than
   the p99 above).
2. Every fit is reported with its decoy expectation (table above) and the 10-test family
   size. A single exact fit on one reading, with 10 tests and 0.038 expected per test
   (about 0.3 for the family at the upper-bound rate), is a curiosity, not a finding.
3. Fits on `reversed` or `crosshair_null` count as the same event as the canonical fit.
4. A fit says only that a string has this repeat pattern. It is never evidence about a person,
   and fits are not extended or reinterpreted after the fact.
5. No list edits after checking. A new idea gets a new list (v2) with a new hash.
