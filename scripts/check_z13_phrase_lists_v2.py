#!/usr/bin/env python3
"""C1 v2: check the pre-registered Z13 phrase lists (letter and non-letter readings).

Lists were committed and pushed to github.com/herakles-dev/Zodiac (branch
prereg/z13-phrase-lists-v2, commit ad8e1e9, 2026-11-23T18:25:14Z) before this ran.
Plan, readings, per-test sizes and decision rule: hypotheses/candidates/z13_phrase_lists_v2_PLAN.md.
Hashes are verified first; a changed list aborts.

  python scripts/check_z13_phrase_lists_v2.py   # -> hypotheses/candidates/z13_phrase_lists_v2_results.json

Self-contained. The null for each test: how many of its phrases fit each of 5,000 random repeat
patterns with the reading's own profile (seed 20261123; every pattern when fewer exist), excluding
the reading's own pattern and its reversal. p = (1 + #decoys with >= observed fits) / (1 + #decoys).
Notable iff p < 0.05 / n_tests of the test's family (primary 4, secondary 32).
"""
from __future__ import annotations

import collections
import hashlib
import itertools
import json
import math
import pathlib
import random
import sys

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parent.parent
CAND = ROOT / "hypotheses" / "candidates"
VAR = ROOT / "data" / "ciphers" / "variants"
SEED, ALPHA = 20261123, 0.05
PRIMARY_LISTS = ("nameslot_v2", "opener_v2")
PRIMARY_N = {"exact": 100_000, "homophonic": 15_000}   # first N/2 lines of EACH primary list
N_PRIMARY_TESTS, N_SECONDARY_TESTS = 4, 32
# reading -> (N simple key, N homophonic key); None = exploratory (whole list, never confirmatory)
SECONDARY_N = {
    "blank_p0": (250, None), "blank_p2": (250, None), "blank_p7": (250, None),
    "dash_p0": (None, None),
    "blank_p1": (2000, 2000), "blank_p3": (2000, 2000), "blank_p5": (2000, 2000), "blank_p9": (2000, 2000),
    "dash_p1": (303, 303), "dash_p2": (None, None), "dash_p3": (10000, 5000),
    "blank_p4": (None, None), "dash_p4": (None, None),
    "dash_p5": (5000, None), "dash_p7": (250, None), "dash_p9": (1000, 1000),
}


# ---- patterns ----------------------------------------------------------------

def iso(seq) -> tuple:
    m: dict = {}
    return tuple(m.setdefault(c, len(m)) for c in seq)


def profile_of(ct) -> list[int]:
    return sorted(collections.Counter(ct).values(), reverse=True)


def fits(plain, ct, mode="simple", skip=None) -> bool:
    idx = [i for i in range(len(ct)) if i != skip]
    p, c = "".join(plain[i] for i in idx), "".join(ct[i] for i in idx)
    if mode == "simple":
        return iso(p) == iso(c)
    m: dict = {}
    return all(m.setdefault(a, b) == b for a, b in zip(c, p))


def fits_one_slip(plain, ct) -> bool:
    return fits(plain, ct) or any(fits(plain, ct, "simple", i) for i in range(len(ct)))


def n_isomorphs(profile) -> int:
    out = math.factorial(sum(profile))
    for c in profile:
        out //= math.factorial(c)
    for m in collections.Counter(profile).values():
        out //= math.factorial(m)
    return out


def decoys(profile, n, seed, exclude=()) -> list[tuple]:
    """n distinct random patterns with this profile; every pattern if fewer than n exist."""
    excl = {e for e in exclude if len(e) == sum(profile) and profile_of(e) == sorted(profile, reverse=True)}
    avail = n_isomorphs(profile)
    rng = random.Random(seed)
    base = [i for i, cnt in enumerate(profile) for _ in range(cnt)]
    if n > avail - len(excl):   # small space: the full population, sorted
        seen: set = set()
        while len(seen) < avail:
            rng.shuffle(base)
            seen.add(iso(base))
        return sorted(seen - excl)
    seen, out = set(exclude), []
    while len(out) < n:
        rng.shuffle(base)
        p = iso(base)
        if p not in seen:
            seen.add(p)
            out.append(p)
    return out


# ---- fast null via position-pair equality bitmasks ---------------------------

def _pairs(L):
    return list(itertools.combinations(range(L), 2))


def masks(arr):
    n, L = arr.shape
    lo, hi = np.zeros(n, np.uint64), np.zeros(n, np.uint64)
    for k, (i, j) in enumerate(_pairs(L)):
        bit = (arr[:, i] == arr[:, j]).astype(np.uint64)
        if k < 64:
            lo |= bit << np.uint64(k)
        else:
            hi |= bit << np.uint64(k - 64)
    return lo, hi


def null_counts(cands, profile, key, n_decoys=5000, seed=SEED, exclude=()):
    """Per decoy: how many candidates fit it under `key` (exact | homophonic | slip)."""
    L = sum(profile)
    arr = np.frombuffer("".join(cands).encode("ascii"), np.uint8).reshape(-1, L).astype(np.int16)
    clo, chi = masks(arr)
    dlo, dhi = masks(np.array(decoys(profile, n_decoys, seed, exclude), dtype=np.int16))
    out = np.empty(len(dlo), np.int32)
    if key == "exact":
        cnt = collections.Counter(zip(clo.tolist(), chi.tolist()))
        return np.array([cnt.get(k, 0) for k in zip(dlo.tolist(), dhi.tolist())], np.int32)
    drop = []
    for i in range(L):
        a = b = 0
        for k, (x, y) in enumerate(_pairs(L)):
            if i not in (x, y):
                if k < 64:
                    a |= 1 << k
                else:
                    b |= 1 << (k - 64)
        drop.append((np.uint64(a), np.uint64(b)))
    for j in range(len(dlo)):
        a, b = dlo[j], dhi[j]
        if key == "homophonic":
            out[j] = int((((clo & a) == a) & ((chi & b) == b)).sum())
        else:
            ok = np.zeros(len(clo), bool)
            for mlo, mhi in drop:
                ok |= ((clo & mlo) == (a & mlo)) & ((chi & mhi) == (b & mhi))
            out[j] = int(ok.sum())
    return out


def decision(observed: int, null, n_tests: int, alpha: float = ALPHA) -> dict:
    null = np.asarray(null)
    pval = (1 + int((null >= observed).sum())) / (1 + len(null))
    per = alpha / n_tests
    return {"pval": pval, "alpha_per_test": per, "expected": float(null.mean()),
            "notable": bool(observed > 0 and pval < per)}


# ---- readings ------------------------------------------------------------------

def read(name):
    return (VAR / f"z13.{name}.txt").read_text().strip()


def secondary_readings() -> list[dict]:
    """Each distinct symbol of the canonical reading as a blank (null) or a dash (word separator)."""
    base, out, seen = read("canonical"), [], []
    for s in base:
        if s in seen:
            continue
        seen.append(s)
        pos = [i for i, c in enumerate(base) if c == s]
        ct = "".join(c for c in base if c != s)
        runs, n = [], 0
        for c in base:
            if c != s:
                n += 1
            elif n:
                runs.append(n)
                n = 0
        if n:
            runs.append(n)
        out.append({"name": f"blank_p{pos[0]}", "ct": ct, "list": f"blank_len{len(ct)}_v2"})
        out.append({"name": f"dash_p{pos[0]}", "ct": ct, "lengths": tuple(runs),
                    "list": "dash_" + "-".join(map(str, runs)) + "_v2"})
    return out


# ---- check ---------------------------------------------------------------------

def load(name):
    body = (CAND / f"z13_{name}.txt").read_bytes()
    want = (CAND / f"z13_{name}.sha256").read_text().strip()
    got = hashlib.sha256(body).hexdigest()
    if got != want:
        sys.exit(f"z13_{name}: hash mismatch ({got} != {want}); list changed after registration")
    return [l for l in body.decode().splitlines() if l]


def test_row(name, phrases, ct, key, n_decoys, n_tests, confirmatory):
    letters = [p.replace(" ", "") for p in phrases if len(p.replace(" ", "")) == len(ct)]
    if key == "slip":
        hits = [p for p in letters if fits_one_slip(p, ct)]
    else:
        hits = [p for p in letters if fits(p, ct, "simple" if key == "exact" else "homophonic")]
    null = null_counts(letters, profile_of(ct), key, n_decoys, SEED, {iso(ct), iso(ct[::-1])})
    d = decision(len(hits), null, n_tests if confirmatory else 1)
    return {"test": name, "key": key, "n_lines": len(letters), "confirmatory": confirmatory,
            "observed": len(hits), "fits": hits, "expected_chance": d["expected"], "pval": d["pval"],
            "alpha_per_test": d["alpha_per_test"], "notable": d["notable"] and confirmatory,
            "n_decoys": int(len(null))}


def main():
    lists = {n: load(n) for n in PRIMARY_LISTS}
    sec = secondary_readings()
    for r in sec:
        lists.setdefault(r["list"], load(r["list"]))
    print(f"verified {len(lists)} list hashes")
    rows = []
    prim = {"canonical": read("canonical"), "reversed": read("reversed")}
    assert iso(read("bracket_is_perp")) == iso(prim["canonical"])   # same test as canonical
    for rname, ct in prim.items():
        for key, N in PRIMARY_N.items():
            ph = [p for n in PRIMARY_LISTS for p in lists[n][: N // 2]]
            rows.append(test_row(f"primary/{rname}", ph, ct, key, 5000, N_PRIMARY_TESTS, True))
    full = [p for n in PRIMARY_LISTS for p in lists[n]]
    for rname, ct in prim.items():                       # exploratory
        for key in ("homophonic", "slip"):
            rows.append(test_row(f"explore/{rname}", full, ct, key, 5000, N_PRIMARY_TESTS, False))
    for key in ("exact", "homophonic", "slip"):
        rows.append(test_row("explore/circles_distinct", full, read("circles_distinct"), key, 2000,
                             N_PRIMARY_TESTS, False))
    for r in sec:
        for key, N in zip(("exact", "homophonic"), SECONDARY_N[r["name"]]):
            ph = lists[r["list"]][:N] if N else lists[r["list"]]
            rows.append(test_row(f"secondary/{r['name']}", ph, r["ct"], key, 5000, N_SECONDARY_TESTS, N is not None))

    for x in rows:
        tag = "NOTABLE" if x["notable"] else ("exploratory" if not x["confirmatory"] and x["observed"] else "")
        print(f"{x['test']:28} {x['key']:10} {x['n_lines']:>7} {x['observed']:>4} "
              f"E={x['expected_chance']:.4f} p={x['pval']:.4f} {tag}")
    conf = [x for x in rows if x["confirmatory"]]
    print(f"\nconfirmatory: {len(conf)} tests, {sum(x['observed'] for x in conf)} fits, "
          f"{sum(x['expected_chance'] for x in conf):.3f} expected by chance, "
          f"{sum(x['notable'] for x in conf)} notable")
    (CAND / "z13_phrase_lists_v2_results.json").write_text(json.dumps({"rows": rows}, indent=1) + "\n")


if __name__ == "__main__":
    main()
