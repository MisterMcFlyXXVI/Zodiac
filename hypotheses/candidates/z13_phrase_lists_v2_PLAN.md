# C1 v2 pre-registration: Z13 phrase lists, letter and non-letter readings

STATUS: NO LIST HAS BEEN CHECKED AGAINST Z13. Lists, hashes, sizes and the decision rule below
are fixed before any check. The Z13 transcriptions were read only to (a) get each reading's repeat
profile, (b) confirm that `bracket_is_perp` has the same isomorph as `canonical`, (c) derive the
non-letter readings from `canonical`, and (d) exclude each reading's own isomorph and its reversal
from its decoys. No candidate was compared to any reading.

No names of real people appear in any list. Lists are generated from a vocabulary that excludes
every word capitalized mid-sentence more often than not (names and places can't be generated),
and any phrase with two partly name-like words is dropped. A fit is never evidence about a person.

## How the lists were made (deterministic; `research/C1v2/`)

- A word trigram model (stupid backoff) of the same English corpora as zbot's LM (brown + gutenberg),
  proper nouns excluded as above; single-letter words limited to A, I, O.
- Beam search for the most probable word sequences of a required length, in two contexts:
  after the Z13 header **"MY NAME IS"** (`nameslot`; the corpora rarely continue "name is" with a
  non-name, so this mostly backs off to continuations of "is") and at a **sentence start** (`opener`).
- 13-letter lists are deduplicated against everything already tried (548,042 strings: the C1 v1
  lists, the owner's mikado/persona list, windows of Zodiac's letters, and all 714,956 corpus
  passages measured in C2).
- **Every list is in rank order** (most probable first). A test that uses N lines uses the first N.

## Lists

| list | lines | sha256 |
|---|---|---|
| `z13_nameslot_v2` | 50,000 | `79e6ed2c0fc0f48def37a0471dd9665c97dad4f8f2c8afecaf5f7ebf9c0e2d4c` |
| `z13_opener_v2` | 50,000 | `a335578acbe106a65d24ec2eb413bc3773a469bb8d85f33777b565d0f89c1ce2` |
| `z13_blank_len11_v2` | 250 | `858461282d44120f50dc980c7929c8bec0e19f0fc0d8121f5bf9c791686a7185` |
| `z13_dash_10-1_v2` | 250 | `3989ebffcc5cd5d36b21d7bfb24e7ba93d9eaa29ff90c8597b341c94b5f52850` |
| `z13_blank_len12_v2` | 2,000 | `a0a3aac815d4f88137c06c42dfa34021f709f41b145d870af55b497e9bc5b705` |
| `z13_dash_1-11_v2` | 303 | `5e1317a09b94804960df7e420887938cf930670956900da571f0ad742c9d4204` |
| `z13_dash_2-7-2_v2` | 250 | `25402f685cbf5d685530dfc132901e70c288f829ffda5033c88b6bb085f69507` |
| `z13_dash_3-9_v2` | 10,000 | `e31d799c6b8bc24b74dccb680d57234d814b6b1775a42151a94bc7822c11103a` |
| `z13_blank_len10_v2` | 250 | `9f9f61ff1c40a323a4b157e9f783fec34016d61b2ef107094ea1b2a62a390c50` |
| `z13_dash_4-1-1-4_v2` | 250 | `11e59cd1cf9af733359f649af6434f26632d35d7c7cb2da642ba536f583cd411` |
| `z13_dash_5-7_v2` | 5,000 | `d4daa8f991f92b16e8c9b2f8cac39d08f4731f0ed7917dce5af99801a813399d` |
| `z13_dash_7-4_v2` | 250 | `a1b07756041e71cd7441b45501f0d4fea9324ab53f4dfcdc7b93d3fc96069a56` |
| `z13_dash_9-3_v2` | 1,000 | `9a41154e6f9ea3393c7e49fc443d75f945e1fac56bcb3784772ef6ab15b3dc6a` |

Total: 119,803 lines.

## Readings and tests

**Primary** (13 letters): `canonical` and `reversed` x {simple key, homophonic key}.
`bracket_is_perp` has the same isomorph as `canonical`, so it is the same test. A fit on `reversed`
counts as the same event as a fit on `canonical`.

**Secondary** (non-letter symbols, from a question by a collaborator): for each of the 8 distinct
symbols of `canonical`, two readings. `blank_pK`: the symbol is a null; drop it, any phrase of the
remaining length. `dash_pK`: the symbol is a word separator (dash/space); drop it, and words must end
exactly at its positions (fixed word-length pattern). K is the symbol's first position.
`blank_p3` (the crosshair) is the already-declared `crosshair_null`.

**Exploratory** (reported, never confirmatory): `circles_distinct` (its loose profile gives
0.2-1.4 exact and 4-35 homophonic chance fits at these sizes); one encoding slip on the primary
readings (B4: one-slip fits are common by chance, so they only ever downgrade); the homophonic key
beyond the first 15,000 primary lines; the 13 secondary tests marked exploratory below.


**Primary family** (4 tests, alpha/test = 0.0125). Each test uses the first N/2 lines of BOTH primary lists.

| reading | key | N | E[chance fits] | P(>=1) 95% upper |
|---|---|---|---|---|
| canonical | simple | 100,000 | 0.0080 | 0.0106 |
| canonical | homophonic | 15,000 | 0.0094 | 0.0122 |
| reversed | simple | 100,000 | 0.0080 | 0.0106 |
| reversed | homophonic | 15,000 | 0.0094 | 0.0122 |

Primary family expected chance fits: 0.035

**Secondary family** (32 tests, alpha/test = 0.00156). Test uses the first N lines of its list.

| reading | list | simple N | homophonic N | E simple | E homophonic |
|---|---|---|---|---|---|
| blank_p0 | `z13_blank_len11_v2` | 250 | exploratory | 0.0004 | — |
| blank_p2 | `z13_blank_len11_v2` | 250 | exploratory | 0.0004 | — |
| blank_p7 | `z13_blank_len11_v2` | 250 | exploratory | 0.0004 | — |
| dash_p0 | `z13_dash_10-1_v2` | exploratory | exploratory | — | — |
| blank_p1 | `z13_blank_len12_v2` | 2,000 | 2,000 | 0.0002 | 0.0004 |
| blank_p3 | `z13_blank_len12_v2` | 2,000 | 2,000 | 0.0002 | 0.0004 |
| blank_p5 | `z13_blank_len12_v2` | 2,000 | 2,000 | 0.0002 | 0.0004 |
| blank_p9 | `z13_blank_len12_v2` | 2,000 | 2,000 | 0.0002 | 0.0004 |
| dash_p1 | `z13_dash_1-11_v2` | 303 | 303 | 0.0000 | 0.0000 |
| dash_p2 | `z13_dash_2-7-2_v2` | exploratory | exploratory | — | — |
| dash_p3 | `z13_dash_3-9_v2` | 10,000 | 5,000 | 0.0004 | 0.0004 |
| blank_p4 | `z13_blank_len10_v2` | exploratory | exploratory | — | — |
| dash_p4 | `z13_dash_4-1-1-4_v2` | exploratory | exploratory | — | — |
| dash_p5 | `z13_dash_5-7_v2` | 5,000 | exploratory | 0.0002 | — |
| dash_p7 | `z13_dash_7-4_v2` | 250 | exploratory | 0.0002 | — |
| dash_p9 | `z13_dash_9-3_v2` | 1,000 | 1,000 | 0.0004 | 0.0006 |

Secondary: 19 of 32 tests confirmatory; expected chance fits across them: 0.006

ALL confirmatory tests: expected chance fits 0.041

## How sizes were chosen (decoys only)

For each test, N is the largest size on a grid at which ONE fit would be robustly notable: the 95%
Wilson upper bound of P(a decoy gets >= 1 chance fit) is below that family's alpha per test.
Decoys: random repeat patterns with the reading's own profile (5,000; seed 20261123). Where fewer
patterns exist (the length-10 readings have 3,150), all of them are used. A test with no such N is
exploratory: one true hit could not be told from chance.

Process notes, for transparency: the single-letter-word filter was added and the secondary grid was
extended down to 250 after first pricing passes. Both changes were driven by decoy numbers only.

## PRE-REGISTERED DECISION RULE (written before checking)

1. For each test, count the fits among its first N lines (dash/blank readings: the phrase's letters,
   spaces removed, against the reading with the symbol dropped).
2. p-value from that reading's own decoys, add-one smoothed: (1 + #decoys with >= observed fits) /
   (1 + #decoys). Computed by `research/B4/slip_rule.decision`.
3. **Notable** iff p < 0.05 / n_tests of its family (primary 4 -> 0.0125; secondary 32 -> 0.00156).
   Each family is corrected on its own.
4. Every fit (notable or not, exploratory included) is reported with its expected chance count.
5. A notable fit means only that a committed phrase has Z13's repeat pattern beyond chance. It is
   not a decryption: the success bar's independent backing (a key consistent with Zodiac's habits,
   a second cipher read with the same key, or a checkable predicted fact) is still required.
6. No list is edited after checking. A new idea gets a new list (v3) with a new hash.
7. Names of real people are never fit, tested or reported.

Reproduce: `generate.py pool && generate.py pool2 && price.py && price2.py && generate.py final`
(tests: `test_c1v2.py`, `../B4/test_slip_rule.py`).
