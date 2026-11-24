import importlib.util
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("audit", ROOT / "scripts" / "audit_z32_word_orders.py")
audit = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(audit)


def test_pairs_come_from_the_transcription():
    assert audit.repeat_pairs() == [(0, 25), (1, 31), (5, 13)]


def test_pairs_follow_a_given_file(tmp_path):
    f = tmp_path / "c.json"
    f.write_text(json.dumps({"symbols": [{"positions": [0, 3, 5]}, {"positions": [1]}]}))
    assert audit.repeat_pairs(f) == [(0, 3), (0, 5)]


def test_arrangements_dedupe_and_fit_toy_case():
    # words AB, AB: orders collapse, reversals give AB/BA each -> 4 distinct strings
    assert audit.arrangements(["AB", "AB"]) == {"ABAB", "ABBA", "BAAB", "BABA"}
    assert audit.audit(["AB", "AB"], [(0, 2)]) == (4, 2)  # ABAB, ABBA


def test_published_claim_is_one_of_twenty_chance_fits():
    total, fit = audit.audit()
    assert (total, fit) == (23040, 20)
    assert len(audit.PUBLISHED) == 32
    assert audit.fits(audit.PUBLISHED, audit.repeat_pairs())
