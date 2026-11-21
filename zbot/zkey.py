"""Zodiac's key habits, measured on his two solved ciphers.

HOMOPHONES[L] = most symbols Zodiac gave letter L in Z408 or Z340 (from their true keys).
Measured 2026-11-21 in this repo; he did NOT cycle strictly (a symbol was reused before its
letter's other symbols ~42-44% of the time), so only the key SIZE per letter is used as a
constraint, with one symbol of slack.
"""
from __future__ import annotations

from collections import defaultdict

import numpy as np

from .cipher import apply_order, load

SLACK = 1


def measured() -> dict[str, int]:
    out: dict[str, int] = defaultdict(int)
    z408 = load("z408")
    z340 = load("z340")
    z340r = apply_order(z340, z340.meta["read_order"])
    for text, plain in ((z408.text, z408.plaintext), (z340r.text, z340r.plaintext)):
        hom: dict[str, set] = defaultdict(set)
        for c, p in zip(text, plain):
            if p.isalpha():
                hom[p].add(c)
        for L, v in hom.items():
            out[L] = max(out[L], len(v))
    return dict(out)


_budget: np.ndarray | None = None


def budget() -> np.ndarray:
    """Max distinct symbols per letter (A..Z) allowed under the 'zodiac' key model."""
    global _budget
    if _budget is None:
        m = measured()
        _budget = np.array([m.get(chr(65 + i), 1) + SLACK for i in range(26)], dtype=np.int64)
    return _budget
