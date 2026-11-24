"""I1c phase 2, exactly as pre-registered (fork commit 59d9924; metrics sealed 0591b39).
Usage:
  python scripts/z13_circles/run_i1c.py bench   --p171 .. --p176 .. --p180 .. --p196 .. [--out DIR]
  python scripts/z13_circles/run_i1c.py circles --p210 P09_p210.png --p041 P09_p041.png [--out DIR]
Pages are FBI Vault Part 09 (150 ppi renders for 171/176/180/196; native-resolution extractions for 210 and 41), see
results/z13_circles/IMAGES.md. `circles` reads tournament.json from --out (default results/z13_circles/i1c).
bench   : build ringed SAME/LOOK pairs + grouped split, all metrics on benchmark pairs, writes tournament.json.
circles : (only after tournament.json exists) apply the winner alone to Z13 circles, writes results.json, RESULTS.md.
Choices: ringed symbols = codes 5 6 1 2 3 4 ( ) z pooled; SAME = <=10 random pairs per symbol per cipher,
LOOK = <=10 random pairs per unordered symbol pair per cipher; rng seed 20261124 (fresh). Cells from I1b's
segmentation (same pages/rois/smudge exclusion). Split: symbols shuffled (seed), 2/3 train; pairs with both
symbols in one split belong to it, mixed pairs are dropped."""
import argparse, hashlib, itertools, json, os, sys
import common
from common import HERE, CIPHER_DIR, RESULTS
import numpy as np
from PIL import Image
import measure, grid_seg as seg, metrics as M

PAGE_PATHS = {}       # filled from the command line: 'P09-176' -> png path
OUT = os.path.join(RESULTS, "i1c")
CROPS = {"p210": os.path.join(RESULTS, "p210", "crops.json"), "p41": os.path.join(RESULTS, "p041", "crops.json")}

SEED = 20261124
RINGED = "561234()z"
ALLFAM = {"triangle": "987", "square": "#_%@*", "circle": "561234", "crossed_circle": "()z", "serifI": "I!|:;"}
PAGES = [("P09-176", "z408", 0, (330, 185, 930, 470), 8), ("P09-180", "z408", 1, (350, 240, 950, 540), 8),
         ("P09-171", "z408", 2, (370, 205, 960, 490), 8), ("P09-196", "z340", 0, (150, 430, 1075, 1480), 20)]
NAMES = ["M1", "M2", "M3", "M4", "M5", "M6", "M7"]
sha = lambda p: hashlib.sha256(open(p, "rb").read()).hexdigest()


def smudged(page, box):
    return page == "P09-180" and box[2] >= 900 and 270 <= box[1] <= 480


def get_cells():
    cells, excluded = [], []
    imgs = {}
    for page, cip, part, roi, nr in PAGES:
        tr = json.load(open(CIPHER_DIR + cip + ".json"))["rows"]
        rows = tr[part * 8: part * 8 + 8] if cip == "z408" else tr
        g = Image.open(PAGE_PATHS[page]).convert("L"); imgs[page] = g
        grid, _ = seg.segment(measure.mask_from_gray(np.asarray(g)), roi, nr, 17)
        if sum(c is not None for r in grid for c in r) != nr * 17:
            excluded.append(page); continue
        for r in range(nr):
            for c in range(17):
                if smudged(page, grid[r][c]): continue
                cells.append({"id": f"{page}:{r}:{c}", "cipher": cip, "code": rows[r][c], "box": grid[r][c], "page": page})
    return cells, imgs, excluded


def build_pairs(cells, syms):
    rng = np.random.default_rng(SEED); pairs = []
    for cip in ("z408", "z340"):
        by = {s: [c for c in cells if c["cipher"] == cip and c["code"] == s] for s in sorted(syms)}
        for s in sorted(syms):
            allp = list(itertools.combinations(range(len(by[s])), 2))
            for k in rng.permutation(len(allp))[:10]:
                a, b = allp[k]; pairs.append(("SAME", s, s, by[s][a], by[s][b]))
        for s, t in itertools.combinations(sorted(syms), 2):
            allp = [(i, j) for i in range(len(by[s])) for j in range(len(by[t]))]
            for k in rng.permutation(len(allp))[:10]:
                i, j = allp[k]; pairs.append(("LOOK", s, t, by[s][i], by[t][j]))
    return pairs


def stage_bench():
    common.check_sealed("measure.py", "metrics.py")
    cells, imgs, excluded = get_cells()
    used = "ringed"
    pairs = build_pairs(cells, RINGED)
    ns = sum(p[0] == "SAME" for p in pairs); nl = sum(p[0] == "LOOK" for p in pairs)
    if ns < 40 or nl < 40:
        used = "all"; pairs = build_pairs(cells, "".join(ALLFAM.values()))
        ns = sum(p[0] == "SAME" for p in pairs); nl = sum(p[0] == "LOOK" for p in pairs)
    syms = sorted({p[1] for p in pairs} | {p[2] for p in pairs})
    rng = np.random.default_rng(SEED); perm = [syms[i] for i in rng.permutation(len(syms))]
    ntr = int(round(len(syms) * 2 / 3)); train_s = set(perm[:ntr]); test_s = set(perm[ntr:])
    mk = lambda c: measure.crop_mask(imgs[c["page"]], c["box"])
    recs, fails = [], []
    for kind, s, t, a, b in pairs:
        split = "train" if s in train_s and t in train_s else "test" if s in test_s and t in test_s else None
        if split is None: continue
        try:
            ma, mb = mk(a), mk(b); M.features(ma); M.features(mb)
        except Exception as e:
            fails.append({"a": a["id"], "b": b["id"], "err": str(e)}); continue
        recs.append({"kind": kind, "split": split, "sa": s, "sb": t, "a": a, "b": b, "ma": ma, "mb": mb})
    tr_cells = {}
    for r in recs:
        if r["split"] == "train":
            for k in ("a", "b"): tr_cells[r[k]["id"]] = r["m" + k]
    F = [M.features(m) for m in tr_cells.values()]
    tsd = np.std([f["topology"] for f in F], axis=0, ddof=1); tsd = np.where(tsd < 1e-9, 1.0, tsd)
    muZ, sdZ = M.zstats([f["zernike"] for f in F]); muR, sdR = M.zstats([f["ring"] for f in F])
    fn = [lambda a, b: M.m1_whole(a, b), M.m2_interior, lambda a, b: M.m4_topology(a, b, tsd)]  # placeholder order fixed below
    fns = [M.m1_whole, M.m2_interior, M.m3_angular, lambda a, b: M.m4_topology(a, b, tsd),
           lambda a, b: M.m5_zernike(a, b, muZ, sdZ), lambda a, b: M.m6_ring(a, b, muR, sdR)]
    D = np.array([[f(r["ma"], r["mb"]) for f in fns] for r in recs])
    y = np.array([r["kind"] == "LOOK" for r in recs]); sp = np.array([r["split"] for r in recs])
    tr = sp == "train"
    model = M.fit_m7(D[tr], y[tr].astype(float))
    S = np.column_stack([D, M.m7_score(model, D)])
    auc = {}
    for j, n in enumerate(NAMES):
        auc[n] = [M.auc(S[tr & y, j], S[tr & ~y, j]), M.auc(S[~tr & y, j], S[~tr & ~y, j])]
    winner = max(NAMES, key=lambda n: (auc[n][0], -NAMES.index(n)))
    out = {"code_sha256": sha(os.path.join(HERE, "metrics.py")), "benchmark": used, "excluded_pages": excluded,
           "n_cells": len(cells), "n_same_all": ns, "n_look_all": nl, "pair_failures": fails,
           "symbols_train": sorted(train_s), "symbols_test": sorted(test_s),
           "n_train": {"same": int((tr & ~y).sum()), "look": int((tr & y).sum())},
           "n_test": {"same": int((~tr & ~y).sum()), "look": int((~tr & y).sum())},
           "auc_train_test": auc, "winner": winner, "winner_train_auc": auc[winner][0], "winner_test_auc": auc[winner][1],
           "topology_scales": tsd.tolist(), "zernike_mu": muZ.tolist(), "zernike_sd": sdZ.tolist(),
           "ring_mu": muR.tolist(), "ring_sd": sdR.tolist(),
           "m7": {k: (v.tolist() if hasattr(v, "tolist") else v) for k, v in model.items()},
           "pairs": [{"kind": r["kind"], "split": r["split"], "sym_a": r["sa"], "sym_b": r["sb"], "id_a": r["a"]["id"],
                      "id_b": r["b"]["id"], "scores": dict(zip(NAMES, map(float, S[i])))} for i, r in enumerate(recs)]}
    json.dump(out, open(os.path.join(OUT, "tournament.json"), "w"), indent=1)
    print({k: v for k, v in out.items() if k not in ("pairs", "m7", "zernike_mu", "zernike_sd")})


def stage_circles():
    T = json.load(open(os.path.join(OUT, "tournament.json")))
    w = T["winner"]; j = NAMES.index(w)
    te = [p for p in T["pairs"] if p["split"] == "test"]
    same = np.array([p["scores"][w] for p in te if p["kind"] == "SAME"]); look = np.array([p["scores"][w] for p in te if p["kind"] == "LOOK"])
    tsd = np.array(T["topology_scales"]); muZ, sdZ = np.array(T["zernike_mu"]), np.array(T["zernike_sd"])
    muR, sdR = np.array(T["ring_mu"]), np.array(T["ring_sd"])
    model = {k: (np.array(v) if isinstance(v, list) else v) for k, v in T["m7"].items()}
    fns = [M.m1_whole, M.m2_interior, M.m3_angular, lambda a, b: M.m4_topology(a, b, tsd),
           lambda a, b: M.m5_zernike(a, b, muZ, sdZ), lambda a, b: M.m6_ring(a, b, muR, sdR)]
    def score(a, b):
        if w == "M7": return float(M.m7_score(model, np.array([f(a, b) for f in fns])))
        return float(fns[j](a, b))
    res = {"winner": w, "test_auc": T["winner_test_auc"], "n_test_same": len(same), "n_test_look": len(look), "images": {}}
    for tag, img in (("p210", PAGE_PATHS["P09-210"]), ("p41", PAGE_PATHS["P09-041"])):
        spec = json.load(open(CROPS[tag]))
        g = Image.open(img).convert("L")
        circ = {int(c["position"]): measure.crop_mask(g, c["box"]) for c in spec["crops"] if c["role"] == "circle"}
        d = {f"{a}-{b}": score(circ[a], circ[b]) for a, b in ((5, 7), (5, 9), (7, 9))}
        l = {k: float(measure.log10_lr(v, same, look)) for k, v in d.items()}
        q = float((look <= max(d.values())).mean()); s = sum(l.values())
        res["images"][tag] = {"D": d, "log10_lr": l, "sum_log10_lr": s, "q": q}
    ta = T["winner_test_auc"]; p = res["images"]["p210"]
    def verdict(im):
        if ta >= 0.80 and im["q"] <= 0.10:
            return "one symbol" if im["sum_log10_lr"] <= -1 else "three different symbols" if im["sum_log10_lr"] >= 1 else "unresolved"
        if ta < 0.65: return "unresolved at this resolution"
        return "weak (LR %.2f, partly separates)" % im["sum_log10_lr"]
    for im in res["images"].values(): im["verdict"] = verdict(im)
    res["verdict"] = res["images"]["p210"]["verdict"]
    json.dump(res, open(os.path.join(OUT, "results.json"), "w"), indent=1)
    print(json.dumps(res, indent=1))


def parse(argv=None, need=None):
    """Parse the command line and fill PAGE_PATHS/OUT. need: 'bench' or 'circles'."""
    global OUT
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    if need is None:
        ap.add_argument("stage", choices=["bench", "circles"])
        need = sys.argv[1] if len(sys.argv) > 1 else "bench"
    if need == "bench":
        common.add_page_args(ap)
    else:
        ap.add_argument("--p210", required=True); ap.add_argument("--p041", required=True)
    ap.add_argument("--out", default=OUT)
    args = ap.parse_args(argv)
    OUT = args.out; os.makedirs(OUT, exist_ok=True)
    PAGE_PATHS.update(common.page_map(args) if need == "bench" else {"P09-210": args.p210, "P09-041": args.p041})
    return args


if __name__ == "__main__":
    a = parse()
    {"bench": stage_bench, "circles": stage_circles}[a.stage]()
