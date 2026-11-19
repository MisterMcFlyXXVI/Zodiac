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


def _current(r: dict) -> bool:
    lang = r.get("lang", "en")
    return lang in lm.available() and r.get("lm") == lm.fingerprint(lang)


def _done_keys(rows: list[dict]) -> set[tuple[str, str]]:
    return {(r["id"], r["spec_hash"]) for r in rows if _current(r)}


def pending() -> list[dict]:
    done = _done_keys(ledger())
    specs = hypotheses.builtin() + hypotheses.queued()
    langs = lm.available()
    return [s for s in specs if (s["id"], evaluate._spec_hash(s)) not in done
            and evaluate.lang_of(s) in langs]


def next_spec() -> dict:
    p = pending()
    if p:
        return p[0]
    n = sum(1 for r in ledger() if r["id"].startswith("explore."))
    return hypotheses.explore(n)


def calib_id(lang: str) -> str:
    return "calib.z408.homophonic" if lang == "en" else f"calib.{lang}.synthetic408"


def calibrated(lang: str = "en") -> bool:
    ok = False
    for r in ledger():
        if r["id"] == calib_id(lang) and _current(r):
            ok = r.get("verdict") == "CALIBRATION PASS"
    return ok


def _skip(spec: dict, why: str) -> None:
    lang = evaluate.lang_of(spec)
    row = {"id": spec["id"], "spec_hash": evaluate._spec_hash(spec), "spec": spec, "lang": lang,
           "lm": lm.fingerprint(lang), "p": None, "power": None, "verdict": "SKIPPED: " + why,
           "finished": time.strftime("%Y-%m-%dT%H:%M:%S")}
    with LEDGER.open("a") as f:
        f.write(json.dumps(row) + "\n")


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
        lang = evaluate.lang_of(spec)
        if not spec["id"].startswith("calib.") and not calibrated(lang):
            cid = calib_id(lang)
            if any(r["id"] == cid and _current(r) for r in ledger()):
                log(f"{cid} FAILED under the current model; skipping {spec['id']}")
                _skip(spec, f"calibration {cid} failed")
                continue
            log(f"calibration for {lm.LANG_NAMES[lang]} has not run yet; running it first")
            spec = next(s for s in hypotheses.builtin() if s["id"] == cid)
        log(f"[{time.strftime('%H:%M:%S')}] {spec['id']}: {spec['title']}")
        try:
            res = evaluate.run(spec, workers=workers, log=log)
        except Exception as e:  # record failures too, so the loop doesn't retry them forever
            res = {"id": spec["id"], "spec_hash": evaluate._spec_hash(spec), "spec": spec,
                   "lang": evaluate.lang_of(spec), "lm": lm.fingerprint(evaluate.lang_of(spec)), "error": repr(e), "p": None, "power": None,
                   "verdict": "ERROR", "finished": time.strftime("%Y-%m-%dT%H:%M:%S")}
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
