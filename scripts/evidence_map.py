#!/usr/bin/env python
"""C2 evidence map: measure message bits, constraint bits, gap, and extra-ciphertext estimate
for Z13 and Z32. Seeded and deterministic. Prints every number used in EVIDENCE_MAP.md.
Run: python scripts/evidence_map.py
No decoding is attempted: only counts of how many English passages fit a repeat pattern."""
import pathlib
import sys, math, time
import numpy as np
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from zbot import lm
from zbot.cipher import load
import voi

SEED = 20261123
rng = np.random.default_rng(SEED)
L2 = math.log(2)
def b2(nat): return nat / L2
def hdr(s): print(f"\n=== {s} ===")

z32 = load("z32.canonical").text
z13 = load("z13.canonical").text
print("Z32:", len(z32), "positions,", len(set(z32)), "distinct symbols")
print("Z13:", len(z13), "positions,", len(set(z13)), "distinct symbols")

# ---------- 1. message bits ----------
hdr("1. Message bits (5-gram letter LM; score_text returns NATURAL log, converted to bits)")
hold = lm.holdout_text()
print("held-out letters available:", len(hold))
seg = hold[:300000]
ce = -b2(lm.score_text(seg)) / len(seg)
print(f"cross-entropy on first {len(seg)} held-out letters: {ce:.3f} bits/letter (steady state, context carried)")
# per-window cold start cost on held-out text, and on pool passages
hw = lm.holdout_words()
print("held-out words:", len(hw))

def holdout_windows(N, n, rg):
    cum = np.concatenate([[0], np.cumsum([len(w) for w in hw])])
    out = []
    tries = 0
    while len(out) < n and tries < 200 * n:
        tries += 1
        s = int(rg.integers(0, len(hw) - 1))
        e = np.searchsorted(cum, cum[s] + N)
        if e < len(cum) and cum[e] == cum[s] + N:
            out.append("".join(hw[s:e]))
    return out

def to_str(arr): return "".join(chr(65 + int(x)) for x in arr)

msg = {}
for N in (13, 32):
    pool = voi.all_passages(N)
    idx = rng.choice(len(pool), 4000, replace=False)
    ps = [-b2(lm.score_text(to_str(pool[i]))) for i in idx]
    ho = [-b2(lm.score_text(w)) for w in holdout_windows(N, 3000, rng)]
    msg[N] = dict(pool=float(np.mean(ps)), pool_sd=float(np.std(ps)), hold=float(np.mean(ho)), hold_sd=float(np.std(ho)), n_hold=len(ho))
    print(f"N={N}: pool passages (n=4000, includes LM training text) mean {msg[N]['pool']:.1f} bits (sd {msg[N]['pool_sd']:.1f}) = {msg[N]['pool']/N:.2f}/letter")
    print(f"      held-out passages (n={len(ho)}, not in LM) mean {msg[N]['hold']:.1f} bits (sd {msg[N]['hold_sd']:.1f}) = {msg[N]['hold']/N:.2f}/letter")
LIT_LO, LIT_HI = 1.0, 1.5
print(f"literature range for long English: {LIT_LO}-{LIT_HI} bits/letter -> 13 letters {13*LIT_LO:.1f}-{13*LIT_HI:.1f}; 32 letters {32*LIT_LO:.1f}-{32*LIT_HI:.1f} bits")

# ---------- 2. constraint bits ----------
hdr("2. Constraint bits (share of whole-word English passages that fit the repeat pattern)")
P32 = voi.all_passages(32); P13 = voi.all_passages(13)
print("pool sizes: L=32", len(P32), " L=13", len(P13))
k32 = int(voi.fit_mask(P32, voi.structure(z32, "homophonic")).sum())
c32 = -math.log2(k32 / len(P32))
lo, hi = voi.wilson(k32, len(P32))
print(f"Z32 homophonic: {k32}/{len(P32)} fit = 1 in {len(P32)/k32:.0f}; constraint {c32:.2f} bits (Wilson 95%: {-math.log2(hi):.2f}-{-math.log2(lo):.2f})")
ks13 = int(voi.fit_mask(P13, voi.structure(z13, "simple")).sum())
kh13 = int(voi.fit_mask(P13, voi.structure(z13, "homophonic")).sum())
print(f"Z13 simple: {ks13}/{len(P13)} fit; rule of three: rate < {3/len(P13):.2e}, constraint > {math.log2(len(P13)/3):.2f} bits")
print(f"Z13 homophonic: {kh13}/{len(P13)} fit", end="")
if kh13 > 0:
    lo, hi = voi.wilson(kh13, len(P13))
    c13h = -math.log2(kh13 / len(P13))
    print(f"; constraint {c13h:.2f} bits (Wilson 95%: {-math.log2(hi):.2f}-{-math.log2(lo):.2f})")
else:
    c13h = None
    print(f"; rule of three: constraint > {math.log2(len(P13)/3):.2f} bits")
eq13, ne13, _ = voi.structure(z13, "simple")
print(f"Z13 repeat pairs (eq): {len(eq13)}; distinct-symbol pairs (neq, simple model): {len(ne13)}")
c13_lb = math.log2(len(P13) / 3)

# ---------- 3. gap ----------
hdr("3. Gap = message bits - constraint bits")
for name, N, con, con_note in (("Z32", 32, c32, "measured"), ("Z13 simple", 13, c13_lb, "lower bound")):
    lo_m = N * LIT_LO; hi_m = msg[N]['hold']
    print(f"{name}: message {lo_m:.1f} (literature 1.0/letter) to {hi_m:.1f} (5-gram, held-out cold start); constraint {con:.1f} ({con_note}) -> gap {lo_m-con:.1f} to {hi_m-con:.1f}")
    print(f"      with message at 1.5/letter: {N*LIT_HI:.1f} -> gap {N*LIT_HI-con:.1f}")
print("(For Z13 the constraint is only a lower bound, so these gaps are upper bounds; a gap cannot be below 0.)")

# ---------- 4. unicity-style estimate ----------
hdr("4. Extra ciphertext under the same key (homophonic test ciphers from held-out English)")
FREQ = np.array([8.2,1.5,2.8,4.3,12.7,2.2,2.0,6.1,7.0,0.15,0.77,4.0,2.4,6.7,7.5,1.9,0.095,6.0,6.3,9.1,2.8,0.98,2.4,0.15,2.0,0.074]); FREQ /= FREQ.sum()
GAMMA = 0.645  # pooled allocation exponent from research/B1/HABITS.md Q1

def key_sizes(c): return np.maximum(1, np.round(c * FREQ ** GAMMA)).astype(int)

def make_cipher(word_window, nsym, rg):
    # each plaintext letter occurrence picks one of that letter's homophones uniformly
    ids = []
    for ch in word_window:
        l = ord(ch) - 65
        ids.append((l, int(rg.integers(0, nsym[l]))))
    return ids

def eq_pairs(ids):
    first, eq = {}, []
    for i, s in enumerate(ids):
        if s in first: eq.append((first[s], i))
        else: first[s] = i
    return eq

def fits_count(P, eq):
    idx = np.arange(len(P))
    for a, b in eq:
        idx = idx[P[idx, a] == P[idx, b]]
        if len(idx) == 0: break
    return len(idx)

def repeats(N, nsym, n, rg):
    ws = holdout_windows(N, n, rg)
    return np.array([len(eq_pairs(make_cipher(w, nsym, rg))) for w in ws])

# Calibrate key size c so that a 32-letter message has TARGET repeated positions on average
def calibrate(target, seedoff):
    best = None
    for c in np.geomspace(0.3, 80, 45):
        rg = np.random.default_rng(SEED + seedoff)
        r = repeats(32, key_sizes(c), 300, rg).mean()
        if best is None or abs(r - target) < abs(best[1] - target): best = (c, r)
    return best

scen = {}
for tgt in (2, 3, 4):
    c, r = calibrate(tgt, 1)
    scen[tgt] = c
    print(f"target repeated positions at 32 letters = {tgt}: key scale c={c:.2f}, total homophones K={key_sizes(c).sum()}, simulated mean repeats {r:.2f}")
print(f"(Z32 itself: {32 - len(set(z32))} repeated positions, {len(set(z32))} distinct symbols)")

# measured constraint bits vs length, scenario target 3
nsym3 = key_sizes(scen[3])
rows = []  # (N, r, fits_excess, M)
print("\nMeasured: random whole-word English passages vs test-cipher repeat pattern (self-match removed)")
print(" N   pool  ciphers  mean_repeats  total_fits  pooled_bits (pooled rate; dominated by low-repeat ciphers, use the per-r table below)")
ST = {}
for N in (32, 48, 64, 96):
    P = voi.all_passages(N)
    ws = holdout_windows(N, 120, np.random.default_rng(SEED + 2 + N))
    rg = np.random.default_rng(SEED + 3 + N)
    tf = 0; rs = []
    for w in ws:
        e = eq_pairs(make_cipher(w, nsym3, rg))
        f = max(0, fits_count(P, e) - 1)  # remove the true passage itself (it is in the pool)
        rows.append((N, len(e), f, len(P))); tf += f; rs.append(len(e))
    M = len(P) * len(ws)
    bits = -math.log2(tf / M) if tf > 0 else None
    bnd = math.log2(M / 3)
    ST[N] = (len(P), len(ws), float(np.mean(rs)), tf, bits, bnd)
    print(f"{N:3d} {len(P):7d} {len(ws):6d}   {np.mean(rs):6.2f}     {tf:8d}   " + (f"{bits:.2f}" if bits is not None else f">{bnd:.1f} (rule of 3)"))

# bits per repeat: pooled by r (uncensored groups), regression
byr = {}
for N, r, f, M in rows:
    g = byr.setdefault(r, [0, 0, 0]); g[0] += 1; g[1] += f; g[2] += M
print("\nPooled by number of repeated positions r (all lengths): r, ciphers, fits, bits")
xs, ys, ws_ = [], [], []
for r in sorted(byr):
    n, f, M = byr[r]
    if f >= 20:
        print(f"  r={r}: n={n} fits={f} bits={-math.log2(f/M):.2f}"); xs.append(r); ys.append(-math.log2(f / M)); ws_.append(n)
    else:
        print(f"  r={r}: n={n} fits={f} bits>= {math.log2(M/max(f,1)) if f else math.log2(M/3):.1f} (censored, not used in regression)")
A = np.polyfit(xs, ys, 1, w=np.sqrt(ws_))
print(f"linear fit over uncensored groups: bits = {A[0]:.2f} * r + {A[1]:.2f}  (about {A[0]:.1f} bits per repeated position)")
a_, b_ = float(A[1]), float(A[0])

def projected(nsym, Ns, h):
    out = {}
    for N in Ns:
        r = repeats(N, nsym, 150, np.random.default_rng(SEED + 9 + N))
        out[N] = (float(r.mean()), float(np.mean(a_ + b_ * r)))
    return out

Ns = [32, 40, 48, 64, 80, 96, 128, 160, 200, 256, 320, 400, 512]
print("\nProjected (ESTIMATE: constraint = fit line applied to simulated repeats; message = N * h)")
H_LM = ce
print(f"h values: literature 1.0, literature 1.5, 5-gram steady state {H_LM:.2f} bits/letter")
res = {}
for tgt in (2, 3, 4):
    nsym = key_sizes(scen[tgt])
    pr = projected(nsym, Ns, None)
    res[tgt] = pr
    if tgt == 3:
        print(" N  mean_repeats  constraint_bits | message bits at h=1.0 / 1.5 / LM")
        for N in Ns:
            r, cb = pr[N]
            print(f"{N:4d}  {r:7.1f}  {cb:9.1f} | {N*1.0:6.0f} {N*1.5:6.0f} {N*H_LM:6.0f}")
    row = []
    for h in (1.0, 1.5, H_LM):
        close = None
        # interpolate between grid points: first N where N*h <= constraint(N)
        prev = None
        for N in Ns:
            r, cb = pr[N]
            if N * h <= cb:
                if prev is None: close = N
                else:
                    N0, g0 = prev; g1 = N * h - cb
                    close = N0 + (N - N0) * g0 / (g0 - g1)
                break
            prev = (N, N * h - cb)
        row.append(close)
    print(f"scenario repeats@32={tgt}: unicity length (gap<=0) at h=1.0: {row[0] and round(row[0])}, h=1.5: {row[1] and round(row[1])}, h=LM: {row[2] and round(row[2])}  -> extra symbols {[None if x is None else round(x-32) for x in row]}")

# Z13 homophonic estimate (if no direct measure) and simple inequality term
hdr("5. Z13 estimates")
est_h = a_ + b_ * len(eq13)
print(f"Z13 homophonic ESTIMATE from fit line at r={len(eq13)}: {est_h:.1f} bits (direct count: {kh13} fits)")
reps = [i for i in range(len(z13)) if z13[i] not in z13[:i]]
dist = voi.fit_mask(P13, ([], [(a, b) for k, a in enumerate(reps) for b in reps[k+1:]], []))
print(f"Z13 inequality term alone (all {len(reps)} symbols distinct letters): {dist.sum()}/{len(P13)} -> {-math.log2(dist.mean()):.2f} bits (ESTIMATE of the simple-over-homophonic extra, assumes independence)")
print(f"Z13 simple ESTIMATE = {est_h + -math.log2(dist.mean()):.1f} bits (bound from zero fits: > {c13_lb:.1f})")
print(f"Z13 message {msg[13]['hold']:.1f} bits (held-out 5-gram), {13*LIT_LO:.0f}-{13*LIT_HI:.1f} (literature)")
# Z13 gap with the estimate
con13 = est_h + -math.log2(dist.mean())
print(f"Z13 gap with estimate: {13*LIT_LO-con13:.1f} to {msg[13]['hold']-con13:.1f}; with bound {13*LIT_LO-c13_lb:.1f} to {msg[13]['hold']-c13_lb:.1f}")

# ---------- 6. crib list capacity ----------
hdr("6. Crib-list capacity = constraint bits - log2(list size); expected chance fits = size * rate")
lists = [("Z32 letters passages", 1031, "z32", c32), ("Z32 radians/inches", 165, "z32", c32),
         ("Z13 letters passages", 992, "z13", c13_lb), ("Z13 suspects", 387, "z13", c13_lb), ("Z13 Mikado/persona", 128, "z13", c13_lb)]
for nm, sz, z, c in lists:
    print(f"{nm}: size {sz}: capacity {'>' if z=='z13' else ''}{c - math.log2(sz):.2f} bits; chance fits expected {'<' if z=='z13' else ''}{sz*2**-c:.4f}")
for sz in (10, 100, 1000, 10000):
    print(f"generic list of {sz}: Z32 capacity {c32-math.log2(sz):.2f} bits; Z13 (simple) > {c13_lb-math.log2(sz):.2f} bits")
print(f"largest list a fit can mean something for (capacity>=0): Z32 {2**c32:.0f}; Z13 simple > {2**c13_lb:.0f}")
hdr("7. Misc")
print(f"map channel: log2(91/57) = {math.log2(91/57):.2f} bits (FINDINGS 2026-11-23)")
print(f"Z32 triangle distinct vs merged: 157 -> 13 hits (B3): {math.log2(157/13):.2f} bits")
