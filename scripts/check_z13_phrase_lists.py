#!/usr/bin/env python3
"""C1b: check the pre-registered Z13 phrase lists against the five Z13 readings.

Lists were committed and pushed to github.com/herakles-dev/Zodiac (branch
prereg/z13-phrase-lists-v1, commit 10f6e3d, 2026-11-23T16:26:27Z) before this ran.
Decision rule: research/C1/PLAN.md. Hashes are verified first; a changed list aborts.
"""
import hashlib, json, pathlib, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
CAND = ROOT / "hypotheses" / "candidates"
VAR = ROOT / "data" / "ciphers" / "variants"
LISTS = ["persona", "taunt", "vocabcombo"]
READINGS = ["canonical", "reversed", "bracket_is_perp", "circles_distinct", "crosshair_null"]


def iso(s):
    m = {}
    return [m.setdefault(c, len(m)) for c in s]


def fits(plain, ct, mode, skip=None):
    idx = [i for i in range(len(ct)) if i != skip]
    p, c = "".join(plain[i] for i in idx), "".join(ct[i] for i in idx)
    if mode == "simple":
        return iso(p) == iso(c)
    m = {}
    return all(m.setdefault(a, b) == b for a, b in zip(c, p))


out = {"lists": {}, "results": []}
for name in LISTS:
    f = CAND / f"z13_{name}_v1.txt"
    body = f.read_bytes()
    want = (CAND / f"z13_{name}_v1.sha256").read_text().strip()
    got = hashlib.sha256(body).hexdigest()
    if got != want:
        sys.exit(f"{f.name}: hash mismatch ({got} != {want}); list changed after registration")
    cands = [l.strip() for l in body.decode().splitlines() if l.strip()]
    out["lists"][name] = {"size": len(cands), "sha256": got}
    for r in READINGS:
        ct = (VAR / f"z13.{r}.txt").read_text().strip()
        letters = {c: c.replace(" ", "") for c in cands}
        usable = [c for c in cands if len(letters[c]) == len(ct)]
        row = {"list": name, "reading": r, "length": len(ct), "tested": len(usable)}
        for mode in ("simple", "homophonic"):
            row[mode] = [c for c in usable if fits(letters[c], ct, mode)]
        row["one_slip_simple"] = [c for c in usable
                                  if any(fits(letters[c], ct, "simple", i) for i in range(len(ct)))]
        out["results"].append(row)

print(f"{'list':11} {'reading':17} {'tested':>6} {'simple':>6} {'homoph':>6} {'1-slip':>6}")
for r in out["results"]:
    print(f"{r['list']:11} {r['reading']:17} {r['tested']:>6} {len(r['simple']):>6} "
          f"{len(r['homophonic']):>6} {len(r['one_slip_simple']):>6}")
hits = [(r["list"], r["reading"], k, c) for r in out["results"]
        for k in ("simple", "homophonic", "one_slip_simple") for c in r[k]]
print("\nall fits:", hits if hits else "none")
(CAND / "z13_phrase_lists_v1_results.json").write_text(json.dumps(out, indent=1))
