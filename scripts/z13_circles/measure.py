"""I1 glyph-shape measurement, implemented exactly as pre-registered in PLAN.md sections 2 and 3.

CLI:  python measure.py CROPS_JSON IMAGE      (writes results.json next to CROPS_JSON)

crops.json schema
-----------------
{
  "image_note": "free text, optional",
  "crops": [
    {"id": "c5", "symbol": "circle", "role": "circle", "position": 5, "box": [x0, y0, x1, y1]},
    {"id": "c7", "symbol": "circle", "role": "circle", "position": 7, "box": [...]},
    {"id": "c9", "symbol": "circle", "role": "circle", "position": 9, "box": [...]},
    {"id": "A1", "symbol": "A",      "role": "cipher",    "box": [...]},
    {"id": "X1", "symbol": "cross",  "role": "crosshair", "box": [...]},
    {"id": "h1", "symbol": "E",      "role": "hand",      "box": [...]}
  ]
}
box is (x0, y0, x1, y1) in native pixels of the primary image (x1, y1 exclusive).
role:
  circle    the three circled glyphs at Z13 positions 5, 7, 9 (field "position" required).
  cipher    other Z13 glyphs; "symbol" is the transcriber's identity label.
  crosshair the crosshair glyph (only used against the circles in set X).
  hand      handwritten capitals; "symbol" is the letter. Only the first two crops of each
            letter, in file order, are used (the plan's fixed rule).
Sets (all pairs are unordered, formed among crops of the stated roles):
  S (same symbol)      cipher+cipher same symbol (all pairs); hand+hand same letter (first two).
  X (different symbol) cipher+cipher different symbols; circle+crosshair.
Circle statistics: D57, D59, D79 (keys "5-7", "5-9", "7-9").
D is computed as shape_distance(first, second) with the pair ordered as listed in the file;
the max-IoU search transforms the second glyph only.
"""
import hashlib
import itertools
import json
import os
import sys

import numpy as np
from PIL import Image

CANVAS = 160
HEIGHT = 64
ANGLES = list(range(-15, 16))
SCALES = [0.85, 0.90, 0.95, 1.00, 1.05, 1.10, 1.15]
SEED = 20261124


# ---------------------------------------------------------------- loading

def otsu_threshold(gray):
    """Otsu threshold on a uint8 array; returns t so that ink = value <= t."""
    hist = np.bincount(gray.ravel(), minlength=256).astype(float)
    total = hist.sum()
    levels = np.arange(256)
    w0 = np.cumsum(hist)
    w1 = total - w0
    m = np.cumsum(hist * levels)
    mt = m[-1]
    with np.errstate(divide="ignore", invalid="ignore"):
        mu0 = m / w0
        mu1 = (mt - m) / w1
        between = w0 * w1 * (mu0 - mu1) ** 2
    between = np.nan_to_num(between)
    return int(np.argmax(between))


def mask_from_gray(gray):
    """Ink (darker) mask from a 2D uint8 array. Two-level images are used as is."""
    gray = np.asarray(gray, dtype=np.uint8)
    levels = np.unique(gray)
    if len(levels) < 2:
        return np.zeros(gray.shape, dtype=bool)
    if len(levels) == 2:
        return gray == levels[0]
    return gray <= otsu_threshold(gray)


def load_crop(image_path, box):
    """Crop box=(x0,y0,x1,y1) from a greyscale version of the image; return bool ink mask."""
    with Image.open(image_path) as im:
        return crop_mask(im.convert("L"), box)


def crop_mask(gray_image, box):
    x0, y0, x1, y1 = [int(v) for v in box]
    arr = np.asarray(gray_image.crop((x0, y0, x1, y1)))
    return mask_from_gray(arr)


# ---------------------------------------------------------------- normalisation

def _bbox(mask):
    ys, xs = np.nonzero(mask)
    if len(ys) == 0:
        raise ValueError("empty mask (no ink)")
    return ys.min(), ys.max() + 1, xs.min(), xs.max() + 1


def _recentre(mask, size):
    """Shift an (size,size) mask so its ink centroid lies on the canvas centre."""
    ys, xs = np.nonzero(mask)
    if len(ys) == 0:
        return mask
    dy = int(round((size - 1) / 2.0 - ys.mean()))
    dx = int(round((size - 1) / 2.0 - xs.mean()))
    out = np.zeros_like(mask)
    sy0, sy1 = max(0, -dy), min(size, size - dy)
    sx0, sx1 = max(0, -dx), min(size, size - dx)
    out[sy0 + dy:sy1 + dy, sx0 + dx:sx1 + dx] = mask[sy0:sy1, sx0:sx1]
    return out


def normalize(mask, height=HEIGHT, size=CANVAS):
    """Scale the ink bbox to `height` rows, pad to a size x size canvas, centre on the centroid."""
    mask = np.asarray(mask, dtype=bool)
    y0, y1, x0, x1 = _bbox(mask)
    sub = mask[y0:y1, x0:x1]
    f = height / float(sub.shape[0])
    w = max(1, int(round(sub.shape[1] * f)))
    im = Image.fromarray((sub * 255).astype(np.uint8)).resize((w, height), Image.BILINEAR)
    sc = np.asarray(im) >= 128
    if sc.shape[1] > size:  # extremely wide glyph: keep the centre
        o = (sc.shape[1] - size) // 2
        sc = sc[:, o:o + size]
    canvas = np.zeros((size, size), dtype=bool)
    oy, ox = (size - sc.shape[0]) // 2, (size - sc.shape[1]) // 2
    canvas[oy:oy + sc.shape[0], ox:ox + sc.shape[1]] = sc
    return _recentre(canvas, size)


# ---------------------------------------------------------------- distance

def _transform(img_l, angle_deg, scale, pivot):
    """Rotate by angle and scale about pivot (PIL affine maps output->input)."""
    th = np.deg2rad(angle_deg)
    c, s = np.cos(th), np.sin(th)
    cx, cy = pivot
    a, b = c / scale, s / scale
    d, e = -s / scale, c / scale
    cc = cx - a * cx - b * cy
    f = cy - d * cx - e * cy
    return img_l.transform(img_l.size, Image.AFFINE, (a, b, cc, d, e, f), resample=Image.BILINEAR)


def shape_distance(a, b):
    """D = 1 - max IoU of normalize(a) against rotated/scaled, re-centred copies of normalize(b)."""
    na = normalize(a)
    nb = normalize(b)
    size = na.shape[0]
    base = Image.fromarray((nb * 255).astype(np.uint8))
    ys, xs = np.nonzero(nb)
    pivot = (xs.mean(), ys.mean())
    area_a = na.sum()
    best = 0.0
    for ang in ANGLES:
        for sc in SCALES:
            t = np.asarray(_transform(base, ang, sc, pivot)) >= 128
            t = _recentre(t, size)
            inter = np.logical_and(na, t).sum()
            union = area_a + t.sum() - inter
            if union > 0:
                best = max(best, inter / union)
    return float(1.0 - best)


# ---------------------------------------------------------------- likelihood ratio

def _log_kde(d, data):
    """log of Gaussian KDE density at d (scipy-style Silverman factor), numerically stable."""
    data = np.asarray(data, dtype=float)
    n = len(data)
    if n < 2:
        raise ValueError("need at least 2 reference distances for a KDE")
    sd = data.std(ddof=1)
    h = max(sd * (n * 3.0 / 4.0) ** (-1.0 / 5.0), 1e-3)
    z = (np.atleast_1d(d)[:, None] - data[None, :]) / h
    lz = -0.5 * z ** 2 - np.log(h * np.sqrt(2 * np.pi))
    m = lz.max(axis=1)
    return m + np.log(np.exp(lz - m[:, None]).sum(axis=1)) - np.log(n)


def log10_lr(d, same_dists, diff_dists):
    """log10 of f_X(d)/f_S(d); d may be scalar or array."""
    out = (_log_kde(d, diff_dists) - _log_kde(d, same_dists)) / np.log(10.0)
    return out if np.ndim(d) else float(out[0])


def kde_lr(d, same_dists, diff_dists):
    """f_X(d)/f_S(d) with Gaussian KDEs and Silverman bandwidth (same_dists = S, diff_dists = X)."""
    return float(np.power(10.0, log10_lr(d, same_dists, diff_dists)))


def decide(log10_lr_sum, circle_px):
    if log10_lr_sum >= 1:
        label = "three different symbols"
    elif log10_lr_sum <= -1:
        label = "one symbol"
    else:
        label = "unresolved at this resolution"
    if circle_px < 20:
        label += " (low resolution)"
    return label


def bootstrap_interval(circle_dists, same_dists, diff_dists, n=2000, seed=SEED):
    """90% interval (5th, 95th percentile) of the summed log10 LR, resampling reference pairs."""
    rng = np.random.default_rng(seed)
    same = np.asarray(same_dists, dtype=float)
    diff = np.asarray(diff_dists, dtype=float)
    cd = np.asarray(circle_dists, dtype=float)
    sums = np.empty(n)
    for i in range(n):
        s = same[rng.integers(0, len(same), len(same))]
        x = diff[rng.integers(0, len(diff), len(diff))]
        sums[i] = log10_lr(cd, s, x).sum()
    lo, hi = np.percentile(sums, [5, 95])
    return float(lo), float(hi)


# ---------------------------------------------------------------- run

def _pairs(crops, masks):
    same, diff = [], []
    cipher = [c for c in crops if c["role"] == "cipher"]
    for a, b in itertools.combinations(cipher, 2):
        rec = (a["id"], b["id"])
        (same if a["symbol"] == b["symbol"] else diff).append(rec)
    seen = {}
    for c in crops:
        if c["role"] == "hand":
            seen.setdefault(c["symbol"], []).append(c)
    for sym, lst in seen.items():
        if len(lst) >= 2:
            same.append((lst[0]["id"], lst[1]["id"]))
    for c in crops:
        if c["role"] == "circle":
            for x in crops:
                if x["role"] == "crosshair":
                    diff.append((c["id"], x["id"]))
    return same, diff


def run(crops_json_path, image_path):
    with open(crops_json_path) as fh:
        spec = json.load(fh)
    crops = spec["crops"]
    ids = [c["id"] for c in crops]
    if len(set(ids)) != len(ids):
        raise ValueError("duplicate crop ids")
    with Image.open(image_path) as im:
        gray = im.convert("L")
        masks = {c["id"]: crop_mask(gray, c["box"]) for c in crops}
    circles = {int(c["position"]): c for c in crops if c["role"] == "circle"}
    if sorted(circles) != [5, 7, 9]:
        raise ValueError("crops.json needs exactly three circle crops with positions 5, 7, 9")
    same_pairs, diff_pairs = _pairs(crops, masks)
    cache = {}

    def dist(p):
        if p not in cache:
            cache[p] = shape_distance(masks[p[0]], masks[p[1]])
        return cache[p]

    same_d = [dist(p) for p in same_pairs]
    diff_d = [dist(p) for p in diff_pairs]
    circle_pairs = {}
    for a, b in ((5, 7), (5, 9), (7, 9)):
        circle_pairs["%d-%d" % (a, b)] = dist((circles[a]["id"], circles[b]["id"]))
    cd = list(circle_pairs.values())
    per_pair = {k: {"D": v, "LR": kde_lr(v, same_d, diff_d), "log10_LR": log10_lr(v, same_d, diff_d)}
                for k, v in circle_pairs.items()}
    total = float(sum(p["log10_LR"] for p in per_pair.values()))
    lo, hi = bootstrap_interval(cd, same_d, diff_d)
    circle_px = int(min(_bbox(masks[c["id"]])[3] - _bbox(masks[c["id"]])[2] for c in circles.values()))
    with open(os.path.abspath(__file__), "rb") as fh:
        code_sha = hashlib.sha256(fh.read()).hexdigest()
    res = {
        "code_sha256": code_sha,
        "image": os.path.basename(image_path),
        "circle_px_min_width": circle_px,
        "circle_pairs": per_pair,
        "summed_log10_LR": total,
        "bootstrap_90_interval": [lo, hi],
        "bootstrap": {"n": 2000, "seed": SEED},
        "decision": decide(total, circle_px),
        "n_same": len(same_d),
        "n_diff": len(diff_d),
        "same_pairs": [{"a": p[0], "b": p[1], "D": d} for p, d in zip(same_pairs, same_d)],
        "diff_pairs": [{"a": p[0], "b": p[1], "D": d} for p, d in zip(diff_pairs, diff_d)],
    }
    out = os.path.join(os.path.dirname(os.path.abspath(crops_json_path)), "results.json")
    with open(out, "w") as fh:
        json.dump(res, fh, indent=2)
    return res


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit("usage: python measure.py CROPS_JSON IMAGE")
    r = run(sys.argv[1], sys.argv[2])
    print(json.dumps({k: r[k] for k in ("summed_log10_LR", "bootstrap_90_interval", "decision")}, indent=2))
