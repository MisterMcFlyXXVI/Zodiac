"""Autonomous loop: pick the next untested hypothesis, run it, record it, repeat.

State lives entirely in results/ledger.jsonl (append-only), so the loop can be
killed at any moment and resumed later, on this machine or another one.
"""
from __future__ import annotations

import json
import os
import pathlib
import re
import subprocess
import time

from . import evaluate, hypotheses, lm, report

ROOT = pathlib.Path(__file__).resolve().parent.parent
RESULTS = pathlib.Path(os.environ.get("ZBOT_RESULTS_DIR", ROOT / "results"))
LEDGER = RESULTS / "ledger.jsonl"


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
    # Work you queued yourself (web app or hypotheses/queue/) goes ahead of the built-ins.
    specs = hypotheses.queued() + hypotheses.builtin()
    langs = lm.available()
    return [s for s in specs if (s["id"], evaluate._spec_hash(s)) not in done
            and evaluate.lang_of(s) in langs]


def _content(spec: dict) -> str:
    """What a test actually does, ignoring its name and description."""
    return json.dumps({k: v for k, v in spec.items() if k not in ("id", "title", "motivation", "source")},
                      sort_keys=True)


def _explore_number(spec_id: str) -> int | None:
    m = re.match(r"explore\.(\d+)\.", spec_id)
    return int(m.group(1)) if m else None


def next_explore(rows: list[dict]) -> dict | None:
    """First exploration idea that has never run, or None if the next 500 all have.

    Ideas are numbered, and numbers whose idea repeats an earlier test are skipped, so the
    scan starts after the highest number used. Starting at the number of exploration rows
    instead falls further behind with every skipped number, until the whole window is old
    work and the bot wrongly reports that nothing is left."""
    seen = {_content(r["spec"]) for r in rows if "spec" in r}
    used = [n for n in (_explore_number(r["id"]) for r in rows) if n is not None]
    start = max(used) + 1 if used else 0
    for k in range(start, start + 500):
        spec = hypotheses.explore(k)
        if _content(spec) not in seen:
            return spec
    return None


def explore_paused() -> bool:
    """Owner switch: a committed hypotheses/EXPLORE_PAUSED file stops idea generation."""
    return (ROOT / "hypotheses" / "EXPLORE_PAUSED").exists()


def next_spec() -> dict | None:
    """Next queued test, else a NEW exploration idea (never one that already ran).
    Returns None when exploration has nothing new left, or is paused."""
    p = pending()
    if p:
        return p[0]
    if explore_paused():
        return None
    return next_explore(ledger())


PILOT = {"nulls": 9, "controls": 20, "extend_nulls": 0}
PILOT_MIN_LOWER = 0.2  # same as the family filter's report.MIN_POWER


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """Wilson score interval for k successes in n trials."""
    if n <= 0:
        return 0.0, 1.0
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * ((p * (1 - p) / n + z * z / (4 * n * n)) ** 0.5) / d
    return max(0.0, c - h), min(1.0, c + h)


def _run(spec: dict, workers, log) -> dict:
    """Exploration ideas get a cheap power pilot first; if genuine text couldn't stand out,
    the pilot result is recorded (as untestable) instead of spending a full test."""
    if spec["id"].startswith("explore."):
        pilot = evaluate.run(dict(spec, **PILOT), workers=workers, log=log)
        lower = None
        if pilot.get("power") is not None:
            n = PILOT["controls"]
            lower = wilson(round(pilot["power"] * n), n)[0]
        if lower is not None and lower < PILOT_MIN_LOWER:
            pilot["spec"] = spec
            pilot["spec_hash"] = evaluate._spec_hash(spec)
            pilot["pilot"] = True
            pilot["verdict"] = (f"UNTESTABLE: power pilot (20 genuine-text tests) found real text would not "
                                f"stand out (power {pilot['power']:.2f}, 95% lower bound {lower:.2f} < "
                                f"{PILOT_MIN_LOWER}); full test skipped")
            return pilot
    return evaluate.run(spec, workers=workers, log=log)


def calib_id(lang: str) -> str:
    return "calib.z408.homophonic" if lang == "en" else f"calib.{lang}.synthetic408"


def calibrated(lang: str = "en") -> bool:
    ok = False
    for r in ledger():
        if r["id"] == calib_id(lang) and _current(r):
            ok = r.get("verdict") == "CALIBRATION PASS"
    return ok


def _publish(current: dict | None = None) -> None:
    """Rewrite REPORT/ALERTS/STATUS. `current` is the test being started, if any."""
    from . import status
    rows = ledger()
    report.write(rows)
    status.write(rows, RESULTS / "STATUS.json", current=current)


def _skip(spec: dict, why: str) -> None:
    lang = evaluate.lang_of(spec)
    row = {"id": spec["id"], "spec_hash": evaluate._spec_hash(spec), "spec": spec, "lang": lang,
           "lm": lm.fingerprint(lang), "p": None, "power": None, "verdict": "SKIPPED: " + why,
           "finished": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    with LEDGER.open("a") as f:
        f.write(json.dumps(row) + "\n")


def _commit(msg: str) -> None:
    subprocess.run(["git", "add", "results"], cwd=ROOT, check=False)
    subprocess.run(["git", "commit", "-q", "-m", msg], cwd=ROOT, check=False)


def run(hours: float, *, workers: int | None = None, commit: bool = False, only: str | None = None,
        log=print) -> str:
    """Returns "idle" if it stopped because nothing is left to test, else "ok"."""
    deadline = time.time() + hours * 3600
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    started_any = False
    while time.time() < deadline:
        spec = next((s for s in pending() if s["id"] == only), None) if only else next_spec()
        if spec is None:
            if only:
                log(f"{only}: already done")
                return "ok"
            if explore_paused():
                log("exploration paused (hypotheses/EXPLORE_PAUSED exists); queue work or delete the file")
            log("nothing new to explore; stopping (queue more work)")
            return "idle"
        lang = evaluate.lang_of(spec)
        if not spec["id"].startswith("calib.") and not calibrated(lang):
            cid = calib_id(lang)
            if any(r["id"] == cid and _current(r) for r in ledger()):
                log(f"{cid} FAILED under the current model; skipping {spec['id']}")
                _skip(spec, f"calibration {cid} failed")
                continue
            log(f"calibration for {lm.LANG_NAMES[lang]} has not run yet; running it first")
            spec = next(s for s in hypotheses.builtin() if s["id"] == cid)
        if spec.get("invalid"):
            log(f"refusing {spec['id']}: {'; '.join(spec['invalid'])}")
            _skip(spec, "invalid spec: " + "; ".join(spec["invalid"]))
            _publish()
            continue
        if not only and started_any:
            from .status import estimate_seconds
            est = estimate_seconds(spec)
            left = deadline - time.time()
            # Don't start something that would run into the job's hard time limit; it will
            # be first in line next run. (Estimates are rough, hence the 1.5x margin.)
            if est == est and est * 1.5 > left and est * 1.5 < hours * 3600:
                log(f"{spec['id']} needs ~{est/60:.0f} min, only {left/60:.0f} min left; leaving it for the next run")
                return "ok"
        started_any = True
        log(f"[{time.strftime('%H:%M:%S')}] {spec['id']}: {spec['title']}")
        _publish(current=spec)  # lets the dashboard show what is running right now
        try:
            res = _run(spec, workers, log)
        except Exception as e:  # record failures too, so the loop doesn't retry them forever
            res = {"id": spec["id"], "spec_hash": evaluate._spec_hash(spec), "spec": spec,
                   "lang": evaluate.lang_of(spec), "lm": lm.fingerprint(evaluate.lang_of(spec)), "error": repr(e), "p": None, "power": None,
                   "verdict": "ERROR", "finished": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
        with LEDGER.open("a") as f:
            f.write(json.dumps(res) + "\n")
        _publish()
        log(f"   -> {res['verdict']}  p={res.get('p')}  power={res.get('power')}  "
            f"({res.get('seconds', '?')}s)")
        if res.get("top"):
            log(f"   best: {res['top'][0]['plaintext'][:70]}  [{res['top'][0]['order']}]")
        if commit:
            _commit(f"zbot: {spec['id']} -> {res['verdict'].split(':')[0]}")
        if only:
            return "ok"
    return "ok"
