"""I1c candidate metrics M1-M7 (PLAN_I1c.md). Pure numpy + Pillow; every metric takes two bool glyph masks
and returns a distance >= 0 (larger = more different).

Implementation choices where the plan leaves room (all fixed here, before any real data is touched):
  * Ring fit: Kasa least-squares circle on the outermost contour (filled-silhouette boundary pixels), one
    robust refit dropping outliers, +0.5 px to move from boundary-pixel centres to the edge. R = outer edge.
  * Ring thickness: median over 90 rays of the length of the outermost ink run near R.
  * Interior = pixels with r < R - thickness - INNER_MARGIN (the annulus [R-t, R+t] plus 1 px safety margin
    against fit error), everything outside also removed.
  * M2: interior resampled so that R -> 32 px about the fitted centre (no bbox renormalisation, so scale
    relative to the ring is kept); max IoU over rotation -15..15 deg x scale .85..1.15 (measure.ANGLES/SCALES)
    x translation {-2,0,2}^2 px. Both empty -> 0, one empty -> 1.
  * M3: 36 bins, r/R in [0.15, 0.65], zero-mean normalised circular cross-correlation, shifts -1..+1 bins
    (+-15 deg at 10 deg/bin). Profiles whose zero-mean norm < FLAT_NORM are 'flat' (no angular structure):
    two flat profiles -> distance 0; flat vs structured -> correlation computed with norm floor FLAT_NORM.
  * M4: (enclosed background regions, skeleton junction clusters, skeleton endpoints) of the interior;
    'enclosed' = 4-connected background components of the interior disc that do not touch the cut boundary.
    Skeleton = Zhang-Suen. Distance = sum |diff| / scale.
  * M5: Zernike magnitudes |A_nm|, n<=8, m>=0, n-m even (25 values) of the interior on the unit disc r=R.
  * M6: [w/h of silhouette bbox, thickness/cell height, 2R/cell height, circularity 4*pi*A/P^2]
    (A = filled silhouette area, P = Crofton 4-direction perimeter estimate).
"""
import os
import sys
from collections import deque

import numpy as np
from PIL import Image

sys.path.insert(0, "/home/hercules/zodiac-lab/research/I1")
import measure  # noqa: E402  (sealed M1; not modified)

INNER_MARGIN = 1.0
N_BINS = 36
R_LO, R_HI = 0.15, 0.65
MAX_SHIFT_BINS = 1
FLAT_NORM = 0.2
ZERNIKE_ORDER = 8
FRAME = 80          # M2 canvas
FRAME_R = 32.0      # ring radius in M2 canvas
SHIFTS = (-2, 0, 2)


# ------------------------------------------------------------------ basic image ops

def label(mask, conn=4):
    """Connected components. Returns (labels int array, count)."""
    mask = np.asarray(mask, dtype=bool)
    h, w = mask.shape
    lab = np.zeros((h, w), dtype=np.int32)
    if conn == 4:
        nbrs = ((1, 0), (-1, 0), (0, 1), (0, -1))
    else:
        nbrs = ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (1, -1), (-1, 1), (-1, -1))
    n = 0
    for y0, x0 in zip(*np.nonzero(mask)):
        if lab[y0, x0]:
            continue
        n += 1
        lab[y0, x0] = n
        dq = deque([(y0, x0)])
        while dq:
            y, x = dq.popleft()
            for dy, dx in nbrs:
                yy, xx = y + dy, x + dx
                if 0 <= yy < h and 0 <= xx < w and mask[yy, xx] and not lab[yy, xx]:
                    lab[yy, xx] = n
                    dq.append((yy, xx))
    return lab, n


def _pad(mask, k=1):
    return np.pad(np.asarray(mask, dtype=bool), k)


def exterior(mask):
    """Background connected (4-conn) to the border of the padded image (returned unpadded)."""
    p = _pad(mask)
    lab, _ = label(~p, 4)
    ext = lab == lab[0, 0]
    return ext[1:-1, 1:-1]


def fit_circle(xs, ys):
    """Kasa least-squares circle: returns (cx, cy, R)."""
    A = np.column_stack([xs, ys, np.ones_like(xs)])
    b = xs ** 2 + ys ** 2
    sol, *_ = np.linalg.lstsq(A, b, rcond=None)
    cx, cy = sol[0] / 2.0, sol[1] / 2.0
    R = np.sqrt(max(sol[2] + cx ** 2 + cy ** 2, 1e-9))
    return float(cx), float(cy), float(R)


def fit_ring(mask):
    """fit_ring(mask) -> (cx, cy, R, thickness); R is the outer-edge radius."""
    mask = np.asarray(mask, dtype=bool)
    if not mask.any():
        raise ValueError("empty mask")
    filled = ~exterior(mask)
    p = _pad(filled)
    inner = p[1:-1, 1:-1] & p[:-2, 1:-1] & p[2:, 1:-1] & p[1:-1, :-2] & p[1:-1, 2:]
    cont = filled & ~inner
    ys, xs = np.nonzero(cont)
    xs = xs.astype(float)
    ys = ys.astype(float)
    cx, cy, R = fit_circle(xs, ys)
    res = np.abs(np.hypot(xs - cx, ys - cy) - R)
    mad = np.median(res)
    keep = res <= max(1.5, 2.5 * 1.4826 * mad)
    if keep.sum() >= 5 and not keep.all():
        cx, cy, R = fit_circle(xs[keep], ys[keep])
    R += 0.5
    # thickness: outermost ink run along rays
    runs = []
    step = 0.5
    rs = np.arange(0.0, R + 3.0, step)
    h, w = mask.shape
    for th in np.linspace(0, 2 * np.pi, 90, endpoint=False):
        px = np.rint(cx + rs * np.cos(th)).astype(int)
        py = np.rint(cy + rs * np.sin(th)).astype(int)
        ok = (px >= 0) & (px < w) & (py >= 0) & (py < h)
        ink = np.zeros(len(rs), dtype=bool)
        ink[ok] = mask[py[ok], px[ok]]
        idx = np.nonzero(ink)[0]
        if len(idx) == 0:
            continue
        last = idx[-1]
        if abs(rs[last] - R) > 3.0:
            continue
        n = 0
        while last - n >= 0 and ink[last - n]:
            n += 1
        runs.append(n * step)
    thick = float(np.median(runs)) if runs else 1.0
    return cx, cy, float(R), max(thick, 1.0)


def interior_mask(mask, cx, cy, R, t):
    h, w = mask.shape
    yy, xx = np.mgrid[0:h, 0:w]
    r = np.hypot(xx - cx, yy - cy)
    return np.asarray(mask, dtype=bool) & (r < R - t - INNER_MARGIN)


def zhang_suen(mask):
    """Zhang-Suen thinning (vectorised)."""
    img = _pad(mask, 1).astype(np.uint8)
    while True:
        changed = False
        for step in (0, 1):
            P2, P3, P4 = img[:-2, 1:-1], img[:-2, 2:], img[1:-1, 2:]
            P5, P6, P7 = img[2:, 2:], img[2:, 1:-1], img[2:, :-2]
            P8, P9 = img[1:-1, :-2], img[:-2, :-2]
            c = img[1:-1, 1:-1]
            nb = [P2, P3, P4, P5, P6, P7, P8, P9, P2]
            B = sum(nb[:8])
            A = sum(((nb[i] == 0) & (nb[i + 1] == 1)).astype(np.uint8) for i in range(8))
            if step == 0:
                m = (P2 * P4 * P6 == 0) & (P4 * P6 * P8 == 0)
            else:
                m = (P2 * P4 * P8 == 0) & (P2 * P6 * P8 == 0)
            rm = (c == 1) & (B >= 2) & (B <= 6) & (A == 1) & m
            if rm.any():
                img[1:-1, 1:-1][rm] = 0
                changed = True
        if not changed:
            break
    return img[1:-1, 1:-1].astype(bool)


def _neighbour_count(sk):
    p = _pad(sk, 1).astype(int)
    h, w = sk.shape
    n = np.zeros((h, w), dtype=int)
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            if dy or dx:
                n += p[1 + dy:1 + dy + h, 1 + dx:1 + dx + w]
    return n


def _arm_count(sk, rad=3):
    """Number of separate skeleton arcs crossing the square ring at Chebyshev distance `rad` around each
    pixel (>=3 = branch point; immune to staircase corners and to thin diagonal crossings)."""
    p = _pad(sk, rad).astype(int)
    h, w = sk.shape
    pos = ([(-rad, d) for d in range(-rad, rad + 1)] + [(d, rad) for d in range(-rad + 1, rad + 1)]
           + [(rad, d) for d in range(rad - 1, -rad - 1, -1)] + [(d, -rad) for d in range(rad - 1, -rad, -1)])
    nb = [p[rad + dy:rad + dy + h, rad + dx:rad + dx + w] for dy, dx in pos]
    n = len(nb)
    return sum(((nb[i] == 0) & (nb[(i + 1) % n] == 1)).astype(int) for i in range(n))


def topology_counts(interior, cx, cy, R, t):
    """(enclosed background regions, skeleton junction clusters, skeleton endpoints) inside the ring."""
    h, w = interior.shape
    yy, xx = np.mgrid[0:h, 0:w]
    r = np.hypot(xx - cx, yy - cy)
    disc = r < R - t - INNER_MARGIN
    if not interior.any():
        return (0, 0, 0)
    bg = disc & ~interior
    lab, n = label(bg, 4)
    # touching the cut boundary: a disc pixel with a 4-neighbour outside the disc
    pd = _pad(disc, 1)
    edge = disc & ~(pd[:-2, 1:-1] & pd[2:, 1:-1] & pd[1:-1, :-2] & pd[1:-1, 2:])
    touching = set(np.unique(lab[edge & bg]).tolist())
    holes = sum(1 for k in range(1, n + 1) if k not in touching)
    sk = zhang_suen(interior)
    nb = _neighbour_count(sk)
    junc = sk & (_arm_count(sk) >= 3)
    _, nj = label(junc, 8)
    ends = int((sk & (nb == 1)).sum())
    return (int(holes), int(nj), ends)


# ------------------------------------------------------------------ Zernike

def _zernike_basis(rho, theta, nmax):
    out = {}
    from math import factorial
    for n in range(nmax + 1):
        for m in range(n % 2, n + 1, 2):
            Rr = np.zeros_like(rho)
            for s in range((n - m) // 2 + 1):
                c = ((-1) ** s * factorial(n - s)
                     / (factorial(s) * factorial((n + m) // 2 - s) * factorial((n - m) // 2 - s)))
                Rr += c * rho ** (n - 2 * s)
            out[(n, m)] = Rr * np.exp(-1j * m * theta)
    return out


def zernike_magnitudes(interior, cx, cy, R, nmax=ZERNIKE_ORDER):
    h, w = interior.shape
    yy, xx = np.mgrid[0:h, 0:w]
    x = (xx - cx) / R
    y = (yy - cy) / R
    rho = np.hypot(x, y)
    inside = rho <= 1.0
    theta = np.arctan2(y, x)
    basis = _zernike_basis(rho[inside], theta[inside], nmax)
    f = interior[inside].astype(float)
    dA = 1.0 / (R * R)
    vals = [abs((n + 1) / np.pi * np.sum(f * np.conj(b)) * dA) for (n, m), b in sorted(basis.items())]
    return np.array(vals)


# ------------------------------------------------------------------ features

def _crofton_perimeter(m):
    p = _pad(m, 1)
    nh = np.sum(p[1:-1, 1:] != p[1:-1, :-1])
    nv = np.sum(p[1:, 1:-1] != p[:-1, 1:-1])
    d1 = np.sum(p[1:, 1:] != p[:-1, :-1])
    d2 = np.sum(p[1:, :-1] != p[:-1, 1:])
    return (np.pi / 2.0) * (1.0 / 4.0) * (nh + nv + (d1 + d2) / np.sqrt(2.0))


_CACHE = {}


def polar_profile(mask, cx, cy, R):
    h, w = mask.shape
    yy, xx = np.mgrid[0:h, 0:w]
    dx, dy = xx - cx, yy - cy
    rr = np.hypot(dx, dy) / R
    sel = (rr >= R_LO) & (rr <= R_HI)
    ang = (np.degrees(np.arctan2(dy, dx)) % 360.0)
    b = np.minimum((ang[sel] / (360.0 / N_BINS)).astype(int), N_BINS - 1)
    tot = np.bincount(b, minlength=N_BINS).astype(float)
    ink = np.bincount(b, weights=mask[sel].astype(float), minlength=N_BINS)
    return np.where(tot > 0, ink / np.maximum(tot, 1), 0.0)


def _frame(interior, cx, cy, R):
    """Resample the interior so the ring radius becomes FRAME_R about the canvas centre."""
    s = FRAME_R / R
    c = (FRAME - 1) / 2.0
    # PIL affine maps output (u,v) -> input (a u + b v + c0, d u + e v + f)
    a = 1.0 / s
    im = Image.fromarray((interior * 255).astype(np.uint8))
    out = im.transform((FRAME, FRAME), Image.AFFINE,
                       (a, 0, cx - a * c, 0, a, cy - a * c), resample=Image.BILINEAR)
    return np.asarray(out) >= 128


def features(mask):
    """Everything the metrics need for one glyph mask (cached by content)."""
    mask = np.asarray(mask, dtype=bool)
    key = (mask.shape, mask.tobytes())
    if key in _CACHE:
        return _CACHE[key]
    cx, cy, R, t = fit_ring(mask)
    inter = interior_mask(mask, cx, cy, R, t)
    ys, xs = np.nonzero(mask)
    h_cell = float(mask.shape[0])
    filled = ~exterior(mask)
    A = float(filled.sum())
    P = float(_crofton_perimeter(filled))
    bh = ys.max() - ys.min() + 1
    bw = xs.max() - xs.min() + 1
    f = {
        "cx": cx, "cy": cy, "R": R, "thickness": t,
        "interior": inter,
        "frame": _frame(inter, cx, cy, R),
        "profile": polar_profile(mask, cx, cy, R),
        "topology": np.array(topology_counts(inter, cx, cy, R, t), dtype=float),
        "zernike": zernike_magnitudes(inter, cx, cy, R),
        "ring": np.array([bw / float(bh), t / h_cell, 2.0 * R / h_cell,
                          4.0 * np.pi * A / (P * P) if P > 0 else 0.0]),
    }
    if len(_CACHE) > 4000:
        _CACHE.clear()
    _CACHE[key] = f
    return f


def zstats(vectors):
    """mu, sd (sd floored to 1e-6 -> 1.0 if degenerate) from a list of feature vectors."""
    V = np.asarray(vectors, dtype=float)
    mu = V.mean(axis=0)
    sd = V.std(axis=0, ddof=1) if len(V) > 1 else np.ones(V.shape[1])
    sd = np.where(sd < 1e-9, 1.0, sd)
    return mu, sd


# ------------------------------------------------------------------ metrics

def m1_whole(a, b):
    return float(measure.shape_distance(a, b))


def _frame_iou_distance(fa, fb):
    na, nb = int(fa.sum()), int(fb.sum())
    if na == 0 and nb == 0:
        return 0.0
    if na == 0 or nb == 0:
        return 1.0
    base = Image.fromarray((fb * 255).astype(np.uint8))
    pivot = ((FRAME - 1) / 2.0, (FRAME - 1) / 2.0)
    best = 0.0
    for ang in measure.ANGLES:
        for sc in measure.SCALES:
            t = np.asarray(measure._transform(base, ang, sc, pivot)) >= 128
            ts = int(t.sum())
            if ts == 0:
                continue
            for dy in SHIFTS:
                for dx in SHIFTS:
                    s = np.roll(np.roll(t, dy, 0), dx, 1)
                    inter = int(np.logical_and(fa, s).sum())
                    union = na + ts - inter
                    if union > 0 and inter / union > best:
                        best = inter / union
    return float(1.0 - best)


def m2_interior(a, b):
    return _frame_iou_distance(features(a)["frame"], features(b)["frame"])


def _profile_distance(pa, pb):
    a = pa - pa.mean()
    b = pb - pb.mean()
    na, nb = np.linalg.norm(a), np.linalg.norm(b)
    if na < FLAT_NORM and nb < FLAT_NORM:
        return 0.0
    den = max(na, FLAT_NORM) * max(nb, FLAT_NORM)
    best = -np.inf
    for s in range(-MAX_SHIFT_BINS, MAX_SHIFT_BINS + 1):
        best = max(best, float(np.dot(a, np.roll(b, s))) / den)
    return float(max(0.0, 1.0 - best))


def m3_angular(a, b):
    return _profile_distance(features(a)["profile"], features(b)["profile"])


def m4_topology(a, b, scales=1.0):
    d = np.abs(features(a)["topology"] - features(b)["topology"])
    return float(np.sum(d / np.asarray(scales, dtype=float)))


def _z(v, mu, sd):
    mu = 0.0 if mu is None else np.asarray(mu, dtype=float)
    sd = 1.0 if sd is None else np.asarray(sd, dtype=float)
    return (v - mu) / sd


def m5_zernike(a, b, mu=None, sd=None):
    return float(np.linalg.norm(_z(features(a)["zernike"], mu, sd) - _z(features(b)["zernike"], mu, sd)))


def m6_ring(a, b, mu=None, sd=None):
    return float(np.linalg.norm(_z(features(a)["ring"], mu, sd) - _z(features(b)["ring"], mu, sd)))


# ------------------------------------------------------------------ M7 and AUC

def fit_m7(train_pairs_distances, labels, l2=1e-3, iters=3000, lr=0.2):
    """Logistic regression (label 1 = LOOK, 0 = SAME) on an (n, k) matrix of M1..M6 distances.
    Standardised by train mean/sd, full-batch gradient descent from zero: deterministic."""
    X = np.asarray(train_pairs_distances, dtype=float)
    y = np.asarray(labels, dtype=float)
    mu = X.mean(axis=0)
    sd = X.std(axis=0)
    sd = np.where(sd < 1e-9, 1.0, sd)
    Z = (X - mu) / sd
    w = np.zeros(Z.shape[1])
    b = 0.0
    n = len(y)
    for _ in range(iters):
        p = 1.0 / (1.0 + np.exp(-(Z @ w + b)))
        g = p - y
        w -= lr * (Z.T @ g / n + l2 * w)
        b -= lr * g.mean()
    return {"mu": mu, "sd": sd, "w": w, "b": float(b)}


def m7_score(model, distances):
    """Logit of P(LOOK); larger = more different. Accepts (k,) or (n, k)."""
    Z = (np.asarray(distances, dtype=float) - model["mu"]) / model["sd"]
    return Z @ model["w"] + model["b"]


def auc(look, same):
    """P(look > same), ties counted half."""
    look = np.asarray(look, dtype=float)[:, None]
    same = np.asarray(same, dtype=float)[None, :]
    return float(((look > same).sum() + 0.5 * (look == same).sum()) / (look.size * same.size))
