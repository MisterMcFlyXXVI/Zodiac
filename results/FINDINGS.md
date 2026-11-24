# Research log

Methods work on the bot itself: what was tried to make Z13/Z32 testable, what was measured,
and what was concluded. Written by hand, unlike REPORT.md. Newest first.

## 2026-11-24: Z13's three circles on FBI photocopies: one symbol, leaning, not decisive

**The question.** Z13's circled glyphs sit at positions 5, 7 and 9. The repeat pattern alone favours three
distinct symbols (about 100:1 under the near-simple key Z13 most likely used), but if they are one symbol the
pattern changes completely. Only the glyph shapes can say, and the best public scan (~12 px per circle) was too
small. The FBI's released file (Vault, "The Zodiac Killer", Part 09) holds photocopies of the 20 Apr 1970 letter
(lab item Qc46) at ~150 ppi bilevel: ~32 px per circle on p. 210 and ~31 px on p. 41. Image provenance and how to
fetch the pages: `results/z13_circles/IMAGES.md`.

**Sealed before looking.** Each step was pushed to the fork before the data it concerns existed or was touched:
- `8aed1c8`: the measurement protocol, before any new image arrived.
- `1f041bc`: the measurement code (hash fixed), before it touched a real image.
- `b50fae8`: the look-alike power check, before any look-alike glyph was measured.
- `59d9924`: the metric tournament (pick a metric on Zodiac's solved-cipher symbols, apply it once to Z13).
- `0591b39`: the tournament metrics (hash fixed), before they touched real data.

**Results** (`results/z13_circles/RESULTS.md`; everything reproduces with `scripts/z13_circles/`):
- **I1, protocol as written: one symbol.** The three circles differ from each other no more than Zodiac's repeats of
  a single letter on the same page, and far less than any two different symbols. Σ log10 LR -15.1 on p. 210, -8.7 on
  p. 41. But the "different symbols" reference there is dissimilar letters, so this overstates the case.
- **I1b, can the metric tell Zodiac's look-alike symbols apart: weakly.** On 242 same-symbol and 439 look-alike
  pairs from the FBI copies of Z408 and Z340, AUC 0.76 (pre-registered label "weak"). The p. 210 circles are more
  alike than 96% of his distinct look-alike pairs; the realistic Σ log10 LR is -1.83 (p. 210), -0.45 (p. 41).
- **I1c, metric tournament: winner M7, verdict one symbol.** M7 combines whole shape, interior, angular profile,
  topology, Zernike and ring geometry. Held-out AUC 0.979 on the sealed split; applied once to the circles it gives
  one symbol on both pages (Σ log10 LR -5.3 and -3.8).
- **Robustness (exploratory, cannot change the verdict).** The sealed split was lucky: over 50 other grouped splits M7
  wins every time but held-out AUC has median 0.92 (p10-p90 0.74-0.98). **0 of 50 splits favour three symbols**
  and the circles' Σ log10 LR is at or below -1.37 in all of them, median -3.0 (p. 210). The strict rule still says
  "one symbol" in only 76% (p. 210) and 70% (p. 41) of splits, otherwise "weak" or "unresolved". On the case that
  matters, plain-circle look-alikes (`5 6 1 2 3 4`), AUC is only 0.76-0.80.

**Bottom line: one symbol, leaning, not decisive.** Every image analysis points the same way and none points to
three, but the method separates the most relevant look-alikes only moderately, and the summed ratios are upper
bounds (pairs are not independent). The image evidence now roughly offsets the repeat-pattern evidence for three
symbols. Original photographs of Qc46 are needed to settle it.

## 2026-11-23 (evening): 119,803 pre-registered Z13 phrases, incl. symbols as dashes or blanks: 0 fits

**A single one-slip fit is chance.** Allowing one encoding slip, the loose `circles_distinct` reading
matches 1-4 phrases of a 9,000-phrase list against a *random* pattern of its profile, so the four
v1 one-slip/homophonic fits there are all below their own chance mean. Chance rates must be measured
on each reading's own repeat profile; the v1 canonical-profile baseline under-priced it ~100x.

**C1 v2: 0 fits in all 23 confirmatory tests** (expected by chance: 0.041). Lists were pushed
(`ad8e1e9`) before the check; `scripts/check_z13_phrase_lists_v2.py` verifies every hash first.
- 13 letters: the 100,000 most probable phrases after "MY NAME IS" or at a sentence start, from a
  word trigram model of brown + gutenberg with proper nouns excluded (no names can be generated),
  deduplicated against everything tried before. Simple key on all 100k, homophonic on the top 15k.
- Non-letter readings: each of Z13's 8 symbols as a blank (null) or a dash (word separator), 16
  readings, 11 lists. 19 of their 32 tests could confirm a single hit; the rest are too loose.
- Each test's size was chosen on decoys alone, so that one fit would be robustly notable.
- Exploratory results are at chance (`circles_distinct` homophonic 24 vs 17.2 expected, p = 0.26).

This covers the head of "Z13 is a common English phrase" (with C2's 0 of 714,956 corpus passages).
It does not rule out English. Readings that turn on the three circled symbols can't be tested with
lists at all; a primary-quality scan of those glyphs remains the most informative next step.

## 2026-11-23 (later): Key habits, glyphs, 9,000 pre-registered Z13 phrases, evidence map

**Zodiac's key habits add about 0 bits.** Habits learned from one solved key were used to predict the
other (Z408 → Z340 and back): leave-one-out gain −0.018 bits per symbol, permutation p > 0.4. Of the 47
symbols in both keys, 5 keep their letter, against 2.9 by chance (p = 0.16). Letter-shaped symbols don't
encode their own letter more than chance. The one real habit: he used a letter's homophones evenly
(Z408 p < 0.001, Z340 p = 0.012). Ceiling if every habit transferred: 1.7 bits for Z32, 0.45 for Z13.

**Glyphs.** Every ambiguous reading was priced with `scripts/voi.py`. Z32's repeat pairs (C, O, open
triangle) and the solid vs open triangles are readable on a 5100x7014 police photo of the original
(zodiackillerciphers.com wiki), so the standard Z32 transcription stands. Z13's three circles are the
largest open decision (about 8.4 bits, since three distinct symbols loosen the pattern); no image found above
640x829 resolves them.

**9,000 Z13 phrases, pre-registered.** Three lists built from Zodiac's own vocabulary (181 ordinary words;
no names of any person) were committed and pushed (fork branch `prereg/z13-phrase-lists-v1`, commit
`10f6e3d`, 16:26 UTC) before being checked. The decision rule is in `hypotheses/candidates/z13_phrase_lists_v1_PLAN.md`;
`scripts/check_z13_phrase_lists.py` reproduces the check.

| key | readings checked | fits |
|---|---|---|
| one symbol per letter (primary) | canonical, reversed, bracket_is_perp, circles_distinct | **0 of 9,000** on every reading |
| homophonic | same | 2, both on circles_distinct (I CAN KILL A MAIL, I CAN TELL A MAIL) |

The 2 homophonic fits are at chance. The circles_distinct reading leaves only 3 equal-letter constraints, and on
2,000 decoys with that profile the list averages 0.44 fits (95th percentile 2). That baseline was computed after
checking, because the pre-registered decoys used the canonical profile. One-slip fits (4) are exploratory
and at chance. crosshair_null has 12 symbols, so no 13-letter phrase applies.

**Evidence map** (`results/EVIDENCE_MAP.md`, `scripts/evidence_map.py`):
- **Z32** pins about 12.2 bits of a message carrying roughly 32-48. Every source available today adds under 3. An
  estimated 70-150 more symbols under the same key would close the gap (extrapolated; synthetic keys).
- **Z13** pins at least 17.9 bits under one symbol per letter, about what a 13-letter message carries. None of
  714,956 whole-word passages fit it, but neither do 97% of random patterns with Z13's profile (mean 0.03),
  so that says nothing about whether it is English.
- **Lists.** A committed list of up to roughly 200,000 Z13 candidates (4,500 for Z32) can still yield a
  meaningful fit.

**Next.** The two things that could change the picture are a primary-quality image of the 20 Apr 1970 letter
(the circles) and more ciphertext under the same key. More computing or stronger scoring won't.

## 2026-11-23: Z32 as a "radians & inches" instruction: the map can't settle it

**Question.** The 26 Jul 1970 letter says the Mt. Diablo code "concerns Radians & # inches along the
radians". The 26 Jun letter says the map's 0 "is to be set to Mag. N.". If Z32 is that instruction,
could the map provide the missing information? A candidate would have to fit the cipher and also land
somewhere meaningful when measured out on the map.

**Method.** `scripts/z32_instruction_coverage.py` builds instruction sentences from templates
(A RADIANS [AND] B INCHES, B INCHES ALONG RADIAN A, with openers, joins and tails). It counts how many
fit Z32's repeats: under a homophonic key, only positions (0,25), (1,31) and (5,13) must match. The
measure is how many distinct (radians, inches) **instructions** have at least one fitting wording.
Coverage, not a candidate list: no reading is claimed.

| grammar | sentences | fit (standard transcription) | fit (triangles merged) |
|---|---|---|---|
| broad: abbreviations, fractions, compass tails | 11.6 M | 4,705 (4.1e-4, about 2x random English) | 889 |
| natural: full words, whole numbers, exactly 32 letters | 13,161 | **0** | 0 |
| natural + 1-4 filler letters (as Zodiac padded Z408) | 35,657 | 57 of 91 instructions | 2 of 91 |

- **Natural, unpadded instructions can't fit.** The 2nd and 32nd symbols are the same, but a plain
  instruction's 2nd letter (thE, iT, bOmb, dIg) never matches its last (inchS, radianS, norTH). Chance
  would predict about 3 fits; there are 0.
- **With end padding, the cipher barely narrows the location.** 57 of the 91 whole-number instructions
  (0-6 radians, 0-12 inches) keep a fitting wording. That is less than one bit about where the point is.
- **Only one transcription choice matters:** whether the solid triangle (position 11) is the same symbol
  as the open ones (1 and 31). Merged, 2 of 91 survive. Every image shows it solid, and Z408/Z340 treat
  solid and open triangles as different symbols, so this variant is unlikely.

**Why the map can't help.** No bomb was found, so the map has no known point to check a landing
against. Any "meaningful" landing (a school, a station, a crime scene) would be chosen after seeing it.
For that reason we did not plot the 57 instructions' landing points: doing so invites exactly that
after-the-fact matching. Other map facts (hobbyist sources, not checked against the original):
- scale about 6.4 mi/inch, stated without a source;
- the dial reads 0/3/6/9 clockwise from magnetic north (about 17° E in 1970);
- Zodiac's copy is a cropped Phillips 66 "San Francisco and Vicinity" inset;
- the "#" in the PS is read as "#", "+" or a digit in different transcriptions.

**Conclusion.** A two-channel (cipher + map) test of the radians reading is not feasible. Either the
message is not a plain instruction, or Zodiac padded it, and then the cipher leaves most instructions
open. Only new information would change this: a primary scan settling the "#" glyph and the triangle,
or a way to confirm a landing point that was fixed before checking.

## 2026-11-21 (later): Case-grounded candidate tests

Context-based ideas only help as short, specific candidate lists checked exactly. A fit is meaningful
when (list size) x (chance a random English passage fits) is small. Measured chance rates: Z13 under a
one-to-one key, under 1 in 700,000 (0 of 715,000 whole-word passages); Z32 under a homophonic key,
about 1 in 4,500 (157 of 713,360). The Z32 figure means many meaningful sentences fit it, e.g.
"POLICE GOT CLOSE ENOUGH TO THE PLANE TO", so no judge of meaning can single out its message: a
semantic (neural language model) scorer was therefore NOT pursued.

| List (all committed before checking) | Size | Fits | Chance expects |
|---|---|---|---|
| Passages from Zodiac's own letters, vs Z13 (4 readings) | 992 | 0 | ~0.00 |
| Passages from Zodiac's own letters, vs Z32 | 1,031 | 0 | 0.23 |
| 36 publicly discussed suspects, 387 spellings (winchxyz list, re-checked with our code), vs every Z13 reading | 387 | 0 (only a post-hoc reading built to fit) | – |
| Z32 radians/inches instructions from the 26 Jun / 26 Jul 1970 letters (`hypotheses/candidates/z32_radians_v1`) | 165 | 0 in all 6 readings | 0.036 |
| Z13 Mikado names (26 Jul 1970 letter quotes Ko-Ko's "little list") + persona phrases (`z13_mikado_persona_v1`) | 128 | 0 in all 10 readings x keys | ~0.00 |

Images (update): the Wikimedia Commons scan of the 20 Apr 1970 letter (binarized; fetched as a
500 px thumbnail of the 640x829 original because Wikimedia rate-limits this connection) was examined
at 7x. All three circled glyphs (positions 5, 7, 9) share one construction: heavy circle, inner small
top loop over a lower part split in two (circled 8 / Taurus). Differences are tilt, ovalness and size,
typical of handwriting; no added, missing or differently shaped inner stroke. This supports reading them
as ONE symbol (the standard transcription), moderately: each circle is ~12 px wide. The hooked
upside-down T (position 10) shows its base curling up at the right, as transcribed. The other Commons
Z13 image ("My Name Is....Zodiac Cipher.jpg") is a modern redrawing made for a suspect theory, not
evidence. The environment service refused the FBI vault and Zodiac research sites; Wikimedia was allowed.

Earlier images note: the best Z13 image available offline (zodiackillerfacts.com copy in Oranchak's repository,
407x576) was examined at 8x: the three circles look alike but are ~10 pixels wide, too coarse to
settle whether they are one symbol. A request to reach the FBI vault and other image hosts from this
environment was rejected.

## 2026-11-21: Sharper scoring, Zodiac priors, and why the ciphers resist

**Goal.** Raise the bot's *power* (how often genuine text, enciphered with the real cipher's
exact repeat pattern, beats shuffled copies) so that its verdicts on Z13/Z32 mean something.

**Method.** `scripts/power_study.py` runs the bot's own test machinery (real cipher, 19 shuffled
nulls, 40 genuine-text controls) for each scoring method. ±0.07 is roughly one standard error
on a power of 0.2. Many settings were tried, so the best-looking number is optimistic.

### 1. The decisive result: the search is not the bottleneck

On 12 Z32-like test ciphers (genuine English, homophonic key, Z32's repeat profile) the solver
found a reading that scores **higher than the true plaintext in 12 of 12** cases, under both
letter-pattern and word scoring, typically by 20-40 nats (e.g. truth `BYTHATTIMEBARCOHADDISPOSEDOFITAT`
at -82, solver's `ITWASAPERSOFTHELANDABOUTTHEYCAMP` at -47). Z13-like ciphers under a one-to-one
key: 11-12 of 12.

So with a free key, many readings are *more* English than the real message. No scoring tweak or
extra computation can recover it. **Only constraints on the key** (or new ciphertext) can. This
agrees with winchxyz (2026) and nibzard (2026), now measured directly.

### 2. Power by scoring method (whole-word controls, 40 each)

| cipher, key | letter 5-grams | word scoring | word scoring, gentler unknown-letter cost | letters + words |
|---|---|---|---|---|
| Z32, homophonic | 0.07 | 0.20 | **0.28** | 0.17 |
| Z13, one symbol per letter | 0.40 | 0.20 | 0.45 | 0.10 |
| Z13, homophonic | 0.10 | 0.25 | 0.07 | – |

- Word scoring is the best Z32 detector (0.07 → ~0.2-0.28). It is **not** a good long-cipher
  solver: word-only scoring recovers 20% of Z408, letters+words 97.5%. Each word-scored test
  measures its own power, so its verdicts still say how far to trust them.
- For Z13 nothing beats letter patterns reliably.
- No real cipher stood out under any method (lowest p: Z32 0.05 and 0.10, among ~20 settings,
  so not significant).

### 3. Second statistic: uniqueness of the best reading

Gap between the best reading and the best clearly different reading (>30% of letters differ),
judged against nulls and controls like the score. Power 0.05-0.30; best for Z32 under letter
scoring (0.23). Now reported on every result page as a secondary test (not in the Holm correction).

### 4. Zodiac's habits as key constraints

- **Strict homophone cycling: rejected.** In Z408/Z340 Zodiac reused a symbol for a letter before
  all its other symbols ~42-44% of the time, so a strict-cycling rule would reject his real keys.
- **Key size per letter** (no more symbols per letter than he used in Z408/Z340, +1 slack;
  `zbot/zkey.py`, key model `zodiac`): Z32 power 0.00-0.15, no gain.
- **Key reuse.** Z32 read with the Z408 key: `.IF.LNI.WHDA.NGOAOESNBXLT.ETDIEI`; with the Z340 key:
  `YNSETAI.DOBP.AORTRDFNOPTIYRGAIWN`. Full reuse is clearly ruled out (winchxyz tested partial reuse:
  no evidence).

### 5. Zodiac's vocabulary (his letters, `zbot/words.py`)

Words from his letters (incl. his misspellings, e.g. PARADICE) boosted in the word model. Measured
with a split: vocabulary from half the letters, test texts from the other half.
Z32 with word-only scoring: 0.12 → 0.30 (boost 6). With letters+words: 0.10 → 0.05, no gain.
Fragile; one built-in test uses it. Note: these runs used a vocabulary that still included the
Z408 plaintext file; it is now excluded (Z408 calibration would otherwise be graded on its own words).

### 6. Measurement fixes made along the way

- Controls are now runs of **whole words** (Z13 and Z32 are complete messages); before, they were
  windows cut mid-word, which unfairly penalised word scoring.
- Earlier: controls reproduce the cipher's exact repeat profile (2026-11-19 fix).

### Conclusion and where effort should go

The ciphers resist because of information, not search. The bot now uses the best measured detector
for Z32 and reports power with every verdict. What could actually move things:

1. **New information**: better scans (Z13's three circles; Z32's glyph identities), more ciphertext
   under the same key, Zodiac's worksheets.
2. **Key-constraining hypotheses with a real basis**: a specific key-construction method, a crib
   tied to the map ("radians and inches"), or a link between Z13/Z32 and a known key. Each should
   be queued as one targeted test, not a broad search, to keep the multiple-testing cost low.
