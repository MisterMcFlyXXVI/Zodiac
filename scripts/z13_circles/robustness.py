"""EXPLORATORY robustness checks for I1c (cannot change the pre-registered verdict). Writes robustness.json.
Reuses run_i1c.py's cells/pairs (same pair list, all pairs incl. those later dropped by a split).
Usage: python scripts/z13_circles/robustness.py --p171 .. --p176 .. --p180 .. --p196 .. --p210 .. --p041 .. [--out DIR]
(--out defaults to results/z13_circles/i1c)."""
import json, os, sys
import common
import numpy as np
from PIL import Image
import measure, metrics as M, run_i1c as R

import argparse
_ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
common.add_page_args(_ap)
_ap.add_argument("--p210", required=True); _ap.add_argument("--p041", required=True)
_ap.add_argument("--out", default=R.OUT)
_args = _ap.parse_args()
R.PAGE_PATHS.update(common.page_map(_args)); R.PAGE_PATHS.update({"P09-210": _args.p210, "P09-041": _args.p041})
OUT = _args.out; os.makedirs(OUT, exist_ok=True)

NAMES = R.NAMES
cells, imgs, _ = R.get_cells()
pairs = R.build_pairs(cells, R.RINGED)
mk = lambda c: measure.crop_mask(imgs[c["page"]], c["box"])
masks = {}
def mask(c):
    if c["id"] not in masks: masks[c["id"]] = mk(c)
    return masks[c["id"]]

def raw(ma, mb):
    fa, fb = M.features(ma), M.features(mb)
    return {"d1": M.m1_whole(ma, mb), "d2": M.m2_interior(ma, mb), "d3": M.m3_angular(ma, mb),
            "t": np.abs(fa["topology"] - fb["topology"]), "z": np.abs(fa["zernike"] - fb["zernike"]),
            "r": np.abs(fa["ring"] - fb["ring"])}

P = [dict(kind=k, sa=s, sb=t, a=a["id"], b=b["id"], **raw(mask(a), mask(b))) for k, s, t, a, b in pairs]
syms = sorted({p["sa"] for p in P} | {p["sb"] for p in P})
FAMILY = {s: ("c" if s in "561234" else "x") for s in syms}
circ = {}
for tag, img in (("p210", R.PAGE_PATHS["P09-210"]), ("p41", R.PAGE_PATHS["P09-041"])):
    spec = json.load(open(R.CROPS[tag]))
    g = Image.open(img).convert("L")
    cm = {int(c["position"]): measure.crop_mask(g, c["box"]) for c in spec["crops"] if c["role"] == "circle"}
    circ[tag] = [raw(cm[a], cm[b]) for a, b in ((5, 7), (5, 9), (7, 9))]
cell_feat = {cid: M.features(m) for cid, m in masks.items()}


def scores(items, train_ids):
    """Return (S matrix n x 7 for items, model-fitted-on-train pieces); train_ids = list of pair dicts for fitting."""
    F = [cell_feat[i] for i in {c for p in train_ids for c in (p["a"], p["b"])}]
    tsd = np.std([f["topology"] for f in F], axis=0, ddof=1); tsd = np.where(tsd < 1e-9, 1.0, tsd)
    _, sdZ = M.zstats([f["zernike"] for f in F]); _, sdR = M.zstats([f["ring"] for f in F])
    def D(p): return [p["d1"], p["d2"], p["d3"], float((p["t"] / tsd).sum()), float(np.linalg.norm(p["z"] / sdZ)), float(np.linalg.norm(p["r"] / sdR))]
    Dt = np.array([D(p) for p in train_ids]); yt = np.array([p["kind"] == "LOOK" for p in train_ids], float)
    model = M.fit_m7(Dt, yt)
    def S(its):
        d = np.array([D(p) for p in its]); return np.column_stack([d, M.m7_score(model, d)])
    return S

def verdict(ta, q, s):
    if ta >= 0.80 and q <= 0.10: return "one" if s <= -1 else "three" if s >= 1 else "unresolved"
    if ta < 0.65: return "unresolved"
    return "weak"

# (a) + (b)
out_a = []; wf = {"M1": [0, 0, {}], "M7": [0, 0, {}]}
wins = {f: {n: [0.0, 0] for n in ("M1", "M7")} for f in ("c", "x", "all")}
for seed in range(1, 51):
    rng = np.random.default_rng(seed); perm = [syms[i] for i in rng.permutation(len(syms))]
    tr_s, te_s = set(perm[:6]), set(perm[6:])
    tr = [p for p in P if p["sa"] in tr_s and p["sb"] in tr_s]; te = [p for p in P if p["sa"] in te_s and p["sb"] in te_s]
    ty = np.array([p["kind"] == "LOOK" for p in te])
    if ty.sum() < 2 or (~ty).sum() < 2: out_a.append({"seed": seed, "skipped": True}); continue
    S = scores(None, tr)
    Str, Ste = S(tr), S(te); ytr = np.array([p["kind"] == "LOOK" for p in tr])
    auc_tr = [M.auc(Str[ytr, j], Str[~ytr, j]) for j in range(7)]
    w = int(np.argmax(auc_tr)); auc_te = M.auc(Ste[ty, w], Ste[~ty, w])
    rec = {"seed": seed, "winner": NAMES[w], "test_auc": auc_te}
    for tag in circ:
        cs = S(circ[tag] if False else [dict(p, kind="LOOK") for p in circ[tag]])[:, w]
        same, look = Ste[~ty, w], Ste[ty, w]
        l = measure.log10_lr(cs, same, look); q = float((look <= cs.max()).mean())
        rec[tag] = {"lr": float(np.sum(l)), "q": q, "verdict": verdict(auc_te, q, float(np.sum(l)))}
    out_a.append(rec)
    # (b) within-family LOOK vs same-family SAME on this split's test pairs, M1 and M7
    for fam in ("c", "x"):
        lk = np.array([p["kind"] == "LOOK" and FAMILY[p["sa"]] == fam and FAMILY[p["sb"]] == fam for p in te])
        sm = np.array([p["kind"] == "SAME" and FAMILY[p["sa"]] == fam for p in te])
        for nm, j in (("M1", 0), ("M7", 6)):
            a, b = Ste[lk, j][:, None], Ste[sm, j][None, :]
            for key in (fam, "all"):
                wins[key][nm][0] += float((a > b).sum() + 0.5 * (a == b).sum()); wins[key][nm][1] += a.size * b.size

ok = [r for r in out_a if not r.get("skipped")]
pc = lambda v: {"median": float(np.median(v)), "p10": float(np.percentile(v, 10)), "p90": float(np.percentile(v, 90))}
freq = {n: sum(r["winner"] == n for r in ok) for n in NAMES if any(r["winner"] == n for r in ok)}
res = {"EXPLORATORY": True, "n_splits_used": len(ok), "n_skipped": 50 - len(ok), "winner_freq": freq,
       "winner_test_auc": pc([r["test_auc"] for r in ok]),
       "lr_p210": pc([r["p210"]["lr"] for r in ok]), "lr_p41": pc([r["p41"]["lr"] for r in ok]),
       "verdict_share": {t: {v: sum(r[t]["verdict"] == v for r in ok) / len(ok) for v in ("one", "unresolved", "weak", "three")} for t in ("p210", "p41")},
       "within_family_auc": {fam: {nm: (wins[fam][nm][0] / wins[fam][nm][1] if wins[fam][nm][1] else None) for nm in ("M1", "M7")} for fam in ("c", "x", "all")},
       "within_family_n_comparisons": {fam: wins[fam]["M1"][1] for fam in wins}, "splits": out_a}
# (c) LOSO
loso = {}
for s in syms:
    tr = [p for p in P if s not in (p["sa"], p["sb"])]; te = [p for p in P if s in (p["sa"], p["sb"])]
    ty = np.array([p["kind"] == "LOOK" for p in te]); S = scores(None, tr); Ste = S(te)
    loso[s] = {"auc_M7": M.auc(Ste[ty, 6], Ste[~ty, 6]) if ty.any() and (~ty).any() else None,
               "auc_M1": M.auc(Ste[ty, 0], Ste[~ty, 0]) if ty.any() and (~ty).any() else None,
               "n_same": int((~ty).sum()), "n_look": int(ty.sum())}
res["loso"] = loso
json.dump(res, open(os.path.join(OUT, "robustness.json"), "w"), indent=1)
print(json.dumps({k: v for k, v in res.items() if k != "splits"}, indent=1))
