# Frontier brief: untried routes, if Z13 and Z32 are solvable (2026-11-24)

Sources: three surveys (ML and LLM decipherment, document forensics, key construction), mostly from
abstracts and snippets; **[reported]** unless marked **[read]**. See `FIELD_SURVEY.md` for prior work.

## Premise

If solvable, the missing bits must come from (1) a sharper prior on the message, (2) structure in the key,
(3) links between ciphers, or (4) the physical documents. More compute on 45 symbols will not do it.

## Computed

- **Shared symbols, Z13 and Z32** (`data/ciphers/z13.json`, `z32.json`): A, E, M, `[` (inverted T) and `z`
  (crosshair); each appears once in Z32. Under a shared key each forces one letter equality worth
  -log2(sum p^2) = 3.92 bits (English letter frequencies), about 19.6 bits in total. Joint budget: Z13 ~21 +
  Z32 12.2 + shared 19.6, about 53 bits, against 45 letters times bits per letter. At ~1.2 bits per letter
  the pair is near unicity; at 2.4 (n-gram) it is hopeless.
- **Initials hypothesis.** Fit rate to Z13's simple-key pattern: running text 2 / 13,672,048; consecutive
  word initials 2 / 3,107,653; iid initial-letter model 5 / 80M. The pattern-only Bayes factor of initials
  over text is about 4 with an interval spanning more than 10x either way. The pattern cannot discriminate;
  initials are testable only against a proposed source phrase. Parked.

## Routes, and what has since been tested

1. **Joint Z13+Z32 under one key** (real pairing vs label-permuted fakes of the 5 shared symbols).
   **Tested: not testable with a 5-gram solver.** Not done: a converged joint solver (winchxyz App. C).
2. **A contamination-free pre-1970 language model as the message prior** plus exact pattern-constrained
   enumeration. Untested; bits per letter on held-out 13-letter spans are unmeasured anywhere. Against it:
   winchxyz finds Z13's top fits are word salad.
3. **Imaging the originals** (photometric stereo, which recovered decades-old impressions in Brenner et al.
   2023 [read]; multispectral; groove profiles of the circles). No public record for these letters; needs
   the holding agencies.
4. **Handwriting model for the circles** as a latent transcription. Limited by the resolution of available
   scans. **The circles are addressed in the separate circles PR.**
5. **Structured keys:** does symbol order in Z408/Z340 follow the alphabet or a keyword?
   **Tested: no structure found.** Habits learned from one solved key add about 0 bits when predicting the
   other (leave-one-out gain -0.018 bits per symbol, p > 0.4); see `FINDINGS.md`, 2026-11-23 (later).
6. **Real-cipher calibration bench** (DECODE; matched-length controls as in Wase 2023 on Dorabella
   [reported]). Untested.
7. **Other languages and Vietnam-era GI slang.** Untested (20 queued bot tests never run; a small sealed slang list would be needed).
8. **Initials:** parked (above).

## Notes (reported unless marked)

- Neural homophonic decipherment solved two real historical ciphers (Kambhatla, Born, Sarkar 2023); seq2seq
  cracks substitution from 256 characters (Aldarrab & May 2021). Nothing near 13-32 symbols.
- LLMs on classical ciphers: best under 50% on CipherBank (2025). No LM-under-isomorph-constraint decoding found.
- LLM bits per character on long text about 0.7-1.0; humans about 1.2-1.3. No short-span measurement found.
- Contamination: modern LLMs have seen the forums and proposed answers. Mitigate with a pre-1970 model,
  never naming Zodiac in prompts, and comparing known-wrong forum candidates against matched controls.
- The FBI examined the letters for handwriting, prints and code; DNA attempts on envelopes (2002, 2010, 2018
  private lab). No public record of indentation or spectral imaging of the Z13/Z32 letters.
