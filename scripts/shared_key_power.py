#!/usr/bin/env python3
"""S1: power of a shared-key test for Z13 + Z32, on synthetic pairs only (never touches the real ciphers).

Question: if one key enciphered both a 13-symbol and a 32-symbol message (sharing 3-7 symbols), can a
solver-based test (zbot anneal, 5-gram LM) detect it? Delta = best joint score with the shared symbols
linked minus best score with no links; null = fake link sets; p = rank.

  python scripts/shared_key_power.py [--N 20] [--M 49] [--restarts 4] [--workers 10]   # ~40 min at N=40, M=99
  -> results/shared_key_power/results.json   (committed run: N=40, M=99, restarts=4)

Tests cover only the generator and link logic (tests/test_shared_key_power.py).
"""
import sys, json, time, random, argparse, pathlib
import numpy as np
from multiprocessing import Pool

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from zbot import anneal, lm  # noqa: E402

Z340 = ROOT / "data" / "ciphers" / "z340.json"
ALPHA = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
_cache = {}

def homophone_counts():
    if "hc" not in _cache:
        h = json.load(open(Z340))["key_homophones"]
        _cache["hc"] = {l: max(1, len(h.get(l, []))) for l in ALPHA}  # letters absent from Z340 get 1
    return _cache["hc"]

def words():
    if "w" not in _cache:
        _cache["w"] = lm.holdout_words("en")
    return _cache["w"]

def window(rng, n):
    """Word-aligned window of consecutive held-out words with exactly n letters."""
    w = words()
    for _ in range(100000):
        i = rng.randrange(len(w)); tot = 0; j = i
        while j < len(w) and tot < n:
            tot += len(w[j]); j += 1
        if tot == n:
            return "".join(w[i:j])
    raise RuntimeError("no window")

def make_key(rng):
    """Random assignment of symbol IDs 0..K-1 to letters, with Z340's homophone counts."""
    hc = homophone_counts(); K = sum(hc.values())
    ids = list(range(K)); rng.shuffle(ids)
    key, p = {}, 0
    for l in ALPHA:
        key[l] = ids[p:p + hc[l]]; p += hc[l]
    return key, K

def enc13(rng, text, key):
    pick = {l: rng.choice(h) for l, h in key.items()}   # one homophone per letter, no cycling
    return [pick[c] for c in text]

def enc32(rng, text, key):
    order = {}; off = {}
    for l, h in key.items():
        o = list(h); rng.shuffle(o); order[l] = o; off[l] = rng.randrange(len(o))
    cnt = {l: 0 for l in key}; out = []
    for c in text:
        o = order[c]; out.append(o[(off[c] + cnt[c]) % len(o)]); cnt[c] += 1
    return out

def relabel(c13, c32, shared):
    """Compact IDs: 13-cipher symbols 0..n13-1, 32-cipher symbols n13..; shared IDs get a link pair."""
    m13 = {}; 
    for s in c13: m13.setdefault(s, len(m13))
    n13 = len(m13); m32 = {}
    for s in c32: m32.setdefault(s, n13 + len(m32))
    a = np.array([m13[s] for s in c13], dtype=np.int64)
    b = np.array([m32[s] for s in c32], dtype=np.int64)
    links = [(m13[s], m32[s]) for s in sorted(shared)]
    return a, b, n13, n13 + len(m32), links

def accept(c13, c32):
    d13, d32 = len(set(c13)), len(set(c32)); sh = set(c13) & set(c32)
    return 7 <= d13 <= 9 and d32 >= 26 and 3 <= len(sh) <= 7, sh

def gen_pair(seed, shared_key):
    """Returns dict(a,b,n13,n_tot,links,t13,t32,shared_key) and tries counts; rejects until accepted."""
    rng = random.Random(seed); tries = 0
    while True:
        tries += 1
        t13, t32 = window(rng, 13), window(rng, 32)
        k1, K = make_key(rng)
        k2 = k1 if shared_key else make_key(rng)[0]
        c13, c32 = enc13(rng, t13, k1), enc32(rng, t32, k2)
        ok, sh = accept(c13, c32)
        if ok:
            a, b, n13, ntot, links = relabel(c13, c32, sh)
            return dict(a=a, b=b, n13=n13, n_tot=ntot, links=links, t13=t13, t32=t32,
                        shared_key=shared_key, tries=tries, K=K)


# ---- power study ----

def best(segs, n_sym, restarts, seed):
    return anneal.solve(segs, n_sym, restarts=restarts, seed=seed)[0].score

def merge(a, b, n13, n_tot, links):
    """Merge links (13-sym, 32-sym): the 32-cipher symbol takes the 13-cipher ID; compact the rest."""
    remap = {y: x for x, y in links}
    old = [s for s in range(n13, n_tot) if s not in remap]
    for i, s in enumerate(old): remap[s] = n13 + i
    b2 = np.array([remap.get(s, s) for s in b], dtype=np.int64)
    return [a, b2], n13 + len(old)

def fake_links(rng, links, n13, n_tot):
    true32 = {y for _, y in links}
    cand = [s for s in range(n13, n_tot) if s not in true32]
    ch = rng.sample(cand, len(links))
    return [(x, y) for (x, _), y in zip(links, ch)]

def run_pair(args):
    seed, shared, M, restarts = args
    p = gen_pair(seed, shared)
    a, b, n13, n_tot, links = p["a"], p["b"], p["n13"], p["n_tot"], p["links"]
    sseed = 7  # identical solver seed for every solve
    s_sep = best([a, b], n_tot, restarts, sseed)
    segs, n = merge(a, b, n13, n_tot, links)
    d_obs = best(segs, n, restarts, sseed) - s_sep
    rng = random.Random(seed * 7919 + 1); d_fake = []
    for _ in range(M):
        segs, n = merge(a, b, n13, n_tot, fake_links(rng, links, n13, n_tot))
        d_fake.append(best(segs, n, restarts, sseed) - s_sep)
    pv = (1 + sum(d >= d_obs for d in d_fake)) / (1 + M)
    return dict(seed=seed, shared=shared, k=len(links), tries=p["tries"], d_obs=d_obs,
                fake_mean=float(np.mean(d_fake)), fake_max=float(np.max(d_fake)), p=pv)

def wilson(x, n, z=1.96):
    if n == 0: return [0, 0]
    ph = x / n; d = 1 + z * z / n; c = ph + z * z / (2 * n)
    r = z * ((ph * (1 - ph) / n + z * z / (4 * n * n)) ** .5)
    return [round((c - r) / d, 3), round((c + r) / d, 3)]

def timing(restarts):
    p = gen_pair(1000, True); a, b, n13, n_tot, links = p["a"], p["b"], p["n13"], p["n_tot"], p["links"]
    t = time.time(); sc = [best([a, b], n_tot, restarts, s) for s in (1, 2, 3)]; dt = (time.time() - t) / 3
    return dt, float(np.std(sc, ddof=1)), sc

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--N", type=int, default=20); ap.add_argument("--M", type=int, default=49)
    ap.add_argument("--restarts", type=int, default=4); ap.add_argument("--workers", type=int, default=10)
    ap.add_argument("--out", default=str(ROOT / "results" / "shared_key_power" / "results.json"))
    ap.add_argument("--time-only", action="store_true")
    A = ap.parse_args()
    words(); anneal.solve([np.array([0, 1, 2, 3, 4, 5])], 6, restarts=1, iters=100)  # warm jit
    dt, noise, sc = timing(A.restarts)
    print(f"sec/solve={dt:.2f} sep_noise={noise:.2f} nats {sc}", flush=True)
    if A.time_only: sys.exit()
    jobs = [(10000 + i, True, A.M, A.restarts) for i in range(A.N)] + \
           [(20000 + i, False, A.M, A.restarts) for i in range(A.N)]
    t0 = time.time()
    with Pool(A.workers) as pool: rows = pool.map(run_pair, jobs, chunksize=1)
    sh = [r for r in rows if r["shared"]]; ind = [r for r in rows if not r["shared"]]
    def rate(rs, th): x = sum(r["p"] < th for r in rs); return x / len(rs), wilson(x, len(rs))
    p05, c05 = rate(sh, .05); p01, c01 = rate(sh, .01); f05, cf = rate(ind, .05)
    acc = {"shared": A.N / sum(r["tries"] for r in sh), "independent": A.N / sum(r["tries"] for r in ind)}
    res = dict(power_005=p05, power_001=p01, fpr_005=f05, ci=dict(power_005=c05, power_001=c01, fpr_005=cf),
               N=A.N, M=A.M, restarts=A.restarts, sec_per_solve=dt, sep_noise_nats=noise,
               min_p_possible=1 / (1 + A.M), acceptance=acc, wall_sec=time.time() - t0, rows=rows)
    json.dump(res, open(A.out, "w"), indent=1, default=float)
    print({k: v for k, v in res.items() if k != "rows"})
