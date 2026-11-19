"""Load the Zodiac ciphers and their transcription variants.

Transcriptions follow David Oranchak's ASCII convention (see NOTICE.md).
Every cipher is turned into an integer symbol sequence plus grid shape.
"""
from __future__ import annotations

import json
import pathlib
from dataclasses import dataclass, field

import numpy as np

DATA = pathlib.Path(__file__).resolve().parent.parent / "data" / "ciphers"


@dataclass
class Cipher:
    name: str
    text: str                       # ASCII transcription, written order
    rows: list[int]                 # row lengths, written order
    plaintext: str | None = None    # letters, aligned to `text` (written order) when known
    meta: dict = field(default_factory=dict)

    @property
    def symbols(self) -> list[str]:
        return sorted(set(self.text))

    def seq(self) -> np.ndarray:
        idx = {s: i for i, s in enumerate(self.symbols)}
        return np.array([idx[c] for c in self.text], dtype=np.int64)

    def isomorph(self) -> str:
        seen: dict[str, str] = {}
        out = []
        for c in self.text:
            if c not in seen:
                seen[c] = chr(97 + len(seen)) if len(seen) < 26 else chr(65 + len(seen) - 26)
            out.append(seen[c])
        return "".join(out)

    def with_text(self, text: str, name: str | None = None, rows: list[int] | None = None) -> "Cipher":
        return Cipher(name or self.name, text, rows or [len(text)], None, dict(self.meta))


def _json(name: str) -> dict:
    return json.loads((DATA / f"{name}.json").read_text(encoding="utf-8"))


def load(name: str) -> Cipher:
    """name: 'z408', 'z340', 'z13', 'z32', or '<cipher>.<variant>' e.g. 'z13.circles_distinct'."""
    if "." in name:
        base, variant = name.split(".", 1)
        p = DATA / "variants" / f"{base}.{variant}.txt"
        if not p.exists():
            raise KeyError(f"unknown variant {name}; have {variants(base)}")
        text = "".join(l.strip() for l in p.read_text(encoding="utf-8").splitlines()
                       if l.strip() and not l.startswith("#"))
        c = load(base)
        rows = c.rows if len(text) == len(c.text) else [len(text)]
        return Cipher(name, text, rows, None, c.meta)
    d = _json(name)
    rows = d["rows"] if isinstance(d["rows"], list) else json.loads(d["rows"])
    text = "".join(rows)
    pt = None
    meta = {}
    if name == "z408":
        pt = d["plaintext"]
    elif name == "z340":
        # Store the plaintext in written order so it aligns with `text`.
        ro = d["read_order"]
        pt_read = d["plaintext"]
        w = ["?"] * len(text)
        for k, pos in enumerate(ro):
            w[pos] = pt_read[k]
        pt = "".join(w)
        meta["read_order"] = ro
    return Cipher(name.upper(), text, [len(r) for r in rows], pt, meta)


def variants(base: str) -> list[str]:
    return sorted(p.stem for p in (DATA / "variants").glob(f"{base}.*.txt"))


def apply_order(c: Cipher, order: list[int], name: str | None = None) -> Cipher:
    """Re-read cipher in the given order (order[k] = written index of k-th read symbol)."""
    text = "".join(c.text[i] for i in order)
    pt = "".join(c.plaintext[i] for i in order) if c.plaintext else None
    return Cipher(name or c.name, text, [len(text)], pt, dict(c.meta))
