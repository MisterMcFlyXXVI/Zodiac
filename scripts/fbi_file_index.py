#!/usr/bin/env python3
"""Tag every page of the released FBI Zodiac file by topic (cipher pages, evidence photocopies, ...).

Usage:
  python scripts/fbi_file_index.py PDF_DIR [-o results/FBI_FILE/index.csv] [--ocr-dir DIR] [-j 4]

PDF_DIR holds the ten PDFs named in results/FBI_FILE/README.md. Each page is OCR'd (150 dpi,
tesseract; needs pdftoppm and tesseract on PATH) via scripts/fbi_ocr_page.sh, tagged by keyword
patterns plus the manual visual tags below, and only the tags are written. The OCR text is held in
memory and discarded: it contains names of private individuals and must never be committed.
--ocr-dir reads previously saved OCR files (PART_pNNN.txt) instead of re-running OCR.

index.csv columns: pdf (file name), part, page (1-based PDF page), ocr_chars (non-space characters
OCR found; 0 = blank or pure image), tags (semicolon-separated).
"""
import argparse
import csv
import os
import re
import subprocess
import sys
from collections import Counter
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))

# part -> file name. F1-F5: Wikimedia Commons File:FBIZodiacFile1-5.pdf. P07-P11: FBI Vault parts 07-11.
PDFS = {
    "F1": "FBIZodiacFile1.pdf", "F2": "FBIZodiacFile2.pdf", "F3": "FBIZodiacFile3.pdf",
    "F4": "FBIZodiacFile4.pdf", "F5": "FBIZodiacFile5.pdf",
    "P07": "The_Zodiac_Killer_Part_07_Final.pdf", "P08": "The_Zodiac_Killer_Part_08.pdf",
    "P09": "The_Zodiac_Killer_Part_09.pdf", "P10": "The_Zodiac_Killer_Part_10.pdf",
    "P11": "The_Zodiac_Killer_Part_11_Final.pdf",
}

# Keyword tags, applied to a page's OCR text.
PATTERNS = {
    "crypt": re.compile(r"cipher|cryptogram|cryptanal|crypto|decipher|decrypt|cryptographic", re.I),
    "c13": re.compile(r"13[- ]?(character|symbol|letter)|thirteen[- ]?(character|symbol)|my name is", re.I),
    "c32": re.compile(r"32[- ]?(character|symbol)|thirty[- ]two", re.I),
    "c408": re.compile(r"\b408\b", re.I),
    "c340": re.compile(r"\b340\b|3[4A]0[- ]?character", re.I),
    "item": re.compile(r"\bQ[ce] ?[0-9]{1,3}\b|\bKc ?[0-9]{1,3}\b|\bQ[0-9]{1,3}\b|Specimens? (received|submitted)", re.I),
    "hw": re.compile(r"hand ?print|handwriting|writing specimen", re.I),
    "photo": re.compile(r"photocop|photograph of (envelope|letter|card)", re.I),
}

# Tags that make a page a "cipher page" in results/FBI_FILE/CIPHER_PAGES.md (282 of 1,945 pages).
CIPHER_TAGS = {"crypt", "c13", "c32", "c408", "c340", "symbols_image", "z13_letter_image",
               "z32_letter_image", "z13_typed_thirdparty", "lab_cryptanalysis_request"}

# Manual tags from looking at the page images (not derivable from OCR). Ranges are inclusive.
MANUAL = []


def _m(tag, part, a, b=None):
    MANUAL.append((tag, part, a, b or a))


# Part 09 pp168-262 is the evidence section: photocopies of the envelopes, letters and cards (Qc items).
_m("evidence_image", "P09", 168, 262)
for _a, _b in [(41, None), (39, 40), (45, 49), (270, 272), (290, None), (297, None)]:
    _m("evidence_image", "P09", _a, _b)
for _a, _b in [(41, None), (209, None), (210, None), (211, None), (45, 49)]:
    _m("z13_letter_image", "P09", _a, _b)
_m("z32_letter_image", "P09", 215)
for _p in (171, 182, 196, 200, 215, 17):
    _m("symbols_image", "P09", _p)
for _a, _b in [(45, None), (106, 115), (171, None), (233, None), (254, 255)]:
    _m("symbols_image", "F5", _a, _b)
_m("symbols_image", "F3", 58)
_m("symbols_image", "P08", 17)
_m("symbols_image", "P11", 82)
_m("z13_typed_thirdparty", "P09", 76)
_m("z13_typed_thirdparty", "P10", 71, 72)
_m("z13_typed_thirdparty", "P10", 129)
_m("lab_cryptanalysis_request", "F3", 169, 173)
_m("lab_cryptanalysis_request", "F5", 191, 194)
_m("lab_cryptanalysis_request", "P11", 239)
_m("photo_of_envelope_or_card", "P09", 168, 262)
_m("photo_of_envelope_or_card", "P11", 201)
_m("photo_of_envelope_or_card", "F5", 2, 3)


def tag_page(text, part, page):
    """Tags for one page: keyword matches on `text` plus manual tags for (part, page). Order is stable."""
    tags = [k for k, rx in PATTERNS.items() if rx.search(text)]
    for tag, p, a, b in MANUAL:
        if p == part and a <= page <= b and tag not in tags:
            tags.append(tag)
    return tags


def is_cipher_page(tags):
    return bool(CIPHER_TAGS & set(tags))


def page_count(pdf):
    out = subprocess.run(["pdfinfo", pdf], capture_output=True, text=True, check=True).stdout
    return int(re.search(r"^Pages:\s+(\d+)", out, re.M).group(1))


def ocr(pdf, page):
    helper = os.path.join(HERE, "fbi_ocr_page.sh")
    return subprocess.run([helper, pdf, str(page)], capture_output=True, text=True, errors="ignore").stdout


def build_rows(pdf_dir, ocr_dir=None, jobs=4):
    jobs_list = []
    for part, name in PDFS.items():
        path = os.path.join(pdf_dir, name)
        if not os.path.exists(path):
            sys.exit("missing PDF: %s (see results/FBI_FILE/README.md)" % path)
        jobs_list += [(part, name, path, p) for p in range(1, page_count(path) + 1)]

    def one(j):
        part, name, path, p = j
        if ocr_dir:
            with open(os.path.join(ocr_dir, "%s_p%03d.txt" % (part, p)), errors="ignore") as fh:
                text = fh.read()
        else:
            text = ocr(path, p)
        return (name, part, p, len(re.sub(r"\s", "", text)), ";".join(tag_page(text, part, p)))

    with ThreadPoolExecutor(jobs) as ex:
        return list(ex.map(one, jobs_list))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("pdf_dir")
    ap.add_argument("-o", "--out", default=os.path.join(HERE, "..", "results", "FBI_FILE", "index.csv"))
    ap.add_argument("--ocr-dir", help="read saved OCR text (PART_pNNN.txt) instead of running OCR")
    ap.add_argument("-j", "--jobs", type=int, default=4)
    a = ap.parse_args(argv)
    rows = build_rows(a.pdf_dir, a.ocr_dir, a.jobs)
    with open(a.out, "w", newline="") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(["pdf", "part", "page", "ocr_chars", "tags"])
        w.writerows(rows)
    cipher = sum(1 for r in rows if is_cipher_page(r[4].split(";")))
    print("pages indexed %d, tagged %d, cipher pages %d" % (len(rows), sum(1 for r in rows if r[4]), cipher))
    print(Counter(t for r in rows for t in r[4].split(";") if t))


if __name__ == "__main__":
    main()
