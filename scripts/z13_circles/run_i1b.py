"""I1b: look-alike power check, exactly as pre-registered (fork commit b50fae8). Reproduces results/z13_circles/i1b/results.json.
Run (about 2 min):
  python scripts/z13_circles/run_i1b.py --p171 P09-171.png --p176 P09-176.png --p180 P09-180.png --p196 P09-196.png [--out DIR]
The four pages are FBI Vault Part 09 pp. 171, 176, 180, 196 rendered at 150 ppi (see results/z13_circles/IMAGES.md).
"""
import argparse, sys, json, itertools, hashlib, os
import common
from common import HERE, CIPHER_DIR, RESULTS
import numpy as np
from PIL import Image
import measure, grid_seg as seg

SEED = 20261124
FAM = {"triangle": "987", "square": "#_%@*", "circle": "561234", "crossed_circle": "()z", "serifI": "I!|:;"}
# page, cipher, part index (rows of the transcription), roi (generous box around the grid), n rows
PAGES = [
    ("P09-176", "z408", 0, (330, 185, 930, 470), 8),   # part 1, Times-Herald
    ("P09-180", "z408", 1, (350, 240, 950, 540), 8),   # part 2 (Examiner); first row cZKq.. matches
    ("P09-171", "z408", 2, (370, 205, 960, 490), 8),   # part 3 (Chronicle); first row Nk)S.. matches
    ("P09-196", "z340", 0, (150, 430, 1075, 1480), 20),
]
# cells covered by a thumbprint on P09-180 (excluded before any D was computed): right edge x>=900, y in [270,480]
def smudged(page, box):
    return page == "P09-180" and box[2] >= 900 and 270 <= box[1] <= 480


def sha(p): return hashlib.sha256(open(p, "rb").read()).hexdigest()

def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    common.add_page_args(ap)
    ap.add_argument("--out", default=os.path.join(RESULTS, "i1b"), help="directory for results.json")
    args = ap.parse_args()
    PG = common.page_map(args)
    common.check_sealed("measure.py")
    cells, excluded, parts = [], [], []
    for page, cip, part, roi, nr in PAGES:
        tr = json.load(open(CIPHER_DIR + cip + ".json"))["rows"]
        rows = tr[part * 8: part * 8 + 8] if cip == "z408" else tr
        assert len(rows) == nr and all(len(r) == 17 for r in rows)
        g = Image.open(PG[page]).convert("L")
        m = measure.mask_from_gray(np.asarray(g))
        grid, ext = seg.segment(m, roi, nr, 17)
        n_found = sum(c is not None for r in grid for c in r)
        ok = n_found == nr * 17
        if not ok:
            excluded.append({"page": page, "reason": f"{n_found} cells found, expected {nr*17}"}); continue
        parts.append({"page": page, "cipher": cip, "rows": nr, "cols": 17, "cells": n_found})
        for r in range(nr):
            for c in range(17):
                code = rows[r][c]; box = grid[r][c]
                if smudged(page, box):
                    excluded.append({"page": page, "row": r, "col": c, "reason": "thumbprint smudge"}); continue
                cells.append({"id": f"{page}:{r}:{c}", "cipher": cip, "code": code, "box": box, "page": page})
    fam_of = {s: f for f, ss in FAM.items() for s in ss}
    imgs = {}
    def mask(cell):
        if cell["page"] not in imgs: imgs[cell["page"]] = Image.open(PG[cell["page"]]).convert("L")
        m = measure.crop_mask(imgs[cell["page"]], cell["box"])
        return m
    rng = np.random.default_rng(SEED)
    pairs = []
    for cip in ("z408", "z340"):
        for fam, syms in FAM.items():
            by = {s: [c for c in cells if c["cipher"] == cip and c["code"] == s] for s in sorted(syms)}
            for s in sorted(syms):
                inst = by[s]
                allp = list(itertools.combinations(range(len(inst)), 2))
                if not allp: continue
                pick = rng.permutation(len(allp))[:10]
                for k in pick:
                    a, b = allp[k]; pairs.append(("SAME", cip, fam, s, s, inst[a], inst[b]))
            for s, t in itertools.combinations(sorted(syms), 2):
                if not by[s] or not by[t]: continue
                allp = [(i, j) for i in range(len(by[s])) for j in range(len(by[t]))]
                pick = rng.permutation(len(allp))[:10]
                for k in pick:
                    i, j = allp[k]; pairs.append(("LOOK", cip, fam, s, t, by[s][i], by[t][j]))
    out = []
    for kind, cip, fam, s, t, a, b in pairs:
        d = measure.shape_distance(mask(a), mask(b))
        out.append({"kind": kind, "cipher": cip, "family": fam, "sym_a": s, "sym_b": t, "id_a": a["id"], "id_b": b["id"], "D": d})
    same = np.array([o["D"] for o in out if o["kind"] == "SAME"]); look = np.array([o["D"] for o in out if o["kind"] == "LOOK"])
    # AUC = P(D_LOOK > D_SAME), ties count 1/2
    gt = (look[:, None] > same[None, :]).mean(); eq = (look[:, None] == same[None, :]).mean(); auc = float(gt + 0.5 * eq)
    q39 = float((look <= 0.39).mean()); q31 = float((look <= 0.31).mean())
    r1 = json.load(open(os.path.join(RESULTS, "p210", "results.json"))); r41 = json.load(open(os.path.join(RESULTS, "p041", "results.json")))
    same_ref = np.concatenate([[p["D"] for p in r1["same_pairs"]], same])
    def lr(res): 
        ds = [v["D"] for v in res["circle_pairs"].values()]
        l = [float(measure.log10_lr(d, same_ref, look)) for d in ds]
        return ds, l, float(sum(l))
    ds210, l210, s210 = lr(r1); ds41, l41, s41 = lr(r41)
    if auc >= 0.80 and q39 <= 0.10:
        verdict = "metric separates look-alikes: " + ("one symbol" if s210 <= -1 else "three different symbols" if s210 >= 1 else "unresolved")
    elif auc < 0.65:
        verdict = "metric cannot separate: circles verdict becomes 'unresolved at this resolution'"
    else:
        verdict = "weak: realistic LR reported, metric only partly separates look-alikes"
    res = {"measure_sha256": sha(os.path.join(HERE, "measure.py")), "seed": SEED, "parts_used": parts, "excluded": excluded,
           "n_cells_used": len(cells), "n_same": int(len(same)), "n_look": int(len(look)),
           "same_D": {"mean": float(same.mean()), "median": float(np.median(same))}, "look_D": {"mean": float(look.mean()), "median": float(np.median(look))},
           "auc": auc, "q_039": q39, "q_031": q31,
           "per_family": {f: {"n_same": int(sum(1 for o in out if o["kind"]=="SAME" and o["family"]==f)), "n_look": int(sum(1 for o in out if o["kind"]=="LOOK" and o["family"]==f)),
                              "mean_same": float(np.mean([o["D"] for o in out if o["kind"]=="SAME" and o["family"]==f] or [np.nan])), "mean_look": float(np.mean([o["D"] for o in out if o["kind"]=="LOOK" and o["family"]==f] or [np.nan]))} for f in FAM},
           "realistic_p210": {"circle_D": ds210, "log10_lr": l210, "sum": s210}, "realistic_p041": {"circle_D": ds41, "log10_lr": l41, "sum": s41},
           "realistic_log10_lr_sum": s210, "verdict": verdict, "pairs": out}
    os.makedirs(args.out, exist_ok=True)
    json.dump(res, open(os.path.join(args.out, "results.json"), "w"), indent=1)
    print({k: v for k, v in res.items() if k not in ("pairs",)})

if __name__ == "__main__":
    main()
