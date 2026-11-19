"""Simulated-annealing solver for (homophonic or simple) substitution.

The key maps each cipher symbol to a letter. Score = letter 5-gram
log-probability of the decode (summed over segments, so separate ciphers
can share one key without windows crossing between them), minus an
optional frequency penalty that stops long homophonic decodes collapsing
onto E/T/A.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numba import njit

from . import lm


@njit(cache=True)
def _score(key, seq, seg_start, seg_end, lp1, lp2, lp3, lp4, lp5, logu, klw, counts):
    total = 0.0
    for s in range(seg_start.shape[0]):
        a, b = seg_start[s], seg_end[s]
        for i in range(a, b):
            n = i - a + 1
            if n > 5:
                n = 5
            code = 0
            for j in range(i - n + 1, i + 1):
                code = code * 26 + key[seq[j]]
            if n == 5:
                total += lp5[code]
            elif n == 4:
                total += lp4[code]
            elif n == 3:
                total += lp3[code]
            elif n == 2:
                total += lp2[code]
            else:
                total += lp1[code]
    if klw > 0.0:
        for l in range(26):
            counts[l] = 0
        N = 0
        for s in range(seg_start.shape[0]):
            for i in range(seg_start[s], seg_end[s]):
                counts[key[seq[i]]] += 1
                N += 1
        pen = 0.0
        for l in range(26):
            c = counts[l]
            if c > 0:
                pen += c * (np.log(c / N) - logu[l])
        total -= klw * pen
    return total


@njit(cache=True)
def _contrib(i, key, seq, posseg, lp1, lp2, lp3, lp4, lp5):
    a = posseg[i]
    n = i - a + 1
    if n > 5:
        n = 5
    code = 0
    for j in range(i - n + 1, i + 1):
        code = code * 26 + key[seq[j]]
    if n == 5:
        return lp5[code]
    elif n == 4:
        return lp4[code]
    elif n == 3:
        return lp3[code]
    elif n == 2:
        return lp2[code]
    return lp1[code]


@njit(cache=True)
def _pen(counts, N, logu, xlogx):
    # sum_l c_l * (log(c_l / N) - log p_l)  ==  N * KL(observed || English)
    pen = -xlogx[N]
    for l in range(26):
        c = counts[l]
        if c > 0:
            pen += xlogx[c] - c * logu[l]
    return pen


@njit(cache=True)
def _affected(s, partner, sym_ptr, sym_pos, posend, stamp, tick, buf):
    m = 0
    for q in (s, partner):
        if q < 0:
            continue
        for k in range(sym_ptr[q], sym_ptr[q + 1]):
            p = sym_pos[k]
            e = posend[p]
            for i in range(p, min(p + 5, e)):
                if stamp[i] != tick:
                    stamp[i] = tick
                    buf[m] = i
                    m += 1
    return m


@njit(cache=True)
def _anneal(seq, seg_start, seg_end, n_sym, pins, injective, lp1, lp2, lp3, lp4, lp5,
            logu, klw, iters, t0, t1, seed):
    np.random.seed(seed)
    N = seq.shape[0]
    posseg = np.zeros(N, dtype=np.int64)
    posend = np.zeros(N, dtype=np.int64)
    for g in range(seg_start.shape[0]):
        for i in range(seg_start[g], seg_end[g]):
            posseg[i] = seg_start[g]
            posend[i] = seg_end[g]
    mult = np.zeros(n_sym, dtype=np.int64)
    for i in range(N):
        mult[seq[i]] += 1
    sym_ptr = np.zeros(n_sym + 1, dtype=np.int64)
    for q in range(n_sym):
        sym_ptr[q + 1] = sym_ptr[q] + mult[q]
    fill = sym_ptr[:-1].copy()
    sym_pos = np.zeros(N, dtype=np.int64)
    for i in range(N):
        sym_pos[fill[seq[i]]] = i
        fill[seq[i]] += 1
    xlogx = np.zeros(N + 1)
    for c in range(1, N + 1):
        xlogx[c] = c * np.log(c)
    stamp = np.full(N, -1, dtype=np.int64)
    buf = np.zeros(N, dtype=np.int64)

    key = np.zeros(n_sym, dtype=np.int64)
    if injective:
        perm = np.random.permutation(26)
        for q in range(n_sym):
            key[q] = perm[q % 26]
    else:
        for q in range(n_sym):
            key[q] = np.random.randint(26)
    for q in range(n_sym):
        if pins[q] >= 0:
            key[q] = pins[q]
    nfree = 0
    for q in range(n_sym):
        if pins[q] < 0 and mult[q] > 0:
            nfree += 1
    free = np.zeros(nfree, dtype=np.int64)
    k = 0
    for q in range(n_sym):
        if pins[q] < 0 and mult[q] > 0:
            free[k] = q
            k += 1
    counts = np.zeros(26, dtype=np.int64)
    for i in range(N):
        counts[key[seq[i]]] += 1
    lmsum = 0.0
    for i in range(N):
        lmsum += _contrib(i, key, seq, posseg, lp1, lp2, lp3, lp4, lp5)
    pen = _pen(counts, N, logu, xlogx) if klw > 0.0 else 0.0
    cur = lmsum - klw * pen
    best = cur
    best_key = key.copy()
    if nfree == 0:
        return best_key, best
    step = (t1 / t0) ** (1.0 / iters)
    T = t0
    for it in range(iters):
        T *= step
        s = free[np.random.randint(nfree)]
        old = key[s]
        new = np.random.randint(26)
        if new == old:
            continue
        partner = -1
        if injective:
            for q in range(n_sym):
                if q != s and key[q] == new:
                    partner = q
                    break
            if partner >= 0 and pins[partner] >= 0:
                continue
        m = _affected(s, partner, sym_ptr, sym_pos, posend, stamp, it, buf)
        before = 0.0
        for z in range(m):
            before += _contrib(buf[z], key, seq, posseg, lp1, lp2, lp3, lp4, lp5)
        key[s] = new
        counts[old] -= mult[s]
        counts[new] += mult[s]
        if partner >= 0:
            key[partner] = old
            counts[new] -= mult[partner]
            counts[old] += mult[partner]
        after = 0.0
        for z in range(m):
            after += _contrib(buf[z], key, seq, posseg, lp1, lp2, lp3, lp4, lp5)
        npen = _pen(counts, N, logu, xlogx) if klw > 0.0 else 0.0
        cand = lmsum + after - before - klw * npen
        d = cand - cur
        if d >= 0 or np.random.random() < np.exp(d / T):
            cur = cand
            lmsum += after - before
            pen = npen
            if cur > best:
                best = cur
                best_key[:] = key
        else:
            key[s] = old
            counts[new] -= mult[s]
            counts[old] += mult[s]
            if partner >= 0:
                key[partner] = new
                counts[old] -= mult[partner]
                counts[new] += mult[partner]
    return best_key, best


@dataclass
class Solution:
    score: float          # total log-prob (nats), penalty included
    per_letter: float     # score / length
    key: np.ndarray
    plaintext: str        # segments joined with '/'


def solve(segments: list[np.ndarray], n_sym: int, *, restarts: int = 8, iters: int | None = None,
          injective: bool = False, pins: dict[int, int] | None = None, klw: float = 1.0,
          t0: float = 20.0, t1: float = 0.5, seed: int = 0) -> list[Solution]:
    """Return the best solution of each restart, best first."""
    t = lm.load()
    seq = np.concatenate(segments).astype(np.int64)
    lens = np.array([len(s) for s in segments], dtype=np.int64)
    seg_end = np.cumsum(lens)
    seg_start = seg_end - lens
    pin_arr = np.full(n_sym, -1, dtype=np.int64)
    for s, l in (pins or {}).items():
        pin_arr[s] = l
    if iters is None:
        iters = max(50_000, 10_000 * n_sym)
    logu = np.log(t["unigram"])
    out = []
    for r in range(restarts):
        key, sc = _anneal(seq, seg_start, seg_end, n_sym, pin_arr, injective,
                          t["lp1"], t["lp2"], t["lp3"], t["lp4"], t["lp5"], logu, klw,
                          iters, t0, t1, seed * 1_000_003 + r)
        letters = [chr(65 + key[x]) for x in seq]
        parts, i = [], 0
        for L in lens:
            parts.append("".join(letters[i:i + L]))
            i += L
        out.append(Solution(sc, sc / len(seq), key.copy(), "/".join(parts)))
    out.sort(key=lambda s: -s.score)
    return out


def accuracy(plain: str, truth: str) -> float:
    pairs = [(a, b) for a, b in zip(plain.replace("/", ""), truth) if b.isalpha()]
    return sum(a == b for a, b in pairs) / max(1, len(pairs))
