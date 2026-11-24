import json
import random

import numpy as np
import pytest

from zbot import anneal, cipher, evaluate, lm, report, transforms


def test_ciphers_load():
    assert cipher.load("z13").text == "AENz0K0M0[NAM"
    assert len(cipher.load("z32").text) == 32
    z408 = cipher.load("z408")
    assert len(z408.text) == len(z408.plaintext) == 408
    z340 = cipher.load("z340")
    ro = cipher.apply_order(z340, z340.meta["read_order"])
    assert ro.plaintext.startswith("IHOPEYOUAREHAVING")
    assert cipher.load("z13.circles_distinct").text != cipher.load("z13").text


@pytest.mark.parametrize("n", [13, 32, 153])
def test_families_are_permutations(n):
    for name in transforms.FAMILIES:
        if name.startswith("columnar7") and n > 40:
            continue
        for label, order in transforms.FAMILIES[name](n):
            assert sorted(order) == list(range(n)), (name, label)


def test_griddec_contains_z340_section1():
    z340 = cipher.load("z340")
    target = z340.meta["read_order"][:153]
    orders = [o for _, o in transforms.grid_decimations(153, shapes=[(9, 17)])]
    assert target in orders


def test_control_scramble_roundtrip():
    rng = random.Random(1)
    plain = "THEQUICKBROWNFOXJUMPSOVERTHELAZYDOG"
    for _, order in transforms.family(["columnar2to6", "decimations", "railfences"], len(plain))[:200]:
        scr = [""] * len(plain)
        for k, w in enumerate(order):
            scr[w] = plain[k]
        assert "".join(scr[i] for i in order) == plain


def test_holm():
    assert report.holm([0.01, 0.04, 0.03]) == pytest.approx([0.03, 0.06, 0.06])


lm_built = pytest.mark.skipif(not lm.LM_PATH.exists(), reason="run `python -m zbot setup` first")


@lm_built
def test_lm_prefers_english():
    assert lm.score_text("THISISTHEZODIACSPEAKING") > lm.score_text("QZXJKVQWPZXJKVQWPZXJKVQ")


@lm_built
def test_solver_recovers_simple_substitution():
    hold = lm.holdout_text()
    plain = hold[1000:1150]
    rng = random.Random(3)
    perm = list(range(26))
    rng.shuffle(perm)
    seq = np.array([perm[ord(c) - 65] for c in plain])
    sol = anneal.solve([seq], 26, restarts=3, iters=200_000, injective=True)[0]
    assert anneal.accuracy(sol.plaintext, plain) > 0.9


@lm_built
@pytest.mark.parametrize("name,model", [("z13", "simple"), ("z13", "homophonic"), ("z32", "homophonic")])
def test_controls_match_real_repeat_profile(name, model):
    texts = evaluate.real_texts({"cipher": name})
    for lang in lm.available():
        plain, c = evaluate._encipher_matching(texts, model, lang, random.Random(0), {})
        assert evaluate.profile(c) == evaluate.profile(texts[0])
        assert len(plain) == len(c)


@lm_built
def test_pinned_symbol_used_in_control():
    texts = evaluate.real_texts({"cipher": "z13"})
    for seed in range(5):
        plain, c = evaluate._encipher_matching(texts, "simple", "en", random.Random(seed), {"A": "A"})
        assert all((p == "A") == (s == "A") for p, s in zip(plain, c))


def test_simple_model_rejected_for_z32():
    with pytest.raises(ValueError):
        evaluate.validate({"id": "x", "cipher": "z32", "model": "simple"})


@lm_built
def test_each_language_prefers_itself():
    samples = {"en": "THEPOLICEWILLNEVERCATCHME", "es": "LAPOLICIANUNCAMEATRAPARA",
               "fr": "LAPOLICENEMATTRAPERAJAMAIS", "de": "DIEPOLIZEIWIRDMICHNIEFANGEN",
               "it": "LAPOLIZIANONMIPRENDERAMAI", "vi": "CANHSATSEKHONGBAOGIOBATDUOCTOI"}
    langs = lm.available()
    for lang in langs:
        t = samples[lang]
        assert max(langs, key=lambda m: lm.score_text(t, m)) == lang


def test_letters_only_strips_accents():
    assert lm.letters_only("Nguyễn Văn Đức, señor, Straße") == "NGUYENVANDUCSENORSTRASSE"


def test_schema_accepts_good_user_spec():
    from zbot import schema
    spec = {"id": "user.test.z13-fr", "title": "Z13 as French", "cipher": "z13", "model": "simple",
            "lang": "fr", "families": ["reverse"], "pins": {"A": "A"}, "nulls": 19}
    assert schema.check(spec) == []


@pytest.mark.parametrize("bad,why", [
    ({"id": "base.z13x", "title": "t", "cipher": "z13"}, "id must"),
    ({"id": "user.bad1", "title": "t", "cipher": "z99"}, "cipher must"),
    ({"id": "user.bad2", "title": "t", "cipher": "z32", "model": "simple"}, "impossible"),
    ({"id": "user.bad3", "title": "t", "cipher": "z13", "nulls": 10_000}, "nulls must"),
    ({"id": "user.bad4", "title": "t", "cipher": "z13", "pins": {"Q": "A"}}, "pins map"),
    ({"id": "user.bad5", "title": "t", "cipher": "z13", "evil": "__import__"}, "unknown fields"),
    ({"id": "user.bad6", "title": "t", "cipher": "z408",
      "families": ["columnar2to6", "columnar7to8_sampled", "griddec", "routes"]}, "more than 2000"),
    ({"id": "user.bad7", "title": "", "cipher": "z13"}, "title is required"),
])
def test_schema_rejects_bad_user_specs(bad, why):
    from zbot import schema
    problems = schema.check(bad)
    assert len(problems) == 1 and why in problems[0], problems


def test_estimate_is_positive():
    from zbot import status
    assert status.estimate_seconds({"id": "x", "cipher": "z13"}) > 0


def test_runner_leaves_long_work_for_next_run(tmp_path, monkeypatch):
    from zbot import runner, status, evaluate
    monkeypatch.setattr(runner, "LEDGER", tmp_path / "ledger.jsonl")
    monkeypatch.setattr(runner, "RESULTS", tmp_path)
    monkeypatch.setattr(runner, "calibrated", lambda lang="en": True)
    monkeypatch.setattr(runner, "_publish", lambda current=None: None)
    specs = iter([{"id": "a", "title": "a", "cipher": "z13"}, {"id": "b", "title": "b", "cipher": "z13"}])
    monkeypatch.setattr(runner, "next_spec", lambda: next(specs))
    import time as _time
    clock = {"t": 1_000_000.0}
    fake = type("T", (), {"time": staticmethod(lambda: clock["t"]),
                          "strftime": staticmethod(_time.strftime), "gmtime": staticmethod(_time.gmtime)})
    monkeypatch.setattr(runner, "time", fake)
    ran = []

    def fake_run(spec, **k):
        ran.append(spec["id"])
        clock["t"] += 1800                       # each test takes 30 min
        return {"id": spec["id"], "spec_hash": "h", "verdict": "NO SIGNAL", "p": 0.5, "power": 0.5}

    monkeypatch.setattr(evaluate, "run", fake_run)
    monkeypatch.setattr(status, "estimate_seconds", lambda spec: 1800.0)   # estimated 30 min each
    runner.run(hours=1.0, log=lambda *a: None)                          # 60 min budget
    # After "a", 30 min are left; "b" needs 30 min x 1.5 margin, so it waits for the next run.
    assert ran == ["a"]


words_built = pytest.mark.skipif(not (lm.LM_PATH.parent / "words_en.npz").exists(), reason="run `python -m zbot setup`")


@words_built
def test_word_segmentation_prefers_real_words():
    from zbot import words
    good, seg = words.segment("INTHEDESERTIS")
    assert seg == ["IN", "THE", "DESERT", "IS"]
    assert good > words.segment("QXZJVKWPQXZJV")[0] + 30


@words_built
def test_numba_word_score_matches_reference():
    from zbot import words
    t = words.load()
    text = "ILIKEKILLINGPEOPLE"
    seq = np.array([ord(c) - 65 for c in text])
    key = np.arange(26)
    got = anneal._wordseg(key, seq, np.array([0]), np.array([len(text)]), t["children"], t["wscore"],
                          -8.0, 0.0, np.zeros(len(text) + 1))
    assert got == pytest.approx(words.segment(text, unk=-8.0)[0], abs=1e-3)


def test_zodiac_vocab_excludes_z408_solution():
    from zbot import words
    if not words.LETTERS_DIR.exists():
        pytest.skip("letters not fetched")
    assert all(p.name != "1969-07-31-cipher.txt" for p in words.zodiac_files())
    a, b = set(words.zodiac_files("A")), set(words.zodiac_files("B"))
    assert a and b and not (a & b)


def test_schema_scorer_must_be_offered():
    from zbot import schema
    ok = {"id": "user.words-z32", "title": "t", "cipher": "z32", "scorer": schema.SCORERS["words"]["config"]}
    assert schema.check(ok) == []
    assert schema.check(dict(ok, scorer={"words": 99.0}))
    assert schema.check(dict(ok, lang="fr"))


def test_exploration_never_repeats_a_test(tmp_path, monkeypatch):
    from zbot import runner, hypotheses
    monkeypatch.setattr(runner, "LEDGER", tmp_path / "ledger.jsonl")
    monkeypatch.setattr(runner, "pending", lambda: [])
    done = []
    for _ in range(30):
        spec = runner.next_spec()
        assert runner._content(spec) not in {runner._content(d) for d in done}
        done.append(spec)
        with runner.LEDGER.open("a") as f:
            f.write(json.dumps({"id": spec["id"], "spec": spec, "spec_hash": "x"}) + "\n")


def test_holm_family_excludes_untestable():
    from zbot import report
    rows = [{"id": "good", "p": 0.01, "power": 0.6, "verdict": "NO SIGNAL", "spec": {}},
            {"id": "blind", "p": 0.02, "power": 0.05, "verdict": "UNTESTABLE", "spec": {}}]
    report.write.__globals__["OUT"]  # module loads
    fam = [r for r in rows if r["power"] >= report.MIN_POWER]
    assert [r["id"] for r in fam] == ["good"]


def test_exploration_continues_past_skipped_numbers():
    # Reproduces the stall of 2026-11-23: idea numbers that repeat an earlier test are
    # skipped, so the ledger held ~600 exploration rows numbered up to 1149. A scan starting
    # at the row count saw only old work and the bot stopped; it must start after 1149.
    from zbot import runner, hypotheses
    rows, seen = [], set()
    for k in range(1150):
        spec = hypotheses.explore(k)
        if runner._content(spec) not in seen:
            seen.add(runner._content(spec))
            rows.append({"id": spec["id"], "spec": spec})
    n = len(rows)
    assert all(runner._content(hypotheses.explore(k)) in seen for k in range(n, n + 500))
    spec = runner.next_explore(rows)
    assert spec is not None and int(spec["id"].split(".")[1]) >= 1150
    assert runner._content(spec) not in seen


def test_run_reports_idle_and_cli_exits_3(tmp_path, monkeypatch):
    from zbot import runner, __main__ as cli
    monkeypatch.setattr(runner, "LEDGER", tmp_path / "ledger.jsonl")
    monkeypatch.setattr(runner, "next_spec", lambda: None)
    assert runner.run(hours=1.0, log=lambda *a: None) == "idle"
    with pytest.raises(SystemExit) as e:
        cli.main(["run", "--hours", "0.01"])
    assert e.value.code == cli.IDLE_EXIT == 3


def test_site_files_are_compact(tmp_path, monkeypatch):
    from zbot import report
    monkeypatch.setattr(report, "SLIM", tmp_path / "ledger_slim.jsonl")
    monkeypatch.setattr(report, "ROWS", tmp_path / "rows")
    rows = [{"id": "explore.1.z32.columnar10", "p": 0.5, "power": 0.3, "verdict": "NO SIGNAL",
             "null_scores": [1.0] * 999, "control_scores": [2.0] * 50, "top": [{"plaintext": "A"}] * 10,
             "spec": {"id": "explore.1.z32.columnar10", "explore_columnar": {"width": 10, "perms": [list(range(10))] * 60}}}]
    report.write_site_files(rows)
    slim = json.loads((tmp_path / "ledger_slim.jsonl").read_text())
    assert "null_scores" not in slim and len(slim["top"]) == 1
    assert slim["spec"]["explore_columnar"] == {"width": 10, "keys": 60} and slim["n_nulls"] == 999
    full = json.loads((tmp_path / "rows" / "explore.1.z32.columnar10.json").read_text())
    assert len(full["null_scores"]) == 999
