# Prior work and what zbot has already done

A briefing for collaborators: which research and data zbot is built on, what earlier work on
Z13 and Z32 it reuses or replicates, what it has tested itself, and what is still open. Updated
2026-11-23. Detailed measurements are in [`results/FINDINGS.md`](../results/FINDINGS.md); live
results are on the `zbot-results` branch and the dashboard.

## 1. Data the bot uses

| What | Source | How it's used | In the repo? |
|---|---|---|---|
| Transcriptions of Z13, Z32, Z408, Z340, and 11 transcription variants of Z13/Z32 | [winchxyz/zodiac-z13-z32](https://github.com/winchxyz/zodiac-z13-z32) `data/ciphers/` (MIT / CC BY 4.0), checked glyph by glyph against scans by its authors | Everything; the variants become separate hypotheses | Yes, `data/ciphers/` |
| Transcription convention (ASCII code for each glyph) | David Oranchak (zodiackillerciphers.com, Cipher Explorer, AZdecrypt files) | Symbol naming; the site draws glyphs from the descriptions | Yes (via the above) |
| Z408 plaintext | Donald and Bettye Harden (1969), aligned by Oranchak | Calibration: the solver must re-crack Z408 (it gets 97.5% of letters) | Yes |
| Z340 plaintext and read order | Oranchak, Blake and Van Eycke (2020), [arXiv:2403.17350](https://arxiv.org/abs/2403.17350) | Calibration (97.1% once un-transposed); test that the transposition families contain the real Z340 read order | Yes |
| English letter model | Brown Corpus (1961, weighted x2) + NLTK Gutenberg selection | Letter 5-gram scoring | No, downloaded by `python -m zbot setup` |
| Spanish, French, German, Italian | NLTK Europarl sample | Language hypotheses, each with its own calibration | No, downloaded |
| Vietnamese | VNTC news corpus (MIT), github.com/duyvuleo/VNTC | Language hypothesis | No, downloaded |
| English word frequencies | Peter Norvig's `count_1w.txt` (Google Web 1T), filtered to words in the training corpus | Word-level scoring | No, downloaded |
| Zodiac letter transcriptions (45 items, 1966-1974) | github.com/DrDub/zodiac-killer-ciphers `letters/` (mirror of Oranchak's project data) | Zodiac-vocabulary prior; candidate lists; reading context. The Z408 plaintext file is excluded from the vocabulary | No (no licence file), downloaded |
| Publicly discussed suspects: 36 people, 387 name spellings | winchxyz `results/z13names/suspects_table.tsv` | Re-checked against every Z13 reading with zbot's own code | No |
| Letter scans | zodiackillerfacts.com copies inside Oranchak's repository; Wikimedia Commons `Zodiac-name.gif` | Visual check of Z13's three circles | No |

## 2. Earlier work on Z13/Z32, and how zbot relates to it

**winchxyz, *Zodiac Z13 and Z32: an exhaustive, reproducible attempt* (2026).** The main
foundation. zbot takes from it:
- the verified transcriptions and variants;
- the testing method: compare the real cipher with shuffled copies, and measure power with
  genuine-text controls;
- its "not tested" list (Appendix C), which seeded zbot's built-in queue;
- its suspect list.

Its main conclusions, which zbot has replicated or agrees with:
- About 1 in 2.1 million English windows fits Z13's pattern, and about 1 in 3,800-5,400 fit Z32's.
- No suspect fits the standard Z13 transcription.
- A radians-and-inches message grammar fits Z32 at the null rate.
- The reported reuse of the Z340 key in Z13 does not hold up.
- The map geometry (Lake Herman Road at about one radian) is a coincidence.
- Published proposals (43) are indistinguishable from chance.

**nibzard/zodiac (2026).** An automated research loop on Z13/Z32. It found 1,007 Z13 readings
within 8 nats of the best (no dominant reading), and that an AI "coherence judge" did not help on
Z340 or 13-letter texts. Read for ideas; no code or data copied (no licence).

**Oranchak, Blake and Van Eycke.** The Z340 solution (2020) and paper (2024). The (1,2) diagonal
read of Z340 inspired zbot's grid-decimation transposition family. Oranchak's site and code are the
source of the transcription scheme and many observations (e.g. his 2012 list of Z13 phrase fits).

**AZdecrypt (Jarl Van Eycke).** The solver that cracked Z340. zbot's letter-frequency penalty
plays the role of AZdecrypt's entropy weighting; no code reused.

**Seen but not reviewed in depth** (found in a GitHub search; a collaborator may want to check
them): dstampher/zodiac-z32-cipher (a Z32 radians/inches constraint solver),
praetorian-inc/zodiac-z32-cipher-research, maddiedreese/zodiac (a proposed Z32 solution),
sa0156553345-cmyk/zodiac-cipher-investigation, taufiq0205/zodiac-cipher-analysis,
SoylentAquamarine/zodiac-collective, BudongJW/zodiac-cipher-research.

## 3. What zbot has done itself

**The machine.** A numba simulated-annealing solver (homophonic, one-symbol-per-letter, and a
"Zodiac key size" model) with:
- letter 5-gram, dictionary-word and Zodiac-vocabulary scoring;
- transposition families;
- every result reported with p, power, and a multiple-testing correction (Holm). The correction
  covers only tests that could detect anything (power of 0.2 or more), because power is measured
  on controls, independently of the real cipher.

It runs back to back on GitHub Actions, about 5.5 hours per run.

**Tests run (703 as of 2026-11-23).** All six calibrations pass. **No alerts.**

| Group | Count | Outcome |
|---|---|---|
| Baselines and all transcription variants (Z13, Z32) | 12 | untestable or no signal |
| winchxyz's "not tested" list: Z13 transpositions; Z32 transpositions incl. Z340-style; Z32 crosshair or omega as a null; a key shared by Z13 and Z32; letters standing for themselves | 8 | untestable or no signal |
| Spanish, French, German, Italian, Vietnamese (Z13 both key types, Z32) | 15 | untestable or no signal |
| Word-scored Z32 (canonical, variants, null crosshair, transpositions, Zodiac vocabulary) | 6 | untestable or no signal |
| User-queued (circles distinct, reversed) | 3 | untestable or no signal |
| Exploration (random columnar keys for Z32, pinned letters with columnar for Z13) | 653 | 597 untestable at the pilot stage; the rest no signal, except one "candidate" (below) |

The one exploratory "candidate signal" (`explore.807.z32.columnar10`, p = 0.01) is the
roughly 1-in-100 chance result expected among 100 testable tests. Its corrected p is 1.0 and its
decodes are word salad.

**Method studies** (`scripts/power_study.py`, details in FINDINGS.md):
- **The decisive one:** on genuine Z32-like test ciphers, the solver finds readings that score
  higher than the true message 12 of 12 times. The limit is the key's freedom, not the search.
- Word scoring raised Z32 power from about 0.07 to about 0.2-0.28. Nothing helps Z13 reliably.
- Strict homophone cycling was rejected: Zodiac reused a symbol early 42-44% of the time in
  Z408/Z340.
- A Zodiac key-size budget added no power.
- Full reuse of the Z408 or Z340 key on Z32 reads as gibberish.
- 157 of 713,360 genuine English passages fit Z32 (e.g. "POLICE GOT CLOSE ENOUGH TO THE PLANE
  TO"); 0 of 715,000 fit Z13 under a one-to-one key.

**Case-grounded candidate lists** (committed before checking; `scripts/candidates.py`,
`hypotheses/candidates/`). Every one came back with 0 fits:
- suspects (387 spellings);
- every passage of Zodiac's own letters (about 1,000 per cipher);
- 165 radians/inches instructions for Z32;
- 128 *Mikado* and persona phrases for Z13.

**Images.** The Commons scan of the 20 Apr 1970 letter, examined at 7x: the three circles share
one construction and differ only in tilt and size, so they look like one symbol. Moderate evidence;
each circle is about 12 pixels across.

## 4. What is still open

- **Better images.** A high-resolution or colour image of the 20 Apr 1970 letter would settle the
  circles question. Also the SFPD high-resolution photo of Z32 (5100x7014, on
  zodiackillerciphers.com) for the bar, triangles and tau-like glyph. This environment can't reach
  those sites; download them by hand and attach them.
- **Key-constraining hypotheses with a real basis.** Z32 is underdetermined under a free
  homophonic key; only a specific, justified claim about its key (or its plaintext) can change
  that. Queue each as one targeted test.
- **Z13 as a name.** The pattern allows it, but fits of random names are common. We chose not to
  generate lists of private people's names.
- **Not done:** partial key reuse with Z408/Z340 (broad, previously negative); Z13/Z32 against
  other Zodiac-era ciphers or hoaxes; the reviews listed under "seen but not reviewed".

## 5. Where things are

| Path | What |
|---|---|
| `zbot/` | the bot (solver, scoring, tests, runner, report) |
| `scripts/power_study.py`, `scripts/candidates.py` | method studies; pre-registered candidate lists |
| `hypotheses/queue/`, `hypotheses/candidates/` | queued tests; registered candidate lists |
| `results/FINDINGS.md` | research log (hand-written) |
| `zbot-results` branch | ledger, REPORT.md, ALERTS.md, STATUS.json (written by the bot) |
| `web/` | dashboard (Vercel) |
| `NOTICE.md` | licences and credits |
