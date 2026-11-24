# FBI file: cipher-focused index

A text-only index of the released FBI file on the Zodiac case, made to find the best available copies of the
Z13 (20 Apr 1970) and Z32 (26 Jun 1970) ciphers and any FBI analysis of them. No page images and no OCR text
are included (the pages name private individuals); only page numbers, lab item numbers and tags.

**Result in one paragraph.** The file has photocopies of both cipher letters but no FBI transcription of either
cipher and no image better than about 32 px per circle for Z13. The originals are held as evidence (pages
stamped EVIDENCE). Z13 is on Part 09 p210 (Qc46) and p41; Z32 on Part 09 p215 (Qc51). The FBI's own lab pages
say only that no decryption could be effected for the ciphertext portion of Qc46. What to request next is the
original photographs of Qc45-47 and Qc51 (see CIPHER_PAGES.md).

## What the released file is

"The Zodiac Killer", the FBI Vault (vault.fbi.gov) release of the bureau's Zodiac file. Wikimedia Commons
mirrors the first five sections as `File:FBIZodiacFile1.pdf` to `FBIZodiacFile5.pdf` (1,037 pages, 300 ppi
bilevel scans, no text layer). The Vault later released parts 07-11 (908 pages), mostly new material (see
NEW_IN_07_11.md). Parts 07-11 used here were obtained from a collaborator's copy of the FBI Vault release.

## What was searched

All 1,945 pages (1,037 Commons + 908 parts 07-11). Each page was OCR'd locally (tesseract, 150 dpi), matched
against keyword patterns (cipher, "my name is", 13/32/340/408, lab item numbers, handwriting, photocopy),
and the ~270 low-text or cipher-keyword pages were checked visually on contact sheets, with full-size
inspection of the pages around the lab reports and the evidence photocopies. 282 pages are tagged as cipher
pages (any of: cipher keywords, symbol grids, the Z13/Z32 letter photocopies, third-party typed Z13, FBI
cryptanalysis requests). Caveat: OCR and thumbnails can miss a cipher photocopy on a page with much text.
Rows marked (OCR) in EVIDENCE_ITEMS.md were read from noisy OCR only.

## Files

| File | Content |
|---|---|
| `CIPHER_PAGES.md` | where the Z13, Z32, Z408 and Z340 photocopies and the FBI lab pages are |
| `EVIDENCE_ITEMS.md` | FBI lab item numbers (Q, Qc, Kc) -> item, page references, image location |
| `TRANSCRIPTIONS.md` | analyst and third-party transcriptions of Z13/Z32 (none by the FBI) |
| `NEW_IN_07_11.md` | what parts 07-11 add to Commons parts 1-5 |
| `index.csv` | one row per page: pdf, part, page, ocr_chars, tags (no text) |

Rebuild the index: `python scripts/fbi_file_index.py PDF_DIR` (needs `pdftoppm`, `pdfinfo`, `tesseract`;
`--ocr-dir` reuses saved OCR). The tagging rules are `tag_page` in `scripts/fbi_file_index.py`, tested in
`tests/test_fbi_file_index.py`. Part labels: F1-F5 = Commons files, P07-P11 = Vault parts. A page's tags
come from keywords plus manual tags from looking at the page image; the manual tags are listed in the script.

## Obtaining the PDFs

Source: the FBI Vault Zodiac release (the Commons files carry the first five sections). Expected file names
and SHA-256 (all ten must sit in one directory for the script):

```
57c7fae221556ff6dc087035fede61f503435c09178f3d74046cfffbca0b4cc8  FBIZodiacFile1.pdf
c578b37f951d31b978e1b37c12952f5505723f68f575aefa427532fb4a29a671  FBIZodiacFile2.pdf
7ac72cac3ffe4b902ecbce29c62eb9775ad083db7df54a697ac432e7e8ca4579  FBIZodiacFile3.pdf
5c66064fcdaf140e54c5aec782668c0057b4ab8e8f84fb77d3fcf00ea8860cbd  FBIZodiacFile4.pdf
a2265b2a5f6e288e53432cce47eaa59135c8fcc22ff659f8ad97040b4031f0cb  FBIZodiacFile5.pdf
90c96565910168549be6be08fd2781e47101777e554e5ec2614a2b281258eed6  The_Zodiac_Killer_Part_07_Final.pdf
bd504e702f2b16ca7f3fce5ec0f74cf77b4ce73cd1e1d7d8bae6a08d3d80e53d  The_Zodiac_Killer_Part_08.pdf
c6bf289e485d82ea158f7fe6077c9842d87a3c49f1155387f282464507c776be  The_Zodiac_Killer_Part_09.pdf
0aee436f0b58a16d1e5f0fb858c1871ff32dfd0aff71c2c2bc5a7baaf8503128  The_Zodiac_Killer_Part_10.pdf
49baa24c833414edbacfdc28816912022916427358fbf4fcda42154f0ce74ac6  The_Zodiac_Killer_Part_11_Final.pdf
```

Parts 07-11 were obtained from a collaborator's copy of the FBI Vault release; check them against the hashes
above, and if the Vault's own files differ, tell us so the page numbers can be re-mapped. The same copy also
held `zodiac1.pdf` ... `zodiac5` (partial duplicates of sections 1-5, no new content found); they are not
used by the script.
