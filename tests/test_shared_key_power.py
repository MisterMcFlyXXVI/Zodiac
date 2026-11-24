"""Tests for scripts/shared_key_power.py (S1): generator and link logic only; the full study takes ~40 min."""
import glob, importlib.util, os, random
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_spec = importlib.util.spec_from_file_location("shared_key_power", os.path.join(ROOT, "scripts", "shared_key_power.py"))
bench = power = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(bench)

def test_determinism():
    a, b = bench.gen_pair(5, True), bench.gen_pair(5, True)
    assert (a["a"] == b["a"]).all() and (a["b"] == b["b"]).all() and a["links"] == b["links"] and a["t13"] == b["t13"]
    assert bench.gen_pair(6, True)["t13"] != a["t13"] or bench.gen_pair(6, True)["t32"] != a["t32"]

def test_filters_and_shapes():
    for seed in range(30):
        for sk in (True, False):
            p = bench.gen_pair(seed, sk)
            assert len(p["t13"]) == 13 and len(p["t32"]) == 32 and len(p["a"]) == 13 and len(p["b"]) == 32
            assert 7 <= len(set(p["a"])) <= 9 and len(set(p["b"])) >= 26 and 3 <= len(p["links"]) <= 7
            assert set(p["a"]) == set(range(p["n13"])) and set(p["b"]) == set(range(p["n13"], p["n_tot"]))

def test_shared_key_consistent():
    # in a shared pair, each linked symbol must decode to the same letter in both texts
    for seed in range(20):
        p = bench.gen_pair(seed, True)
        for x, y in p["links"]:
            l13 = {p["t13"][i] for i in range(13) if p["a"][i] == x}
            l32 = {p["t32"][i] for i in range(32) if p["b"][i] == y}
            assert len(l13) == 1 and l13 == l32, (seed, x, y)

def test_enc_rules():
    rng = random.Random(1); key, K = bench.make_key(rng)
    assert K >= 63 and sorted(i for h in key.values() for i in h) == list(range(K))
    t = "EEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEE"
    assert len(set(bench.enc13(rng, "EEEEEEEEEEEEE", key))) == 1          # one homophone, no cycling
    assert len(set(bench.enc32(rng, t, key))) == len(key["E"])           # cycles through all

def test_link_construction():
    for seed in range(20):
        p = bench.gen_pair(seed, seed % 2 == 0); a, b, n13, nt, L = p["a"], p["b"], p["n13"], p["n_tot"], p["links"]
        segs, n = power.merge(a, b, n13, nt, L)
        assert n == nt - len(L) and set(segs[0]) | set(segs[1]) == set(range(n)) and len(set(segs[1])) == len(set(b))
        rng = random.Random(seed); F = power.fake_links(rng, L, n13, nt)
        assert len(F) == len(L) and [x for x, _ in F] == [x for x, _ in L]
        assert len({y for _, y in F}) == len(F) and not ({y for _, y in F} & {y for _, y in L})
        segs, n = power.merge(a, b, n13, nt, F)
        assert n == nt - len(F) and set(segs[0]) | set(segs[1]) == set(range(n))
        assert all(s < n for s in segs[1])

def test_guard():
    """The script must never read the real Z13 / Z32 ciphers (strings split so this file passes itself)."""
    bad = ["z13" + ".json", "z32" + ".json", "vari" + "ants"]
    s = open(os.path.join(ROOT, "scripts", "shared_key_power.py")).read()
    assert not any(w in s for w in bad)
    assert "z340.json" in s


def test_committed_results_support_no_power_verdict():
    import json
    r = json.load(open(os.path.join(ROOT, "results", "shared_key_power", "results.json")))
    assert r["power_005"] < 0.2 and r["fpr_005"] <= 0.1 and r["N"] == 40 and r["M"] == 99
