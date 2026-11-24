# I1 pre-registration: are Z13's three circled glyphs one symbol or three?

STATUS: WRITTEN BEFORE THE NEW IMAGES WERE RECEIVED OR VIEWED. Nothing in this plan is changed after
images arrive; any deviation is logged as a deviation with its reason.

## Question

In the 20 April 1970 letter, Z13 positions 5, 7 and 9 (1-based) are circled glyphs read by every
transcriber as one symbol. The repeat pattern alone favours "three different symbols" by 10^2 to 10^4.5
(winchxyz 2026, §4.5). Only the images can settle it. Worth ~8.4 bits for Z13.

## 1. Image intake (provenance first)

Each image gets a row in `images.csv` before any measurement: file, source (who, where, when obtained),
claimed origin (photograph/scan of the original letter, a newspaper reproduction, a photocopy, a
redrawing), pixel size, colour/greyscale/binarized, compression, and the pixel width of a circled glyph.

- **Eligible:** images derived from photographing or scanning the original letter (any generation), or a
  newspaper reproduction of it.
- **Excluded:** redrawings, retypes, fonts, and any image whose origin can't be stated. Exclusions are listed.
- **Primary image:** the eligible image with the most pixels per circled glyph (ties: colour > greyscale >
  binarized; then the earliest generation). Every other eligible image is analysed as a replication.

## 2. Measurements (code fixed and hashed before it touches the new images)

Crops: bounding boxes of every Z13 glyph, placed by hand on the primary image at its native resolution,
saved to `crops.json` before any metric runs. Each crop is converted to a binary mask at Otsu's threshold
(binarized images used as is), centred on its centroid and scaled to equal height.

- **D (shape distance)** between two glyphs = 1 − best IoU of their masks over rotations of −15° to +15°
  in 1° steps and scale factors 0.85-1.15 in 0.05 steps.
- **Same-symbol reference set S:** all pairs of instances of the same symbol on the SAME letter page,
  in the cipher and in Zodiac's handwritten text (at least the Z13 pairs A–A, N–N, M–M, plus up to 30
  pairs of repeated handwritten capitals chosen by a fixed rule: the first 10 letters that occur at least
  twice in the letter's first line of body text, first two occurrences each).
- **Different-symbol reference set X:** pairs of different glyphs of similar size on the same page
  (all pairs among the Z13 glyphs other than the circles, plus the circled glyphs against the crosshair).
- **Statistic:** the three circle pairs' distances D57, D59, D79.

## 3. Decision rule

Fit a kernel density (Gaussian, Silverman bandwidth) to D over S and over X. For each circle pair,
LR = f_X(D) / f_S(D). Combined log10 LR = sum of the three (reported with a bootstrap 90% interval over
the reference pairs; the pairs are not independent, so the sum is an upper bound on evidence).

- log10 LR ≥ +1 → evidence for **three different symbols**.
- log10 LR ≤ −1 → evidence for **one symbol**.
- In between → **unresolved at this resolution**.
- If a circled glyph is under 20 px wide in the primary image, the result is reported but labelled
  "low resolution", and only a structural difference (below) can move it out of "unresolved".

## 4. Structural check, done blind

A human comparison (the user and/or a collaborator) on the 3 circle crops plus 6 decoy crops (other
glyphs from the same page, processed identically), shuffled, unlabelled. Question per crop pair: "same
symbol, different symbol, or can't tell?", plus a free-text note on internal strokes. Answers are
recorded before the key is revealed. Reported alongside, never pooled with section 3.

## 5. What gets published

images.csv (provenance; no image is republished without rights), crops.json, the code, all distances,
the LR with interval, the blind answers, and the verdict, including "unresolved".
No names of real people, ever.
