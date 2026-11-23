import json

POISON = {
    "model_list": {"id": "user.model-list", "title": "t", "cipher": "z13", "model": ["simple"]},
    "lang_list": {"id": "user.lang-list", "title": "t", "cipher": "z13", "lang": ["en"]},
    "id_list": {"id": ["user.x"], "title": "t", "cipher": "z13"},
    "families_dict": {"id": "user.families-dict", "title": "t", "cipher": "z13", "families": [{}]},
    "drop_int": {"id": "user.drop-int", "title": "t", "cipher": "z13", "drop_symbols": [1]},
}


def test_malformed_queue_files_are_refused_not_fatal(tmp_path, monkeypatch):
    # One badly typed file in hypotheses/queue/ (committed directly, past the web checks)
    # must be recorded as invalid, not crash every run, report and status call.
    from zbot import hypotheses, runner
    qdir = tmp_path / "hypotheses" / "queue"
    qdir.mkdir(parents=True)
    for name, spec in POISON.items():
        (qdir / f"{name}.json").write_text(json.dumps(spec))
    monkeypatch.setattr(hypotheses, "QUEUE_DIR", qdir)
    monkeypatch.setattr(hypotheses, "ROOT", tmp_path)
    monkeypatch.setattr(runner, "LEDGER", tmp_path / "ledger.jsonl")
    specs = hypotheses.queued()
    assert len(specs) == len(POISON)
    assert all(s.get("invalid") for s in specs), [s["id"] for s in specs if not s.get("invalid")]
    assert all(isinstance(s["id"], str) for s in specs)
    runner.pending()          # must not raise
