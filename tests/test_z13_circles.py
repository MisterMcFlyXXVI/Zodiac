"""Tests for the Z13 circles image analysis (scripts/z13_circles). Synthetic data only: no real image is read.

Adapted from the pre-registered test scripts (research test_measure.py, sha256 266210d4...; test_metrics.py,
sha256 9057019d...). Also asserts that measure.py and metrics.py are byte-identical to the versions sealed on the
fork (commits 1f041bc and 0591b39) before they touched any real image."""
import hashlib
import importlib.util
import json
import os
import pathlib
import sys
import tempfile

import numpy as np
import pytest
from PIL import Image, ImageDraw

ROOT = pathlib.Path(__file__).resolve().parent.parent
CIRCLES = ROOT / "scripts" / "z13_circles"
CAND = ROOT / "hypotheses" / "candidates"

SEALED = {
    "measure.py": "7c0b6bbb229a36a135866c88fde959f5de7063de543e3fa2ae95d843ee4e0cd2",
    "metrics.py": "1a5bfee41b6920e0d56f53538cc599608da37a8eedb30bfe3cbbc484e5d31ee5",
}


def _load(name):
    spec = importlib.util.spec_from_file_location(name, CIRCLES / (name + ".py"))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod          # metrics.py does `import measure`: make it find this copy
    spec.loader.exec_module(mod)
    return mod


M = _load("measure")                 # must come first (see above)
MT = _load("metrics")


def check(cond, msg):
    assert cond, msg


def test_sealed_code_hashes():
    """measure.py and metrics.py must equal the code sealed on the fork before any real image was measured."""
    for fn, want in SEALED.items():
        assert hashlib.sha256((CIRCLES / fn).read_bytes()).hexdigest() == want, fn
    listed = dict(reversed(l.split()) for l in (CIRCLES / "SEALED.sha256").read_text().splitlines() if l.strip())
    assert listed == SEALED
    # the copies pushed in the pre-registration commits carry the same bytes
    assert hashlib.sha256((CAND / "z13_circles_measure.py").read_bytes()).hexdigest() == SEALED["measure.py"]
    assert hashlib.sha256((CAND / "z13_circles_tournament_metrics.py").read_bytes()).hexdigest() == SEALED["metrics.py"]


def test_no_path_to_real_data_in_sealed_code():
    """The sealed code must not reference the real-image folder (same guards as the pre-registered tests)."""
    m = (CIRCLES / "measure.py").read_text()
    assert "research" + "/I2" not in m and "I" + "2/" not in m
    bad = ["research" + "/I2", "i1b" + "/pages", "crops" + ".json", "results" + ".json"]
    assert not any(b in (CIRCLES / "metrics.py").read_text() for b in bad)


# ---------------------------------------------------------------- measure.py
def canvas(size=120):
    im = Image.new("L", (size, size), 0)
    return im, ImageDraw.Draw(im)


def ring(r=40, w=5, size=120):
    im, d = canvas(size)
    c = size / 2
    d.ellipse([c - r, c - r, c + r, c + r], fill=255)
    d.ellipse([c - r + w, c - r + w, c + r - w, c + r - w], fill=0)
    return im, d


def circle_eight(dx=0, dy=0, rr=0, size=120):
    im, d = ring(size=size)
    c = size / 2
    for oy in (-12, 12):
        r = 10 + rr
        d.ellipse([c + dx - r, c + dy + oy - r, c + dx + r, c + dy + oy + r], outline=255, width=4)
    return np.asarray(im) > 0


def circle_cross(size=120):
    im, d = ring(size=size)
    c = size / 2
    d.line([c - 22, c, c + 22, c], fill=255, width=5)
    d.line([c, c - 22, c, c + 22], fill=255, width=5)
    return np.asarray(im) > 0


def asym():
    im, d = canvas(120)
    d.polygon([(30, 20), (90, 30), (50, 60), (95, 100), (25, 90)], fill=255)
    d.ellipse([60, 40, 75, 55], fill=0)
    return im



def test_shape_distance():
    a = np.asarray(asym()) > 0
    check(M.shape_distance(a, a) < 0.01, "identical shapes: D ~ 0")
    rot = np.asarray(asym().rotate(10, resample=Image.BILINEAR)) > 128
    check(M.shape_distance(a, rot) < 0.1, "10-degree rotated copy: D small")
    ringm = np.asarray(ring()[0]) > 0
    im, d = canvas()
    d.ellipse([20, 20, 100, 100], fill=255)
    disc = np.asarray(im) > 0
    check(M.shape_distance(ringm, disc) > 0.5, "ring vs filled disc: D large")
    e1, e2 = circle_eight(), circle_eight(dx=2, dy=-1, rr=1)
    d_same = M.shape_distance(e1, e2)
    d_diff = M.shape_distance(e1, circle_cross())
    print("     jittered-8 D=%.3f  8-vs-cross D=%.3f" % (d_same, d_diff))
    check(d_diff > d_same, "inner-8 vs inner-cross larger than two jittered inner-8")


def test_kde_lr():
    same = np.array([0.08, 0.10, 0.12, 0.09, 0.11, 0.13, 0.10, 0.07])
    diff = np.array([0.45, 0.50, 0.55, 0.48, 0.52, 0.60, 0.47, 0.53])
    check(M.kde_lr(0.5, same, diff) > 1, "kde_lr > 1 in the 'different' cloud")
    check(M.kde_lr(0.1, same, diff) < 1, "kde_lr < 1 in the 'same' cloud")
    check(np.isfinite(M.log10_lr(5.0, same, diff)), "log10_lr finite in far tail")


def test_decide():
    check(M.decide(1.0, 30) == "three different symbols", "decide +1")
    check(M.decide(-1.0, 30) == "one symbol", "decide -1")
    check(M.decide(0.5, 30) == "unresolved at this resolution", "decide in between")
    check(M.decide(2.0, 19).endswith(" (low resolution)"), "decide low resolution suffix")
    check(not M.decide(2.0, 20).endswith("(low resolution)"), "decide 20 px not low")


def test_bootstrap_interval():
    same = np.array([0.08, 0.10, 0.12, 0.09, 0.11, 0.13, 0.10, 0.07])
    diff = np.array([0.45, 0.50, 0.55, 0.48, 0.52, 0.60, 0.47, 0.53])
    cd = [0.5, 0.48, 0.52]
    b1 = M.bootstrap_interval(cd, same, diff, n=200)
    b2 = M.bootstrap_interval(cd, same, diff, n=200)
    b3 = M.bootstrap_interval(cd, same, diff, n=200, seed=1)
    check(b1 == b2 and b1[0] <= b1[1], "bootstrap deterministic with seed")
    check(b1 != b3, "bootstrap differs with another seed")


def test_end_to_end_synthetic_page():
    # end-to-end run on a synthetic page
    with tempfile.TemporaryDirectory() as td:
        page = Image.new("L", (700, 200), 255)
        dr = ImageDraw.Draw(page)
        boxes = {}
        def put(i, x, kind):
            sub = {"ring": ring(r=28, w=4, size=70)[0], "plus": canvas(70)[0]}[kind]
            if kind == "plus":
                dd = ImageDraw.Draw(sub); dd.line([10, 35, 60, 35], fill=255, width=5); dd.line([35, 10, 35, 60], fill=255, width=5)
            inv = Image.eval(sub, lambda v: 255 - v)
            page.paste(inv, (x, 10))
            boxes[i] = [x, 10, x + 70, 80]
        for i, x in enumerate((0, 80, 160)):
            put("c%d" % (5 + 2 * i), x, "ring")
        put("x1", 240, "plus"); put("A1", 320, "ring"); put("A2", 400, "ring"); put("B1", 480, "plus"); put("B2", 560, "plus")
        page.save(os.path.join(td, "p.png"))
        spec = {"crops": [
            {"id": "c5", "symbol": "circle", "role": "circle", "position": 5, "box": boxes["c5"]},
            {"id": "c7", "symbol": "circle", "role": "circle", "position": 7, "box": boxes["c7"]},
            {"id": "c9", "symbol": "circle", "role": "circle", "position": 9, "box": boxes["c9"]},
            {"id": "x1", "symbol": "cross", "role": "crosshair", "box": boxes["x1"]},
            {"id": "A1", "symbol": "A", "role": "cipher", "box": boxes["A1"]},
            {"id": "A2", "symbol": "A", "role": "cipher", "box": boxes["A2"]},
            {"id": "B1", "symbol": "B", "role": "cipher", "box": boxes["B1"]},
            {"id": "B2", "symbol": "B", "role": "cipher", "box": boxes["B2"]}]}
        cj = os.path.join(td, "crops.json")
        json.dump(spec, open(cj, "w"))
        r = M.run(cj, os.path.join(td, "p.png"))
        check(os.path.exists(os.path.join(td, "results.json")), "run writes results.json")
        check(all(v["D"] < 0.05 for v in r["circle_pairs"].values()), "run: identical synthetic circles D ~ 0")
        check(r["n_same"] == 2 and r["n_diff"] == 7, "run: set S/X sizes as defined")



# ---------------------------------------------------------------- metrics.py
def seg_dist(x, y, p0, p1, wid):
    """distance-to-segment <= wid/2."""
    p0, p1 = np.array(p0, float), np.array(p1, float)
    d = p1 - p0
    t = np.clip(((x - p0[0]) * d[0] + (y - p0[1]) * d[1]) / (d @ d), 0, 1)
    return np.hypot(x - (p0[0] + t * d[0]), y - (p0[1] + t * d[1])) <= wid / 2.0


def draw(design, rng=None, size=96, R=30.0, thick=3.0, rot=0.0, scale=1.0, shift=(0.0, 0.0), aspect=1.0):
    c = (size - 1) / 2.0
    yy, xx = np.mgrid[0:size, 0:size].astype(float)
    cx, cy = c + shift[0], c + shift[1]
    R = R * scale
    u = (xx - cx) / aspect
    v = yy - cy
    r = np.hypot(u, v)
    img = np.abs(r - (R - thick / 2.0)) <= thick / 2.0
    th = np.deg2rad(rot)
    x = np.cos(th) * u + np.sin(th) * v      # glyph-frame coordinates
    y = -np.sin(th) * u + np.cos(th) * v
    s = scale
    if design == "eight":
        for oy in (-10 * s, 10 * s):
            rr = np.hypot(x, y - oy)
            img |= np.abs(rr - 9 * s) <= thick / 2.0
    elif design == "x":
        img |= seg_dist(x, y, (-17 * s, -17 * s), (17 * s, 17 * s), thick)
        img |= seg_dist(x, y, (-17 * s, 17 * s), (17 * s, -17 * s), thick)
    elif design == "dot":
        img |= np.hypot(x, y) <= 6 * s
    elif design == "vline":
        img |= seg_dist(x, y, (0, -20 * s), (0, 20 * s), thick)
    elif design == "blank":
        pass
    if rng is not None:  # salt noise on edge pixels
        edge = img ^ np.roll(img, 1, 0)
        flip = edge & (rng.random(img.shape) < 0.05)
        img = img ^ flip
    return img


def jitter(design, rng):
    return draw(design, rng, R=rng.uniform(26, 32), thick=rng.uniform(2.5, 3.5), rot=rng.uniform(-6, 6),
                scale=1.0, shift=(rng.uniform(-3, 3), rng.uniform(-3, 3)))




designs = ["eight", "x", "dot", "vline"]
K = 20


@pytest.fixture(scope="module")
def synth():
    rng = np.random.default_rng(7)
    samples = {d: [jitter(d, rng) for _ in range(K)] for d in designs}
    return rng, samples




def test_no_paths_in_run_scripts_to_workspace():
    """Run scripts take image paths on the command line; nothing may point into a private workspace."""
    for p in CIRCLES.glob("*.py"):
        if p.name == "metrics.py":      # sealed byte-for-byte; its fallback path is inert (see README note)
            continue
        txt = p.read_text()
        assert "/home/" not in txt and "zodiac-lab" not in txt and "zodiac-verify" not in txt, p.name


def test_ring_fit(synth):
    rng, _ = synth
    for d in designs:
        for _ in range(5):
            R0 = rng.uniform(24, 32)
            sh = (rng.uniform(-3, 3), rng.uniform(-3, 3))
            img = draw(d, None, R=R0, thick=3.0, shift=sh)
            cx, cy, R, t = MT.fit_ring(img)
            c = 47.5
            assert abs(cx - (c + sh[0])) < 1.5 and abs(cy - (c + sh[1])) < 1.5 and abs(R - R0) < 1.5, (d, cx, cy, R, R0, sh)
            assert abs(t - 3.0) < 1.5, t


def test_topology_on_clean_drawings():
    tp = {d: tuple(MT.features(draw(d))["topology"].astype(int)) for d in designs}
    check(tp["eight"][0] == 2, "8 has 2 enclosed inner loops")
    check(tp["x"][0] == 0 and tp["x"][1] == 1 and tp["x"][2] == 4, "X: 0 loops, 1 junction, 4 endpoints")
    check(tp["vline"][0] == 0 and tp["vline"][1] == 0 and tp["vline"][2] == 2, "vline: 0 loops, 0 junctions, 2 endpoints")
    check(tp["dot"] == (0, 0, 0), "dot: no loops/junctions/endpoints")


def test_distances_separate_synthetic_designs(synth):
    _, samples = synth
    allm = [m for d in designs for m in samples[d]]
    muZ, sdZ = MT.zstats([MT.features(m)["zernike"] for m in allm])
    tsd = np.array([1.0, 1.0, 1.0])
    metrics = {
        "M2": lambda a, b: MT.m2_interior(a, b),
        "M3": lambda a, b: MT.m3_angular(a, b),
        "M4": lambda a, b: MT.m4_topology(a, b, tsd),
        "M5": lambda a, b: MT.m5_zernike(a, b, muZ, sdZ),
    }
    for name, f in metrics.items():
        same, diff = [], []
        for d in designs:
            for i in range(0, K - 1, 2):
                same.append(f(samples[d][i], samples[d][i + 1]))
        for i, d1 in enumerate(designs):
            for d2 in designs[i + 1:]:
                for k in range(K):
                    diff.append(f(samples[d1][k], samples[d2][(k + 3) % K]))
        ms, md = np.mean(same), np.mean(diff)
        check(ms < md and MT.auc(diff, same) > 0.8, "%s: same-design closer than different designs" % name)
        check(min(same + diff) >= 0, name + " distances >= 0")


def test_m6_ring_geometry(synth):
    _, samples = synth
    allm = [m for d in designs for m in samples[d]]
    muR, sdR = MT.zstats([MT.features(m)["ring"] for m in allm])
    a = draw("blank")
    check(MT.m6_ring(a, a.copy(), muR, sdR) < 1e-9, "M6 ~0 for identical rings")
    check(MT.m6_ring(draw("blank"), draw("blank", thick=6.0), muR, sdR) > 0.5, "M6 sees thickness change")
    check(MT.m6_ring(draw("blank"), draw("blank", aspect=0.7), muR, sdR) > 0.5, "M6 sees aspect change")
    circ = MT.features(draw("blank", R=30))["ring"][3]
    check(0.85 < circ < 1.1, "circularity of a clean ring ~1 (%.3f)" % circ)


def test_m1_passthrough(synth):
    _, samples = synth
    check(abs(MT.m1_whole(samples["x"][0], samples["x"][0])) < 1e-6, "M1 identical -> 0")


def test_m7_fit_is_deterministic_and_separates(synth):
    rng, _ = synth
    X = np.vstack([rng.normal(0.3, 0.1, (40, 6)), rng.normal(0.6, 0.1, (40, 6))])
    y = np.r_[np.zeros(40), np.ones(40)]
    m1 = MT.fit_m7(X, y)
    m2 = MT.fit_m7(X, y)
    check(all(np.array_equal(m1[k], m2[k]) for k in ("mu", "sd", "w")) and m1["b"] == m2["b"], "M7 fit deterministic")
    sc = MT.m7_score(m1, X)
    check(MT.auc(sc[y == 1], sc[y == 0]) > 0.95, "M7 separates synthetic distances")


def test_auc():
    check(MT.auc([2, 3], [1, 1]) == 1.0, "auc perfect")
    check(MT.auc([1, 1], [1, 1]) == 0.5, "auc ties -> 0.5")
    check(abs(MT.auc([1, 3], [2]) - 0.5) < 1e-12 and abs(MT.auc([1, 2, 3], [2, 4]) - (1.5 / 6)) < 1e-12, "auc known lists")


def test_glyph_widths_on_synthetic_line():
    gw = _load("glyph_widths")
    img = Image.new("L", (200, 40), 255)
    d = ImageDraw.Draw(img)
    d.ellipse([10, 10, 30, 30], outline=0, width=2)     # 21 px wide ring
    d.rectangle([60, 12, 71, 28], fill=0)               # 12 x 17 block
    d.ellipse([100, 8, 128, 32], outline=0, width=3)    # 29 px wide ring
    boxes = gw.glyph_boxes(np.asarray(img) < 128)
    assert [(b["width"], b["height"]) for b in boxes] == [(21, 21), (12, 17), (29, 25)]
    assert [b["x0"] for b in boxes] == [10, 60, 100]
