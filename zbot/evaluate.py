"""Run one hypothesis end to end: real cipher, null ciphers, positive controls.

For a hypothesis H (cipher + transcription choice + read-order family +
key model + optional pins) we compute:

* real   - best score over the whole family on the real cipher.
* nulls  - the same search on the real cipher's symbols shuffled into a
           random order. This keeps the symbol counts and destroys any
           structure. p = (1 + #nulls >= real) / (1 + #nulls).
* controls - held-out English of the same length, enciphered under H's
           model and scrambled by a random member of H's family, then
           searched exactly like the real cipher. power = share of
           controls scoring above the nulls' 95th percentile. Low power
           means H cannot be tested at this length, whatever the result.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import random
import time
from concurrent.futures import ProcessPoolExecutor

import numpy as np

from . import anneal, lm, transforms
from .cipher import load as load_cipher

def _spec_hash(spec: dict) -> str:
    return hashlib.sha256(json.dumps(spec, sort_keys=True).encode()).hexdigest()[:10]


def real_texts(spec: dict) -> list[str]:
    names = spec["cipher"] if isinstance(spec["cipher"], list) else [spec["cipher"]]
    out = []
    for n in names:
        t = load_cipher(n).text
        for d in spec.get("drop_symbols", []):
            t = t.replace(d, "")
        out.append(t)
    return out


def family_for(spec: dict, n: int):
    ec = spec.get("explore_columnar")
    if ec:
        w = ec["width"]
        return [(f"columnar{w}:{'-'.join(map(str, p))}", transforms.columnar(n, w, tuple(p)))
                for p in ec["perms"]]
    return transforms.family(spec.get("families", ["identity"]), n)


def pin_sets(spec: dict) -> list[dict[str, str]]:
    if "pin_family" in spec:
        return spec["pin_family"]
    return [spec.get("pins", {})]


def _search(texts: list[str], spec: dict, seed: int, keep: int = 0):
    """Best score over family x pin sets for one instance. Returns (score, top list)."""
    alphabet = sorted(set("".join(texts)))
    idx = {s: i for i, s in enumerate(alphabet)}
    fams = [family_for(spec, len(t)) for t in texts]
    joint = len(texts) > 1
    if joint and any(len(f) > 1 for f in fams):
        raise ValueError("read-order families are only supported for single-cipher hypotheses")
    best = -math.inf
    top: list[tuple[float, str, str]] = []
    for pins in pin_sets(spec):
        pin_idx = {idx[s]: ord(l) - 65 for s, l in pins.items() if s in idx}
        for label, order in fams[0]:
            segs = []
            for ti, t in enumerate(texts):
                o = order if ti == 0 else list(range(len(t)))
                segs.append(np.array([idx[t[i]] for i in o], dtype=np.int64))
            sols = anneal.solve(segs, len(alphabet), restarts=spec.get("restarts", 4),
                                iters=spec.get("iters"), injective=spec.get("model") == "simple",
                                pins=pin_idx, klw=spec.get("klw", 1.0), seed=seed)
            s = sols[0]
            if s.score > best:
                best = s.score
            if keep:
                tag = label + (f" pins={pins}" if pins else "")
                top.append((s.score, tag, s.plaintext))
    top.sort(key=lambda x: -x[0])
    return best, top[:keep]


def _shuffle(texts: list[str], rng: random.Random) -> list[str]:
    out = []
    for t in texts:
        l = list(t)
        rng.shuffle(l)
        out.append("".join(l))
    return out


def _encipher(plain: str, n_distinct: int, model: str, rng: random.Random,
              pinned: dict[str, str]) -> str:
    """Encipher with a random key whose distinct-symbol count is close to the real one."""
    symbols = [chr(c) for c in range(0x100, 0x100 + 200)]
    rng.shuffle(symbols)
    # Pinned symbols keep their own name and letter, so pin hypotheses are tested fairly.
    key: dict[str, list[str]] = {}
    for s, l in pinned.items():
        key.setdefault(l, []).append(s)
    if model == "simple":
        for l in map(chr, range(65, 91)):
            key.setdefault(l, [symbols.pop()])
        out = [key[c][0] if len(key[c]) == 1 else rng.choice(key[c]) for c in plain]
        return "".join(out)
    # Homophonic: choose a total key size H so the used symbol count matches the real one.
    freq = lm.load()["unigram"]
    best_out, best_gap = None, 10**9
    for H in range(26, 90, 4):
        k = {l: list(v) for l, v in key.items()}
        sym = list(symbols)
        alloc = np.maximum(1, np.round(freq * H)).astype(int)
        for li, l in enumerate(map(chr, range(65, 91))):
            k.setdefault(l, [])
            while len(k[l]) < alloc[li]:
                k[l].append(sym.pop())
        ptr = {l: rng.randrange(len(v)) for l, v in k.items()}
        out = []
        for c in plain:  # Zodiac-style: cycle through each letter's homophones
            out.append(k[c][ptr[c] % len(k[c])])
            ptr[c] += 1
        gap = abs(len(set(out)) - n_distinct)
        if gap < best_gap:
            best_out, best_gap = "".join(out), gap
    return best_out


def _control(texts: list[str], spec: dict, rng: random.Random):
    hold = lm.holdout_text()
    pinned = rng.choice(pin_sets(spec))  # controls honour one of H's pin sets
    plains, ciphers = [], []
    distinct = len(set("".join(texts)))
    total = sum(len(t) for t in texts)
    start = rng.randrange(len(hold) - total - 1)
    plain_all = hold[start:start + total]
    enc_all = _encipher(plain_all, distinct, spec.get("model", "homophonic"), rng, pinned)
    i = 0
    for t in texts:
        p, c = plain_all[i:i + len(t)], enc_all[i:i + len(t)]
        i += len(t)
        plains.append(p)
        ciphers.append(c)
    fam = family_for(spec, len(texts[0]))
    label, order = rng.choice(fam)
    # Scramble cipher 0 so that reading it in `order` restores the plaintext order.
    scr = [""] * len(ciphers[0])
    for k, w in enumerate(order):
        scr[w] = ciphers[0][k]
    ciphers[0] = "".join(scr)
    return ciphers, plains, label


def _task(args):
    kind, j, texts, spec, seed = args
    t0 = time.time()
    if kind == "real":
        score, top = _search(texts, spec, seed, keep=10)
        return kind, j, score, {"top": top}, time.time() - t0
    rng = random.Random(seed)
    if kind == "null":
        score, _ = _search(_shuffle(texts, rng), spec, seed)
        return kind, j, score, {}, time.time() - t0
    ciphers, plains, label = _control(texts, spec, rng)
    score, top = _search(ciphers, spec, seed, keep=1)
    acc = anneal.accuracy(top[0][2], "".join(plains)) if top else 0.0
    return kind, j, score, {"truth_order": label, "recovery": acc}, time.time() - t0


def run(spec: dict, *, nulls: int | None = None, controls: int | None = None,
        extend_nulls: int | None = None, workers: int | None = None, log=print) -> dict:
    nulls = nulls if nulls is not None else spec.get("nulls", 19)
    controls = controls if controls is not None else spec.get("controls", 10)
    extend_nulls = extend_nulls if extend_nulls is not None else spec.get("extend_nulls", 99)
    workers = workers or os.cpu_count() or 1
    texts = real_texts(spec)
    base = int(_spec_hash(spec), 16) % 10**6
    started = time.time()

    def batch(tasks):
        if workers == 1:
            return [_task(t) for t in tasks]
        with ProcessPoolExecutor(workers) as ex:
            return list(ex.map(_task, tasks))

    tasks = [("real", 0, texts, spec, base)]
    tasks += [("null", j, texts, spec, base + 1 + j) for j in range(nulls)]
    tasks += [("control", j, texts, spec, base + 10_000 + j) for j in range(controls)]
    res = batch(tasks)
    real = next(r for r in res if r[0] == "real")
    null_scores = [r[2] for r in res if r[0] == "null"]
    ctrl = [r for r in res if r[0] == "control"]

    def pval(ns):
        return (1 + sum(s >= real[2] for s in ns)) / (1 + len(ns))

    p = pval(null_scores)
    if p <= 0.1 and extend_nulls > nulls:
        log(f"  p={p:.3f} with {nulls} nulls; extending to {extend_nulls}")
        more = batch([("null", j, texts, spec, base + 1 + j) for j in range(nulls, extend_nulls)])
        null_scores += [r[2] for r in more]
        p = pval(null_scores)

    q95 = float(np.quantile(null_scores, 0.95)) if null_scores else math.inf
    sd = float(np.std(null_scores)) if len(null_scores) > 1 else 0.0
    z = (real[2] - float(np.mean(null_scores))) / sd if sd > 0 else None
    power = sum(c[2] > q95 for c in ctrl) / len(ctrl) if ctrl else None
    recovery = float(np.mean([c[3]["recovery"] for c in ctrl])) if ctrl else None
    n_total = sum(len(t) for t in texts)
    if spec["id"].startswith("calib."):
        beats = bool(null_scores) and real[2] > max(null_scores)
        verdict = "CALIBRATION PASS" if beats else "CALIBRATION FAIL: solver/model too weak"
    elif power is not None and power < 0.2:
        verdict = "UNTESTABLE: real English would not stand out from nulls at this length"
    elif p > 0.05:
        verdict = "NO SIGNAL: real cipher scores like shuffled nulls"
    else:
        verdict = "CANDIDATE SIGNAL: beats nulls before multiple-comparison correction; needs review"
    return {
        "id": spec["id"],
        "spec_hash": _spec_hash(spec),
        "spec": spec,
        "lm": lm.fingerprint(),
        "finished": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "seconds": round(time.time() - started, 1),
        "family_size": len(family_for(spec, len(texts[0]))) * len(pin_sets(spec)),
        "length": n_total,
        "real_score": real[2],
        "real_per_letter": real[2] / n_total,
        "top": [{"score": s, "order": lab, "plaintext": pt} for s, lab, pt in real[3]["top"]],
        "null_scores": null_scores,
        "null_q95": q95,
        "control_scores": [c[2] for c in ctrl],
        "control_recovery": recovery,
        "p": p,
        "z": z,
        "power": power,
        "verdict": verdict,
    }
