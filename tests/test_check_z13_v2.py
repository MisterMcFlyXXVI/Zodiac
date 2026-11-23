"""Tests for scripts/check_z13_phrase_lists_v2.py (C1 v2 pre-registered Z13 check)."""
import importlib.util
import pathlib
import random
import re

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("chk", ROOT / "scripts" / "check_z13_phrase_lists_v2.py")
chk = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(chk)
PLAN = ROOT / "hypotheses" / "candidates" / "z13_phrase_lists_v2_PLAN.md"


def test_sizes_match_preregistered_plan():
    """The check must use exactly the per-test sizes declared in the pushed plan."""
    text = PLAN.read_text()
    n = lambda s: None if s.strip() == "exploratory" else int(s.replace(",", ""))
    rows = re.findall(r"^\| (blank_p\d+|dash_p\d+) \| `z13_([^`]+)` \| ([^|]+) \| ([^|]+) \|", text, re.M)
    assert len(rows) == 16
    assert {r: (n(e), n(h)) for r, _, e, h in rows} == chk.SECONDARY_N
    prim = dict(re.findall(r"^\| canonical \| (simple|homophonic) \| ([\d,]+) \|", text, re.M))
    assert n(prim["simple"]) == chk.PRIMARY_N["exact"] and n(prim["homophonic"]) == chk.PRIMARY_N["homophonic"]
    lists = {r["name"]: r["list"] for r in chk.secondary_readings()}
    assert all(lists[r] == l for r, l, _, _ in rows)


def test_all_lists_verify_and_cover_their_tests():
    for name in chk.PRIMARY_LISTS:
        assert len(chk.load(name)) * 2 >= chk.PRIMARY_N["exact"]
    for r in chk.secondary_readings():
        lines = chk.load(r["list"])
        for N in chk.SECONDARY_N[r["name"]]:
            assert N is None or N <= len(lines)
        if "lengths" in r:   # dash readings: words end exactly at the dropped positions
            assert all(tuple(len(w) for w in p.split()) == r["lengths"] for p in lines)


def test_secondary_readings():
    sec = chk.secondary_readings()
    assert len(sec) == 16
    blank3 = next(r for r in sec if r["name"] == "blank_p3")
    assert blank3["ct"] == chk.read("crosshair_null")
    for r in sec:
        if "lengths" in r:
            assert sum(r["lengths"]) == len(r["ct"])


def test_mask_null_matches_bruteforce():
    rng = random.Random(5)
    profile = [2, 2, 1, 1, 1, 1]
    cands = ["".join(rng.choice("ABCDE") for _ in range(8)) for _ in range(400)]
    D = ["".join(chr(97 + s) for s in d) for d in chk.decoys(profile, 300, seed=9)]  # patterns as symbol strings
    for key in ("exact", "homophonic", "slip"):
        fast = chk.null_counts(cands, profile, key, n_decoys=300, seed=9)
        brute = []
        for d in D:
            if key == "slip":
                brute.append(sum(chk.fits_one_slip(c, d) for c in cands))
            else:
                brute.append(sum(chk.fits(c, d, "simple" if key == "exact" else "homophonic") for c in cands))
        assert np.array_equal(fast, np.array(brute)), key


def test_lone_fit_is_not_notable_when_chance_fits_are_common():
    null = np.array([1] * 200 + [0] * 4800)          # 4% of decoys get a chance fit
    assert not chk.decision(1, null, n_tests=4)["notable"]
    assert chk.decision(1, np.zeros(5000, int), n_tests=4)["notable"]   # p = 1/5001


def test_small_pattern_space_uses_full_population():
    d = chk.decoys([2, 2, 2, 1, 1, 1, 1], 5000, seed=1, exclude={chk.iso("AABBCCDEFG")})
    assert len(d) == len(set(d)) == 3150 - 1
