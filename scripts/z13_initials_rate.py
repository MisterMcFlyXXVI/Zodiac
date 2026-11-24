#!/usr/bin/env python3
"""Z13 initials hypothesis: does word-initial text fit Z13's simple-key repeat pattern more often than running text?

How often do 13-letter sequences fit Z13's repeat pattern (simple key), for
(a) running text letters, (b) initial letters of consecutive words? Corpus: brown + gutenberg.
Pattern-only Bayes factor for 'Z13 = initials' vs 'Z13 = running text'. No candidate is reported.

  python scripts/z13_initials_rate.py     # -> results/z13_initials_rate/results.json
Needs data/corpus (scripts/fetch_corpus.py). Pattern-only: no phrase is reported, no names are involved.
"""
import json, pathlib, re, sys
from math import sqrt
import numpy as np

ROOT = pathlib.Path(__file__).resolve().parent.parent
ISO = np.array([0,1,2,3,4,5,4,6,4,7,2,0,6])  # AENz0K0M0[NAM  (Z13 canonical repeat pattern)
L = 13
pairs = [(i, j) for i in range(L) for j in range(i+1, L)]
EQ = np.array([ISO[i] == ISO[j] for i, j in pairs])


def load_words(corpus=ROOT / "data" / "corpus"):
    words = []
    for n in ("brown", "gutenberg"):
        words += [w for w in (re.sub(r"[^a-z]", "", t.lower()) for t in (corpus / f"{n}.txt").read_text(encoding="utf-8").split()) if w]
    return words


def count_fits(arr):  # arr (n,13) int
    ok = np.ones(len(arr), bool)
    for k, (i, j) in enumerate(pairs):
        ok &= (arr[:, i] == arr[:, j]) == EQ[k]
    return int(ok.sum())


def ci(k, n):
    z = 1.96; ph = k / n; den = 1 + z*z/n
    c = (ph + z*z/(2*n)) / den; h = z*sqrt(ph*(1-ph)/n + z*z/(4*n*n)) / den
    return max(c-h, 0), c+h


def to_arr(s):
    return np.frombuffer(s.encode(), np.uint8).astype(np.int16) - 97


def main():
    words = load_words()
    a = to_arr("".join(words))
    fa = na = 0
    for s in range(0, len(a) - L, 2_000_000):
        e = min(s + 2_000_000, len(a) - L + 1)
        W = a[np.arange(s, e)[:, None] + np.arange(L)]
        fa += count_fits(W); na += len(W)
    b = to_arr("".join(w[0] for w in words))
    Wb = b[np.arange(len(b) - L + 1)[:, None] + np.arange(L)]
    fb, nb = count_fits(Wb), len(Wb)
    p = np.bincount(b, minlength=26) / len(b)
    rng = np.random.default_rng(20261124); fc = nc = 0
    for _ in range(40):
        W = rng.choice(26, size=(2_000_000, L), p=p).astype(np.int16); fc += count_fits(W); nc += len(W)
    out = {}
    for key, name, k, n in (("running", "running text, any start", fa, na), ("initials", "word initials, consecutive", fb, nb),
                            ("iid_initials", "iid initial-letter freqs", fc, nc)):
        lo, hi = ci(k, n); out[key] = dict(fits=k, windows=n, rate=k / n, ci95=[lo, hi])
        print(f"{name:28} {k:4d} / {n:>11,}  rate {k/n:.2e}  (95% {lo:.1e}-{hi:.1e})")
    bf = (fb/nb)/(fa/na) if fa else float("nan")
    out["bayes_factor_initials_over_running"] = bf
    print(f"Bayes factor initials/running (pattern only): {bf:.2f}")
    d = ROOT / "results" / "z13_initials_rate"; d.mkdir(parents=True, exist_ok=True)
    (d / "results.json").write_text(json.dumps(out, indent=1) + "\n")


if __name__ == "__main__":
    main()
