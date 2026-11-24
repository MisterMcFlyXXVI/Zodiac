#!/usr/bin/env python3
"""How many orderings of a claimed Z32 plaintext's own words fit Z32 by chance?

A published claim reads Z32 as six words (see results/CLAIMS_AUDIT_Z32.md) put in a
non-natural order, some of them reversed, with the key fitted afterwards. Under a
homophonic key the only test a 32-letter reading faces is that equal cipher symbols
carry equal letters: Z32's repeat pairs, read from data/ciphers/z32.json. This counts
how many arrangements of those same words (every order, every reversal pattern) pass.

  python scripts/audit_z32_word_orders.py

Prints: distinct strings, how many fit, the fraction, and whether the published
arrangement is one of the fits. No reading is claimed; this prices one claim's freedom.
"""
from __future__ import annotations

import itertools
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent

WORDS = ["TOWNSHIP", "THREE", "NORTH", "RANGE", "THREE", "WEST"]
PUBLISHED = "HTRONEERHTTHREERANGETOWNSHIPWEST"


def repeat_pairs(path=None):
    """0-based position pairs of equal symbols in Z32, from the transcription file."""
    path = path or ROOT / "data" / "ciphers" / "z32.json"
    data = json.loads(pathlib.Path(path).read_text())
    pairs = []
    for sym in data["symbols"]:
        pos = sym["positions"]
        pairs += [(pos[0], p) for p in pos[1:]]
    return sorted(pairs)


def arrangements(words):
    """All distinct strings from ordering the words and reversing any subset."""
    seen = set()
    n = len(words)
    for perm in set(itertools.permutations(range(n))):
        for mask in range(1 << n):
            seen.add("".join(words[i][::-1] if mask >> k & 1 else words[i]
                             for k, i in enumerate(perm)))
    return seen


def fits(s, pairs):
    return all(s[a] == s[b] for a, b in pairs)


def audit(words=WORDS, pairs=None):
    pairs = pairs if pairs is not None else repeat_pairs()
    strings = arrangements(words)
    return len(strings), sum(fits(s, pairs) for s in strings)


def main():
    pairs = repeat_pairs()
    total, fit = audit(WORDS, pairs)
    print("repeat pairs (0-based):", pairs)
    print(f"distinct arrangements: {total}")
    print(f"fit Z32's repeats:     {fit} ({100 * fit / total:.3f}%)")
    print(f"published arrangement {PUBLISHED} fits: {fits(PUBLISHED, pairs)} (length {len(PUBLISHED)})")


if __name__ == "__main__":
    main()
