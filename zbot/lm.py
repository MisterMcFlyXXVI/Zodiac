"""Letter n-gram language models (orders 1..5), one per language.

Built from data/corpus/ by `python -m zbot build-lm [--lang ...]`. Stored in
data/lm/ (gitignored, rebuildable). The last HOLDOUT_FRAC of each corpus is
held out: it never enters the n-gram counts and is used to make
positive-control ciphers, so the controls are not text the model memorised.

All languages are reduced to the 26 letters A-Z: accents and Vietnamese tone
marks are stripped (é->E, ñ->N, ơ->O, đ->D), ß->SS. That is how someone
enciphering with Zodiac's symbol set would most likely have written them.
"""
from __future__ import annotations

import hashlib
import pathlib
import re
import unicodedata

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parent.parent
CORPUS_DIR = ROOT / "data" / "corpus"
LM_DIR = ROOT / "data" / "lm"
ORDER = 5
HOLDOUT_FRAC = 0.05
# Dirichlet-style interpolation strength per order (higher = trust lower order more).
BETA = 4.0

# Corpus files and weights per language. English: Brown (1961 American English) is
# closest in era and register to Zodiac's letters, so it counts double.
CORPORA = {
    "en": {"brown": 2, "gutenberg": 1},
    "es": {"es": 1},
    "fr": {"fr": 1},
    "de": {"de": 1},
    "it": {"it": 1},
    "vi": {"vi": 1},
}
LANG_NAMES = {"en": "English", "es": "Spanish", "fr": "French", "de": "German",
              "it": "Italian", "vi": "Vietnamese"}
_SPECIAL = str.maketrans({"ß": "SS", "đ": "D", "Đ": "D", "æ": "AE", "Æ": "AE",
                          "œ": "OE", "Œ": "OE", "ø": "O", "Ø": "O"})


def lm_path(lang: str = "en") -> pathlib.Path:
    return LM_DIR / ("lm5.npz" if lang == "en" else f"lm5_{lang}.npz")


def holdout_path(lang: str = "en") -> pathlib.Path:
    return LM_DIR / ("holdout.txt" if lang == "en" else f"holdout_{lang}.txt")


LM_PATH = lm_path("en")


def letters_only(text: str) -> str:
    text = unicodedata.normalize("NFD", text.translate(_SPECIAL))
    return re.sub(r"[^A-Z]", "", text.upper())


def _to_idx(s: str) -> np.ndarray:
    return np.frombuffer(s.encode("ascii"), dtype=np.uint8).astype(np.int64) - 65


def _counts(seq: np.ndarray, n: int) -> np.ndarray:
    m = len(seq) - n + 1
    code = np.zeros(m, dtype=np.int64)
    for j in range(n):
        code = code * 26 + seq[j : j + m]
    return np.bincount(code, minlength=26**n).astype(np.float64)


def build(check_plaintexts: list[str] | None = None, lang: str = "en") -> dict:
    train_parts, hold_parts = [], []
    for name, w in CORPORA[lang].items():
        p = CORPUS_DIR / f"{name}.txt"
        if not p.exists():
            raise FileNotFoundError(f"{p} missing: run `python scripts/fetch_corpus.py --lang {lang}`")
        s = letters_only(p.read_text(encoding="utf-8"))
        cut = int(len(s) * (1 - HOLDOUT_FRAC))
        train_parts += [s[:cut]] * w
        hold_parts.append(s[cut:])
    train = "".join(train_parts)
    holdout = "".join(hold_parts)

    if check_plaintexts:
        for pt in check_plaintexts:
            for i in range(0, len(pt) - 20, 10):
                if pt[i : i + 20] in train:
                    raise RuntimeError(f"calibration plaintext leaked into corpus: {pt[i:i+20]}")

    seq = _to_idx(train)
    # P1: add-one smoothed unigram.
    c1 = _counts(seq, 1)
    probs = [(c1 + 1) / (c1.sum() + 26)]
    for n in range(2, ORDER + 1):
        cn = _counts(seq, n).reshape(-1, 26)  # rows: context (n-1 letters), cols: next letter
        ctx_tot = cn.sum(axis=1, keepdims=True)
        # lower-order prob indexed by the last n-2 letters of the context
        lower = probs[-1].reshape(-1, 26)
        rep = 26 ** (n - 1) // lower.shape[0]
        lower_full = np.tile(lower, (rep, 1))  # context drops its first letter
        p = (cn + BETA * lower_full) / (ctx_tot + BETA)
        probs.append(p.reshape(-1))
    tables = {f"lp{n}": np.log(probs[n - 1]).astype(np.float32) for n in range(1, ORDER + 1)}
    tables["unigram"] = probs[0].astype(np.float64)
    LM_DIR.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(lm_path(lang), **tables)
    holdout_path(lang).write_text(holdout, encoding="ascii")
    _cache.pop(lang, None)
    _fp.pop(lang, None)
    return tables


_cache: dict[str, dict] = {}
_fp: dict[str, str] = {}


def load(lang: str = "en") -> dict:
    if lang not in _cache:
        p = lm_path(lang)
        if not p.exists():
            raise FileNotFoundError(f"{p} missing: run `python -m zbot build-lm --lang {lang}`")
        z = np.load(p)
        _cache[lang] = {k: z[k] for k in z.files}
    return _cache[lang]


def available() -> list[str]:
    return [l for l in CORPORA if lm_path(l).exists()]


def fingerprint(lang: str = "en") -> str:
    """Hash of the model file: results are only comparable under the same model."""
    if lang not in _fp:
        _fp[lang] = hashlib.sha256(lm_path(lang).read_bytes()).hexdigest()[:12]
    return _fp[lang]


_hold: dict[str, str] = {}


def holdout_text(lang: str = "en") -> str:
    if lang not in _hold:
        _hold[lang] = holdout_path(lang).read_text(encoding="ascii")
    return _hold[lang]


def score_text(text: str, lang: str = "en") -> float:
    """Total log-probability of a letter string (natural log)."""
    t = load(lang)
    x = _to_idx(letters_only(text))
    total = 0.0
    for i in range(len(x)):
        n = min(i + 1, ORDER)
        code = 0
        for j in range(i - n + 1, i + 1):
            code = code * 26 + int(x[j])
        total += float(t[f"lp{n}"][code])
    return total
