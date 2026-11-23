import importlib.util
import pathlib
import sys

import numpy as np
import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
_spec = importlib.util.spec_from_file_location("voi", ROOT / "scripts" / "voi.py")
voi = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(voi)


def iso(s):
    m = {}
    return "".join(m.setdefault(c, chr(97 + len(m))) for c in s)


def ref_fits(s, t, mode):  # copied from scripts/candidates.py check(): s = candidate, t = cipher
    if len(s) != len(t):
        return False
    if mode == "simple":
        return iso(s) == iso(t)
    m = {}
    return all(m.setdefault(a, b) == b for a, b in zip(t, s))


def arr(words):
    return np.array([[ord(c) - 65 for c in w] for w in words], dtype=np.uint8)


CASES = [("ABCA", ["HELP", "HELH", "TEST", "ABCA", "ABBA", "XYZX", "QRSQ"]),
         ("ABAB", ["TOTO", "TOTA", "ABAB", "ABAC", "AAAA"]),
         ("AB", ["XY", "XX", "YX"])]


@pytest.mark.parametrize("model", ["simple", "homophonic"])
def test_fit_matches_candidates_semantics(model):
    for cipher, cands in CASES:
        got = voi.fit_mask(arr(cands), voi.structure(cipher, model))
        assert list(got) == [ref_fits(c, cipher, model) for c in cands]
    # homophonic is looser than simple: distinct symbols may share a letter
    assert voi.fit_mask(arr(["XX"]), voi.structure("AB", "homophonic"))[0]
    assert not voi.fit_mask(arr(["XX"]), voi.structure("AB", "simple"))[0]


def test_pin_requires_letter():
    st = voi.structure("ABCA", "homophonic", {"A": "H"})
    assert list(voi.fit_mask(arr(["HELH", "TEST"]), st)) == [True, False]


def test_identity_fact_zero_bits():
    p = voi.sample_passages(6, 50_000, np.random.default_rng(1))
    r = voi.fit_rate("abcdab", "homophonic", 0, None, passages=p)
    b = voi.bits(r, r)
    assert r["fits"] > 0 and b["bits"] == 0 and b["lo"] <= 0 <= b["hi"]


def test_pin_and_merge_positive_split_negative():
    p = voi.sample_passages(6, 100_000, np.random.default_rng(2))
    base = voi.fit_rate("abcdea", "homophonic", 0, None, passages=p)
    pin = voi.fit_rate("abcdea", "homophonic", 0, None, pins={"a": "T"}, passages=p)
    merge = voi.fit_rate("abcdba", "homophonic", 0, None, passages=p)  # e merged into b: extra repeat
    assert voi.bits(base, pin)["bits"] > 0
    m = voi.bits(base, merge)
    assert m["bits"] > 0 and m["lo"] > 0
    # split: removing the repeat of 'a' loosens the constraint
    split = voi.fit_rate("abcde\x00", "homophonic", 0, None, passages=p)
    assert voi.bits(base, split)["bits"] < 0
    # simple model is tighter than homophonic on the same text
    simple = voi.fit_rate("abcdea", "simple", 0, None, passages=p)
    assert voi.bits(base, simple)["bits"] > 0


def test_rule_of_three():
    base = {"fits": 100, "n": 1000, "rate": .1, "lo": .08, "hi": .12}
    zero = {"fits": 0, "n": 1000, "rate": 0.0, "lo": 0.0, "hi": .004}
    assert voi.bits(base, zero)["kind"] == "lower_bound"
    assert voi.bits(zero, base)["kind"] == "upper_bound"


def test_z32_homophonic_base_rate():
    from zbot.cipher import load
    text = load("z32.canonical").text
    r = voi.fit_rate(text, "homophonic", 200_000, np.random.default_rng(0))
    assert r["lo"] <= 1 / 4544 <= r["hi"], r


def test_passages_are_drawn_without_replacement():
    # Resampling the small held-out text with replacement counted ~33k distinct passages
    # over and over (0 of "40M" was really 0 of ~33k). Draws must not repeat a passage.
    pool = voi.all_passages(32)
    assert len(pool) > 500_000
    starts = voi.sample_passages(32, 50_000, np.random.default_rng(3))
    assert len(starts) == 50_000
    assert len(voi.sample_passages(32, 10**9, np.random.default_rng(3))) == len(pool)
