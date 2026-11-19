"""Letter n-gram language model (orders 1..5) with interpolated smoothing.

Built from data/corpus/*.txt by `python -m zbot build-lm`. Stored as one
.npz in data/lm/ (gitignored, rebuildable). The last HOLDOUT_FRAC of each
corpus is held out: it never enters the n-gram counts and is used to make
positive-control ciphers, so the controls are not text the model memorised.
"""
from __future__ import annotations

import hashlib
import pathlib
import re

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parent.parent
CORPUS_DIR = ROOT / "data" / "corpus"
LM_PATH = ROOT / "data" / "lm" / "lm5.npz"
HOLDOUT_PATH = ROOT / "data" / "lm" / "holdout.txt"
ORDER = 5
HOLDOUT_FRAC = 0.05
# Corpus weights: Brown (1961 American English) is the closest in era and
# register to Zodiac's letters, so it counts double.
WEIGHTS = {"brown": 2, "gutenberg": 1}
# Dirichlet-style interpolation strength per order (higher = trust lower order more).
BETA = 4.0


def letters_only(text: str) -> str:
    return re.sub(r"[^A-Z]", "", text.upper())


def _to_idx(s: str) -> np.ndarray:
    return np.frombuffer(s.encode("ascii"), dtype=np.uint8).astype(np.int64) - 65


def _counts(seq: np.ndarray, n: int) -> np.ndarray:
    m = len(seq) - n + 1
    code = np.zeros(m, dtype=np.int64)
    for j in range(n):
        code = code * 26 + seq[j : j + m]
    return np.bincount(code, minlength=26**n).astype(np.float64)


def build(check_plaintexts: list[str] | None = None) -> dict:
    train_parts, hold_parts = [], []
    for name, w in WEIGHTS.items():
        p = CORPUS_DIR / f"{name}.txt"
        if not p.exists():
            raise FileNotFoundError(f"{p} missing: run `python scripts/fetch_corpus.py`")
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
    LM_PATH.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(LM_PATH, **tables)
    HOLDOUT_PATH.write_text(holdout, encoding="ascii")
    return tables


_cache: dict | None = None


def load() -> dict:
    global _cache
    if _cache is None:
        if not LM_PATH.exists():
            raise FileNotFoundError(f"{LM_PATH} missing: run `python -m zbot build-lm`")
        z = np.load(LM_PATH)
        _cache = {k: z[k] for k in z.files}
    return _cache


def fingerprint() -> str:
    """Hash of the model file: results are only comparable under the same model."""
    h = hashlib.sha256(LM_PATH.read_bytes()).hexdigest()
    return h[:12]


def holdout_text() -> str:
    return HOLDOUT_PATH.read_text(encoding="ascii")


def score_text(text: str) -> float:
    """Total log-probability of a letter string (natural log)."""
    t = load()
    x = _to_idx(letters_only(text))
    total = 0.0
    for i in range(len(x)):
        n = min(i + 1, ORDER)
        code = 0
        for j in range(i - n + 1, i + 1):
            code = code * 26 + int(x[j])
        total += float(t[f"lp{n}"][code])
    return total
