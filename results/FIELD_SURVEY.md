# Field survey: prior work on Z13 and Z32, and where our results stand

Survey of 2026-11-24 (web surveys plus a direct read of the winchxyz report). Source tags:
**[read]** = the source itself was read; **[reported]** = known only from another source or a snippet.
Name-based solution claims are described by year and method only.

## Bottom line

The field reached the same wall. The Z340 solvers state that Z13 and Z32 are below unicity and that
"no known test can scientifically falsify or validate" a candidate; confirmation needs Zodiac's
worksheets, a known source text, or solid links to the solved ciphers (arXiv 2403.17350, section 8.2.1) [read].
The most thorough prior study, winchxyz (Oct 2026), reached many of our conclusions independently and
goes further in places. No image of the Z13 letter better than 640x829 is known, and no new ciphertext
under the same key has surfaced 2020-2026.

## Prior work

| Who / what | Date | Finding | Source |
|---|---|---|---|
| Donald and Bettye Harden | 1969 | Solved Z408 | known |
| Oranchak, Blake, Van Eycke | 2020, paper 2024 | Solved Z340: a period-19 bigram anomaly led to billions of transposition variants (Blake), then AZdecrypt; 3 chance cribs fixed 27 of 63 symbols in section 1. Z13 and Z32 lack the length, a period signal and the low multiplicity | arXiv 2403.17350 [read] |
| von zur Gathen | 2022/23 | Z340 unicity distance 80-152 symbols | HistoCrypt 2022 / Cryptologia [read] |
| Ravi & Knight; Nuhn et al.; Kambhatla et al. | 2011-18 | Solve Z408-class homophonic ciphers; nothing for 13-32 symbols | ACL P11-1025 [read]; others [reported] |
| Oranchak | 2012-13 | More than 2,700 Gutenberg fragments fit Z13; no Z408 window shorter than 22 symbols (Z340: 15) is as repetitive as Z13 | zodiackillerciphers.com blog [read] |
| winchxyz | Oct 2026 | 51 analyses; audit of 43 proposals and 1,153 wiki strings (10 compatible, none beyond chance) | github.com/winchxyz/zodiac-z13-z32, REPORT.md [read] |
| nibzard | Sep 2026 | Exact A* enumeration: Z13 52 readings within 4 nats, 1,007 within 8; Z32 one reading at +3.44 nats, attributed by the author to corpus contamination | github.com/nibzard/zodiac README [read] |
| Z32 geometric claims | 1981-2026 | Radian, clock and compass readings (Penn 1981; Sundberg & Thelin 2014; Foxon, ePrint 2023/982; 2026 preprints; a blog with 22,500 tuned combinations and no null). None validated; no physical search reported. See `CLAIMS_AUDIT_Z32.md` | ciphermysteries.com Z32 page [read]; abstracts [read]; others [reported] |
| Name-based Z13 claims | 2021, 2025-26 | Expert scepticism; a 2x7-box transposition claim fits 0 of 423,922 orders (winchxyz) | NYT 2021-06-22 via others [reported]; winchxyz [read] |

## winchxyz findings that bear on this project

- **Z13 favours a near-simple key** by 10^2.7 to 10^3.8: Zodiac-style cycled homophonic keys never produce
  Z13's repeat profile (0 of 20,000). Supports our choice of the simple key as primary.
- **The circles.** The repeat pattern alone favours three distinct symbols over one (Bayes factor 10^2.0 for
  a simple key, 10^4.5 for a Zodiac-size key). Every transcriber reads one glyph from the images. The posterior
  for "same symbol" is 0.06-0.91 depending on the image prior; only a better image can decide.
- **Objective matters (their section 3.3).** "The solver always beats the truth" holds for a 5-gram plus word
  objective; with a 6-gram likelihood the solver recovers 4 of 12 13-letter simple-substitution phrases.
  Z32-like homophonic ciphers: 0 of 12 under either. zbot's letter score is a 5-gram log-likelihood, so our
  Z32 statement stands, while for Z13 "search cannot win" is model-dependent.
- **Calibration.** Real phrases with Z13's profile rank near the top of their own fits (median rank 2); Z13's
  top fits are word salad, which counts against "Z13 is an ordinary fluent English phrase".
- **Z340 key on Z13's six shared symbols:** a weak excess (p = 0.039 family-wise) that fails its negative
  control (the Z408 key does as well); refuted as key reuse.
- **Map.** True north is about 4.6 degrees clockwise of map-up and the printed scale bar is about 9% long
  (7.0-7.2 ground miles per inch), from forum posts of 16 May 2026. Our earlier "6.4 mi/inch" was the printed
  value and is corrected in `FINDINGS.md`.
- **Not done by them** (their Appendix C): one-slip and filler-letter phrase runs, circles-distinct at full
  scale, crosshair/omega as nulls, insert/delete misspellings, transpositions other than reversal for Z13,
  a key model combined with transposition for Z32.

## Where our results stand relative to this

- Agree with winchxyz on: simple key favoured for Z13; circles undecidable from the pattern; Z32 not
  recoverable by search; no published Z13/Z32 claim beats chance. Agree with the Z340 solvers that both
  ciphers are below unicity.
- Added here, to our knowledge: each Z13 symbol as a null or word separator (16 readings, pre-registered,
  sized on own-profile decoys); one-slip chance priced per reading's own profile; the 100,000 most probable
  "MY NAME IS" continuations and sentence openings, sealed by public push. Consistent with their calibration
  result; none of it supersedes it.
- Correction recorded: the 12-of-12 solver result depends on the objective for Z13 (see `FINDINGS.md`).

## Images and originals

- Custody of the 20 Apr 1970 letter is not confirmed by any source found. Case files are open at Vallejo PD,
  Napa, Solano and California DOJ [reported].
- Best known images: Commons Zodiac-name.gif 640x829 (binarized); zodiackillerfacts.com 407x576 (the only
  colour copy found); bomb-diagram page 648x864. winchxyz also stops at 640x829.
- Unsearched: FBI file PDFs on Wikimedia, Chronicle microfilm 21-23 Apr 1970, archive.org, newspapers.com.
- No published pixel-level analysis of whether the circles match.

## Other ciphertext

None new and credible 2020-2026. Z18 (the 18-symbol tail of Z408; 15 of 18 unique) has not been tested as a
second message under a shared procedure. Halloween card and Exorcist letter marks are not usable ciphertext.

## Where the work is discussed

forum.zodiackillerciphers.com (active 2026), the AZdecrypt community, ciphermysteries.com comments.
