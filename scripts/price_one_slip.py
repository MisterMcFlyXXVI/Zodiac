#!/usr/bin/env python3
"""B4 report: price the one-slip (and exact/homophonic) fit counts for the C1 v1 lists against
every Z13 reading, using each reading's OWN profile for the null. Writes slip_pricing.json and
prints a verdict table. Reproduces (does not re-register) -- it reads the already-committed C1
lists and the published readings; no list is edited.

Run: python scripts/price_one_slip.py   # -> results/one_slip_pricing/slip_pricing.json
"""
from __future__ import annotations

import json
import pathlib

import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import slip_rule as sr  # noqa: E402

OUT = ROOT / "results" / "one_slip_pricing"
CAND = ROOT / "hypotheses" / "candidates"
VAR = ROOT / "data" / "ciphers" / "variants"
LISTS = ["persona", "taunt", "vocabcombo"]
READINGS = ["canonical", "reversed", "bracket_is_perp", "circles_distinct", "crosshair_null"]
N_DECOYS, SEED, ALPHA = 2000, 20261123, 0.05


def load_cands(name):
    f = CAND / f"z13_{name}_v1.txt"
    return [l.strip() for l in f.read_text().splitlines() if l.strip()]


def observed_counts(letters, ct):
    """Counts on the REAL reading: exact-simple, one-slip-simple, homophonic. Matches check.py."""
    ex = [c for c, p in letters.items() if sr.fits(p, ct, "simple")]
    hom = [c for c, p in letters.items() if sr.fits(p, ct, "homophonic")]
    slip = [c for c, p in letters.items()
            if any(sr.fits(p, ct, "simple", i) for i in range(len(ct)))]
    return {"exact": ex, "slip": slip, "homophonic": hom}


def main():
    readings = {r: VAR.joinpath(f"z13.{r}.txt").read_text().strip() for r in READINGS}
    profiles = {r: sr.profile_of(ct) for r, ct in readings.items()}

    # exclude each reading's own isomorph and its reversal from its decoy pool
    excl = {r: {sr.iso(ct), sr.iso(ct[::-1])} for r, ct in readings.items()}

    # which (list, reading) cells are evaluable (candidate length == reading length)?
    cells = []
    for name in LISTS:
        cands = load_cands(name)
        letters = {c: c.replace(" ", "") for c in cands}
        for r in READINGS:
            ct = readings[r]
            usable = {c: p for c, p in letters.items() if len(p) == len(ct)}
            if usable:
                cells.append((name, r, usable))
    n_tests = len(cells)  # Bonferroni family size (simple-key one-slip family)

    rows, pricing = [], {}
    for name, r, usable in cells:
        ct = readings[r]
        obs = observed_counts(usable, ct)
        null = sr.null_counts(list(usable.values()), profiles[r],
                              n_decoys=N_DECOYS, seed=SEED, exclude=excl[r])
        for key, nullkey in (("exact", "exact"), ("slip", "slip"), ("homophonic", "homophonic")):
            k = len(obs[key])
            dec = sr.decision(k, null[nullkey], n_tests=n_tests, alpha=ALPHA)
            rows.append((name, r, profiles[r], key, dec))
            pricing.setdefault(name, {}).setdefault(r, {})[key] = {
                "observed": k, "fits": obs[key], **{kk: dec[kk] for kk in (
                    "expected", "p99", "max", "frac_ge1", "pval",
                    "alpha_per_test", "family_expected", "notable", "naive_notable")}}

    # ---- table ----
    hdr = f"{'list':11} {'reading':17} {'key':11} {'prof':>6} {'obs':>4} {'E':>7} {'p99':>4} {'pval':>7} {'notable':>7}"
    print(hdr)
    print("-" * len(hdr))
    naive_hits = priced_hits = 0
    for name, r, prof, key, d in rows:
        if d["naive_notable"]:
            naive_hits += 1
        if d["notable"]:
            priced_hits += 1
        tag = "**" if d["notable"] else ("chance" if d["naive_notable"] else "")
        print(f"{name:11} {r:17} {key:11} {len(prof):>6} {d['observed']:>4} "
              f"{d['expected']:>7.4f} {d['p99']:>4.0f} {d['pval']:>7.4f} {tag:>7}")

    print(f"\nfamily size (Bonferroni n_tests): {n_tests}  alpha={ALPHA}  "
          f"alpha_per_test={ALPHA / n_tests:.5f}")
    print(f"naive rule ('any fit counts') would flag: {naive_hits}")
    print(f"priced rule flags:                        {priced_hits}")

    out = {
        "seed": SEED, "n_decoys": N_DECOYS, "alpha_family": ALPHA, "n_tests": n_tests,
        "profiles": {r: profiles[r] for r in READINGS},
        "naive_notable_count": naive_hits, "priced_notable_count": priced_hits,
        "pricing": pricing,
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "slip_pricing.json").write_text(json.dumps(out, indent=1) + "\n")
    print(f"\nwrote {OUT / 'slip_pricing.json'}")


if __name__ == "__main__":
    main()
