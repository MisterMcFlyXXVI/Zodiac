"""Run one hypothesis end to end: real cipher, null ciphers, positive controls.

For a hypothesis H (cipher + transcription choice + read-order family +
key model + optional pins + language) we compute:

* real   - best score over the whole family on the real cipher.
* nulls  - the same search on the real cipher's symbols shuffled into a
           random order. This keeps the symbol counts and destroys any
           structure. p = (1 + #nulls >= real) / (1 + #nulls).
* controls - held-out text in H's language, enciphered under H's key model
           so that the control has EXACTLY the real cipher's repeat profile
           (how many symbols occur 3x, 2x, 1x...), then scrambled by a random
           member of H's family and searched exactly like the real cipher.
           power = share of controls scoring above the nulls' 95th
           percentile. Low power means H cannot be tested at this length.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import random
import time
from collections import Counter
from concurrent.futures import ProcessPoolExecutor

import numpy as np

from . import anneal, lm, transforms
from .cipher import load as load_cipher

LETTERS = [chr(c) for c in range(65, 91)]


def _spec_hash(spec: dict) -> str:
    return hashlib.sha256(json.dumps(spec, sort_keys=True).encode()).hexdigest()[:10]


def lang_of(spec: dict) -> str:
    return spec.get("lang", "en")


def synthetic(spec: dict) -> tuple[list[str], str]:
    """A Z408-like calibration cipher made from held-out text in the spec's language."""
    cfg = spec["synthetic"]
    rng = random.Random(cfg.get("seed", 0))
    hold = lm.holdout_text(lang_of(spec))
    n = cfg.get("length", 408)
    start = rng.randrange(len(hold) - n)
    plain = hold[start:start + n]
    freq = lm.load(lang_of(spec))["unigram"]
    H = cfg.get("key_size", 54)
    alloc = np.maximum(1, np.round(freq * H)).astype(int)
    sym = [chr(c) for c in range(0x100, 0x100 + 200)]
    rng.shuffle(sym)
    key = {l: [sym.pop() for _ in range(alloc[i])] for i, l in enumerate(LETTERS)}
    ptr = Counter()
    out = []
    for c in plain:  # Zodiac-style cycling through homophones
        out.append(key[c][ptr[c] % len(key[c])])
        ptr[c] += 1
    return ["".join(out)], plain


def real_texts(spec: dict) -> list[str]:
    if "synthetic" in spec:
        return synthetic(spec)[0]
    names = spec["cipher"] if isinstance(spec["cipher"], list) else [spec["cipher"]]
    out = []
    for n in names:
        t = load_cipher(n).text
        for d in spec.get("drop_symbols", []):
            t = t.replace(d, "")
        out.append(t)
    return out


def truth(spec: dict) -> str | None:
    if "synthetic" in spec:
        return synthetic(spec)[1]
    if spec.get("cipher") == "z408":
        return load_cipher("z408").plaintext
    return None


def validate(spec: dict) -> None:
    texts = real_texts(spec)
    if spec.get("model") == "simple" and len(set("".join(texts))) > 26:
        raise ValueError("simple substitution impossible: more than 26 distinct symbols")
    if lang_of(spec) not in lm.CORPORA:
        raise ValueError(f"unknown language {lang_of(spec)}")


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


def _budget(spec: dict):
    if spec.get("model") != "zodiac":
        return None
    from . import zkey
    return zkey.budget()


def _search(texts: list[str], spec: dict, seed: int, keep: int = 0):
    """Best score over family x pin sets for one instance. Returns (score, top list)."""
    alphabet = sorted(set("".join(texts)))
    idx = {s: i for i, s in enumerate(alphabet)}
    fams = [family_for(spec, len(t)) for t in texts]
    if len(texts) > 1 and any(len(f) > 1 for f in fams):
        raise ValueError("read-order families are only supported for single-cipher hypotheses")
    best = -math.inf
    top: list[tuple[float, str, str]] = []
    pool: list[tuple[float, str]] = []  # every restart's answer, for the uniqueness measure
    for pins in pin_sets(spec):
        pin_idx = {idx[s]: ord(l) - 65 for s, l in pins.items() if s in idx}
        for label, order in fams[0]:
            segs = []
            for ti, t in enumerate(texts):
                o = order if ti == 0 else list(range(len(t)))
                segs.append(np.array([idx[t[i]] for i in o], dtype=np.int64))
            sols = anneal.solve(segs, len(alphabet), restarts=spec.get("restarts", 4),
                                iters=spec.get("iters"), injective=spec.get("model") == "simple",
                                pins=pin_idx, klw=spec.get("klw", 1.0), seed=seed,
                                lang=lang_of(spec), scorer=spec.get("scorer"),
                                key_budget=_budget(spec), key_budget_weight=spec.get("key_budget_weight", 6.0)
                                if spec.get("model") == "zodiac" else 0.0)
            s = sols[0]
            best = max(best, s.score)
            pool.extend((x.score, x.plaintext) for x in sols)
            if keep:
                tag = label + (f" pins={pins}" if pins else "")
                top.append((s.score, tag, s.plaintext))
    top.sort(key=lambda x: -x[0])
    return best, top[:keep], dominance(pool)


DISTINCT = 0.30  # readings differing in more than 30% of letters count as different answers


def dominance(pool: list[tuple[float, str]]) -> float:
    """How far the best reading stands above the best clearly different reading (nats).

    Large = one reading dominates; near 0 = several unrelated readings tie. If every
    restart agreed on the same reading, the gap to the worst restart is used (a lower
    bound), so convergence still counts as dominance.
    """
    if not pool:
        return float("nan")
    pool = sorted(pool, key=lambda x: -x[0])
    s1, p1 = pool[0]
    for s, p in pool[1:]:
        diff = sum(a != b for a, b in zip(p, p1)) / max(1, len(p1))
        if diff > DISTINCT:
            return s1 - s
    return s1 - pool[-1][0]


def _shuffle(texts: list[str], rng: random.Random) -> list[str]:
    out = []
    for t in texts:
        l = list(t)
        rng.shuffle(l)
        out.append("".join(l))
    return out


def profile(text: str) -> tuple[int, ...]:
    return tuple(sorted(Counter(text).values(), reverse=True))


def _partitions(c: int, need: Counter, max_part: int):
    """Partitions of c into non-increasing parts whose sizes are still needed."""
    if c == 0:
        yield []
        return
    for k in range(min(c, max_part), 0, -1):
        if need[k] > 0:
            need[k] -= 1
            for rest in _partitions(c - k, need, k):
                yield [k] + rest
            need[k] += 1


def _refine(counts: list[tuple[str, int]], need: Counter, rng: random.Random, budget: list[int],
            maxparts: dict[str, int] | None = None):
    """Split each letter's count into homophone parts so the parts equal `need` exactly."""
    if not counts:
        return {} if sum(need.values()) == 0 else None
    budget[0] -= 1
    if budget[0] < 0:
        return None
    (letter, c), rest = counts[0], counts[1:]
    opts = [o for o in _partitions(c, need, c) if maxparts is None or len(o) <= maxparts.get(letter, 99)]
    rng.shuffle(opts)
    for parts in opts:
        for k in parts:
            need[k] -= 1
        sub = _refine(rest, need, rng, budget, maxparts)
        for k in parts:
            need[k] += 1
        if sub is not None:
            sub[letter] = parts
            return sub
    return None


def _sample_words(words: list[str], total: int, rng: random.Random) -> str | None:
    """A run of whole consecutive words with exactly `total` letters, or None."""
    i = rng.randrange(len(words))
    out = ""
    while len(out) < total and i < len(words):
        out += words[i]
        i += 1
    return out if len(out) == total else None


def _encipher_matching(texts: list[str], model: str, lang: str, rng: random.Random,
                       pinned: dict[str, str], tries: int = 400_000, control_source: str | None = None,
                       words: list[str] | None = None):
    """Held-out plaintext + key giving a cipher with exactly the real repeat profile.

    With `words`, the plaintext is a run of whole words (like a complete message);
    otherwise a window cut anywhere from `control_source` or the held-out letters."""
    hold = control_source or lm.holdout_text(lang)
    target = profile("".join(texts))
    need0 = Counter(target)
    total = sum(target)
    pin_by_letter = {l: s for s, l in pinned.items()}
    for _ in range(tries):
        if words is not None:
            plain = _sample_words(words, total, rng)
            if plain is None:
                continue
        else:
            start = rng.randrange(len(hold) - total)
            plain = hold[start:start + total]
        lc = Counter(plain)
        if model == "simple":
            if tuple(sorted(lc.values(), reverse=True)) != target:
                continue
            parts = {l: [c] for l, c in lc.items()}
        else:
            if len(lc) > len(target) or max(lc.values()) < target[0]:
                continue
            counts = sorted(lc.items(), key=lambda x: -x[1])
            maxparts = None
            if model == "zodiac":
                from . import zkey
                b = zkey.budget()
                maxparts = {chr(65 + i): int(b[i]) for i in range(26)}
            parts = _refine(counts, Counter(need0), rng, [2_000], maxparts)
            if parts is None:
                continue
        # Assign symbols: each part of a letter is one homophone; occurrences are dealt
        # out at random so the part sizes come out exactly.
        symbols = [chr(c) for c in range(0x100, 0x100 + 400)]
        rng.shuffle(symbols)
        deal: dict[str, list[str]] = {}
        for l, ps in parts.items():
            syms = [pin_by_letter[l] if (i == 0 and l in pin_by_letter) else symbols.pop()
                    for i in range(len(ps))]
            seq = [s for s, k in zip(syms, ps) for _ in range(k)]
            rng.shuffle(seq)
            deal[l] = seq
        out = [deal[c].pop() for c in plain]
        cipher = "".join(out)
        assert profile(cipher) == target
        return plain, cipher
    raise RuntimeError(f"no {lang} held-out window fits profile {target} under {model} in {tries} tries")


def _control(texts: list[str], spec: dict, rng: random.Random):
    pinned = rng.choice(pin_sets(spec))  # controls honour one of H's pin sets
    # Test texts are runs of whole words, like a complete message (both Z13 and Z32 are).
    if spec.get("control_text") in ("zodiac_A", "zodiac_B", "zodiac"):
        from . import words
        raw = words.zodiac_text({"zodiac_A": "A", "zodiac_B": "B"}.get(spec["control_text"], "all"))
        wl = [w for w in (lm.letters_only(t) for t in raw.split()) if w]
    else:
        wl = lm.holdout_words(lang_of(spec))
    plain_all, enc_all = _encipher_matching(texts, spec.get("model", "homophonic"),
                                            lang_of(spec), rng, pinned, words=wl)
    plains, ciphers, i = [], [], 0
    for t in texts:
        plains.append(plain_all[i:i + len(t)])
        ciphers.append(enc_all[i:i + len(t)])
        i += len(t)
    label, order = rng.choice(family_for(spec, len(texts[0])))
    # Scramble cipher 0 so that reading it in `order` restores the plaintext order.
    scr = [""] * len(ciphers[0])
    for k, w in enumerate(order):
        scr[w] = ciphers[0][k]
    ciphers[0] = "".join(scr)
    return ciphers, plains, label


CONFIRM_NULL_STAGES = (499, 999)
CONFIRM_MAX_EXTRA_SECONDS = 2 * 3600  # a stage that would take longer is left to a dedicated run


def tier(spec_id: str) -> str:
    if spec_id.startswith("calib."):
        return "calibration"
    if spec_id.startswith("explore."):
        return "exploratory"
    return "confirmatory"


def power_pooled(real_score, null_scores, control_scores):
    """Share of controls above the 95th percentile of {real} + nulls.

    Under the null the real score is exchangeable with the nulls, so this threshold does
    not depend on which of the scores is the real one, and filtering on it leaves p valid.
    """
    if not control_scores or not null_scores or real_score is None:
        return None
    q = float(np.quantile(np.append(np.asarray(null_scores, dtype=float), real_score), 0.95))
    return sum(c > q for c in control_scores) / len(control_scores)


def _task(args):
    kind, j, texts, spec, seed = args
    t0 = time.time()
    if kind == "real":
        score, top, dom = _search(texts, spec, seed, keep=10)
        return kind, j, score, {"top": top, "dom": dom}, time.time() - t0
    rng = random.Random(seed)
    if kind == "null":
        score, _, dom = _search(_shuffle(texts, rng), spec, seed)
        return kind, j, score, {"dom": dom}, time.time() - t0
    ciphers, plains, label = _control(texts, spec, rng)
    score, top, dom = _search(ciphers, spec, seed, keep=1)
    acc = anneal.accuracy(top[0][2], "".join(plains)) if top else 0.0
    return kind, j, score, {"truth_order": label, "recovery": acc, "dom": dom}, time.time() - t0


def run(spec: dict, *, nulls: int | None = None, controls: int | None = None,
        extend_nulls: int | None = None, workers: int | None = None, log=print) -> dict:
    validate(spec)
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
    null_doms = [r[3]["dom"] for r in res if r[0] == "null"]
    null_secs = [r[4] for r in res if r[0] == "null"]
    ctrl = [r for r in res if r[0] == "control"]

    def pval(ns):
        return (1 + sum(s >= real[2] for s in ns)) / (1 + len(ns))

    p = pval(null_scores)
    if p <= 0.1 and extend_nulls > nulls:
        log(f"  p={p:.3f} with {nulls} nulls; extending to {extend_nulls}")
        more = batch([("null", j, texts, spec, base + 1 + j) for j in range(nulls, extend_nulls)])
        null_scores += [r[2] for r in more]
        null_doms += [r[3]["dom"] for r in more]
        p = pval(null_scores)
    nulls_capped = False
    if tier(spec["id"]) == "confirmatory":
        # Only a result that still looks significant gets more nulls, so most tests cost the
        # same as before. Stop once 5 nulls reach the real score: p is then known well enough.
        for stage in CONFIRM_NULL_STAGES:
            if p > 0.05 or sum(s >= real[2] for s in null_scores) >= 5:
                break
            if stage <= len(null_scores):
                continue
            need = (stage - len(null_scores)) * (sum(null_secs) / len(null_secs)) / workers
            if need > CONFIRM_MAX_EXTRA_SECONDS:
                log(f"  confirmatory: {stage} nulls would take ~{need / 60:.0f} more min; stopping at "
                    f"{len(null_scores)} (queue a dedicated run with more nulls)")
                nulls_capped = True
                break
            log(f"  confirmatory: p={p:.4f} with {len(null_scores)} nulls; extending to {stage}")
            more = batch([("null", j, texts, spec, base + 1 + j) for j in range(len(null_scores), stage)])
            null_scores += [r[2] for r in more]
            null_doms += [r[3]["dom"] for r in more]
            p = pval(null_scores)
    # Second statistic: uniqueness of the best reading, judged the same way.
    real_dom = real[3]["dom"]
    p_dom = (1 + sum(d >= real_dom for d in null_doms)) / (1 + len(null_doms)) if null_doms else None
    dq95 = float(np.quantile(null_doms, 0.95)) if null_doms else math.inf
    power_dom = sum(c[3]["dom"] > dq95 for c in ctrl) / len(ctrl) if ctrl else None

    q95 = float(np.quantile(null_scores, 0.95)) if null_scores else math.inf
    sd = float(np.std(null_scores)) if len(null_scores) > 1 else 0.0
    z = (real[2] - float(np.mean(null_scores))) / sd if sd > 0 else None
    power = power_pooled(real[2], null_scores, [c[2] for c in ctrl])
    recovery = float(np.mean([c[3]["recovery"] for c in ctrl])) if ctrl else None
    n_total = sum(len(t) for t in texts)
    top = [{"score": s, "order": lab, "plaintext": pt} for s, lab, pt in real[3]["top"]]
    out = {
        "id": spec["id"],
        "spec_hash": _spec_hash(spec),
        "spec": spec,
        "lang": lang_of(spec),
        "lm": lm.fingerprint(lang_of(spec)),
        "finished": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "seconds": round(time.time() - started, 1),
        "family_size": len(family_for(spec, len(texts[0]))) * len(pin_sets(spec)),
        "length": n_total,
        "real_score": real[2],
        "real_per_letter": real[2] / n_total,
        "top": top,
        "null_scores": null_scores,
        "null_q95": q95,
        "control_scores": [c[2] for c in ctrl],
        "control_recovery": recovery,
        "p": p,
        "z": z,
        "power": power,
        "power_basis": "pooled",
        "nulls_capped": nulls_capped,
        "dominance": real_dom,
        "null_dominance": null_doms,
        "control_dominance": [c[3]["dom"] for c in ctrl],
        "p_dominance": p_dom,
        "power_dominance": power_dom,
    }
    if spec["id"].startswith("calib."):
        t = truth(spec)
        out["calib_accuracy"] = anneal.accuracy(top[0]["plaintext"], t) if (t and top) else 0.0
        beats = bool(null_scores) and real[2] > max(null_scores)
        ok = beats and out["calib_accuracy"] > 0.9
        out["verdict"] = "CALIBRATION PASS" if ok else "CALIBRATION FAIL: solver/model too weak"
    elif power is not None and power < 0.2:
        out["verdict"] = "UNTESTABLE: real text would not stand out from nulls at this length"
    elif p > 0.05:
        out["verdict"] = "NO SIGNAL: real cipher scores like shuffled nulls"
    else:
        out["verdict"] = "CANDIDATE SIGNAL: beats nulls before multiple-comparison correction; needs review"
    return out
