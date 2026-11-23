#!/usr/bin/env python3
"""How much does Z32's repeat pattern narrow down a 'radians & inches' instruction?

The 26 Jul 1970 letter says the Mt. Diablo code "concerns Radians & # inches along the
radians". If the plaintext is such an instruction, the question is not "which sentence
fits?" (thousands do) but "which INSTRUCTIONS (angle, distance) have at least one fitting
wording?". If most do, the cipher says little about the location, and the map can't make
up for it: no bomb was found, so there is no known point to check a landing against.

Under a homophonic key the only constraints are the repeated symbols: equal symbols must
be equal letters. For the standard transcription that is positions (0,25), (1,31), (5,13).

  python scripts/z32_instruction_coverage.py

Three measurements, all per transcription variant:
  1. broad grammar   ~11.6M sentences: openers, joins, tails, abbreviations, fractions
  2. natural grammar full words, whole numbers, plain openers; exactly 32 letters
  3. natural + 1-4 filler letters at the end (Zodiac padded Z408 this way)
No reading is claimed, so nothing here needs pre-registering: it measures coverage.
"""
from __future__ import annotations

import collections
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from zbot.cipher import variants  # noqa: E402

ONES = ["ZERO", "ONE", "TWO", "THREE", "FOUR", "FIVE", "SIX", "SEVEN", "EIGHT", "NINE", "TEN",
        "ELEVEN", "TWELVE", "THIRTEEN", "FOURTEEN", "FIFTEEN", "SIXTEEN", "SEVENTEEN", "EIGHTEEN",
        "NINETEEN", "TWENTY"]


def numbers(maxn: int) -> dict[str, float]:
    """Spelled numbers 0..maxn with halves, quarters and one decimal place."""
    out = {}
    for i, n in enumerate(ONES[:maxn + 1]):
        out[n] = i
        for s, v in (("ANDAHALF", .5), ("ANDONEHALF", .5), ("ANDAQUARTER", .25), ("POINTFIVE", .5)):
            out[n + s] = i + v
        for d in range(1, 10):
            out[f"{n}POINT{ONES[d]}"] = i + d / 10
    out.update({"HALF": .5, "HALFA": .5, "AHALF": .5, "ONEHALF": .5, "AQUARTER": .25, "POINTFIVE": .5})
    return out


BROAD = dict(
    RN=numbers(9), IN=numbers(20),
    RU=["RADIAN", "RADIANS", "RAD", "RADS"], IU=["INCH", "INCHES", "IN"],
    OPEN=["", "THEBOMBIS", "BOMBIS", "BOMBAT", "THEBOMBISAT", "ITIS", "ITS", "ITISAT", "DIG", "DIGAT",
          "GO", "LOOK", "SET", "SETAT", "BURIED", "BURIEDAT", "YOUWILLFINDIT", "FINDIT", "MEASURE",
          "FROMDIABLO", "FROMMTDIABLO", "FROMMOUNTDIABLO", "FROMTHEMOUNTAIN", "FROMZERO",
          "ITISBURIED", "THEBOMBISBURIED"],
    JOIN=["", "AND", "THEN", "ANDTHEN", "ANDGO", "GO", "OUT", "ANDOUT", "ALONG"],
    ALONG=["ALONG", "ALONGTHE", "ON", "ONTHE", "OUTON", "OUTALONG", "OUT", "FROM", "AT"],
    TAIL=["", "FROMMAGN", "FROMMAGNORTH", "FROMNORTH", "FROMZERO", "CLOCKWISE", "EAST", "WEST",
          "NORTH", "SOUTH", "FROMTHETOP", "FROMDIABLO", "DIGIT", "DIG", "DIGHERE"],
)
NATURAL = dict(
    RN={n: i for i, n in enumerate(ONES[:7])}, IN={n: i for i, n in enumerate(ONES[:13])},
    RU=["RADIAN", "RADIANS"], IU=["INCH", "INCHES"],
    OPEN=["", "THEBOMBIS", "BOMBIS", "ITIS", "THEBOMBISAT", "ITISAT", "DIG", "DIGAT", "BURIEDAT",
          "ITISBURIED"],
    JOIN=["", "AND", "THEN"], ALONG=["ALONG", "ALONGTHE", "ON", "ONTHE", "OUTALONG"],
    TAIL=["", "FROMMAGN", "FROMMAGNORTH", "FROMNORTH", "FROMDIABLO", "FROMMTDIABLO"],
)
TEMPLATES = [  # A = radians, B = inches
    ["OPEN", "RN", "RU", "JOIN", "IN", "IU", "TAIL"],     # A RADIANS [AND] B INCHES
    ["OPEN", "RU", "RN", "JOIN", "IN", "IU", "TAIL"],     # RADIAN A [AND] B INCHES
    ["OPEN", "IN", "IU", "ALONG", "RU", "RN", "TAIL"],    # B INCHES ALONG RADIAN A
    ["OPEN", "IN", "IU", "ALONG", "RN", "RU", "TAIL"],    # B INCHES ALONG A RADIANS
    ["OPEN", "IN", "IU", "JOIN", "RN", "RU", "TAIL"],     # B INCHES [AND] A RADIANS
]


def repeats(ct: str) -> dict[int, list[int]]:
    """later position -> earlier positions holding the same symbol"""
    first: dict[str, int] = {}
    out = collections.defaultdict(list)
    for i, c in enumerate(ct):
        if c in first:
            out[i].append(first[c])
        else:
            first[c] = i
    return out


def enumerate_fits(grammar: dict, ct: str, length: int):
    """Yield (sentence, radians, inches) for every grammar sentence of `length` letters whose
    letters are consistent with the repeats in ct[:length]. Also returns the sentence count."""
    rep = repeats(ct[:length])
    total = 0
    fits = []
    for slots in TEMPLATES:
        opts = [list(grammar[s]) for s in slots]
        # number of completions of each length from slot k on, for counting and pruning
        cnt = [collections.Counter() for _ in range(len(slots) + 1)]
        cnt[-1][0] = 1
        for k in range(len(slots) - 1, -1, -1):
            for x in opts[k]:
                for r, c in cnt[k + 1].items():
                    if len(x) + r <= length:
                        cnt[k][len(x) + r] += c
        total += cnt[0][length]

        def rec(k, prefix, chosen):
            if k == len(slots):
                d = dict(chosen)
                fits.append((prefix, grammar["RN"][d["RN"]], grammar["IN"][d["IN"]]))
                return
            for x in opts[k]:
                s = prefix + x
                if cnt[k + 1][length - len(s)] == 0:
                    continue
                if all(s[a] == s[b] for b in range(len(prefix), len(s)) for a in rep.get(b, ())):
                    rec(k + 1, s, chosen + ((slots[k], x),))
        rec(0, "", ())
    return total, fits


def main() -> None:
    ciphers = {v.split(".", 1)[1]: (ROOT / "data/ciphers/variants" / f"{v}.txt").read_text().strip()
               for v in variants("z32")}
    print("1. Broad grammar, exactly 32 letters")
    for name, ct in ciphers.items():
        total, fits = enumerate_fits(BROAD, ct, 32)
        n = len({s for s, _, _ in fits})
        print(f"   {name:20} {total:>11,} sentences, {n:>6,} fit ({n / total:.1e}; random English ~2.2e-04)")
    print("2. Natural grammar (whole numbers: radians 0-6, inches 0-12), exactly 32 letters")
    for name, ct in ciphers.items():
        total, fits = enumerate_fits(NATURAL, ct, 32)
        print(f"   {name:20} {total:>11,} sentences, {len(fits):>6,} fit")
    print("3. Natural grammar + 1-4 filler letters: instructions (of 7 x 13 = 91) with a fitting wording")
    for name, ct in ciphers.items():
        found = collections.defaultdict(list)
        for pad in (1, 2, 3, 4):
            for s, a, b in enumerate_fits(NATURAL, ct, 32 - pad)[1]:
                found[(a, b)].append(s + "?" * pad)
        ex = "; ".join(f"{k}: {v[0]}" for k, v in sorted(found.items())[:2])
        print(f"   {name:20} {len(found):>3} of 91   e.g. {ex}")


if __name__ == "__main__":
    main()
