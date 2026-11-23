"""Tiers, pooled power, and adaptive nulls."""
import numpy as np
import pytest

from zbot import evaluate, report


def _row(i, p, power, prefix=""):
    return {"id": f"{prefix}{i}", "p": p, "power": power, "spec": {"title": "t"},
            "top": [{"plaintext": "x", "order": "o", "score": 1.0}], "verdict": "CANDIDATE SIGNAL: x"}


def _write(tmp_path, monkeypatch, rows):
    monkeypatch.setattr(report, "OUT", tmp_path / "REPORT.md")
    monkeypatch.setattr(report, "ALERTS", tmp_path / "ALERTS.md")
    report.write(rows)
    return (tmp_path / "ALERTS.md").read_text(), (tmp_path / "REPORT.md").read_text()


def test_exploratory_never_enters_confirmatory_family_or_alerts(tmp_path, monkeypatch):
    rows = [_row(i, 0.0001, 0.9, "explore.") for i in range(5)] + [_row("c1", 0.5, 0.9)]
    alerts, rpt = _write(tmp_path, monkeypatch, rows)
    assert alerts.startswith("# Alerts") and "## " not in alerts
    by = {r["id"]: r for r in rows}
    assert by["c1"]["p_holm"] == 0.5  # family of one: exploration did not enter
    assert by["explore.0"]["p_holm"] == 5 * 0.0001
    assert "screening only" in rpt and "| tier |" in rpt


def test_confirmatory_alert_fires_with_999_nulls(tmp_path, monkeypatch):
    rows = [_row(f"c{i}", 0.5, 0.9) for i in range(11)] + [_row("hit", 1 / 1000, 0.6)]
    alerts, _ = _write(tmp_path, monkeypatch, rows)
    assert "## hit" in alerts and "## c0" not in alerts


def test_power_pooled_hand_value_and_differs_when_real_is_max():
    nulls = [0.0, 1.0, 2.0, 3.0]
    controls = [2.5, 3.5, 4.5, 5.5]
    # pooled {0,1,2,3,10}: q95 = 3 + 0.8*(10-3) = 8.6 ; none above
    assert evaluate.power_pooled(10.0, nulls, controls) == 0.0
    # nulls-only q95 = 2 + 0.85*1 = 2.85 -> 3 of 4 controls above
    assert float(np.quantile(nulls, 0.95)) == pytest.approx(2.85)
    assert sum(c > 2.85 for c in controls) / 4 == 0.75
    # real in the middle of the nulls: pooled {0,1,1.5,2,3}: q95 = 2 + 0.8*1 = 2.8
    assert evaluate.power_pooled(1.5, nulls, controls) == 0.75
    assert evaluate.power_pooled(1.5, nulls, []) is None


def _patch_search(monkeypatch, real_beats):
    monkeypatch.setattr(evaluate, "validate", lambda s: None)
    monkeypatch.setattr(evaluate, "real_texts", lambda s: ["ABCD"])
    monkeypatch.setattr(evaluate, "family_for", lambda s, n: [("id", [0])])
    monkeypatch.setattr(evaluate, "pin_sets", lambda s: [None])
    monkeypatch.setattr(evaluate, "lang_of", lambda s: "en")
    monkeypatch.setattr(evaluate.lm, "fingerprint", lambda l: "fp")
    calls = []

    def fake(args):
        kind, j, texts, spec, seed = args
        if kind == "real":
            return kind, j, 100.0, {"top": [(100.0, "id", "AB")], "dom": 1.0}, 0.0
        if kind == "null":
            calls.append((j, seed))
            # nulls beat real from index 3 on when real_beats is False
            sc = 0.0 if real_beats or j < 3 else 200.0
            return kind, j, sc, {"dom": 0.0}, 0.0
        return kind, j, 150.0, {"truth_order": "id", "recovery": 0.5, "dom": 2.0}, 0.0

    monkeypatch.setattr(evaluate, "_task", fake)
    return calls


def _spec(i):
    return {"id": i, "nulls": 19, "extend_nulls": 99, "controls": 2}


def test_adaptive_nulls(monkeypatch):
    calls = _patch_search(monkeypatch, True)
    out = evaluate.run(_spec("conf.a"), workers=1, log=lambda *_: None)
    assert len(out["null_scores"]) == 999 and out["p"] == 1 / 1000
    assert out["power_basis"] == "pooled"
    base = int(evaluate._spec_hash(_spec("conf.a")), 16) % 10**6
    assert sorted(calls) == [(j, base + 1 + j) for j in range(999)]
    calls.clear()
    out = evaluate.run(_spec("explore.a"), workers=1, log=lambda *_: None)
    assert len(out["null_scores"]) == 99


def _beaten_by(monkeypatch, winners):
    """Nulls whose index is in `winners` score above the real cipher."""
    _patch_search(monkeypatch, True)
    inner = evaluate._task

    def fake(args):
        kind, j, *_ = args
        if kind == "null" and j in winners:
            return kind, j, 200.0, {"dom": 0.0}, 0.0
        return inner(args)

    monkeypatch.setattr(evaluate, "_task", fake)


def test_adaptive_nulls_skip_results_that_are_not_significant(monkeypatch):
    # 4 of 19 nulls beat real: p=0.25, nowhere near significant, so no extra nulls at all.
    _beaten_by(monkeypatch, {0, 1, 2, 3})
    out = evaluate.run(_spec("conf.b"), workers=1, log=lambda *_: None)
    assert len(out["null_scores"]) == 19


def test_adaptive_nulls_stop_at_first_stage_with_five_exceedances(monkeypatch):
    # p=0.05 at 19 nulls -> 99 (p=0.02) -> 499, where the 5th exceedance appears: stop there.
    _beaten_by(monkeypatch, {25, 120, 300, 450, 480})
    out = evaluate.run(_spec("conf.c"), workers=1, log=lambda *_: None)
    assert len(out["null_scores"]) == 499
    assert out["p"] == 6 / 500
    assert sum(s >= out["real_score"] for s in out["null_scores"]) == 5


def test_adaptive_nulls_respect_the_time_cap(monkeypatch):
    # Nulls that take 100 s each: 480 more would take ~13 h on one worker, so the run stops
    # at 99 nulls and says so instead of running into the job's time limit.
    _patch_search(monkeypatch, True)
    inner = evaluate._task

    def slow(args):
        r = inner(args)
        return (*r[:4], 100.0) if args[0] == "null" else r

    monkeypatch.setattr(evaluate, "_task", slow)
    out = evaluate.run(_spec("conf.d"), workers=1, log=lambda *_: None)
    assert len(out["null_scores"]) == 99 and out["nulls_capped"] is True
