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
