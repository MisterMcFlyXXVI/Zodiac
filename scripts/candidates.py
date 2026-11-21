#!/usr/bin/env python3
"""Pre-registered candidate plaintexts for Z13 and Z32, and an exact fit checker.

  python scripts/candidates.py generate   # writes hypotheses/candidates/*.txt (+ SHA-256)
  python scripts/candidates.py check      # tests every list against every transcription

Lists are generated from facts in the letters and COMMITTED BEFORE CHECKING, so a fit
can't come from adjusting the list afterwards. A fit is judged against how often a random
English passage of the same length fits (measured in results/FINDINGS.md), times list size.
"""
from __future__ import annotations

import hashlib
import itertools
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
OUT = ROOT / "hypotheses" / "candidates"

NUM = ["ZERO", "ONE", "TWO", "THREE", "FOUR", "FIVE", "SIX", "SEVEN", "EIGHT", "NINE", "TEN", "ELEVEN", "TWELVE"]


def z32_radians() -> list[str]:
    """Letters of 26 Jun 1970 (map, 'where the bomb is set', '0 is to be set to Mag. N.', marks
    3/6/9) and 26 Jul 1970 ('Radians & # inches along the radians')."""
    out = set()
    rad_counts = NUM[0:10]      # the map dial shows 0, 3, 6, 9
    inch_counts = NUM[1:13]     # map-scale distances
    for a, b in itertools.product(rad_counts, inch_counts):
        R = "RADIAN" if a == "ONE" else "RADIANS"
        I = "INCH" if b == "ONE" else "INCHES"
        templates = [
            f"{a} {R} {b} {I}", f"{a} {R} AND {b} {I}", f"{a} {R} THEN {b} {I}",
            f"{b} {I} ALONG {a} {R}", f"{b} {I} ALONG RADIAN {a}", f"{b} {I} ALONG THE RADIAN {a}",
            f"RADIAN {a} {b} {I}", f"RADIAN {a} AND {b} {I}", f"RADIAN {a} THEN {b} {I}",
            f"THE BOMB IS {a} {R} {b} {I}", f"THE BOMB IS AT RADIAN {a} {b} {I}",
            f"BOMB IS {b} {I} ALONG RADIAN {a}", f"THE BOMB IS {b} {I} ALONG RADIAN {a}",
            f"SET AT RADIAN {a} AND GO {b} {I}", f"GO {b} {I} ALONG RADIAN {a}",
            f"DIG {b} {I} ALONG RADIAN {a}", f"DIG AT RADIAN {a} {b} {I}",
            f"{a} {R} FROM MAG N {b} {I}", f"{a} {R} FROM NORTH {b} {I}",
            f"{a} {R} FROM MAGNETIC NORTH {b} {I}", f"{b} {I} OUT ON RADIAN {a}",
            f"MEASURE {a} {R} AND {b} {I}", f"BOMB AT {a} {R} AND {b} {I}",
        ]
        for t in templates:
            s = t.replace(" ", "")
            if len(s) == 32:
                out.add(t)
    return sorted(out)


def z13_mikado_persona() -> list[str]:
    """Letter of 20 Apr 1970 ('My name is --') and 26 Jul 1970 (quotes Ko-Ko's 'I've got a
    little list' from Gilbert & Sullivan's The Mikado; '13 of my slaves')."""
    names = ["KOKO", "NANKIPOO", "POOHBAH", "PISHTUSH", "YUMYUM", "PITTISING", "PEEPBO", "KATISHA",
             "MIKADO", "THE MIKADO", "LORD HIGH EXECUTIONER", "EXECUTIONER", "THE EXECUTIONER",
             "ZODIAC", "THE ZODIAC", "ZODIAC KILLER", "THE ZODIAC KILLER"]
    lead = ["", "I AM", "IM", "MY NAME IS", "NAME IS", "IT IS", "ITS", "MR", "CALL ME", "I AM THE", "THE"]
    tail = ["", "SAN", "JAPAN", "OF JAPAN", "THE", "SR", "JR"]
    out = set()
    for l, n, t in itertools.product(lead, names, tail):
        phrase = " ".join(x for x in (l, n, t) if x)
        if len(phrase.replace(" ", "")) == 13:
            out.add(phrase)
    for a, b in itertools.permutations(names, 2):  # pairs, e.g. 'KOKO THE MIKADO'
        for j in ("", "AND", "THE"):
            phrase = " ".join(x for x in (a, j, b) if x)
            if len(phrase.replace(" ", "")) == 13:
                out.add(phrase)
    return sorted(out)


LISTS = {"z32_radians_v1": (z32_radians, ["z32"]),
         "z13_mikado_persona_v1": (z13_mikado_persona, ["z13"])}


def generate() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for name, (fn, _) in LISTS.items():
        lines = fn()
        body = "\n".join(lines) + "\n"
        (OUT / f"{name}.txt").write_text(body)
        (OUT / f"{name}.sha256").write_text(hashlib.sha256(body.encode()).hexdigest() + "\n")
        print(f"{name}: {len(lines)} candidates")


def check() -> None:
    from zbot import evaluate as E
    from zbot.cipher import variants

    def iso(s):
        m = {}
        return "".join(m.setdefault(c, chr(97 + len(m))) for c in s)

    def fits(s, t, mode):
        if len(s) != len(t):
            return False
        if mode == "simple":
            return iso(s) == iso(t)
        m = {}
        return all(m.setdefault(a, b) == b for a, b in zip(t, s))

    chance = {("z13", "simple"): 1 / 715_000, ("z13", "homophonic"): 1 / 2_100_000, ("z32", "homophonic"): 1 / 4_544}
    for name, (_, bases) in LISTS.items():
        body = (OUT / f"{name}.txt").read_text()
        assert hashlib.sha256(body.encode()).hexdigest() == (OUT / f"{name}.sha256").read_text().strip(), \
            "list changed after registration"
        cands = [l for l in body.splitlines() if l]
        for base in bases:
            for v in [base] + [x for x in variants(base) if not x.endswith(".canonical")]:
                t = E.real_texts({"cipher": v})[0]
                for mode in ("simple", "homophonic"):
                    if mode == "simple" and len(set(t)) > 26:
                        continue
                    hits = [c for c in cands if fits(c.replace(" ", ""), t, mode)]
                    exp = len(cands) * chance.get((base, mode), chance.get((base, "homophonic")))
                    print(f"{name:24} {v:24} {mode:10} candidates={len(cands):5} fits={len(hits)} "
                          f"(chance expects {exp:.3f})" + (f"  -> {hits[:5]}" if hits else ""))


if __name__ == "__main__":
    {"generate": generate, "check": check}[sys.argv[1]]()
