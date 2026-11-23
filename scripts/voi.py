#!/usr/bin/env python3
"""Value-of-information calculator for the Zodiac Z13 / Z32 ciphers.

For a proposed fact (a transcription variant, a symbol merge/split, pinned letters, or a
different key model) it reports how many bits of constraint the fact adds, and optionally
the statistical power of the evaluate test with and without it.

What "bits" means here: bits = log2(rate_base / rate_fact), where rate is the share of
whole-word English passages (every run of whole words with the cipher's length in the full
English corpus, about 700k per length, drawn without replacement) that fit the
cipher under the key model. It measures how much the fact narrows what a random English
message can match. It says nothing about whether the TRUE message obeys the fact. Positive
bits: the fact tightens the constraint; negative bits: it loosens it. Base and fact are
scored on the SAME sampled passages (paired), so the difference is less noisy than the two
rates alone. The interval combines the Wilson 95% bounds of both rates (conservative).
When a count is 0 the rule of three is used (rate < 3/n) and bits are printed as a bound.

Fit semantics are those of scripts/candidates.py check():
  homophonic: positions sharing a cipher symbol share a plaintext letter
  simple:     additionally, distinct symbols have distinct letters
  pins:       SYMBOL=LETTER forces that letter at every position of the symbol

Examples:
  python scripts/voi.py z32 --variant z32.triangles_merged
  python scripts/voi.py z13 --model simple --split 6
  python scripts/voi.py z32 --pin 9=E
  python scripts/voi.py z13 --model simple --vs-model homophonic --json
  python scripts/voi.py z32 --variant z32.tau_distinct --power --controls 20
"""
from __future__ import annotations

import argparse
import json
import math
import pathlib
import sys
import time

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

SPLIT_CHAR = "\x00"  # private symbol for --split


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n <= 0:
        return (0.0, 1.0)
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (max(0.0, c - h), min(1.0, c + h))


_pool: dict | None = None


def _word_pool():
    """All words of the English corpus (training and held-out text). Held-out text alone gives
    only ~33k distinct passages per length, too few for rates near 1e-6, and resampling it
    with replacement would count the same passages again and again."""
    global _pool
    if _pool is None:
        from zbot import lm
        words = []
        for name in lm.CORPORA["en"]:
            raw = (lm.CORPUS_DIR / f"{name}.txt").read_text(encoding="utf-8")
            words += [w for w in (lm.letters_only(t) for t in raw.split()) if w]
        lens = np.array([len(w) for w in words], dtype=np.int64)
        cum = np.concatenate([[0], np.cumsum(lens)])
        letters = np.frombuffer("".join(words).encode("ascii"), dtype=np.uint8) - 65
        _pool = {"cum": cum, "letters": letters.astype(np.uint8), "by_len": {}}
    return _pool


def all_passages(total: int) -> np.ndarray:
    """Every run of whole consecutive corpus words with exactly `total` letters, one per start
    word, as an (m, total) uint8 array (A=0..Z=25). Cached per length."""
    pool = _word_pool()
    if total not in pool["by_len"]:
        cum, letters = pool["cum"], pool["letters"]
        e = cum[:-1] + total
        j = np.searchsorted(cum, e)
        ok = (j < len(cum)) & (cum[np.minimum(j, len(cum) - 1)] == e)
        starts = cum[:-1][ok]
        pool["by_len"][total] = letters[starts[:, None] + np.arange(total, dtype=np.int64)]
    return pool["by_len"][total]


def sample_passages(total: int, n: int | None, rng: np.random.Generator) -> np.ndarray:
    """n passages drawn WITHOUT replacement from all_passages(total); all of them when n is
    None or at least the pool size, so every passage counts once."""
    pool = all_passages(total)
    if n is None or n >= len(pool):
        return pool
    return pool[np.sort(rng.choice(len(pool), size=n, replace=False))]


def structure(cipher_text: str, model: str, pins: dict[str, str] | None = None):
    """Constraint structure: (equal_pairs, unequal_pairs, pinned) over positions."""
    if model not in ("simple", "homophonic"):
        raise ValueError(f"unknown model {model}")
    first: dict[str, int] = {}
    eq = []
    for i, c in enumerate(cipher_text):
        if c in first:
            eq.append((first[c], i))
        else:
            first[c] = i
    reps = list(first.values())
    if model == "simple" and len(reps) > 26:
        raise ValueError(f"simple substitution impossible: {len(reps)} distinct symbols")
    ne = [(a, b) for k, a in enumerate(reps) for b in reps[k + 1:]] if model == "simple" else []
    pinned = []
    for s, l in (pins or {}).items():
        if s not in first:
            raise ValueError(f"pinned symbol {s!r} not in cipher text")
        if not (len(l) == 1 and "A" <= l <= "Z"):
            raise ValueError(f"pin letter must be A-Z, got {l!r}")
        pinned.append((first[s], ord(l) - 65))
    return eq, ne, pinned


def fit_mask(passages: np.ndarray, struct) -> np.ndarray:
    eq, ne, pinned = struct
    m = np.ones(len(passages), dtype=bool)
    for a, b in eq:
        m &= passages[:, a] == passages[:, b]
    for a, b in ne:
        m &= passages[:, a] != passages[:, b]
    for a, v in pinned:
        m &= passages[:, a] == v
    return m


def _result(fits: int, n: int) -> dict:
    lo, hi = wilson(fits, n)
    return {"fits": int(fits), "n": int(n), "rate": fits / n, "lo": lo, "hi": hi}


def fit_rate(cipher_text: str, model: str, n: int, rng, pins=None, passages=None) -> dict:
    """Sample n whole-word English passages of len(cipher_text) letters and count fits.
    `passages` lets callers reuse one sample for several comparisons (paired design)."""
    if passages is None:
        if not isinstance(rng, np.random.Generator):
            rng = np.random.default_rng(rng)
        passages = sample_passages(len(cipher_text), n, rng)
    return _result(int(fit_mask(passages, structure(cipher_text, model, pins)).sum()), len(passages))


def bits(base: dict, fact: dict) -> dict:
    """log2(rate_base/rate_fact) with interval from the Wilson bounds; rule of three at 0."""
    n_b, n_f = base["n"], fact["n"]
    b_lo, b_hi = base["lo"], base["hi"]
    f_lo, f_hi = fact["lo"], fact["hi"]
    if base["fits"] == 0 and fact["fits"] == 0:
        return {"bits": None, "lo": None, "hi": None, "kind": "undetermined"}
    if fact["fits"] == 0:  # fact rate < 3/n: bits are a lower bound
        r = 3 / n_f
        return {"bits": math.log2(base["rate"] / r), "lo": math.log2(b_lo / r), "hi": None, "kind": "lower_bound"}
    if base["fits"] == 0:  # base rate < 3/n: bits are an upper bound
        r = 3 / n_b
        return {"bits": math.log2(r / fact["rate"]), "lo": None, "hi": math.log2(r / f_lo), "kind": "upper_bound"}
    return {"bits": math.log2(base["rate"] / fact["rate"]), "lo": math.log2(b_lo / f_hi),
            "hi": math.log2(b_hi / f_lo), "kind": "estimate"}


def apply_fact(text: str, a) -> str:
    if a.variant:
        from zbot.cipher import load
        if not a.variant.startswith(a.cipher + "."):
            raise SystemExit(f"--variant must be a {a.cipher}.* id")
        text = load(a.variant).text
    if a.merge:
        x, y = a.merge
        if x not in text or y not in text:
            raise SystemExit(f"--merge symbols must both occur in the text {text!r}")
        text = text.replace(y, x)
    if a.split is not None:
        if not 0 <= a.split < len(text):
            raise SystemExit(f"--split position out of range 0..{len(text) - 1}")
        text = text[:a.split] + SPLIT_CHAR + text[a.split + 1:]
    return text


def parse_pins(items) -> dict[str, str]:
    out = {}
    for it in items or []:
        s, sep, l = it.partition("=")
        if not sep or len(s) != 1 or len(l) != 1 or not l.isalpha():
            raise SystemExit(f"bad --pin {it!r}, expected SYMBOL=LETTER")
        out[s] = l.upper()
    return out


def fmt_bits(b: dict) -> str:
    f = lambda x: "?" if x is None else f"{x:+.2f}"
    if b["kind"] == "undetermined":
        return "undetermined (both counts 0; raise -n)"
    if b["kind"] == "lower_bound":
        return f">= {b['bits']:+.2f} (rule of three; interval lower {f(b['lo'])})"
    if b["kind"] == "upper_bound":
        return f"<= {b['bits']:+.2f} (rule of three; interval upper {f(b['hi'])})"
    return f"{b['bits']:+.2f}  [{f(b['lo'])}, {f(b['hi'])}]"


def power_for(cipher: str, model: str, pins, controls: int, nulls: int, workers):
    from zbot import evaluate
    spec = {"id": f"voi.{cipher}.{model}", "cipher": cipher, "model": model,
            "nulls": nulls, "controls": controls, "extend_nulls": 0}
    if pins:
        spec["pins"] = pins
    r = evaluate.run(spec, workers=workers, log=lambda *x: None)
    k = round(r["power"] * controls)
    lo, hi = wilson(k, controls)
    return {"power": r["power"], "controls": controls, "nulls": nulls, "lo": lo, "hi": hi}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="Bits of constraint a proposed fact adds to Z13/Z32 (see module docstring).",
        epilog="--power supports --variant, --pin and --vs-model (evaluate specs can express a "
               "cipher id, pins and a model); --merge/--split cannot be expressed and are refused. "
               "Default n: 200,000 for z32, 1,000,000 for z13 (about 10-30 s each on 12 cores).")
    ap.add_argument("cipher", choices=["z13", "z32"])
    ap.add_argument("--model", choices=["simple", "homophonic"], default=None,
                    help="key model (default: homophonic for z32, simple for z13)")
    ap.add_argument("--variant", help="variant id, e.g. z32.triangles_merged")
    ap.add_argument("--merge", nargs=2, metavar=("A", "B"), help="treat symbols A and B as one")
    ap.add_argument("--split", type=int, metavar="POS", help="symbol at 0-based POS becomes a new distinct symbol")
    ap.add_argument("--pin", action="append", metavar="SYMBOL=LETTER", help="repeatable")
    ap.add_argument("--vs-model", choices=["simple", "homophonic"], help="compare this key model against --model on the same text")
    ap.add_argument("-n", type=int, help="passages to use, drawn without replacement (default: all whole-word passages of the cipher's length, about 700k)")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--json", action="store_true", help="also print JSON")
    ap.add_argument("--power", action="store_true", help="slow: evaluate-based power for base and fact")
    ap.add_argument("--controls", type=int, default=20)
    ap.add_argument("--nulls", type=int, default=19)
    ap.add_argument("--workers", type=int)
    a = ap.parse_args(argv)

    from zbot.cipher import load
    model = a.model or ("simple" if a.cipher == "z13" else "homophonic")
    pins = parse_pins(a.pin)
    if not (a.variant or a.merge or a.split is not None or pins or a.vs_model):
        ap.error("give at least one fact: --variant, --merge, --split, --pin or --vs-model")
    base_text = load(f"{a.cipher}.canonical").text
    fact_text = apply_fact(base_text, a)
    fact_model = a.vs_model or model
    t0 = time.time()
    try:
        sb = structure(base_text, model)
        sf = structure(fact_text, fact_model, pins or None)
    except ValueError as e:
        raise SystemExit(str(e))
    # Same seed for both, so base and fact are scored on the same passages (paired).
    pb = sample_passages(len(base_text), a.n, np.random.default_rng(a.seed))
    pf = pb if len(fact_text) == len(base_text) else \
        sample_passages(len(fact_text), a.n, np.random.default_rng(a.seed))
    kb, kf = int(fit_mask(pb, sb).sum()), int(fit_mask(pf, sf).sum())
    n = len(pb)
    base, fact = _result(kb, len(pb)), _result(kf, len(pf))
    b = bits(base, fact)
    out = {"cipher": a.cipher, "model": model, "fact_model": fact_model, "n": n, "seed": a.seed,
           "fact": {"variant": a.variant, "merge": a.merge, "split": a.split, "pins": pins, "vs_model": a.vs_model},
           "base_text": base_text, "fact_text": fact_text.replace(SPLIT_CHAR, "<new>"),
           "paired": len(base_text) == len(fact_text), "base": base, "with_fact": fact, "bits": b,
           "seconds": round(time.time() - t0, 1)}

    if a.power:
        if a.merge or a.split is not None:
            raise SystemExit("--power cannot express --merge/--split as an evaluate spec")
        fid = a.variant or f"{a.cipher}.canonical"
        out["power"] = {"base": power_for(f"{a.cipher}.canonical", model, None, a.controls, a.nulls, a.workers),
                        "with_fact": power_for(fid, fact_model, pins or None, a.controls, a.nulls, a.workers)}

    print(f"{a.cipher} base: {model} on {base_text}   fact: {fact_model} on {out['fact_text']}"
          f"{' pins=' + str(pins) if pins else ''}   n={n} seed={a.seed}")
    print(f"{'':6}{'fits/n':>20}{'rate':>12}{'95% Wilson':>26}")
    for name, r in (("base", base), ("fact", fact)):
        print(f"{name:6}{str(r['fits']) + '/' + str(r['n']):>20}{r['rate']:>12.3e}{'[%.2e, %.2e]' % (r['lo'], r['hi']):>26}")
    print(f"bits = {fmt_bits(b)}")
    if "power" in out:
        for k, p in out["power"].items():
            print(f"power {k:9} {p['power']:.2f}  [{p['lo']:.2f}, {p['hi']:.2f}]  (controls={p['controls']}, nulls={p['nulls']})")
    if a.json:
        print(json.dumps(out, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
