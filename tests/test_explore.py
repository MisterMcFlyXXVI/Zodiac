import pytest

from zbot import evaluate, runner

SPEC = {"id": "explore.1.test", "title": "t", "cipher": "z13"}


def _fake(power, calls):
    def run(spec, workers=None, log=print):
        calls.append(spec)
        return {"id": spec["id"], "power": power, "p": 0.5, "verdict": "x"}
    return run


def test_weak_pilot_is_untestable(monkeypatch):
    calls = []
    monkeypatch.setattr(evaluate, "run", _fake(5 / 20, calls))
    res = runner._run(SPEC, None, print)
    assert len(calls) == 1 and calls[0]["controls"] == 20
    assert res["pilot"] is True and res["verdict"].startswith("UNTESTABLE: power pilot (20 genuine-text tests)")
    assert "lower bound" in res["verdict"]


def test_strong_pilot_runs_full_test(monkeypatch):
    calls = []
    monkeypatch.setattr(evaluate, "run", _fake(12 / 20, calls))
    res = runner._run(SPEC, None, print)
    assert len(calls) == 2 and calls[1] == SPEC
    assert "pilot" not in res


def test_pilot_controls_and_wilson():
    assert runner.PILOT["controls"] == 20
    assert runner.wilson(5, 20)[0] == pytest.approx(0.112, abs=0.005)
    assert runner.wilson(12, 20)[0] == pytest.approx(0.387, abs=0.005)


def test_pause_file(monkeypatch, tmp_path):
    monkeypatch.setattr(runner, "ROOT", tmp_path)
    monkeypatch.setattr(runner, "pending", lambda: [])
    monkeypatch.setattr(runner, "ledger", lambda: [])
    assert runner.next_spec() is not None  # no file: exploration spec
    (tmp_path / "hypotheses").mkdir()
    (tmp_path / "hypotheses" / "EXPLORE_PAUSED").write_text("")
    assert runner.next_spec() is None
    monkeypatch.setattr(runner, "RESULTS", tmp_path / "res")
    monkeypatch.setattr(runner, "LEDGER", tmp_path / "res" / "ledger.jsonl")
    logs = []
    assert runner.run(1, log=logs.append) == "idle"
    assert sum("paused" in l for l in logs) == 1
