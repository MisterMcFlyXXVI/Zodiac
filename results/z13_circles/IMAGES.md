# Images used by the circles analysis

No image files are included in this repository. Provenance of each one (recorded before any measurement), and how
to get them.

| Role | Image | Source | Evidence item | Pixels | Mode | Circle width (px) |
|---|---|---|---|---|---|---|
| Primary | `P09_p210.png` | FBI Vault release "The Zodiac Killer", Part 09, p. 210 (FBI lab item Qc46) | Qc46 | 1276x2084 | bilevel, ~150 ppi | 32 |
| Replication | `P09_p041.png` | same PDF, p. 41 (photocopy of the same letter, labelled "Bus Bomb Letter") | | 1272x1650 | bilevel, ~150 ppi | 31 |
| Replication (low resolution, not used by the scripts) | `Zodiac-name.gif` | Wikimedia Commons File:Zodiac-name.gif (credited there to zodiackiller.com) | | 640x829 | binarized | ~12 |

Both PDF pages are photocopies of the 20 Apr 1970 letter (page 1, with the SFPD ruler stamp on p. 210). They are
the sharpest public images of Z13's circles found (about 32 px per circled glyph against about 12 px on the best
earlier public scan).

For I1b and I1c the Z408 and Z340 look-alike benchmark uses four more pages of the same PDF: pp. 171, 176 and 180
(the three Z408 parts) and p. 196 (Z340, item Qc32), rendered at 150 ppi as `P09-171.png` etc.

PDF used: `The_Zodiac_Killer_Part_09.pdf`, **sha256 `c6bf289e485d82ea158f7fe6077c9842d87a3c49f1155387f282464507c776be`**
(213,812,914 bytes). The copy analysed was a collaborator's copy of the FBI Vault release, received 2026-11-24.

## FETCH

1. Download Part 09 of the Zodiac Killer release from the FBI Vault (https://vault.fbi.gov/zodiac-killer) and check
   `sha256sum The_Zodiac_Killer_Part_09.pdf` gives the hash above. (The file name and Vault URL layout may change; the
   hash is what identifies the file. If it differs, the pixel boxes in `p210/crops.json` and `p041/crops.json` do not
   apply.)
2. Pages 210 and 41 are single JPEG 2000 images at 150 ppi. Extract them at native resolution, without resampling:

   ```
   pdfimages -list -f 210 -l 210 The_Zodiac_Killer_Part_09.pdf      # expect one 1276x2084 image
   pdfimages -png  -f 210 -l 210 The_Zodiac_Killer_Part_09.pdf p210   # writes p210-000.png
   pdfimages -png  -f 41  -l 41  The_Zodiac_Killer_Part_09.pdf p41    # writes p41-000.png (1272x1650)
   mv p210-000.png P09_p210.png; mv p41-000.png P09_p041.png
   ```

   The extracted pixels are identical to the PNGs the results were computed from (checked array-equal).
3. The four benchmark pages are rendered, not extracted:
   `for p in 171 176 180 196; do pdftoppm -r 150 -png -f $p -l $p The_Zodiac_Killer_Part_09.pdf P09; done`
   (poppler `pdftoppm` writes `P09-171.png` etc.; if your poppler pads the page number, rename to that form).

Pass the resulting paths to the run scripts as command-line arguments (see `RESULTS.md`, "Reproduce").
