#!/usr/bin/env python3
"""Tests for B4 slip_rule. Runs under pytest or standalone:

  python -m pytest tests/test_slip_rule.py

The load-bearing test is test_lone_one_slip_is_chance / test_v1_one_slip_all_chance: without
pricing the one-slip chance rate into the decision, the four one-slip/homophonic fits observed
on the circles_distinct reading in C1 v1 would be reported as hits. The priced, family-aware
rule classifies every one of them as chance -- and the test asserts exactly that, so it fails
if the rule ever reverts to "any fit counts".
"""
from __future__ import annotations

import pathlib

import importlib.util

ROOT = pathlib.Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("slip_rule", ROOT / "scripts" / "slip_rule.py")
sr = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(sr)

VAR = ROOT / "data" / "ciphers" / "variants"
CAND = ROOT / "hypotheses" / "candidates"
SEED, N = 20261123, 2000


def reading(r):
    return VAR.joinpath(f"z13.{r}.txt").read_text().strip()


def cands(name):
    return [l.strip().replace(" ", "")
            for l in CAND.joinpath(f"z13_{name}_v1.txt").read_text().splitlines() if l.strip()]


def null_for(name, r, key):
    ct = reading(r)
    usable = [c for c in cands(name) if len(c) == len(ct)]
    excl = {sr.iso(ct), sr.iso(ct[::-1])}
    return sr.null_counts(usable, sr.profile_of(ct), n_decoys=N, seed=SEED, exclude=excl)[key]


# ---- structure -------------------------------------------------------------


def test_profiles():
    assert sr.profile_of(reading("canonical")) == [3, 2, 2, 2, 1, 1, 1, 1]
    assert sr.profile_of(reading("circles_distinct")) == [2, 2, 2, 1, 1, 1, 1, 1, 1, 1]
    assert sr.profile_of(reading("crosshair_null")) == [3, 2, 2, 2, 1, 1, 1]
    # circles_distinct is strictly looser (more distinct symbols) than canonical
    assert len(set(reading("circles_distinct"))) > len(set(reading("canonical")))


def test_fits_matches_known_v1():
    # "I AM YOUR NEW MAN" was the v1 one-slip fit on circles_distinct (not an exact fit).
    p, ct = "IAMYOURNEWMAN", reading("circles_distinct")
    assert len(p) == len(ct) == 13
    assert not sr.fits(p, ct, "simple")           # not exact
    assert sr.fits_one_slip(p, ct, "simple")       # fits with one slip


def test_exact_implies_one_slip():
    ct = reading("canonical")
    # a letter string that IS the canonical isomorph fits exactly...
    exact = "".join(chr(65 + i) for i in sr.iso(ct))
    assert sr.fits(exact, ct, "simple")
    assert sr.fits_one_slip(exact, ct, "simple")   # ...so it fits under one slip too


def test_length_guard():
    ct = reading("crosshair_null")  # length 12
    try:
        sr.null_counts(["ABCDEFGHIJKLM"], sr.profile_of(ct), n_decoys=10, seed=SEED)  # 13 letters
    except ValueError:
        return
    raise AssertionError("expected ValueError on a length mismatch")


def test_n_isomorphs():
    assert sr.n_isomorphs([2, 2, 2, 1, 1, 1, 1]) == 3150        # 10!/(2!^3 * 3! * 4!)
    assert sr.n_isomorphs([3, 2, 2, 2, 1, 1, 1, 1]) == 900900   # Z13 canonical profile
    assert sr.n_isomorphs([1, 1, 1]) == 1 and sr.n_isomorphs([2, 1]) == 3


def test_decoy_guard_small_space():
    """Asking for more decoys than patterns exist must raise, not hang (it used to hang)."""
    import signal

    def _hang(*_):
        raise AssertionError("decoy_isomorphs hung instead of raising")
    old = signal.signal(signal.SIGALRM, _hang)
    signal.alarm(10)
    try:
        sr.decoy_isomorphs([2, 2, 2, 1, 1, 1, 1], 5000, seed=1)
    except ValueError:
        pass
    else:
        raise AssertionError("expected ValueError")
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, old)


def test_determinism():
    a = null_for("taunt", "circles_distinct", "slip")
    b = null_for("taunt", "circles_distinct", "slip")
    assert list(a) == list(b)


# ---- the priced decision ---------------------------------------------------


def test_lone_one_slip_is_chance():
    """A single one-slip fit on the loose circles_distinct reading is chance, not a hit."""
    null = null_for("taunt", "circles_distinct", "slip")
    d = sr.decision(observed=1, null=null, n_tests=12, alpha=0.05)
    assert d["naive_notable"] is True       # "any fit counts" would have flagged it
    assert d["notable"] is False            # the priced, family-aware rule does not
    assert d["family_expected"] > 1.0       # chance alone makes >1 such fit across the family


def test_planted_signal_is_notable():
    """A count well above the null max survives the Bonferroni correction."""
    null = null_for("persona", "canonical", "slip")  # tiny null (mean ~0.009)
    planted = int(null.max()) + 5
    d = sr.decision(observed=planted, null=null, n_tests=12, alpha=0.05)
    assert d["notable"] is True
    assert d["pval"] < d["alpha_per_test"]


def test_v1_one_slip_all_chance():
    """Every one-slip / homophonic fit actually observed in C1 v1 prices out as chance."""
    observed = [  # (list, reading, key, observed_count) from hypotheses/candidates/z13_phrase_lists_v1_results.json
        ("persona", "circles_distinct", "slip", 1),
        ("taunt", "circles_distinct", "slip", 1),
        ("taunt", "circles_distinct", "homophonic", 2),
        ("vocabcombo", "circles_distinct", "slip", 2),
    ]
    for name, r, key, k in observed:
        d = sr.decision(k, null_for(name, r, key), n_tests=12, alpha=0.05)
        assert d["notable"] is False, f"{name}/{r}/{key} wrongly flagged notable"
        assert d["naive_notable"] is True


def _run():
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for fn in fns:
        fn()
        print(f"ok  {fn.__name__}")
    print(f"\n{len(fns)} passed")


if __name__ == "__main__":
    _run()


def test_price_one_slip_reproduces_committed_pricing():
    """scripts/price_one_slip.py re-derives results/one_slip_pricing/slip_pricing.json byte for byte."""
    import contextlib, io, json, sys
    sys.path.insert(0, str(ROOT / "scripts"))
    spec = importlib.util.spec_from_file_location("price_one_slip", ROOT / "scripts" / "price_one_slip.py")
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    committed = json.loads((mod.OUT / "slip_pricing.json").read_text())
    with contextlib.redirect_stdout(io.StringIO()):
        mod.main()
    again = json.loads((mod.OUT / "slip_pricing.json").read_text())
    assert again == committed
    assert committed["naive_notable_count"] == 4 and committed["priced_notable_count"] == 0
