"""Tests for scripts/z13_initials_rate.py (does word-initial text fit Z13's repeat pattern more often than running text?)."""
import importlib.util
import pathlib

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("ini", ROOT / "scripts" / "z13_initials_rate.py")
ini = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ini)


def _window(letters_for_class):
    return [letters_for_class[c] for c in ini.ISO]


def test_count_fits_exact_pattern_only():
    good = np.array([_window(list(range(10, 18)))], dtype=np.int16)
    merged = good.copy(); merged[0, 1] = merged[0, 0]          # two classes collapsed: extra equality
    split = good.copy(); split[0, 11] = 99                      # a required repeat broken
    allsame = np.zeros((1, 13), dtype=np.int16)
    assert ini.count_fits(good) == 1
    assert ini.count_fits(merged) == ini.count_fits(split) == ini.count_fits(allsame) == 0
    assert ini.count_fits(np.vstack([good, merged, split])) == 1


def test_pattern_shape():
    assert len(ini.ISO) == ini.L == 13 and len(set(ini.ISO)) == 8
    assert sorted(np.bincount(ini.ISO), reverse=True) == [3, 2, 2, 2, 1, 1, 1, 1]


def test_ci_and_arrays():
    lo, hi = ini.ci(2, 1_000_000)
    assert 0 < lo < 2e-6 < hi
    assert list(ini.to_arr("abz")) == [0, 1, 25]


def test_committed_results_back_pattern_neutral_claim():
    import json
    r = json.loads((ROOT / "results" / "z13_initials_rate" / "results.json").read_text())
    assert (r["initials"]["fits"], r["initials"]["windows"]) == (2, 3107653)
    assert (r["running"]["fits"], r["running"]["windows"]) == (2, 13672048)
    lo, hi = r["initials"]["ci95"]; rlo, rhi = r["running"]["ci95"]
    assert lo < rhi and rlo < hi      # intervals overlap: neutral
