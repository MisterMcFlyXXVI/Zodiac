"""Command line: python -m zbot <command>

  setup              download corpora and build the language model
  build-lm           (re)build the language model only
  list               show the hypothesis queue and what is done
  run [--hours H]    work through the queue autonomously (resumable)
  run --only ID      run a single hypothesis
  report             regenerate results/REPORT.md and ALERTS.md
  solve CIPHER       quick look: best decodes of one cipher, no statistics
"""
from __future__ import annotations

import argparse
import subprocess
import sys

from . import cipher, evaluate, hypotheses, lm, report, runner


def _build_lm():
    z340 = cipher.load("z340")
    ro = cipher.apply_order(z340, z340.meta["read_order"])
    lm.build([cipher.load("z408").plaintext, ro.plaintext.replace("?", "")])
    print(f"language model built: {lm.LM_PATH} ({lm.fingerprint()})")


def main(argv=None):
    ap = argparse.ArgumentParser(prog="zbot", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("setup")
    sub.add_parser("build-lm")
    sub.add_parser("list")
    r = sub.add_parser("run")
    r.add_argument("--hours", type=float, default=1.0)
    r.add_argument("--workers", type=int)
    r.add_argument("--commit", action="store_true", help="git-commit results after each hypothesis")
    r.add_argument("--only", help="run just this hypothesis id")
    sub.add_parser("report")
    s = sub.add_parser("solve")
    s.add_argument("cipher")
    s.add_argument("--model", default="homophonic", choices=["homophonic", "simple"])
    s.add_argument("--restarts", type=int, default=8)
    s.add_argument("--iters", type=int)
    a = ap.parse_args(argv)

    if a.cmd == "setup":
        subprocess.run([sys.executable, str(lm.ROOT / "scripts" / "fetch_corpus.py")], check=True)
        _build_lm()
    elif a.cmd == "build-lm":
        _build_lm()
    elif a.cmd == "list":
        done = {r["id"]: r for r in runner.ledger()}
        for spec in hypotheses.builtin() + hypotheses.queued():
            r = done.get(spec["id"])
            status = r["verdict"].split(":")[0] if r else "pending"
            print(f"{status:18} {spec['id']:45} {spec['title']}")
    elif a.cmd == "run":
        runner.run(a.hours, workers=a.workers, commit=a.commit, only=a.only)
    elif a.cmd == "report":
        report.write(runner.ledger())
        print(report.OUT)
    elif a.cmd == "solve":
        import numpy as np
        from . import anneal
        texts = evaluate.real_texts({"cipher": a.cipher})
        alphabet = sorted(set("".join(texts)))
        segs = [np.array([alphabet.index(ch) for ch in t]) for t in texts]
        for sol in anneal.solve(segs, len(alphabet), restarts=a.restarts, iters=a.iters,
                                injective=a.model == "simple"):
            print(f"{sol.per_letter:7.3f}  {sol.plaintext}")


if __name__ == "__main__":
    main()
