import pytest


@pytest.fixture(autouse=True)
def _site_files_to_tmp(tmp_path, monkeypatch):
    """report.write also writes the dashboard's compact files; keep tests from writing them
    into the repository's results/ folder."""
    from zbot import report
    monkeypatch.setattr(report, "SLIM", tmp_path / "ledger_slim.jsonl")
    monkeypatch.setattr(report, "ROWS", tmp_path / "rows")
