"""English word model for word-level scoring (dictionary segmentation).

Frequencies: Peter Norvig's count_1w.txt (Google Web 1T unigrams; fetched by
scripts/fetch_corpus.py, md5 1710e1aa36917a32ba8cee42acf8af4f). Web counts contain junk
tokens, so only words that also occur in the TRAINING part of the English corpus are kept.
The held-out part (used to make positive-control ciphers) is deliberately excluded, so the
controls don't get words the dictionary was built from them: that would overstate power.

Stored as a trie in flat arrays so the numba solver can walk it:
  children[node, letter] -> child node or -1
  wscore[node]           -> log P(word) if a word ends here, else -inf
"""
from __future__ import annotations

import math
import pathlib
import re

import numpy as np

from . import lm

ROOT = pathlib.Path(__file__).resolve().parent.parent
COUNTS = ROOT / "data" / "corpus" / "count_1w.txt"
OUT = ROOT / "data" / "lm" / "words_en.npz"
MAX_WORDS = 60_000
MAX_LEN = 18


def _training_vocab() -> set[str]:
    vocab: set[str] = set()
    for name in lm.CORPORA["en"]:
        raw = (lm.CORPUS_DIR / f"{name}.txt").read_text(encoding="utf-8")
        cut = int(len(raw) * (1 - lm.HOLDOUT_FRAC))  # same proportion as the letter model
        vocab.update(re.findall(r"[a-z]+", raw[:cut].lower()))
    return vocab


def build() -> dict:
    vocab = _training_vocab()
    rows = []
    for line in COUNTS.read_text().splitlines():
        w, c = line.split("\t")
        if not w.isalpha() or len(w) > MAX_LEN or w not in vocab:
            continue
        if len(w) == 1 and w not in ("a", "i"):
            continue
        rows.append((w.upper(), int(c)))
        if len(rows) >= MAX_WORDS:
            break
    total = sum(c for _, c in rows)
    nodes = [[-1] * 26]
    score = [-math.inf]
    for w, c in rows:
        n = 0
        for ch in w:
            k = ord(ch) - 65
            if nodes[n][k] < 0:
                nodes[n][k] = len(nodes)
                nodes.append([-1] * 26)
                score.append(-math.inf)
            n = nodes[n][k]
        score[n] = math.log(c / total)
    arrays = {"children": np.array(nodes, dtype=np.int32), "wscore": np.array(score, dtype=np.float32),
              "nwords": np.array(len(rows))}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(OUT, **arrays)
    _cache.clear()
    return arrays


_cache: dict = {}

LETTERS_DIR = ROOT / "data" / "corpus" / "zodiac_letters"
SOLUTION_FILES = {"1969-07-31-cipher.txt"}  # holds the Z408 plaintext; no file holds the Z340 one
RARE_LOGP = math.log(1e-8)  # base probability for a Zodiac word missing from the web counts


def zodiac_files(fold: str = "all") -> list[pathlib.Path]:
    """Letter transcriptions, split into two folds by alternating date order.

    fold 'A' builds the vocabulary when measuring power; fold 'B' supplies the test texts,
    so the measurement never grades the prior on the text it was built from.
    """
    # The solved ciphers' plaintexts are excluded: with them, the Z408 calibration would be
    # graded on words the prior was given.
    files = sorted(p for p in LETTERS_DIR.glob("*.txt") if p.name not in SOLUTION_FILES)
    if fold == "A":
        return files[0::2]
    if fold == "B":
        return files[1::2]
    return files


def zodiac_text(fold: str = "all") -> str:
    return "\n".join(p.read_text(encoding="utf-8", errors="replace") for p in zodiac_files(fold))


def zodiac_vocab(fold: str = "all") -> set[str]:
    words = re.findall(r"[a-z]+", zodiac_text(fold).lower().replace("'", ""))
    return {w.upper() for w in words if len(w) > 1 or w in ("a", "i")}


def _with_boost(base: dict, boost: float, fold: str) -> dict:
    """Copy of the trie where Zodiac's own words get +boost (and his misspellings exist)."""
    children = base["children"].copy()
    wscore = base["wscore"].copy()
    extra_nodes: list[np.ndarray] = []
    extra_scores: list[float] = []

    def node_for(word: str) -> int:
        n = 0
        for ch in word:
            k = ord(ch) - 65
            nxt = children[n, k] if n < children.shape[0] else extra_nodes[n - children.shape[0]][k]
            if nxt < 0:
                nxt = children.shape[0] + len(extra_nodes)
                extra_nodes.append(np.full(26, -1, dtype=np.int32))
                extra_scores.append(-np.inf)
                if n < children.shape[0]:
                    children[n, k] = nxt
                else:
                    extra_nodes[n - children.shape[0]][k] = nxt
            n = nxt
        return n

    for w in zodiac_vocab(fold):
        if len(w) > MAX_LEN:
            continue
        n = node_for(w)
        if n < wscore.shape[0]:
            base_score = wscore[n] if wscore[n] > -np.inf else RARE_LOGP
            wscore[n] = base_score + boost
        else:
            extra_scores[n - wscore.shape[0]] = RARE_LOGP + boost
    if extra_nodes:
        children = np.vstack([children, np.stack(extra_nodes)])
        wscore = np.concatenate([wscore, np.array(extra_scores, dtype=np.float32)])
    return {"children": children, "wscore": wscore.astype(np.float32)}


def load(boost: float = 0.0, fold: str = "all") -> dict:
    """The English word trie; with boost > 0, Zodiac's own vocabulary is favoured."""
    if "base" not in _cache:
        if not OUT.exists():
            raise FileNotFoundError(f"{OUT} missing: run `python -m zbot build-lm`")
        z = np.load(OUT)
        _cache["base"] = {k: z[k] for k in z.files}
    if boost <= 0:
        return _cache["base"]
    key = (boost, fold)
    if key not in _cache:
        _cache[key] = _with_boost(_cache["base"], boost, fold)
    return _cache[key]


def segment(text: str, unk: float = -8.0) -> tuple[float, list[str]]:
    """Best segmentation of an A-Z string (python reference, for reports and tests)."""
    t = load()
    ch, ws = t["children"], t["wscore"]
    n = len(text)
    best = [-math.inf] * (n + 1)
    back: list[tuple[int, bool]] = [(0, False)] * (n + 1)
    best[0] = 0.0
    for j in range(n):
        if best[j] == -math.inf:
            continue
        if best[j] + unk > best[j + 1]:
            best[j + 1], back[j + 1] = best[j] + unk, (j, False)
        node = 0
        for i in range(j, min(n, j + MAX_LEN)):
            node = ch[node, ord(text[i]) - 65]
            if node < 0:
                break
            if ws[node] > -math.inf and best[j] + ws[node] > best[i + 1]:
                best[i + 1], back[i + 1] = best[j] + float(ws[node]), (j, True)
    out, i = [], n
    while i > 0:
        j, isword = back[i]
        out.append(text[j:i] if isword else text[j:i].lower())
        i = j
    return best[n], out[::-1]
