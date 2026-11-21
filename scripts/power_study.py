#!/usr/bin/env python3
"""Compare scoring methods by statistical power on Z13 / Z32.

For each (cipher, key model, scorer) it runs the full test the bot uses: the real cipher,
shuffled copies (nulls) and genuine-text controls with the same repeat profile, then
reports power (share of controls beating the nulls' 95th percentile) and the real
cipher's p. Results go to results/power_study.json and a table on stdout.

  python scripts/power_study.py                 # default grid
  python scripts/power_study.py --controls 40   # tighter power estimates
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from zbot import evaluate  # noqa: E402

SCORERS = {
    "letters": None,
    "words": {"ngram": 1.0, "words": 1.0, "unk": -8.0, "wpen": 2.0},
    "words_strong": {"ngram": 0.3, "words": 1.0, "unk": -8.0, "wpen": 2.0},
    "words_only": {"ngram": 0.0, "words": 1.0, "unk": -6.0, "wpen": 3.0},
    "words_strict": {"ngram": 0.3, "words": 1.0, "unk": -12.0, "wpen": 3.0},
    "words_only_u5": {"ngram": 0.0, "words": 1.0, "unk": -5.0, "wpen": 3.0},
    "words_only_u7w4": {"ngram": 0.0, "words": 1.0, "unk": -7.0, "wpen": 4.0},
    "words_only_u6w2": {"ngram": 0.0, "words": 1.0, "unk": -6.0, "wpen": 2.0},
    # Zodiac-vocabulary prior built from letters fold A (measure with --control-text zodiac_B)
    "zvocab3": {"ngram": 0.0, "words": 1.0, "unk": -6.0, "wpen": 3.0, "zodiac_boost": 3.0, "zodiac_fold": "A"},
    "zvocab6": {"ngram": 0.0, "words": 1.0, "unk": -6.0, "wpen": 3.0, "zodiac_boost": 6.0, "zodiac_fold": "A"},
    # hybrids (letters + words): these also pass the Z408 calibration
    "hybrid": {"ngram": 1.0, "words": 1.0, "unk": -5.0, "wpen": 3.0},
    "hybrid05": {"ngram": 0.5, "words": 1.0, "unk": -5.0, "wpen": 3.0},
    "hybrid_zv6A": {"ngram": 1.0, "words": 1.0, "unk": -5.0, "wpen": 3.0, "zodiac_boost": 6.0, "zodiac_fold": "A"},
    "hybrid05_zv6A": {"ngram": 0.5, "words": 1.0, "unk": -5.0, "wpen": 3.0, "zodiac_boost": 6.0, "zodiac_fold": "A"},
}
TARGETS = [("z13", "simple"), ("z13", "homophonic"), ("z32", "homophonic")]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--nulls", type=int, default=19)
    ap.add_argument("--controls", type=int, default=20)
    ap.add_argument("--scorers", nargs="*", default=list(SCORERS))
    ap.add_argument("--out", default=str(ROOT / "results" / "power_study.json"))
    ap.add_argument("--targets", nargs="*", default=[f"{c}:{m}" for c, m in TARGETS],
                    help="cipher:model pairs, e.g. z32:zodiac")
    ap.add_argument("--iters", type=int, help="annealing steps per restart (default: automatic)")
    ap.add_argument("--tag", default="", help="label appended to the scorer name in the output")
    ap.add_argument("--control-text", help="where control plaintexts come from, e.g. zodiac_B")
    a = ap.parse_args()
    out_path = pathlib.Path(a.out)
    rows = json.loads(out_path.read_text()) if out_path.exists() else []
    for cipher, model in (t.split(":") for t in a.targets):
        for name in a.scorers:
            spec = {"id": f"study.{cipher}.{model}.{name}", "cipher": cipher, "model": model,
                    "nulls": a.nulls, "controls": a.controls, "extend_nulls": 0}
            if SCORERS[name]:
                spec["scorer"] = SCORERS[name]
            if a.iters:
                spec["iters"] = a.iters
            if a.control_text:
                spec["control_text"] = a.control_text
            label = name + a.tag
            t = time.time()
            r = evaluate.run(spec, log=lambda *x: None)
            row = {"cipher": cipher, "model": model, "scorer": label, "config": SCORERS[name], "iters": a.iters,
                   "power": r["power"], "p": r["p"], "z": r["z"],
                   "power_dominance": r["power_dominance"], "p_dominance": r["p_dominance"], "controls": a.controls, "nulls": a.nulls,
                   "control_recovery": r["control_recovery"], "best": r["top"][0]["plaintext"],
                   "seconds": round(time.time() - t, 1)}
            rows = [x for x in rows if (x["cipher"], x["model"], x["scorer"]) != (cipher, model, label)] + [row]
            out_path.write_text(json.dumps(rows, indent=1))
            print(f"{cipher:4} {model:10} {label:13} power={row['power']:.2f} p={row['p']:.2f} "
                  f"dom_power={row['power_dominance']:.2f} dom_p={row['p_dominance']:.2f} "
                  f"recovery={row['control_recovery']:.2f}  {row['seconds']:6.1f}s  {row['best']}", flush=True)


if __name__ == "__main__":
    main()
