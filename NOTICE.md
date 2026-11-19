# Notice and credits

## Cipher data (`data/ciphers/`)

Copied from [winchxyz/zodiac-z13-z32](https://github.com/winchxyz/zodiac-z13-z32)
(`data/ciphers/`). Their code is MIT-licensed and their documentation is CC BY 4.0,
Copyright (c) 2026 winchxyz. `data/ciphers/SOURCE_README.md` is their README for those
files, unchanged.

- The **transcription convention** and the base transcriptions are David Oranchak's
  (zodiackillerciphers.com webtoy, Cipher Explorer, and the AZdecrypt cipher files by
  Jarl Van Eycke). winchxyz checked each Z13 and Z32 glyph against scans.
- **Z408 plaintext**: solved in 1969 by Donald and Bettye Harden.
- **Z340 plaintext and read order**: solved in 2020 by David Oranchak, Sam Blake and
  Jarl Van Eycke ([arXiv:2403.17350](https://arxiv.org/abs/2403.17350)).

## Language data (not in the repository)

`scripts/fetch_corpus.py` downloads these from the NLTK data mirror at build time.
Neither is redistributed here.

- Brown Corpus of Standard American English (Francis and Kučera, 1961/1979).
- NLTK's selection of Project Gutenberg texts.

## Prior work this project builds on

- winchxyz, *Zodiac Z13 and Z32: an exhaustive, reproducible attempt* (2026). It sets
  the null-model and power methodology this bot follows, and its Appendix C supplied
  the "not tested" hypotheses in the queue.
- nibzard/zodiac, an autoresearch loop on Z13/Z32 (2026). Its finding that Z13 has no
  dominant reading, and its caution about Z32's "SAN FRANCISCO… PLEASE RUSH TO EDITOR"
  reading, informed the design.
- doranchak/zodiac-killer-ciphers and zodiackillerciphers.com: two decades of Zodiac
  cipher analysis.
- AZdecrypt (Jarl Van Eycke): the homophonic solver that cracked Z340. The frequency
  penalty used here plays the role of its entropy weighting.
