# C2: Evidence map for Z13 and Z32

**Headline.** Z32's repeat pattern pins down about 12.2 bits of a message that carries roughly 32-48 bits
(literature) or 88 bits (our 5-gram model). That leaves a gap of about 20-36 bits (up to 76 with the model).
Every source we measured that exists today supplies under 3 bits. Z13 is different: its repeat pattern
already pins down at least 17.9 bits, about as many as a 13-letter message carries, so its gap is roughly
0-18 bits. None of 714,956 whole-word English passages fit it, but that is normal for a pattern this strict:
97% of 300 random patterns with Z13's repeat profile also get 0 fits (mean 0.03; checked in review), so it says
nothing about whether Z13 is English. What it does mean: under a one-symbol-per-letter key, few ordinary English
messages fit Z13, so a committed list of up to ~200,000 candidates can still produce a meaningful fit. Z32 needs
more information. Z13 needs the right candidate (on a committed list) and a better image of its three circles.

Reproduce: `scripts/evidence_map.py` (about 20 s, seeded, deterministic).
Section numbers below refer to the printed sections. "Bits" here means log2 of how many English passages
the information rules out. No decoding was attempted.

## 1. What each message carries (measure.py section 1)
- 5-gram letter model, held-out English: **2.69 bits/letter** steady state (300k letters).
- Short whole-word passages, cold start (no context before the first letter), held-out text:
  13 letters = **36.2 bits** (sd 8.0); 32 letters = **88.3 bits** (sd 14.8). Sampled from the full
  713k-passage pool (which includes the model's training text): 32.9 and 78.4 bits.
- Literature range for English, ~1.0-1.5 bits/letter (not measured here): 13 letters 13-20 bits; 32 letters 32-48 bits.
- Our model sits far above the literature range (it is a small 5-gram on about 3M words with no word
  boundaries). It overestimates true entropy, so treat the 5-gram figures as an upper end.

## 2. Z32 (32 positions, 29 distinct symbols, homophonic key)
| quantity | value | source |
|---|---|---|
| message bits | 32-48 (literature); 88.3 (5-gram) | section 1 |
| constraint bits | **12.15** (Wilson 95%: 11.92-12.38); 157 of 713,360 passages fit, 1 in 4,544 | section 2; FINDINGS 2026-11-21 |
| gap | **19.9-35.9** (literature); up to 76.1 (5-gram) | section 3 |

## 3. Z13 (13 positions, 8 distinct symbols, 5 repeated positions)
| quantity | value | source |
|---|---|---|
| message bits | 13-20 (literature); 36.2 (5-gram) | section 1 |
| constraint, one symbol per letter | **> 17.86** (0 of 714,956 fit; rule of three). Estimate 22.0 (see below) | section 2, 5 |
| constraint, homophonic | 19.45 (1 of 714,956 fit; Wilson 95%: 16.95-21.95) | section 2 |
| gap | about **0-18** (a gap cannot be negative; literature end gives <= 1.6, 5-gram end gives <= 18.3) | section 3 |

The 22.0 estimate adds the homophonic fit line (3.9 bits per repeated position, section 4) to the chance
that 8 distinct symbols are 8 distinct letters (2.46 bits). It assumes the two parts are independent.
Reading: the pattern is tight enough to pin a 13-letter message down, but nothing in the English pool
matches. So the missing item is not bits; it is that the plain-English, whole-word assumption or the
transcription (below) is probably wrong. The three circled glyphs alone are worth about 8.4 bits
(B3, row 1); if they are not one symbol the constraint drops sharply and the gap reopens.

## 4. Extra ciphertext under the same key (estimate, section 4)
Method. Test ciphers: held-out whole-word English windows; each letter occurrence picks uniformly among
that letter's homophones; homophones per letter proportional to freq^0.645 (pooled exponent, B1 Q1). The key
size was calibrated so a 32-letter message averages 3 repeated positions (Z32 has 3; scenarios 2 and 4 bracket it).
The key size that fits is large (about 120-230 homophones), so the real key is unconstrained by this.
Fit rate measured on all ~712k whole-word passages per length (true passage removed).

| repeated positions r | ciphers | fits | measured bits |
|---|---|---|---|
| 1 | 19 | 858,446 | 3.98 |
| 2 | 41 | 120,304 | 7.93 |
| 3 | 33 | 6,690 | 11.78 |
| 4 | 32 | 420 | 15.73 |
| 5 | 36 | 36 | 19.44 |
| 6+ | 313 | 1 | not measurable (above ~22, rule of three) |

About **3.9 bits per repeated position** (linear fit, r = 1-5). Z32's 3 repeats give 11.8 bits here against
12.15 measured on Z32: a consistency check. Beyond r = 5 the pool is too small, so the lines below are
**extrapolated**. A homophonic key's repeats grow roughly with the square of the length.
Estimated length at which constraint bits equal message bits (the gap reaches 0), total symbols:

| repeats at 32 letters | message at 1.0 bit/letter | at 1.5 bits/letter | at 5-gram 2.69 |
|---|---|---|---|
| 2 | 135 | 231 | over 512 |
| 3 (Z32's own) | **104** | **180** | over 512 |
| 4 | 73 | 123 | 365 |

So roughly **40-200 extra symbols under the same key** (about 70-150 in the middle case). The estimate is
very sensitive to the key size, to the bits-per-letter figure and to the extrapolation, and it assumes a new message
of English with the same key. New text with a different key does not count.

## 5. Sources of extra bits
| source | bits (measured / bound / estimate) | status | citation |
|---|---|---|---|
| repeat pattern | Z32 12.15 measured; Z13 > 17.86 bound (19.45 homophonic) | already counted above | measure.py s2 |
| key habits (Z408/Z340 shapes, allocation, reuse) | about 0.00 measured; ceiling 1.70 (Z32) and 0.45 (Z13) if everything transferred | exhausted; nothing transfers | research/B1/HABITS.md Q5, Q6 |
| glyph decisions | none to gain: Z32 triangle now settled (distinct, +3.5 bits, 157 hits fall to 13); other Z32 pairs high confidence. Z13 circles: 8.4 bits at stake, can only loosen | open for Z13, needs better scan | research/B3/GLYPHS.md rows 1-6 |
| map channel (radians, inches) | at most 0.7 bit (57 of 91 instructions keep a fitting wording; estimate) | no known bomb to check a landing against | FINDINGS 2026-11-23 |
| stronger scoring / language models | 0 bits. Solver beat the true text in 12/12 test ciphers by 20-40 nats; power 0.07-0.28 | closed; only key constraints or new ciphertext help | FINDINGS 2026-11-21 s1-2 |
| committed crib lists | capacity = constraint - log2(list size): Z32 2.14 bits for 1,031 passages, 4.78 for 165 instructions; Z13 over 7.9 for 992 passages, over 9.3 for 387, over 10.9 for 128 | all tried lists got 0 fits | measure.py s6; FINDINGS 2026-11-21 (later) |
| more ciphertext, same key | 3.9 bits per repeat; closes Z32 at roughly 40-200 extra symbols (estimate) | none exists | measure.py s4 |
| the key or worksheets | up to the whole gap (20-76 bits Z32) | not available | FINDINGS conclusion, item 1 |

Crib capacity means: a list of size S whose member fits is meaningful only when S times the chance rate is small.
Z32 can validate a list of at most about 4,500 (2^12.15); a list of 10,000 is already below chance. Z13 under
a one-symbol-per-letter key could validate lists up to about 240,000, so any plausible Z13 crib list is testable.

## What would crack Z13 (ranked)
1. A primary-quality image of the 20 Apr 1970 letter settling the three circles (one symbol or not). That is
   the biggest swing, 8.4 bits (B3 row 1); every published transcription says one symbol, our best scan cannot tell.
2. Other targeted hypotheses: misspellings, nulls (the crosshair), a transposition, or a
   two-letter-per-symbol key. Each should be queued as a single targeted test (the fit check is exact
   and cheap). Note: 0/714,956 is not evidence against English; random patterns with Z13's profile
   score the same (97% get 0).
3. A short committed crib list from Zodiac's own context; Z13 capacity is above 7.9 bits for 1,000 cribs,
   so a hit would mean something. The lists tried so far (992 letter passages, 128 Mikado/persona phrases
   and, on 23 Nov, 9,000 pre-registered phrases) all gave 0 fits under one symbol per letter.
4. Any independent statement of the plaintext, such as a worksheet or a confession of the key.

## What would crack Z32 (ranked)
1. More ciphertext under the same key: roughly 70-150 more symbols (range 40-200) would close the gap.
   Another encrypted letter that shares the key is the only realistic source.
2. The key or Zodiac's worksheets: they would settle it, at 20-76 bits.
3. A very short, specific crib committed in advance (capacity 4.8 bits for 165 candidates, 2.1 for 1,031);
   a fit would be weak evidence, and the log shows 0 fits for both lists tried.
4. A key-construction rule shown to hold in solved ciphers. B1 found no such rule (0.00 bits; ceiling 1.7).
5. Not useful: better language models, bigger searches, the map (0.7 bit), further habit mining.

## Caveats
- The 5-gram model overestimates English entropy (2.69 vs 1.0-1.5 bits/letter in the literature), so message
  bits and gaps have wide ranges. The literature range is quoted, not measured here.
- Corpus windows overlap and the pool is whole-word runs of one 3M-word corpus (including model training
  text). Fit counts are pool counts, not true rates over all English. The 157 and 0 results move with the corpus.
- Z13's constraint is a bound and its gap an upper bound; the 22.0 estimate assumes independent terms.
- The extra-ciphertext estimate uses a synthetic key (uniform homophone choice, size calibrated to Z32's 3 repeats)
  and extrapolates the per-repeat cost past the measurable range (r above 5). Zodiac reused symbols unevenly
  (B1 Q4b: homophone use is more even than chance), which would change the repeat rate.
- Only two solved keys (Z408, Z340) back every habit finding. Low power below about 0.1 bit per symbol.
- Transcription assumptions: Z32 confirmed on a police photo (B3); Z13 circles unresolved; Z13 crosshair taken as a symbol.
- A fit means "an English passage matches this pattern", not "this is the message". Z32 has 157 such passages.
