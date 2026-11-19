"""Autonomous loop: pick the next untested hypothesis, run it, record it, repeat.

State lives entirely in results/ledger.jsonl (append-only), so the loop can be
killed at any moment and resumed later, on this machine or another one.
"""
from __future__ import annotations

import json
import pathlib
import subprocess
import time

from . import evaluate, hypotheses, lm, report

ROOT = pathlib.Path(__file__).resolve().parent.parent
LEDGER = ROOT / "results" / "ledger.jsonl"


def ledger() -> list[dict]:
    if not LEDGER.exists():
        return []
    return [json.loads(l) for l in LEDGER.read_text().splitlines() if l.strip()]


def _done_keys(rows: list[dict]) -> set[tuple[str, str]]:
    return {(r["id"], r["spec_hash"]) for r in rows if r.get("lm") == lm.fingerprint()}


def pending() -> list[dict]:
    done = _done_keys(ledger())
    specs = hypotheses.builtin() + hypotheses.queued()
    return [s for s in specs if (s["id"], evaluate._spec_hash(s)) not in done]


def next_spec() -> dict:
    p = pending()
    if p:
        return p[0]
    n = sum(1 for r in ledger() if r["id"].startswith("explore."))
    return hypotheses.explore(n)


def calibrated() -> bool:
    for r in ledger():
        if r["id"] == "calib.z408.homophonic" and r.get("lm") == lm.fingerprint():
            return (r.get("real_score", -1e18) > max(r.get("null_scores") or [0])
                    and r.get("calib_accuracy", 0) > 0.9)
    return False


def _commit(msg: str) -> None:
    subprocess.run(["git", "add", "results"], cwd=ROOT, check=False)
    subprocess.run(["git", "commit", "-q", "-m", msg], cwd=ROOT, check=False)


def run(hours: float, *, workers: int | None = None, commit: bool = False, only: str | None = None,
        log=print) -> None:
    deadline = time.time() + hours * 3600
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    while time.time() < deadline:
        spec = next((s for s in pending() if s["id"] == only), None) if only else next_spec()
        if spec is None:
            log(f"{only}: already done")
            return
        if not spec["id"].startswith("calib.") and not calibrated():
            log("calibration has not passed under this language model; running it first")
            spec = next(s for s in hypotheses.builtin() if s["id"] == "calib.z408.homophonic")
        log(f"[{time.strftime('%H:%M:%S')}] {spec['id']}: {spec['title']}")
        try:
            res = evaluate.run(spec, workers=workers, log=log)
        except Exception as e:  # record failures too, so the loop doesn't retry them forever
            res = {"id": spec["id"], "spec_hash": evaluate._spec_hash(spec), "spec": spec,
                   "lm": lm.fingerprint(), "error": repr(e), "p": None, "power": None,
                   "verdict": "ERROR", "finished": time.strftime("%Y-%m-%dT%H:%M:%S")}
        if spec["id"] == "calib.z408.homophonic" and res.get("top"):
            from .cipher import load
            from .anneal import accuracy
            res["calib_accuracy"] = accuracy(res["top"][0]["plaintext"], load("z408").plaintext)
        with LEDGER.open("a") as f:
            f.write(json.dumps(res) + "\n")
        report.write(ledger())
        log(f"   -> {res['verdict']}  p={res.get('p')}  power={res.get('power')}  "
            f"({res.get('seconds', '?')}s)")
        if res.get("top"):
            log(f"   best: {res['top'][0]['plaintext'][:70]}  [{res['top'][0]['order']}]")
        if commit:
            _commit(f"zbot: {spec['id']} -> {res['verdict'].split(':')[0]}")
        if only:
            return
