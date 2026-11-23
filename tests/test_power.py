"""Power at the alert bar, Gumbel tail fit, Wilson intervals, and the report columns."""
import numpy as np
import pytest

from zbot import evaluate, report
from tests.test_stats import _patch_search


def test_gumbel_fit_recovers_parameters():
    x = np.random.default_rng(1).gumbel(loc=50.0, scale=4.0, size=20000)
    mu, beta = evaluate.gumbel_fit(x)
    assert mu == pytest.approx(50.0, rel=0.1) and beta == pytest.approx(4.0, rel=0.1)


def test_power_at_matches_pooled_on_empirical_path():
    rng = np.random.default_rng(2)
    nulls = rng.normal(0, 1, 999).tolist()
    ctrl = rng.normal(1.5, 1, 50).tolist()
    assert evaluate.power_at(0.05, 3.0, nulls, ctrl) == evaluate.power_pooled(3.0, nulls, ctrl)


def test_power_at_is_monotone_in_alpha():
    rng = np.random.default_rng(3)
    nulls = rng.gumbel(0, 1, 99).tolist()
    ctrl = rng.gumbel(3, 1, 50).tolist()
    assert evaluate.power_at(0.004, 2.0, nulls, ctrl) <= evaluate.power_at(0.05, 2.0, nulls, ctrl)
    assert evaluate.power_at(0.05, None, nulls, ctrl) is None


def test_wilson():
    lo, hi = evaluate.wilson(5, 10)
    assert (round(lo, 3), round(hi, 3)) == (0.237, 0.763)


def test_run_confirmatory_uses_50_controls(monkeypatch):
    _patch_search(monkeypatch, True)
    spec = {"id": "conf.x", "nulls": 19, "extend_nulls": 99}
    out = evaluate.run(spec, workers=1, log=lambda *_: None)
    assert len(out["control_scores"]) == evaluate.CONFIRM_CONTROLS == 50
    assert out["power_ci"] is not None and len(out["power_ci"]) == 2
    assert out["power_alert"] is not None
    assert out["power_alert_alpha"] == pytest.approx(0.05 / evaluate.CONFIRM_FAMILY_GUESS)
    out = evaluate.run({"id": "explore.x", "nulls": 19, "extend_nulls": 99}, workers=1, log=lambda *_: None)
    assert len(out["control_scores"]) == 10
    assert "power_alert" not in out and out["power_ci"] is not None


def _row(i):
    rng = np.random.default_rng(hash(i) % 1000)
    return {"id": i, "p": 0.01, "spec": {"title": "t"}, "real_score": 5.0,
            "null_scores": rng.normal(0, 1, 99).tolist(), "control_scores": rng.normal(4, 1, 50).tolist(),
            "top": [{"plaintext": "x", "order": "o", "score": 1.0}], "verdict": "CANDIDATE SIGNAL: x"}


def test_report_columns(tmp_path, monkeypatch):
    monkeypatch.setattr(report, "OUT", tmp_path / "REPORT.md")
    monkeypatch.setattr(report, "ALERTS", tmp_path / "ALERTS.md")
    old = {"id": "explore.old", "p": 0.2, "power": 0.5, "spec": {}, "top": [], "verdict": "NO SIGNAL: x"}
    rows = [_row("c1"), _row("c2"), _row("explore.e"), old]
    report.write(rows)
    txt = (tmp_path / "REPORT.md").read_text()
    assert "power 95% CI" in txt and "power at alert bar" in txt
    by = {r["id"]: r for r in rows}
    assert by["c1"]["power_alert"] is not None and by["c2"]["power_alert"] is not None
    assert by["explore.e"]["power_alert"] is None and by["explore.old"]["power_alert"] is None
    line = next(l for l in txt.splitlines() if l.startswith("| `explore.old`"))
    assert "| – | – |" in line
