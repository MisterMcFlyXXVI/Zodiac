import json
import subprocess

import pytest

SPEC = {"id": "user.test-one", "title": "t", "cipher": "z13", "model": "simple", "lang": "en"}


def _git(repo, *args):
    return subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True, text=True).stdout.strip()


@pytest.fixture
def env(tmp_path, monkeypatch):
    from zbot import evaluate, hypotheses, lm, runner
    repo = tmp_path / "repo"
    qdir = repo / "hypotheses" / "queue"
    qdir.mkdir(parents=True)
    _git(repo, "init", "-q")
    _git(repo, "config", "user.email", "t@example.com")
    _git(repo, "config", "user.name", "t")
    _git(repo, "config", "commit.gpgsign", "false")
    monkeypatch.delenv("ZBOT_ALLOW_UNREGISTERED", raising=False)
    monkeypatch.setattr(runner, "ROOT", repo)
    monkeypatch.setattr(hypotheses, "ROOT", repo)
    monkeypatch.setattr(hypotheses, "QUEUE_DIR", qdir)
    monkeypatch.setattr(hypotheses, "builtin", lambda: [])
    monkeypatch.setattr(runner, "LEDGER", tmp_path / "ledger.jsonl")
    monkeypatch.setattr(runner, "RESULTS", tmp_path)
    monkeypatch.setattr(runner, "calibrated", lambda lang="en": True)
    monkeypatch.setattr(runner, "_publish", lambda current=None: None)
    monkeypatch.setattr(runner, "next_explore", lambda rows: None)
    calls = []

    def fake_run(spec, workers, log):
        calls.append(spec["id"])
        assert len(calls) < 20, "runner looped on the same spec"
        return {"id": spec["id"], "spec_hash": evaluate._spec_hash(spec), "spec": spec,
                "lang": "en", "lm": lm.fingerprint("en"), "verdict": "NO SIGNAL", "p": 0.5, "power": 0.5}

    monkeypatch.setattr(runner, "_run", fake_run)
    path = qdir / "t1.json"
    path.write_text(json.dumps(SPEC))
    return type("E", (), {"repo": repo, "path": path, "calls": calls, "runner": runner,
                          "msgs": [], "commit": staticmethod(lambda: (_git(repo, "add", "-A"), _git(repo, "commit", "-qm", "x")))})


def _run(e):
    return e.runner.run(hours=0.01, log=e.msgs.append)


def test_uncommitted_spec_not_run(env):
    assert _run(env) == "idle"
    assert env.calls == []
    assert env.runner.ledger() == []
    assert any("not registered" in m for m in env.msgs)


def test_committed_spec_runs_and_records_commit(env):
    env.commit()
    _run(env)
    assert env.calls == ["user.test-one"]
    row = env.runner.ledger()[0]
    assert row["registered"]["commit"] == _git(env.repo, "rev-parse", "HEAD")
    assert row["registered"]["path"] == "hypotheses/queue/t1.json"
    assert row["registered"]["committed_at"]


def test_picked_up_after_commit_in_later_run(env):
    assert _run(env) == "idle"
    env.commit()
    _run(env)
    assert env.calls == ["user.test-one"]


def test_modified_after_commit_not_run(env):
    env.commit()
    env.path.write_text(json.dumps(dict(SPEC, model="homophonic")))
    assert _run(env) == "idle"
    assert env.calls == [] and env.runner.ledger() == []


def test_staged_change_not_run(env):
    env.commit()
    env.path.write_text(json.dumps(dict(SPEC, model="homophonic")))
    _git(env.repo, "add", "-A")
    assert _run(env) == "idle"
    assert env.calls == []


def test_override_env_var(env, monkeypatch):
    monkeypatch.setenv("ZBOT_ALLOW_UNREGISTERED", "1")
    _run(env)
    assert env.calls == ["user.test-one"]
    assert env.runner.ledger()[0]["registered"] == {"override": True}


def test_exploration_needs_no_registration(env, monkeypatch):
    env.path.unlink()
    ex = {"id": "explore.0.x", "title": "e", "cipher": "z13", "model": "simple", "lang": "en"}
    queue = [ex]
    monkeypatch.setattr(env.runner, "next_explore", lambda rows: queue.pop() if queue else None)
    _run(env)
    assert env.calls == ["explore.0.x"]
    assert env.runner.ledger()[0]["registered"] is None
