#!/usr/bin/env python3
"""B4: error-tolerant Z13 fitting (one encoding slip), with the chance rate priced in.

A "fit" that tolerates one encoding slip -- one position left free under the simple
(isomorph) key -- is cheap. On the C1 v1 lists, ~4% of profile-matched decoys produce at
least one one-slip fit. So a one-slip fit is never notable on its own: it is notable only
when its COUNT beats what decoys of the SAME reading's repeat profile produce, after paying
for the family of tests that were declared.

Two facts drive the design:

1. Each Z13 reading has its own repeat profile. canonical/reversed/bracket_is_perp are
   [3,2,2,2,1,1,1,1] (8 symbols); circles_distinct is [2,2,2,1,1,1,1,1,1,1] (10 symbols, much
   looser, fits far more by chance); crosshair_null is [3,2,2,2,1,1,1] (12 long, 7 symbols).
   The null must be measured per reading, not once on the canonical profile. (Wave-2 review
   caught the canonical-only baseline under-pricing circles_distinct.)

2. One slip is a single SUBSTITUTION (a transcription/key error at one position), not an
   insertion or deletion. Length is preserved, so a candidate must still have the reading's
   length; a length mismatch is never rescued by a slip.

Public API:
  iso(seq)                           canonical isomorph tuple
  profile_of(ct)                     a reading's repeat profile (descending counts)
  fits(plain, ct, mode, skip)        one candidate vs one reading (matches C1 check.py)
  fits_one_slip(plain, ct, mode)     any single position free
  null_counts(cands, profile, ...)   per-decoy fit-count distribution (exact/slip/homophonic)
  price(observed, null, alpha)       per-cell verdict: expected, threshold, p-value, notable?
  decision(observed, null, n_tests)  family-aware (Bonferroni) verdict

Hard rule for every caller: never fit, test or publish names of real people. A fit is only a
statement about a repeat pattern, never evidence about a person.
"""
from __future__ import annotations

import collections
import random

import numpy as np

# ---- isomorph + profile ----------------------------------------------------


def iso(seq) -> tuple:
    """Canonical isomorph: first occurrence of each symbol gets the next integer."""
    m: dict = {}
    return tuple(m.setdefault(c, len(m)) for c in seq)


def profile_of(ct: str) -> list[int]:
    """Descending repeat counts, e.g. 'AENz0K0M0[NAM' -> [3,2,2,2,1,1,1,1]."""
    return sorted(collections.Counter(ct).values(), reverse=True)


# ---- fit tests (identical semantics to scripts/check_z13_phrase_lists.py) ----------------


def fits(plain, ct, mode: str = "simple", skip=None) -> bool:
    """True if candidate letters `plain` fit reading `ct`.

    simple:     isomorph equality over the kept positions.
    homophonic: each cipher symbol maps to one plain letter (many symbols may share a letter).
    skip:       a position index to leave free (one slip), or None for an exact fit.
    """
    idx = [i for i in range(len(ct)) if i != skip]
    p = "".join(plain[i] for i in idx)
    c = "".join(ct[i] for i in idx)
    if mode == "simple":
        return iso(p) == iso(c)
    m: dict = {}
    return all(m.setdefault(a, b) == b for a, b in zip(c, p))


def fits_one_slip(plain, ct, mode: str = "simple") -> bool:
    """True if the candidate fits with at most one position free."""
    if fits(plain, ct, mode):
        return True
    return any(fits(plain, ct, mode, i) for i in range(len(ct)))


# ---- decoys with an arbitrary profile --------------------------------------


def n_isomorphs(profile) -> int:
    """Number of distinct isomorphs (repeat patterns) with this repeat profile:
    L! / (prod c_i!  *  prod over each count value of (#symbols with that count)!)."""
    import math
    L = sum(profile)
    out = math.factorial(L)
    for c in profile:
        out //= math.factorial(c)
    for m in collections.Counter(profile).values():
        out //= math.factorial(m)
    return out


def decoy_isomorphs(profile, n, seed, exclude=()):  # -> list[tuple]
    """`n` distinct random isomorphs with the given repeat `profile`.

    `exclude` is a set of isomorph tuples to drop (the real reading and its reversal).
    Deterministic in `seed`. Raises ValueError if fewer than `n` such isomorphs exist (it used to
    loop forever, e.g. 5,000 decoys for a profile with only 3,150 patterns).
    """
    excl = {e for e in exclude if len(e) == sum(profile) and sorted(
        collections.Counter(e).values(), reverse=True) == sorted(profile, reverse=True)}
    if n > n_isomorphs(profile) - len(excl):
        raise ValueError(f"only {n_isomorphs(profile) - len(excl)} isomorphs with profile "
                         f"{list(profile)} (after exclusions); asked for {n}")
    rng = random.Random(seed)
    base = [i for i, cnt in enumerate(profile) for _ in range(cnt)]
    seen = set(exclude)
    out: list[tuple] = []
    while len(out) < n:
        rng.shuffle(base)
        p = iso(base)
        if p not in seen:
            seen.add(p)
            out.append(p)
    return out


# ---- per-decoy fit-count null ----------------------------------------------


def null_counts(cands, profile, n_decoys=2000, seed=20261123, exclude=()):
    """Distribution, over `n_decoys` profile-matched decoys, of how many of `cands` fit each
    decoy under the exact-simple, one-slip-simple, and homophonic keys.

    cands: iterable of candidate letter strings (spaces already removed), all of the reading's
           length. Returns {'exact','slip','homophonic'} -> np.int array of length n_decoys.
    """
    cands = list(cands)
    L = len(profile_len_check(cands, profile))
    decoys = decoy_isomorphs(profile, n_decoys, seed, exclude)

    # inverted indices over candidate isomorphs (simple key)
    exact_idx: dict = collections.defaultdict(set)
    slip_idx: dict = collections.defaultdict(set)
    for k, c in enumerate(cands):
        exact_idx[iso(c)].add(k)
        for i in range(L):
            slip_idx[(i, iso(c[:i] + c[i + 1:]))].add(k)

    arr = np.array([[ord(ch) - 65 for ch in c] for c in cands], dtype=np.int16)

    e = np.empty(n_decoys, dtype=np.int32)
    s = np.empty(n_decoys, dtype=np.int32)
    h = np.empty(n_decoys, dtype=np.int32)
    for j, d in enumerate(decoys):
        e[j] = len(exact_idx.get(d, ()))
        hit: set = set()
        for i in range(L):
            hit |= slip_idx.get((i, iso(d[:i] + d[i + 1:])), set())
        s[j] = len(hit)
        # homophonic: equal cipher symbols force equal plain letters
        ok = np.ones(len(cands), bool)
        first: dict = {}
        for pos, sym in enumerate(d):
            if sym in first:
                ok &= arr[:, pos] == arr[:, first[sym]]
            else:
                first[sym] = pos
        h[j] = int(ok.sum())
    return {"exact": e, "slip": s, "homophonic": h}


def profile_len_check(cands, profile):
    """Guard: every candidate must have the reading's length. Returns the first candidate."""
    L = sum(profile)
    bad = [c for c in cands if len(c) != L]
    if bad:
        raise ValueError(f"{len(bad)} candidate(s) not length {L}, e.g. {bad[0]!r}")
    if not cands:
        raise ValueError("no candidates of the reading's length")
    return cands[0]


# ---- pricing + decision ----------------------------------------------------


def price(observed: int, null, alpha: float = 0.01) -> dict:
    """Per-cell pricing of an observed fit count against its null distribution.

    pval uses add-one smoothing: (1 + #{null >= observed}) / (1 + n), so an unobserved count
    never gets p = 0. notable = observed beats the (1-alpha) quantile AND is positive.
    """
    null = np.asarray(null)
    n = len(null)
    thr = float(np.quantile(null, 1 - alpha))
    ge = int((null >= observed).sum())
    return {
        "observed": int(observed),
        "expected": float(null.mean()),
        "p95": float(np.quantile(null, 0.95)),
        "p99": float(np.quantile(null, 0.99)),
        "max": int(null.max()),
        "frac_ge1": float((null >= 1).mean()),
        "threshold": thr,
        "pval": (1 + ge) / (1 + n),
        "notable": bool(observed > 0 and observed > thr),
    }


def decision(observed: int, null, n_tests: int = 1, alpha: float = 0.05) -> dict:
    """Family-aware verdict. The one-slip family is every declared (list x reading) cell, so a
    lone fit must survive a Bonferroni correction for n_tests.

    notable iff the add-one p-value is below alpha / n_tests. family_expected is the number of
    such fits expected across the whole family by chance (mean null count x n_tests): when it
    is near or above 1, seeing a few k=1 fits is exactly what chance predicts.
    """
    per = alpha / n_tests
    p = price(observed, null, alpha=per)
    p["n_tests"] = int(n_tests)
    p["alpha_family"] = alpha
    p["alpha_per_test"] = per
    p["family_expected"] = float(np.asarray(null).mean() * n_tests)
    p["notable"] = bool(observed > 0 and p["pval"] < per)
    # what a naive "any fit counts" rule would have said -- kept to make the difference visible
    p["naive_notable"] = bool(observed > 0)
    return p
