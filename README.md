# zbot: an autonomous hypothesis tester for the unsolved Zodiac ciphers

Two of the Zodiac Killer's four ciphers are still unsolved:

- **Z13**, the "My name is" cipher (13 symbols, 8 distinct)
- **Z32**, the Mt. Diablo map cipher (32 symbols, 29 distinct)

zbot works through a queue of hypotheses about how they were made: the transcription, the
key type, the transposition, and symbols that might be nulls or literal letters. For each
hypothesis it measures whether the real cipher looks any more like English than chance.
When the queue is empty it generates new hypotheses, so it can keep going without anyone
supervising it.

## Why "test hypotheses" and not "crack harder"

Z13 and Z32 are at or below the **unicity distance**: so few symbols that many different
English texts fit equally well. Prior work showed that more computation does not fix this:

- [winchxyz (2026)](https://github.com/winchxyz/zodiac-z13-z32) found about 1,500 English
  strings fitting Z13's repeat pattern. On Z32, its solver outscored the true text on null
  ciphers 12 times out of 12.
- [nibzard (2026)](https://github.com/nibzard/zodiac) found 1,007 distinct Z13 readings
  within 8 nats of the best.

Any solver will print a fluent decode of Z13 or Z32. That proves nothing. So zbot reports
every result with:

| quantity | meaning |
|---|---|
| **p** | How often shuffled copies of the cipher's own symbols score as well as the real cipher. The shuffled copy gets the same search: same read-order family, same pins. |
| **power** | How often real text, enciphered under the same hypothesis, beats the nulls. The control ciphers are built to have *exactly* the real cipher's repeat profile (for Z13: one symbol three times, three symbols twice, four once). **Low power means the hypothesis cannot be tested at this length.** |
| **z** | Effect size against the null distribution. |
| **p (Holm)** | p corrected for *every* hypothesis the bot has ever run, so trying many ideas can't produce a false hit. |

A hypothesis reaches `results/ALERTS.md` only if it survives the Holm correction *with*
power ≥ 0.5. Even then it is a lead for a human to check, not a solution.

## Calibration

Before any other result counts, the bot must solve a known cipher from scratch:

- **Z408**, no cribs, random start: **97.5%** of letters correct. The ceiling is about 98%
  because of Zodiac's own encoding slips. The real cipher beats every null by z ≈ 24.
- **Z340**, with its published transposition undone: **97.1%** (manual check:
  `python -m zbot solve` on the re-ordered text with about 10M iterations).
- A unit test checks that the transposition families contain Z340's real (1,2)
  grid-decimation read order.

The runner refuses to test anything else until the Z408 calibration has passed under the
current language model.

## Quick start

```bash
pip install -r requirements.txt
sudo apt install libarchive-tools   # bsdtar, only needed for the Vietnamese corpus
python -m zbot setup            # downloads corpora for all 6 languages, builds 5-gram models (~2 min)
python -m zbot setup --lang en  # English only
python -m pytest -q tests
python -m zbot list             # the hypothesis queue
python -m zbot run --hours 3    # work autonomously; safe to kill and resume
python -m zbot run --only new.z13.transpositions.simple
python -m zbot solve z13 --model simple            # quick look, no statistics
python -m zbot solve z13 --model simple --lang vi  # same, Vietnamese model
```

The results go to:

- `results/ledger.jsonl`: an append-only record of every run
- `results/REPORT.md`: a table of all hypotheses
- `results/ALERTS.md`: anything that survives the correction

## Running unattended

`.github/workflows/zbot.yml` runs the bot every night for 5 hours on GitHub Actions. It
restores the ledger from the `zbot-results` branch, carries on from where it stopped, and
pushes the updated results back to that branch. Scheduled workflows only run from the
default branch, so merge this branch first. You can also start a run by hand from the
Actions tab.

## What's in the queue

The queue runs in this order:

1. **Calibration**: Z408.
2. **Baselines**: Z13 and Z32 under homophonic and simple substitution, plus every
   transcription variant (three distinct circles, crosshair as a null, and so on).
3. **Hypotheses the 2026 exhaustive study listed as not tested** (its Appendix C):
   - Z13 transpositions other than reversal
   - Z32 transposition combined with a key model, including the Z340-style grid decimation
   - crosshair or omega as a null in Z32
   - a joint Z13 + Z32 shared-key solve
   - subsets of letters standing for themselves
4. **Other languages**: Spanish, French, German, Italian and Vietnamese, each tested on
   Z13 (simple and homophonic) and Z32 (homophonic). See below.
5. **Your own hypotheses**: JSON files in `hypotheses/queue/` (see the README there).
6. **Exploration**: open-ended families such as keyed columnar transposition of Z32 at
   larger widths, and pin and transposition combinations.

## Other languages

| language | corpus | size |
|---|---|---|
| English | Brown (1961 American English, weighted ×2) + Gutenberg selection | ~14M letters |
| Spanish, French, German, Italian | Europarl sample (European Parliament, 1990s) | ~2.8M letters each |
| Vietnamese | VNTC news corpus (2000s, MIT licence) | ~30M letters |

Text is reduced to A–Z: accents and Vietnamese tone marks are stripped (ễ→E, đ→D),
and ß becomes SS. Someone writing with Zodiac's symbol set would almost certainly have
dropped them too.

Each language must first crack a Z408-like synthetic cipher made from its own held-out
text. Until that calibration passes, the bot won't test that language on Z13 or Z32. All
language tests count towards the multiple-comparison correction.

What to expect:

- **The prior is low.** Z408, Z340 and every letter are in idiomatic American English,
  with consistent English misspellings.
- **The length problem is the same in every language.** 13 letters fit thousands of
  strings in any language, so a "best Vietnamese reading" means no more than a "best
  English reading". The power column shows whether a language test could detect anything
  at all.
- **Vietnamese specifically:** stripped of tones it has many very short syllables, so
  *more* random strings look like plausible Vietnamese, and power will likely be even
  lower. A Vietnamese name such as NGUYEN VAN … fitting Z13 would not be evidence about
  any person.
- **Corpus era and register differ** (parliament speeches, 2000s news), and the corpora
  are smaller than the English one, so these models are weaker than English.

## Layout

```
zbot/lm.py           letter 5-gram models (6 languages), held-out split, leak check against Z408/Z340
zbot/anneal.py       numba simulated annealing, homophonic or simple, pins, shared-key segments
zbot/transforms.py   read-order families: decimation, rail fence, routes, columnar, Z340-style grid decimation
zbot/evaluate.py     real vs nulls vs positive controls for one hypothesis
zbot/hypotheses.py   built-in queue, user queue, explorer
zbot/runner.py       resumable autonomous loop
zbot/report.py       REPORT.md / ALERTS.md with Holm correction
data/ciphers/        verified transcriptions and variants (credits in NOTICE.md)
```

## Limits, stated plainly

- **Expected result: no signal, or untestable.** If you want Z13 or Z32 solved, the most
  useful inputs are new evidence, not more CPU: higher-resolution scans, more ciphertext
  under the same key, or Zodiac's worksheets. See winchxyz REPORT §8.
- **The language model** is letter 5-grams from 1961 American English (Brown) and older
  Gutenberg texts. Names, rare words and Zodiac's misspellings score low.
- **The null model** shuffles the symbol order, which keeps the symbol counts. It asks
  whether the repeat pattern and order are more English-compatible than chance. It does
  not ask whether a decode *means* something.
- **This bot does not identify anyone.** A name that fits Z13's pattern is not evidence
  about a person: hundreds of names fit.
