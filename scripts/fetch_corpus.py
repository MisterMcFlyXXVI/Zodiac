#!/usr/bin/env python3
"""Download the English training corpora into data/corpus/ (gitignored).

Sources (fetched from the NLTK data mirror on GitHub):
  * Brown corpus  - 1961 American English, ~1M words. Close in era to the
                    1969-70 Zodiac letters, which is why it is the main source.
  * NLTK Gutenberg selection - 18 public-domain books, ~2.6M words.

Neither corpus contains the Z408 or Z340 plaintexts, so calibrating on those
ciphers is not contaminated. `zbot.lm` checks this again at build time.

Other languages (`--lang es fr de it vi`, or `--lang all`):
  * es/fr/de/it - NLTK's Europarl sample (European Parliament proceedings, ~3.5 MB each).
  * vi          - VNTC Vietnamese news corpus (MIT, github.com/duyvuleo/VNTC), 27-topic
                  training split. Packed as RAR: needs `bsdtar` (apt install libarchive-tools).
"""
from __future__ import annotations

import argparse
import io
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.request
import zipfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "corpus"
BASE = "https://raw.githubusercontent.com/nltk/nltk_data/gh-pages/packages/corpora/"


def fetch(name: str) -> zipfile.ZipFile:
    url = BASE + name + ".zip"
    print(f"downloading {url}", file=sys.stderr)
    with urllib.request.urlopen(url, timeout=120) as r:
        return zipfile.ZipFile(io.BytesIO(r.read()))


def brown_text(z: zipfile.ZipFile) -> str:
    parts = []
    for n in sorted(z.namelist()):
        if not re.search(r"brown/c[a-r]\d\d$", n):
            continue
        raw = z.read(n).decode("latin-1")
        # Tokens look like word/tag; keep the words.
        words = [t.rsplit("/", 1)[0] for t in raw.split()]
        parts.append(" ".join(words))
    return "\n".join(parts)


def gutenberg_text(z: zipfile.ZipFile) -> str:
    return "\n".join(
        z.read(n).decode("latin-1")
        for n in sorted(z.namelist())
        if n.endswith(".txt") and "README" not in n
    )


EUROPARL = {"es": "spanish", "fr": "french", "de": "german", "it": "italian"}
VNTC_URL = "https://raw.githubusercontent.com/duyvuleo/VNTC/master/Data/27Topics/Ver1.1/Train.rar"


def europarl_text(z: zipfile.ZipFile, folder: str) -> str:
    return "\n".join(z.read(n).decode("utf-8", "replace") for n in sorted(z.namelist())
                     if f"/{folder}/" in n and not n.endswith("/"))


def vntc_text() -> str:
    if not shutil.which("bsdtar"):
        raise SystemExit("bsdtar not found: apt install libarchive-tools")
    print(f"downloading {VNTC_URL}", file=sys.stderr)
    with tempfile.TemporaryDirectory() as d:
        rar = pathlib.Path(d) / "train.rar"
        with urllib.request.urlopen(VNTC_URL, timeout=300) as r:
            rar.write_bytes(r.read())
        out = pathlib.Path(d) / "x"
        out.mkdir()
        subprocess.run(["bsdtar", "-xf", str(rar), "-C", str(out)], check=True)
        return "\n".join(p.read_bytes().decode("utf-16", "replace")
                         for p in sorted(out.rglob("*.txt")))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--lang", nargs="*", default=["en"],
                    help="languages to fetch: en es fr de it vi, or 'all'")
    langs = ap.parse_args().lang
    if "all" in langs:
        langs = ["en", *EUROPARL, "vi"]
    OUT.mkdir(parents=True, exist_ok=True)
    ep = None
    for lang in langs:
        if lang == "en":
            continue
        dest = OUT / f"{lang}.txt"
        if dest.exists() and dest.stat().st_size > 0:
            print(f"{dest} exists, skipping", file=sys.stderr)
            continue
        if lang in EUROPARL:
            ep = ep or fetch("europarl_raw")
            text = europarl_text(ep, EUROPARL[lang])
        elif lang == "vi":
            text = vntc_text()
        else:
            raise SystemExit(f"unknown language {lang}")
        dest.write_text(text, encoding="utf-8")
        print(f"wrote {dest} ({dest.stat().st_size:,} bytes)", file=sys.stderr)
    if "en" not in langs:
        return
    targets = {"brown": brown_text, "gutenberg": gutenberg_text}
    for name, extract in targets.items():
        dest = OUT / f"{name}.txt"
        if dest.exists() and dest.stat().st_size > 0:
            print(f"{dest} exists, skipping", file=sys.stderr)
            continue
        dest.write_text(extract(fetch(name)), encoding="utf-8")
        print(f"wrote {dest} ({dest.stat().st_size:,} bytes)", file=sys.stderr)


if __name__ == "__main__":
    main()
