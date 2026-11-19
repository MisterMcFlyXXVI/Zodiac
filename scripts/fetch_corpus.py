#!/usr/bin/env python3
"""Download the English training corpora into data/corpus/ (gitignored).

Sources (fetched from the NLTK data mirror on GitHub):
  * Brown corpus  - 1961 American English, ~1M words. Close in era to the
                    1969-70 Zodiac letters, which is why it is the main source.
  * NLTK Gutenberg selection - 18 public-domain books, ~2.6M words.

Neither corpus contains the Z408 or Z340 plaintexts, so calibrating on those
ciphers is not contaminated. `zbot.lm` checks this again at build time.
"""
from __future__ import annotations

import io
import pathlib
import re
import sys
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


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
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
