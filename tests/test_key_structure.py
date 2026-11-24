"""Tests for scripts/key_structure.py (K1: keyword/shift structure in solved keys)."""
import importlib.util, itertools, json, os
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_spec = importlib.util.spec_from_file_location("key_structure", os.path.join(ROOT, "scripts", "key_structure.py"))
S = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(S)


def test_lnds():
    assert S.lnds([]) == 0
    assert S.lnds([1, 2, 3, 4]) == 4
    assert S.lnds([4, 3, 2, 1]) == 1
    assert S.lnds([1, 1, 1]) == 3                 # non-decreasing: ties count
    assert S.lnds([3, 1, 2, 1, 4, 2]) == 3
    assert S.lnds([5, 1, 2, 2, 3, 0]) == 4
    rs = np.random.default_rng(1)
    for _ in range(200):
        s = list(rs.integers(0, 5, size=8))
        best = max(len(c) for r in range(9) for c in itertools.combinations(s, r)
                   if all(c[i] <= c[i + 1] for i in range(len(c) - 1)))
        assert S.lnds(s) == best, s


def test_stats_and_null():
    assert S.stat_t1([0, 1, 2, 3], [5, 6, 7, 9]) == 3
    assert S.stat_t1([25], [0]) == 1
    enc = [3, 3, 7, 0, 25, 7, 7]
    for p in S.null_perms(np.random.default_rng(5), enc, 50):
        assert sorted(p) == sorted(enc)


def test_determinism_and_power():
    enc = [3, 3, 7, 0, 25, 7, 7]
    a = S.run_test('T2', None, enc, np.random.default_rng(S.SEED), 500)
    b = S.run_test('T2', None, enc, np.random.default_rng(S.SEED), 500)
    assert a == b
    assert S.main(200) == S.main(200)
    obs, p = S.run_test('T2', None, list(range(10)), np.random.default_rng(1), 1000)
    assert obs == 10 and p < 0.01      # a perfectly ordered set must be flagged


def test_glyph_table_matches_descriptions():
    """The committed table is exactly what the description-only rule produces, and the plan hash matches."""
    import hashlib
    d = os.path.join(ROOT, "results", "key_structure")
    gt = json.load(open(os.path.join(d, "glyph_table.json")))
    for c in ("z408", "z340"):
        for s in json.load(open(os.path.join(ROOT, "data", "ciphers", c + ".json")))["symbols"]:
            g, t = S.classify(s["ascii"], s["description"])
            assert gt[c][s["ascii"]] == {"glyph_letter": g, "transform": t}
    hashes = dict(l.split()[::-1] for l in open(os.path.join(d, "PLAN.sha256")) if l.strip())
    for name, h in hashes.items():
        assert hashlib.sha256(open(os.path.join(d, name), "rb").read()).hexdigest() == h, name


def test_committed_results_reproduce():
    res = json.load(open(os.path.join(ROOT, "results", "key_structure", "results.json")))
    assert S.main(res["N"] // 10)["z408"]["set_sizes"] == res["z408"]["set_sizes"]
    assert res["significant_at_bonferroni"] == []
